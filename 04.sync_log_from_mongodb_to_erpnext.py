#!/usr/bin/env python3
"""
Sync attendance data from MongoDB to ERPNext Employee Checkin
"""

import requests
import json
import os
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
import logging
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the path to access local_config
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
import local_config as config
from manual_input_utils import prompt_date_range

# Configure logging - only log errors to file for better performance
log_dir = os.path.join(current_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.ERROR,  # Changed from INFO to ERROR for performance
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'sync_log_from_mongodb_to_erpnext.txt'), mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Separate logger for console with INFO level
console_logger = logging.getLogger(__name__ + '.console')
console_logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
console_logger.addHandler(console_handler)

# MongoDB connection settings - now loaded from config
MONGODB_HOST = getattr(config, 'MONGODB_HOST', "10.0.1.4")
MONGODB_PORT = getattr(config, 'MONGODB_PORT', 27017)
MONGODB_DB = getattr(config, 'MONGODB_DATABASE', "tiqn")
MONGODB_COLLECTION = getattr(config, 'MONGODB_ATTLOG_COLLECTION', "AttLog")
MONGODB_USER = getattr(config, 'MONGODB_USER', None)  # Optional
MONGODB_PASS = getattr(config, 'MONGODB_PASS', None)  # Optional

# ERPNext version detection
ERPNEXT_VERSION = getattr(config, 'ERPNEXT_VERSION', 14)

# Date sync configuration
# Defaults to last 7 days if not specified

# Performance settings
MAX_WORKERS = 200  # Maximum parallel workers (increased from 100)
BATCH_SIZE = 1000  # Batch size for MongoDB cursor
REQUEST_TIMEOUT = 10  # Request timeout in seconds

# Global session for connection pooling
session = None

# Pre-build ERPNext API URL (computed once)
ERPNEXT_API_URL = None

def get_session():
    """Get or create a global requests session with large connection pool"""
    global session
    if session is None:
        session = requests.Session()
        # Increase connection pool to match MAX_WORKERS
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=MAX_WORKERS,
            pool_maxsize=MAX_WORKERS,
            max_retries=2
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({
            'Authorization': "token " + config.ERPNEXT_API_KEY + ":" + config.ERPNEXT_API_SECRET,
            'Accept': 'application/json'
        })
    return session

def connect_to_mongodb():
    """Connect to MongoDB server"""
    try:
        client = MongoClient(
            host=MONGODB_HOST,
            port=MONGODB_PORT,
            # username=MONGODB_USER,
            # password=MONGODB_PASS,
            # authSource='admin'
        )

        # Test connection
        client.admin.command('ping')
        console_logger.info(f"Successfully connected to MongoDB at {MONGODB_HOST}")

        return client
    except Exception as e:
        console_logger.error(f"Failed to connect to MongoDB: {e}")
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

def map_machine_no_to_device_id(machine_no):
    """Map machineNo to device_id"""
    return f"Machine {machine_no}" if 1 <= machine_no <= 7 else None

def get_erpnext_api_url():
    """Get or build ERPNext API URL once"""
    global ERPNEXT_API_URL
    if ERPNEXT_API_URL is None:
        endpoint_app = "hrms" if ERPNEXT_VERSION > 13 else "erpnext"
        ERPNEXT_API_URL = f"{config.ERPNEXT_URL}/api/method/{endpoint_app}.hr.doctype.employee_checkin.employee_checkin.add_log_based_on_employee_field"
    return ERPNEXT_API_URL

def send_to_erpnext(employee_field_value, timestamp, device_id=None):
    """Send attendance to ERPNext - direct insert, no validation"""
    url = get_erpnext_api_url()

    data = {
        'employee_field_value': employee_field_value,
        'timestamp': timestamp.__str__(),
        'device_id': device_id
    }

    try:
        response = get_session().post(url, json=data, timeout=REQUEST_TIMEOUT)
        return response.status_code, json.loads(response._content)['message']['name'] if response.status_code == 200 else _safe_get_error_str(response)
    except Exception as e:
        return 500, str(e)

def _safe_get_error_str(res):
    """Extract error from response"""
    try:
        error_json = json.loads(res._content)
        return json.loads(error_json['exc'])[0] if 'exc' in error_json else json.dumps(error_json)
    except:
        return str(res.__dict__)

def process_record(record, user_id_ignored_set):
    """Process single record - optimized for maximum speed"""
    att_finger_id = record.get('attFingerId')
    timestamp = record.get('timestamp')

    # Fast validation with set lookup O(1)
    if not att_finger_id or not timestamp or str(att_finger_id) in user_id_ignored_set:
        return ('skipped', None)

    device_id = map_machine_no_to_device_id(record.get('machineNo', 0))
    status_code, response = send_to_erpnext(str(att_finger_id), timestamp, device_id)

    if status_code == 200:
        return ('processed', None)
    elif "already has a log" in str(response).lower():
        return ('skipped', None)
    else:
        # Return error with details
        error_detail = {
            'attFingerId': att_finger_id,
            'timestamp': timestamp,
            'machineNo': record.get('machineNo'),
            'device_id': device_id,
            'status_code': status_code,
            'error': str(response)
        }
        return ('error', error_detail)

