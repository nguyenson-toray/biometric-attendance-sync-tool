#!/usr/bin/env python3
"""
Sync Overtime Registration from MongoDB to ERPNext

This script syncs overtime registration data from MongoDB to ERPNext's Overtime Registration doctype.
It groups OT records by requestNo and creates one Overtime Registration per request with multiple details.

MongoDB Collection: tiqn.OtRegister
ERPNext Doctypes:
  - Overtime Registration (parent)
  - Overtime Registration Detail (child table)

Field Mapping:
  MongoDB                    ->  ERPNext
  requestNo                  ->  Overtime Registration.name
  requestDate                ->  Overtime Registration.request_date
  empId                      ->  Overtime Registration Detail.employee
  otDate                     ->  Overtime Registration Detail.date
  otTimeBegin                ->  Overtime Registration Detail.begin_time
  otTimeEnd                  ->  Overtime Registration Detail.end_time

Deduplication Logic:
  - Records with same (otDate, empId, otTimeBegin, otTimeEnd) are considered duplicates
  - Only the record with highest _id (latest) is kept
  - This ensures only the most recent version of each OT entry is synced to ERPNext
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
from pymongo import MongoClient
import requests

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import local_config
from manual_input_utils import prompt_single_date

# Setup logging
log_dir = os.path.join(local_config.LOGS_DIRECTORY, 'ot_sync')
os.makedirs(log_dir, exist_ok=True)

# Create dedicated logger with explicit handlers (avoid basicConfig conflicts)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False  # Don't propagate to root logger

# Clear existing handlers to avoid duplicates when module is reloaded
logger.handlers.clear()

# Add file handler
file_handler = logging.FileHandler(os.path.join(log_dir, 'sync_ot.log'))
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Add console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)


class OTSyncFromMongoDB:
    """Sync Overtime Registration from MongoDB to ERPNext"""

    def __init__(self, start_date=None):
        """Initialize OT sync

        Args:
            start_date (str): Optional start date in YYYYMMDD format.
                            Defaults to today if not provided.
        """
        self.erpnext_url = local_config.ERPNEXT_URL
        self.api_key = local_config.ERPNEXT_API_KEY
        self.api_secret = local_config.ERPNEXT_API_SECRET

        # MongoDB configuration - use shared settings from local_config
        self.mongodb_uri = getattr(local_config, 'MONGODB_URI', f'mongodb://{getattr(local_config, "MONGODB_HOST", "10.0.1.4")}:{getattr(local_config, "MONGODB_PORT", 27017)}/')
        self.mongodb_db = getattr(local_config, 'MONGODB_DATABASE', 'tiqn')
        self.mongodb_collection = getattr(local_config, 'MONGODB_OT_COLLECTION', 'OtRegister')

        # Sync configuration - use parameter or default to today
        if start_date:
            self.start_date = start_date
        else:
            # Default to today
            self.start_date = datetime.now().strftime('%Y%m%d')
            # logger.info(f"No start_date provided, defaulting to today: {self.start_date}")

        self.last_id_file = os.path.join(log_dir, 'last_synced_ot_id.txt')

        # MongoDB client
        self.mongo_client = None
        self.db = None
        self.collection = None

    def connect_mongodb(self):
        """Connect to MongoDB"""
        try:
            self.mongo_client = MongoClient(self.mongodb_uri)
            self.db = self.mongo_client[self.mongodb_db]
            self.collection = self.db[self.mongodb_collection]

            # Test connection
            self.mongo_client.server_info()
            # logger.info(f"✓ Connected to MongoDB: {self.mongodb_db}.{self.mongodb_collection}")
            return True

        except Exception as e:
            logger.error(f"✗ Failed to connect to MongoDB: {str(e)}")
            return False

    def disconnect_mongodb(self):
        """Disconnect from MongoDB"""
        if self.mongo_client:
            self.mongo_client.close()
            # logger.info("✓ Disconnected from MongoDB")

    def get_last_synced_id(self):
        """Get last synced _id from file"""
        if os.path.exists(self.last_id_file):
            try:
                with open(self.last_id_file, 'r') as f:
                    last_id = int(f.read().strip())
                    # Log will be combined with fetch result
                    return last_id
            except Exception as e:
                logger.warning(f"Failed to read last synced ID: {e}")
                return None
        return None

    def save_last_synced_id(self, last_id):
        """Save last synced _id to file"""
        try:
            with open(self.last_id_file, 'w') as f:
                f.write(str(last_id))
            logger.debug(f"Saved last synced OT _id: {last_id}")
        except Exception as e:
            logger.error(f"Failed to save last synced ID: {e}")

    def fetch_ot_records_from_mongodb(self):
        """Fetch OT records from MongoDB

        Returns:
            list: List of OT records grouped by requestNo
        """
        try:
            # Convert start_date to datetime
            start_date_dt = datetime.strptime(self.start_date, '%Y%m%d')

            # Build query
            query = {
                'otDate': {'$gte': start_date_dt}
            }

            # Add _id filter if we have last synced ID
            last_id = self.get_last_synced_id()
            if last_id:
                query['_id'] = {'$gt': last_id}

            # Build filter description
            filter_info = f"otDate >= {self.start_date}"
            if last_id:
                filter_info += f" & _id > {last_id}"

            # Fetch records sorted by _id
            cursor = self.collection.find(query).sort('_id', 1)
            records = list(cursor)

            # Combined log: result + filters in one line
            if records:
                id_range = f" (ID range: {records[0]['_id']} -> {records[-1]['_id']})"
            else:
                id_range = ""

            logger.info(f"Fetched {len(records)} OT records from MongoDB: Filtering: {filter_info}{id_range}")

            return records

        except Exception as e:
            logger.error(f"✗ Failed to fetch OT records: {str(e)}")
            return []

    def deduplicate_records(self, records):
        """Remove duplicate OT records, keeping only the first one

        Duplicates are identified by matching: otDate, empId, otTimeBegin, otTimeEnd
        If multiple records match these 4 fields, keep only the one with lowest _id (first/oldest)

        Args:
            records (list): List of OT records from MongoDB

        Returns:
            list: Deduplicated list of records
        """
        # Dictionary to track first record for each unique combination
        unique_records = {}
        duplicate_count = 0

        for record in records:
            # Extract key fields for duplicate detection
            ot_date = record.get('otDate')
            emp_id = record.get('empId')
            ot_time_begin = record.get('otTimeBegin')
            ot_time_end = record.get('otTimeEnd')
            record_id = record.get('_id')

            # Skip if missing required fields
            if not all([ot_date, emp_id, ot_time_begin, ot_time_end]):
                continue

            # Create unique key from the 4 fields
            # Convert datetime to string for consistent hashing
            if isinstance(ot_date, datetime):
                ot_date_str = ot_date.strftime('%Y%m%d')
            elif isinstance(ot_date, dict) and '$date' in ot_date:
                ot_date_dt = datetime.fromisoformat(ot_date['$date'].replace('Z', '+00:00'))
                ot_date_str = ot_date_dt.strftime('%Y%m%d')
            else:
                ot_date_str = str(ot_date)

            unique_key = (ot_date_str, str(emp_id), str(ot_time_begin), str(ot_time_end))

            # Check if we already have a record with this key
            if unique_key in unique_records:
                # Keep the record with lower _id (first/oldest)
                existing_record = unique_records[unique_key]
                existing_id = existing_record.get('_id', float('inf'))

                if record_id < existing_id:
                    logger.debug(f"Duplicate found: Replacing _id={existing_id} with _id={record_id} (keeping first) for {unique_key}")
                    unique_records[unique_key] = record
                    duplicate_count += 1
                else:
                    logger.debug(f"Duplicate found: Keeping _id={existing_id} (first), skipping _id={record_id} for {unique_key}")
                    duplicate_count += 1
            else:
                unique_records[unique_key] = record

        deduplicated = list(unique_records.values())

        if duplicate_count > 0:
            logger.info(f"🔍 Deduplication: Found {duplicate_count} duplicates")
            logger.info(f"   Original records: {len(records)} → Unique records: {len(deduplicated)}")

        return deduplicated

    def group_records_by_request(self, records):
        """Group OT records by requestNo (after deduplication)

        Args:
            records (list): List of OT records from MongoDB

        Returns:
            dict: Dictionary with requestNo as key and list of records as value
        """
        # First, deduplicate records
        deduplicated_records = self.deduplicate_records(records)

        # Then group by requestNo
        grouped = defaultdict(list)

        for record in deduplicated_records:
            request_no = record.get('requestNo')
            if request_no:
                grouped[request_no].append(record)

        # logger.info(f"Grouped {len(deduplicated_records)} unique records into {len(grouped)} requests")
        return dict(grouped)

    def check_ot_registration_exists(self, request_no):
        """Check if Overtime Registration already exists in ERPNext

        Args:
            request_no (str): Request number to check

        Returns:
            bool: True if exists, False otherwise
        """
        try:
            url = f"{self.erpnext_url}/api/resource/Overtime Registration/{request_no}"

            response = requests.get(
                url,
                headers={
                    'Authorization': f'token {self.api_key}:{self.api_secret}',
                    'Content-Type': 'application/json'
                },
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            logger.debug(f"Check OT registration {request_no}: {str(e)}")
            return False

    def check_employee_ot_conflict(self, emp_id, ot_date, begin_time, end_time):
        """Check if employee already has OT for this date/time

        Args:
            emp_id (str): Employee ID
            ot_date (str): OT date in YYYY-MM-DD format
            begin_time (str): Begin time
            end_time (str): End time

        Returns:
            bool: True if conflict exists, False otherwise
        """
        try:
            # Query existing OT registrations for this employee and date
            url = f"{self.erpnext_url}/api/resource/Overtime Registration Detail"

            params = {
                'filters': json.dumps([
                    ['employee', '=', emp_id],
                    ['date', '=', ot_date]
                ]),
                'fields': json.dumps(['parent', 'employee', 'date', 'begin_time', 'end_time'])
            }

            response = requests.get(
                url,
                params=params,
                headers={
                    'Authorization': f'token {self.api_key}:{self.api_secret}',
                    'Content-Type': 'application/json'
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                existing_records = data.get('data', [])

                # Check if there's a time overlap
                for existing in existing_records:
                    # If exact same time range, it's a conflict
                    if (existing.get('begin_time') == begin_time and
                        existing.get('end_time') == end_time):
                        return True

                return False

            return False

        except Exception as e:
            logger.debug(f"Check OT conflict for employee {emp_id}: {str(e)}")
            return False

    def create_ot_registration(self, request_no, records):
        """Create Overtime Registration in ERPNext

        Args:
            request_no (str): Request number (will be used as name)
            records (list): List of OT records for this request

        Returns:
            dict: Result with success status and message
        """
        try:
            # Check if already exists
            if self.check_ot_registration_exists(request_no):
                logger.info(f"  ⏭  {request_no}: Already exists, skipping")
                return {
                    'success': True,
                    'skipped': True,
                    'message': 'Already exists',
                    'skipped_employees': []
                }

            # Get request date from first record
            first_record = records[0]
            request_date_raw = first_record.get('requestDate')

            # Parse request date
            if isinstance(request_date_raw, dict) and '$date' in request_date_raw:
                request_date_dt = datetime.fromisoformat(request_date_raw['$date'].replace('Z', '+00:00'))
            elif isinstance(request_date_raw, datetime):
                request_date_dt = request_date_raw
            else:
                request_date_dt = datetime.now()

            request_date = request_date_dt.strftime('%Y-%m-%d')
            request_no = str(request_no)
            # Prepare child records (Overtime Registration Detail)
            ot_employees = []
            skipped_employees = []  # Track skipped employees due to conflicts

            for record in records:
                # Parse otDate
                ot_date_raw = record.get('otDate')
                if isinstance(ot_date_raw, dict) and '$date' in ot_date_raw:
                    ot_date_dt = datetime.fromisoformat(ot_date_raw['$date'].replace('Z', '+00:00'))
                elif isinstance(ot_date_raw, datetime):
                    ot_date_dt = ot_date_raw
                else:
                    continue  # Skip if no valid date

                ot_date = ot_date_dt.strftime('%Y-%m-%d')

                # Get times
                begin_time = record.get('otTimeBegin', '17:00')
                end_time = record.get('otTimeEnd', '19:00')

                # Ensure time format is HH:MM:SS
                if len(begin_time) == 5:  # HH:MM
                    begin_time += ':00'
                if len(end_time) == 5:  # HH:MM
                    end_time += ':00'

                # Get employee ID
                emp_id = record.get('empId')
                if not emp_id:
                    continue  # Skip if no employee ID

                # Check if employee already has OT for this date/time
                if self.check_employee_ot_conflict(emp_id, ot_date, begin_time, end_time):
                    logger.debug(f"    Skipping employee {emp_id} - OT conflict on {ot_date} {begin_time}-{end_time}")
                    skipped_employees.append({
                        '_id': record.get('_id'),
                        'empId': emp_id,
                        'otDate': ot_date,
                        'otTimeBegin': begin_time,
                        'otTimeEnd': end_time,
                        'reason': 'OT already exists for this employee on this date/time'
                    })
                    continue

                ot_employees.append({
                    'employee': emp_id,
                    'date': ot_date,
                    'begin_time': begin_time,
                    'end_time': end_time
                })

            # If all employees were skipped
            if not ot_employees and skipped_employees:
                logger.warning(f"  ⚠ {request_no}: All {len(skipped_employees)} employee(s) have OT conflicts - request not created")
                return {
                    'success': True,
                    'skipped': True,
                    'message': f'All {len(skipped_employees)} employees have existing OT',
                    'skipped_employees': skipped_employees
                }

            # If no valid employees at all
            if not ot_employees:
                logger.warning(f"  ✗ {request_no}: No valid OT employee records")
                return {
                    'success': False,
                    'message': 'No valid employee records',
                    'skipped_employees': []
                }

            # Prepare Overtime Registration document
            doc = {
                'doctype': 'Overtime Registration',
                'name': request_no,
                'reason_general': f'Sync from MongoDB: Request number: {request_no}',
                'naming_series': 'OTR-.YY..MM..DD.-.####.',
                'request_date': request_date,
                'ot_employees': ot_employees
            }

            # Create document in ERPNext
            url = f"{self.erpnext_url}/api/resource/Overtime Registration"

            response = requests.post(
                url,
                headers={
                    'Authorization': f'token {self.api_key}:{self.api_secret}',
                    'Content-Type': 'application/json'
                },
                json=doc,
                timeout=30
            )

            if response.status_code in [200, 201]:
                if skipped_employees:
                    logger.info(f"  ✓ {request_no}: Created with {len(ot_employees)} employee(s), skipped {len(skipped_employees)} due to conflicts")
                else:
                    logger.info(f"  ✓ {request_no}: Created with {len(ot_employees)} employee(s)")

                return {
                    'success': True,
                    'skipped': False,
                    'message': f'Created with {len(ot_employees)} employees' + (f', skipped {len(skipped_employees)}' if skipped_employees else ''),
                    'skipped_employees': skipped_employees
                }
            else:
                error_msg = response.text
                logger.error(f"  ✗ {request_no}: Failed - {error_msg}")
                return {
                    'success': False,
                    'message': f'ERPNext error: {error_msg}',
                    'skipped_employees': skipped_employees
                }

        except Exception as e:
            logger.error(f"  ✗ {request_no}: Error - {str(e)}")
            return {
                'success': False,
                'message': f'Exception: {str(e)}',
                'skipped_employees': []
            }

    def sync_ot_to_erpnext(self):
        """Main sync function

        Returns:
            dict: Sync result summary
        """
        # Removed header log - will be combined with fetch result

        start_time = datetime.now()

        # Connect to MongoDB
        if not self.connect_mongodb():
            return {
                'success': False,
                'message': 'Failed to connect to MongoDB',
                'total_records': 0,
                'total_requests': 0,
                'created': 0,
                'skipped': 0,
                'skipped_exists': 0,
                'skipped_conflicts': 0,
                'failed': 0
            }

        try:
            # Fetch OT records
            records = self.fetch_ot_records_from_mongodb()

            if not records:
                # Already logged "Fetched 0 OT records" above
                return {
                    'success': True,
                    'message': 'No new records',
                    'total_records': 0,
                    'total_requests': 0,
                    'created': 0,
                    'skipped': 0,
                    'skipped_exists': 0,
                    'skipped_conflicts': 0,
                    'failed': 0
                }

            # Group by requestNo
            grouped_requests = self.group_records_by_request(records)

            # Sync each request
            created_count = 0
            skipped_exists_count = 0  # Already exists in ERPNext (entire request)
            skipped_conflict_count = 0  # All employees have conflicts (entire request)
            failed_count = 0
            total_skipped_employees = 0  # Total individual employee records skipped

            # Track skipped details
            skipped_exists_list = []
            skipped_conflict_list = []  # Entire requests skipped due to all employees having conflicts
            skipped_employee_records = []  # Individual employee records skipped
            failed_list = []

            logger.info(f"\nSyncing {len(grouped_requests)} OT requests to ERPNext...")

            for i, (request_no, request_records) in enumerate(grouped_requests.items(), 1):
                logger.info(f"[{i}/{len(grouped_requests)}] Processing {request_no} ({len(request_records)} employees)...")

                result = self.create_ot_registration(request_no, request_records)

                # Track skipped employees from this request
                skipped_employees = result.get('skipped_employees', [])
                if skipped_employees:
                    total_skipped_employees += len(skipped_employees)
                    for emp in skipped_employees:
                        skipped_employee_records.append({
                            'request_no': request_no,
                            **emp
                        })

                if result['success']:
                    if result.get('skipped'):
                        # Distinguish between different skip reasons
                        if 'Already exists' in result.get('message', ''):
                            skipped_exists_count += 1
                            skipped_exists_list.append({
                                'request_no': request_no,
                                'employees_count': len(request_records),
                                'reason': result.get('message')
                            })
                        elif 'All' in result.get('message', '') and 'employees have existing OT' in result.get('message', ''):
                            # All employees in this request have conflicts
                            skipped_conflict_count += 1
                            skipped_conflict_list.append({
                                'request_no': request_no,
                                'employees_count': len(request_records),
                                'employees': skipped_employees,
                                'reason': result.get('message')
                            })
                        else:
                            skipped_exists_count += 1  # Default to exists
                            skipped_exists_list.append({
                                'request_no': request_no,
                                'employees_count': len(request_records),
                                'reason': result.get('message')
                            })
                    else:
                        # Request was created (maybe with some employees skipped)
                        created_count += 1
                else:
                    failed_count += 1
                    failed_list.append({
                        'request_no': request_no,
                        'employees_count': len(request_records),
                        'reason': result.get('message')
                    })

            # Save last synced ID
            if records:
                last_id = max(r['_id'] for r in records)
                self.save_last_synced_id(last_id)

            # Summary
            execution_time = (datetime.now() - start_time).total_seconds()
            total_skipped_requests = skipped_exists_count + skipped_conflict_count

            logger.info("\n" + "=" * 80)
            logger.info("OT SYNC COMPLETED")
            logger.info(f"Total records: {len(records)}")
            logger.info(f"Total requests: {len(grouped_requests)}")
            logger.info(f"Created: {created_count}")
            logger.info(f"Skipped requests (entire): {total_skipped_requests}")
            logger.info(f"  - Already exists: {skipped_exists_count}")
            logger.info(f"  - All employees have conflicts: {skipped_conflict_count}")
            logger.info(f"Skipped employee records (individual): {total_skipped_employees}")
            logger.info(f"Failed: {failed_count}")
            logger.info(f"Execution time: {execution_time:.2f}s")

            # Detailed logging for skipped/failed items
            if skipped_exists_list:
                logger.info("\n" + "-" * 80)
                logger.info(f"SKIPPED REQUESTS - ALREADY EXISTS ({len(skipped_exists_list)} requests):")
                for item in skipped_exists_list:
                    logger.info(f"  • {item['request_no']} - {item['employees_count']} employee(s) - {item['reason']}")

            if skipped_conflict_list:
                logger.info("\n" + "-" * 80)
                logger.info(f"SKIPPED REQUESTS - ALL EMPLOYEES HAVE CONFLICTS ({len(skipped_conflict_list)} requests):")
                for item in skipped_conflict_list:
                    logger.info(f"  • Request: {item['request_no']} - {item['employees_count']} employee(s)")
                    logger.info(f"    Reason: {item['reason']}")
                    logger.info(f"    Employees:")
                    for emp in item['employees']:
                        logger.info(f"      - _id: {emp['_id']}, empId: {emp['empId']}, Date: {emp['otDate']}, Time: {emp['otTimeBegin']} - {emp['otTimeEnd']}")

            if skipped_employee_records:
                logger.info("\n" + "-" * 80)
                logger.info(f"SKIPPED EMPLOYEE RECORDS - OT CONFLICTS ({total_skipped_employees} records):")
                # Group by request for better readability
                by_request = {}
                for emp in skipped_employee_records:
                    req_no = emp['request_no']
                    if req_no not in by_request:
                        by_request[req_no] = []
                    by_request[req_no].append(emp)

                for req_no, emps in by_request.items():
                    logger.info(f"  • Request: {req_no} - {len(emps)} employee(s) skipped:")
                    for emp in emps:
                        logger.info(f"      - _id: {emp['_id']}, empId: {emp['empId']}, Date: {emp['otDate']}, Time: {emp['otTimeBegin']} - {emp['otTimeEnd']}")
                        logger.info(f"        Reason: {emp['reason']}")

            if failed_list:
                logger.info("\n" + "-" * 80)
                logger.info(f"FAILED REQUESTS ({len(failed_list)} requests):")
                for item in failed_list:
                    logger.info(f"  • {item['request_no']} - {item['employees_count']} employee(s) - {item['reason']}")

            logger.info("=" * 80)

            return {
                'success': True,
                'message': 'Sync completed',
                'total_records': len(records),
                'total_requests': len(grouped_requests),
                'created': created_count,
                'skipped_requests': total_skipped_requests,
                'skipped_exists': skipped_exists_count,
                'skipped_conflicts': skipped_conflict_count,
                'skipped_employees': total_skipped_employees,
                'failed': failed_count,
                'execution_time': execution_time,
                'skipped_exists_details': skipped_exists_list,
                'skipped_conflict_details': skipped_conflict_list,
                'skipped_employee_details': skipped_employee_records,
                'failed_details': failed_list
            }

        except Exception as e:
            logger.error(f"✗ Sync failed: {str(e)}")
            return {
                'success': False,
                'message': f'Sync error: {str(e)}',
                'total_records': 0,
                'total_requests': 0,
                'created': 0,
                'skipped': 0,
                'skipped_exists': 0,
                'skipped_conflicts': 0,
                'failed': 0
            }

        finally:
            self.disconnect_mongodb()


def main():
    """Main function for standalone execution"""
    parser = argparse.ArgumentParser(description='Sync Overtime Registration from MongoDB to ERPNext')
    parser.add_argument('--manual', action='store_true', help='Manual mode - prompt for start date')
    args = parser.parse_args()

    start_date = None

    try:
        # Manual mode - prompt for start date
        if args.manual:
            date_str = prompt_single_date(
                prompt_message="Sync OT from MongoDB to ERPNext - Enter Start Date",
                allow_today=True
            )
            if not date_str:
                print("Operation cancelled")
                return
            start_date = date_str

        # Create syncer and run sync
        syncer = OTSyncFromMongoDB(start_date=start_date)
        result = syncer.sync_ot_to_erpnext()

        if result['success']:
            logger.info("✓ OT sync completed successfully")
            sys.exit(0)
        else:
            logger.error(f"✗ OT sync failed: {result['message']}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"✗ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
