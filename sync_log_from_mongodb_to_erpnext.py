#!/usr/bin/env python3
"""
Sync attendance data from MongoDB to ERPNext Employee Checkin
"""

import requests
import json
from pymongo import MongoClient
from datetime import datetime, timezone
import logging
import sys

# Add the path to access local_config
sys.path.append('/home/sonnt/frappe-bench/apps/biometric-attendance-sync-tool')
import local_config as config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection settings
MONGODB_HOST = "10.0.1.4"
MONGODB_PORT = 27017
MONGODB_DB = "tiqn"
MONGODB_COLLECTION = "AttLog"
MONGODB_USER = "DB\administrator"
MONGODB_PASS = "itT0ray$"

# ERPNext version detection
ERPNEXT_VERSION = getattr(config, 'ERPNEXT_VERSION', 14)

# Date sync configuration - now loaded from local_config
# Use config.sync_log_from_mongodb_to_erpnext_date_range

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
        logger.info(f"Successfully connected to MongoDB at {MONGODB_HOST}")

        return client
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

def send_to_erpnext(employee_field_value, timestamp, device_id=None):
    """
    Send attendance data to ERPNext using the same API as the reference script
    """
    endpoint_app = "hrms" if ERPNEXT_VERSION > 13 else "erpnext"
    url = f"{config.ERPNEXT_URL}/api/method/{endpoint_app}.hr.doctype.employee_checkin.employee_checkin.add_log_based_on_employee_field"

    headers = {
        'Authorization': "token " + config.ERPNEXT_API_KEY + ":" + config.ERPNEXT_API_SECRET,
        'Accept': 'application/json'
    }

    data = {
        'employee_field_value': employee_field_value,
        'timestamp': timestamp.__str__(),
        'device_id': device_id,
        'log_type': None,  # Let ERPNext auto-determine
        'latitude': None,
        'longitude': None
    }

    try:
        response = requests.request("POST", url, headers=headers, json=data)
        if response.status_code == 200:
            result = json.loads(response._content)['message']['name']
            return 200, result
        else:
            error_str = _safe_get_error_str(response)
            return response.status_code, error_str
    except Exception as e:
        logger.error(f"Exception during ERPNext API call: {e}")
        return 500, str(e)

def _safe_get_error_str(res):
    """Extract error message from response"""
    try:
        error_json = json.loads(res._content)
        if 'exc' in error_json:
            error_str = json.loads(error_json['exc'])[0]
        else:
            error_str = json.dumps(error_json)
    except:
        error_str = str(res.__dict__)
    return error_str

def sync_attendance_data():
    """Main function to sync attendance data"""
    try:
        # Connect to MongoDB
        client = connect_to_mongodb()
        db = client[MONGODB_DB]
        collection = db[MONGODB_COLLECTION]

        # Get date range from config
        date_range = getattr(config, 'sync_log_from_mongodb_to_erpnext_date_range', [])

        # Determine date range based on configuration
        if date_range and isinstance(date_range, list) and len(date_range) == 2:
            # Use specified date range
            start_date_str, end_date_str = date_range
            start_date = datetime.strptime(start_date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
            end_date = datetime.strptime(end_date_str, "%Y%m%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

            query = {
                "timestamp": {
                    "$gte": start_date,
                    "$lte": end_date
                },
                "machineNo": 0
            }

            logger.info(f"Querying MongoDB for records from {start_date_str} to {end_date_str}")
            print(f"📅 Syncing date range: {start_date_str} to {end_date_str}")
        else:
            # Use current date only
            current_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = current_date.replace(hour=23, minute=59, second=59)

            query = {
                "timestamp": {
                    "$gte": current_date,
                    "$lte": end_date
                },
                "machineNo": 0
            }

            current_date_str = current_date.strftime("%Y%m%d")
            logger.info(f"Querying MongoDB for records from {current_date_str} (current date)")
            print(f"📅 Syncing current date: {current_date_str}")

        records = list(collection.find(query))
        logger.info(f"Found {len(records)} records to process")

        processed = 0
        skipped = 0
        errors = 0

        # Process records using ERPNext API
        for record in records:
            try:
                att_finger_id = record.get('attFingerId')
                timestamp = record.get('timestamp')
                machine_no = record.get('machineNo', 0)

                if not att_finger_id or not timestamp:
                    logger.warning(f"Skipping record with missing data: {record}")
                    skipped += 1
                    continue

                # Send to ERPNext using attendance_device_id as employee_field_value
                status_code, message = send_to_erpnext(
                    employee_field_value=str(att_finger_id),
                    timestamp=timestamp,
                    device_id=str(machine_no)
                )

                if status_code == 200:
                    logger.info(f"Success: Created Employee Checkin {message} for attFingerId {att_finger_id}")
                    processed += 1
                else:
                    logger.error(f"Failed: attFingerId {att_finger_id}, Status {status_code}, Error: {message}")

                    # Check for specific error types
                    if "No Employee found for the given employee field value" in message:
                        logger.warning(f"Employee not found for attFingerId: {att_finger_id}")
                        skipped += 1
                    elif "This employee already has a log with the same timestamp" in message:
                        logger.info(f"Duplicate entry skipped for attFingerId {att_finger_id} at {timestamp}")
                        skipped += 1
                    else:
                        errors += 1

            except Exception as e:
                logger.error(f"Error processing record {record}: {e}")
                errors += 1

        # Close MongoDB connection
        client.close()

        logger.info(f"Sync completed: {processed} processed, {skipped} skipped, {errors} errors")

        return {
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
            "total_records": len(records)
        }

    except Exception as e:
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
    try:
        # Run sync
        result = sync_attendance_data()

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