def sync_attendance_data(date_range=None):
    """Main function to sync attendance data with maximum parallel processing

    Args:
        date_range (list): Optional [from_date, to_date] in YYYYMMDD format.
                          Defaults to last 7 days if not provided.
    """
    try:
        # Connect to MongoDB
        client = connect_to_mongodb()
        db = client[MONGODB_DB]
        collection = db[MONGODB_COLLECTION]

        # Use parameter date_range or default to empty (will use last 7 days)
        if date_range is None:
            date_range = []
        user_id_ignored = getattr(config, 'user_id_inorged', [])
        sync_only_machines_0 = getattr(config, 'sync_only_machines_0', True)

        # Convert user_id_ignored to set for O(1) lookup performance
        user_id_ignored_set = set(str(uid) for uid in user_id_ignored)

        # Create indexes (silently skip if exists)
        try:
            collection.create_index([("timestamp", -1), ("machineNo", 1)])
            collection.create_index([("attFingerId", 1)])
        except:
            pass

        # Build query
        if date_range and isinstance(date_range, list) and len(date_range) == 2:
            start_date_str, end_date_str = date_range
            start_date = datetime.strptime(start_date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
            end_date = datetime.strptime(end_date_str, "%Y%m%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

            query = {
                "timestamp": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }

            console_logger.info(f"Syncing date range: {start_date_str} to {end_date_str}")
            print(f"📅 Syncing date range: {start_date_str} to {end_date_str}")
        else:
            # Use last 7 days (current date and 6 days before)
            current_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = current_date - timedelta(days=6)  # 7 days total including today
            end_date = current_date.replace(hour=23, minute=59, second=59)

            query = {
                "timestamp": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }

            print(f"📅 Syncing: last 7 days")

        # Add machineNo filter if configured
        if sync_only_machines_0:
            query["machineNo"] = 0
            print(f"🔍 Filter: Only machineNo = 0")

        if user_id_ignored:
            print(f"🚫 Ignored user IDs: {user_id_ignored}")

        # Fetch all records with projection and batch processing
        projection = {"attFingerId": 1, "timestamp": 1, "machineNo": 1}
        cursor = collection.find(query, projection).batch_size(BATCH_SIZE)

        # Convert cursor to list for parallel processing
        records = list(cursor)
        console_logger.info(f"Found {len(records)} records to process")
        print(f"📊 Total records: {len(records)}")

        # Process all records in parallel with max workers
        total_processed = 0
        total_skipped = 0
        total_errors = 0

        print(f"🚀 Processing with {MAX_WORKERS} parallel workers...")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_record, record, user_id_ignored_set) for record in records]

            for future in as_completed(futures):
                status, error_detail = future.result()

                if status == 'processed':
                    total_processed += 1
                elif status == 'skipped':
                    total_skipped += 1
                else:  # error
                    total_errors += 1
                    # Log error details to file
                    if error_detail:
                        logger.error(
                            f"ERROR - attFingerId: {error_detail['attFingerId']}, "
                            f"timestamp: {error_detail['timestamp']}, "
                            f"machineNo: {error_detail['machineNo']}, "
                            f"device_id: {error_detail['device_id']}, "
                            f"status_code: {error_detail['status_code']}, "
                            f"error: {error_detail['error']}"
                        )

        # Close MongoDB connection
        client.close()

        # Close session when done
        global session
        if session:
            session.close()
            session = None

        console_logger.info(f"Sync completed: {total_processed} processed, {total_skipped} skipped, {total_errors} errors")

        return {
            "processed": total_processed,
            "skipped": total_skipped,
            "errors": total_errors,
            "total_records": total_processed + total_skipped + total_errors
        }

    except Exception as e:
        console_logger.error(f"Sync failed: {e}")
        logger.error(f"Sync failed: {e}")
        raise

def run_mongodb_sync():
    """Run MongoDB sync and return results (for integration with erpnext_sync_all.py)"""
    try:
        result = sync_attendance_data()
        return {
            "success": True,
            "message": f"MongoDB sync completed: {result['processed']} processed, {result['skipped']} skipped, {result['errors']} errors",
            "details": result
        }
    except Exception as e:
        logger.error(f"MongoDB sync failed: {e}")
        return {
            "success": False,
            "message": f"MongoDB sync failed: {str(e)}",
            "details": {"processed": 0, "skipped": 0, "errors": 1, "total_records": 0}
        }

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Sync attendance data from MongoDB to ERPNext')
    parser.add_argument('--manual', action='store_true', help='Manual mode - prompt for date range')
    args = parser.parse_args()

    date_range = None

    try:
        # Manual mode - prompt for date range
        if args.manual:
            date_range = prompt_date_range(
                prompt_message="Sync Attendance Data from MongoDB to ERPNext",
                allow_empty=True,
                default_days_back=7
            )
            if not date_range:
                print("Operation cancelled")
                return

        # Run sync
        result = sync_attendance_data(date_range)

        print(f"\n=== MongoDB to ERPNext Sync Results ===")
        print(f"Total records found: {result['total_records']}")
        print(f"Successfully processed: {result['processed']}")
        print(f"Skipped: {result['skipped']}")
        print(f"Errors: {result['errors']}")
        print("=== Sync Complete ===\n")

    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        print(f"ERROR: {e}")
        raise

if __name__ == "__main__":
    main()