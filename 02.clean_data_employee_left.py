#!/usr/bin/env python3

"""
Clean Data Employee Left - Cleanup tool for departed employees

This tool performs comprehensive cleanup for employees with status "Left":
1. Date filtering: Only process employees who left within the last N days (CLEAR_LEFT_USER_TEMPLATES_RELIEVING_LAST_DAYS)
   - Algorithm: cutoff_date <= relieving_date <= today
   - Avoids daily operations on employees who left a long time ago
2. Delete fingerprint records from ERPNext (if ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_ERPNEXT = True)
3. Clear fingerprint templates from devices (keep user_id for attendance history)
   - Method: Delete user completely, then recreate with same info but NO templates
   - Step 1: conn.delete_user(user_id=attendance_device_id)
   - Step 2: conn.set_user(uid, name, privilege, password, group_id, user_id, card)
   - This ensures ALL template data is removed from device memory
   - User_id is preserved for attendance history tracking

Usage:
    python3 clean_data_employee_left.py [--dry-run]
"""

import datetime
import logging
import os
import sys
import socket
import time
import base64
import json
import threading
from zk import ZK
from zk.base import Finger

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import local_config
from erpnext_api_client import ERPNextAPIClient

# Setup logging to clean_data_employee_left folder
clean_logs_dir = os.path.join(local_config.LOGS_DIRECTORY, 'clean_data_employee_left')
os.makedirs(clean_logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(clean_logs_dir, 'clean_left_employees.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CleanDataEmployeeLeft:
    # Class-level lock for thread-safe file operations
    _file_lock = threading.Lock()

    def __init__(self):
        self.base_url = local_config.ERPNEXT_URL
        self.api_key = local_config.ERPNEXT_API_KEY
        self.api_secret = local_config.ERPNEXT_API_SECRET
        self.devices = local_config.devices
        self.max_workers = min(len(self.devices), 10)

        self.api_client = ERPNextAPIClient(self.base_url, self.api_key, self.api_secret)
        self.setup_logging()
        
    def setup_logging(self):
        # Ensure clean logs directory exists
        os.makedirs(clean_logs_dir, exist_ok=True)
        
    def test_erpnext_connection(self):
        """Test ERPNext API connection"""
        return self.api_client.test_connection()

    @staticmethod
    def shorten_name(full_name, max_length=24):
        """Shorten employee name if it exceeds max length and convert Vietnamese to non-accented"""
        from unidecode import unidecode
        if not full_name:
            return full_name
        text_processed = unidecode(full_name)  # Convert to non-accented text
        # Remove extra spaces
        text_processed = ' '.join(text_processed.split()).strip()

        if len(text_processed) > max_length:
            parts = text_processed.split()
            if len(parts) > 1:
                # Take first letter of all parts except the last one
                initials = "".join(part[0].upper() for part in parts[:-1])
                last_part = parts[-1]
                return f"{initials} {last_part}"
            else:
                # If only one word and too long, truncate it
                return text_processed[:max_length]
        else:
            return text_processed

    def load_processed_employees(self):
        """Load list of already processed employees from tracking file

        Returns:
            dict: Dictionary with structure:
                {
                    "cleared": {
                        "employee_id": {
                            "employee": "TIQN-0001",
                            "name": "Employee Name",
                            "attendance_device_id": "123",
                            "processed_date": "2025-10-15",
                            "action": "cleared_templates"
                        }
                    },
                    "deleted": {
                        "employee_id": {...}
                    }
                }
        """
        processed_file = getattr(local_config, 'PROCESSED_LEFT_EMPLOYEES_FILE', 'logs/clean_data_employee_left/processed_left_employees.json')

        # Convert to absolute path to avoid issues with relative paths in threads
        if not os.path.isabs(processed_file):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            processed_file = os.path.join(base_dir, processed_file)

        if not os.path.exists(processed_file):
            return {"cleared": {}, "deleted": {}}

        # Retry logic for file reading (handle concurrent access)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(processed_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                    # Handle empty file
                    if not content:
                        logger.warning(f"Processed employees file is empty, initializing...")
                        return {"cleared": {}, "deleted": {}}

                    data = json.loads(content)

                    # Ensure structure
                    if "cleared" not in data:
                        data["cleared"] = {}
                    if "deleted" not in data:
                        data["deleted"] = {}
                    return data

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(0.1)  # Wait before retry
                else:
                    logger.error(f"Failed to load after {max_retries} attempts, returning empty data")
                    return {"cleared": {}, "deleted": {}}

            except Exception as e:
                logger.error(f"Error loading processed employees file: {str(e)}")
                return {"cleared": {}, "deleted": {}}

        return {"cleared": {}, "deleted": {}}

    def save_processed_employees(self, processed_data):
        """Save processed employees to tracking file (with atomic write)

        Args:
            processed_data (dict): Dictionary with "cleared" and "deleted" keys
        """
        processed_file = getattr(local_config, 'PROCESSED_LEFT_EMPLOYEES_FILE', 'logs/clean_data_employee_left/processed_left_employees.json')

        # Convert to absolute path to avoid issues with relative paths in threads
        if not os.path.isabs(processed_file):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            processed_file = os.path.join(base_dir, processed_file)

        temp_file = processed_file + '.tmp'

        try:
            # Ensure logs directory exists
            log_dir = os.path.dirname(processed_file)
            os.makedirs(log_dir, exist_ok=True)

            # Write to temporary file first (atomic write)
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)

            # Atomic rename (replace old file)
            os.replace(temp_file, processed_file)

            logger.debug(f"Saved processed employees to {processed_file}")

        except Exception as e:
            logger.error(f"Error saving processed employees file: {str(e)}")
            # Clean up temp file if it exists
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    def add_processed_employee(self, employee_data, action_type):
        """Add an employee to the processed tracking file

        Args:
            employee_data (dict): Employee data with keys: employee_id, employee, employee_name, attendance_device_id
            action_type (str): "cleared" or "deleted"
        """
        processed_data = self.load_processed_employees()

        employee_id = employee_data["employee_id"]

        record = {
            "employee": employee_data["employee"],
            "name": employee_data.get("employee_name", ""),
            "attendance_device_id": employee_data["attendance_device_id"],
            "processed_date": datetime.datetime.now().strftime('%Y-%m-%d'),
            "action": f"{action_type}_templates" if action_type == "cleared" else "permanently_deleted"
        }

        if action_type == "cleared":
            processed_data["cleared"][employee_id] = record
        elif action_type == "deleted":
            processed_data["deleted"][employee_id] = record

        self.save_processed_employees(processed_data)
        logger.debug(f"  📝 Logged {employee_data['employee']} to processed tracking file ({action_type})")

    def is_employee_processed(self, employee_id):
        """Check if an employee has already been processed

        Args:
            employee_id (str): Employee ID to check

        Returns:
            tuple: (is_processed: bool, action_type: str or None)
        """
        processed_data = self.load_processed_employees()

        if employee_id in processed_data["cleared"]:
            return True, "cleared"
        elif employee_id in processed_data["deleted"]:
            return True, "deleted"

        return False, None
    def get_left_employees_for_cleanup(self):
        """Get employees with status 'Left' ready for cleanup

        Priority-based algorithm (checked in order):
        1. FIRST: Permanently delete if left > ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS (e.g., >1400 days)
        2. SECOND: Clear templates if today >= relieving_date + CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS (e.g., >=7 days after leaving)
        3. SKIP employees already processed (from tracking file)

        Returns employees ready for processing (excluding already processed)
        """
        # Get all left employees from ERPNext (with basic date validation)
        all_left_employees = self.api_client.get_left_employees_with_device_id()

        # Load processed employees to skip
        processed_data = self.load_processed_employees()
        processed_employee_ids = set(processed_data["cleared"].keys()) | set(processed_data["deleted"].keys())

        # Get configuration
        delay_days = getattr(local_config, 'CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS', 7)
        delete_after_days = getattr(local_config, 'ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS', 0)

        # Filter: Get employees ready for processing
        from datetime import datetime, timedelta
        today = datetime.now().date()

        ready_employees = []
        skipped_employees = []
        already_processed_count = 0

        logger.info(f"Filtering employees (priority order):")
        logger.info(f"  1. Permanently delete: left > {delete_after_days} days ago" if delete_after_days > 0 else "  1. Permanent deletion: DISABLED")
        logger.info(f"  2. Clear templates: today >= relieving_date + {delay_days} days")
        logger.info(f"  3. Skip already processed employees from tracking file")

        for emp in all_left_employees:
            employee_id = emp.get('employee_id')
            relieving_date = emp.get('relieving_date')

            # Skip employees already processed
            if employee_id in processed_employee_ids:
                already_processed_count += 1
                continue

            if not relieving_date:
                continue

            try:
                # Parse relieving_date
                if isinstance(relieving_date, str):
                    relieving_dt = datetime.strptime(relieving_date, '%Y-%m-%d').date()
                else:
                    relieving_dt = relieving_date

                days_since_relieving = (today - relieving_dt).days

                # PRIORITY 1: Check permanent deletion FIRST
                should_permanently_delete = (delete_after_days > 0 and days_since_relieving > delete_after_days)

                # PRIORITY 2: Check clear templates (only if not permanently deleting)
                should_clear_templates = (not should_permanently_delete and days_since_relieving >= delay_days)

                if should_permanently_delete:
                    logger.info(f"  🗑️ {emp['employee']}: Ready to PERMANENTLY DELETE (left {days_since_relieving} days ago, >{delete_after_days} days)")
                    ready_employees.append(emp)
                elif should_clear_templates:
                    logger.info(f"  ✓ {emp['employee']}: Ready to CLEAR templates (left {days_since_relieving} days ago, >={delay_days} days)")
                    ready_employees.append(emp)
                else:
                    if days_since_relieving < delay_days:
                        # bypass logging for waiting employees to reduce noise 
                        # logger.info(f"  ⏳ {emp['employee']}: Waiting (left {days_since_relieving} days ago, need {delay_days} days)")
                        pass
                    else:
                        logger.info(f"  ⏭ {emp['employee']}: Skipped (left {days_since_relieving} days ago)")
                    skipped_employees.append(emp)

            except (ValueError, TypeError) as e:
                logger.warning(f"  ✗ {emp['employee']}: Invalid date format - {str(e)}")
                continue

        logger.info(f"Filter results: {len(ready_employees)} ready to process, {already_processed_count} already processed (skipped), {len(skipped_employees)} not ready yet")
        return ready_employees
    
    def delete_employee_fingerprints_from_erpnext(self, employee_id):
        """Delete fingerprint records from ERPNext for an employee"""
        return self.api_client.delete_employee_fingerprints(employee_id)
    
    def check_device_connection(self, device_config):
        """Check if device is reachable"""
        try:
            ip_address = device_config['ip']
            port = 4370
            timeout = 3
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip_address, port))
            sock.close()
            
            return result == 0
            
        except Exception as e:
            logger.error(f"Error checking device connection {device_config['device_id']}: {str(e)}")
            return False
    
    def clear_employee_templates_from_device(self, device_config, left_employees):
        """Clear fingerprint templates for Left employees from single device

        Two modes based on time since relieving_date:
        1. Recent left (within RELIEVING_LAST_DAYS): Delete then recreate without templates
        2. Long-term left (> ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS): Permanently delete user

        - conn.delete_user(user_id) - Removes user and ALL associated data
        - conn.set_user(...) - Recreates user with same info but NO fingerprints (recent only)
        - This ensures complete cleanup while managing device memory efficiently

        Runs silently - no logging (parent function handles logging)
        NOTE: Does NOT write to tracking file - parent function handles that after all devices processed
        """
        device_id = device_config['device_id']
        ip_address = device_config['ip']

        try:
            # Check connection
            if not self.check_device_connection(device_config):
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": False,
                    "cleared_count": 0,
                    "deleted_count": 0,
                    "skipped_count": 0,
                    "total_count": len(left_employees),
                    "message": f"Device unreachable",
                    "action_type": None  # Add action type to result
                }

            # Connect to device
            zk = ZK(ip_address, port=4370, timeout=10, force_udp=True, ommit_ping=True)
            conn = zk.connect()

            if not conn:
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": False,
                    "cleared_count": 0,
                    "deleted_count": 0,
                    "skipped_count": 0,
                    "total_count": len(left_employees),
                    "message": f"Connection failed",
                    "action_type": None
                }

            try:
                # Disable device (silently)
                conn.disable_device()

                # Get configuration
                delete_after_days = getattr(local_config, 'ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS', 0)

                from datetime import datetime, timedelta
                today = datetime.now().date()

                cleared_count = 0  # Users recreated without templates
                deleted_count = 0  # Users permanently deleted
                skipped_count = 0  # Already processed employees
                failed_employees = []
                cleared_users = []
                deleted_users = []
                skipped_users = []
                action_type = None  # Track what action was determined

                # Get existing users on device
                existing_users = conn.get_users()
                existing_user_ids = {str(u.user_id): u for u in existing_users}

                # Process Left employees (already filtered to exclude processed employees)
                for i, employee_data in enumerate(left_employees, 1):
                    try:
                        employee_id = employee_data["employee_id"]
                        attendance_device_id = str(employee_data["attendance_device_id"])
                        employee_name = self.shorten_name(employee_data.get("employee_name", employee_data["employee"]),24)
                        relieving_date = employee_data.get('relieving_date')

                        # Check if user exists on device
                        if attendance_device_id in existing_user_ids:
                            user = existing_user_ids[attendance_device_id]

                            # PRIORITY 1: Determine if should permanently delete (checked FIRST)
                            should_permanently_delete = False
                            days_since_relieving = None
                            if delete_after_days > 0 and relieving_date:
                                try:
                                    if isinstance(relieving_date, str):
                                        relieving_dt = datetime.strptime(relieving_date, '%Y-%m-%d').date()
                                    else:
                                        relieving_dt = relieving_date

                                    days_since_relieving = (today - relieving_dt).days
                                    should_permanently_delete = days_since_relieving > delete_after_days
                                except:
                                    pass

                            if should_permanently_delete:
                                # PRIORITY 1: Permanently delete user (no template clearing needed, just delete)
                                conn.delete_user(user_id=attendance_device_id)
                                time.sleep(0.1)

                                deleted_count += 1
                                deleted_users.append(employee_data)
                                action_type = "deleted"  # Track action
                            else:
                                # PRIORITY 2: Clear templates only (delete + recreate without templates)
                                # Step 1: Delete the user completely
                                conn.delete_user(user_id=attendance_device_id)
                                time.sleep(0.1)

                                # Step 2: Recreate user with same info but NO templates
                                conn.set_user(
                                    uid=user.uid,
                                    name=employee_name,
                                    privilege=user.privilege,
                                    password=user.password if hasattr(user, 'password') and user.password else '',
                                    group_id=user.group_id if hasattr(user, 'group_id') else '',
                                    user_id=attendance_device_id,
                                    card=user.card if hasattr(user, 'card') else 0
                                )

                                cleared_count += 1
                                cleared_users.append(employee_data)
                                action_type = "cleared"  # Track action

                        else:
                            # User not found on device - determine expected action for tracking
                            if delete_after_days > 0 and relieving_date:
                                try:
                                    if isinstance(relieving_date, str):
                                        relieving_dt = datetime.strptime(relieving_date, '%Y-%m-%d').date()
                                    else:
                                        relieving_dt = relieving_date

                                    days_since = (today - relieving_dt).days
                                    if days_since > delete_after_days:
                                        action_type = "deleted"
                                    else:
                                        action_type = "cleared"
                                except:
                                    action_type = "cleared"  # Default
                            else:
                                action_type = "cleared"  # Default

                    except Exception as e:
                        failed_employees.append(f"{employee_data['employee']} ({str(e)})")

                # Return results silently (no logging)
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": True,
                    "cleared_count": cleared_count,
                    "deleted_count": deleted_count,
                    "skipped_count": skipped_count,
                    "total_count": len(left_employees),
                    "failed_employees": failed_employees,
                    "cleared_users": cleared_users,
                    "deleted_users": deleted_users,
                    "skipped_users": skipped_users,
                    "action_type": action_type,  # Return action type for parent to log to JSON
                    "message": f"Cleared {cleared_count}, Deleted {deleted_count}, Skipped {skipped_count}, Total: {cleared_count + deleted_count}/{len(left_employees)}"
                }

            finally:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except:
                    pass

        except Exception as e:
            return {
                "device_id": device_id,
                "ip": ip_address,
                "success": False,
                "cleared_count": 0,
                "deleted_count": 0,
                "skipped_count": 0,
                "total_count": len(left_employees),
                "message": f"Error: {str(e)}",
                "action_type": None
            }
    
    def clean_left_employee_complete(self, employee_data):
        """Complete cleanup for single Left employee: ERPNext + all devices

        Logs one line per device with format:
        ✓ TIQN-0001 (ID: 123) | Relieving: 2024-01-15 | Action: Cleared templates | Device: Machine 1 | Result: Success

        IMPORTANT: Writes to JSON tracking file ONLY ONCE after all devices are processed
        """
        employee_id = employee_data["employee_id"]
        employee_name = employee_data["employee"]
        attendance_device_id = employee_data["attendance_device_id"]
        relieving_date = employee_data.get('relieving_date', 'N/A')

        cleanup_result = {
            "employee": employee_name,
            "employee_id": employee_id,
            "attendance_device_id": attendance_device_id,
            "erpnext_deletion": {"success": False, "deleted_count": 0},
            "device_results": [],
            "success": False,
            "message": ""
        }

        try:
            # Determine action type based on days since relieving
            delete_after_days = getattr(local_config, 'ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS', 0)
            delay_days = getattr(local_config, 'CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS', 7)

            from datetime import datetime
            action_type = "Unknown"
            days_since = None

            try:
                if isinstance(relieving_date, str) and relieving_date != 'N/A':
                    relieving_dt = datetime.strptime(relieving_date, '%Y-%m-%d').date()
                    days_since = (datetime.now().date() - relieving_dt).days

                    if delete_after_days > 0 and days_since > delete_after_days:
                        action_type = "Permanently delete user"
                    elif days_since >= delay_days:
                        action_type = "Clear templates"
                    else:
                        action_type = "Waiting (not ready)"
            except:
                action_type = "Unknown"

            # Process devices sequentially (not in parallel to avoid errors)
            device_results = []
            employee_full_name = employee_data.get('employee_name', 'N/A')

            for device in self.devices:
                try:
                    result = self.clear_employee_templates_from_device(device, [employee_data])
                    device_results.append(result)

                    # Log result for this device immediately
                    device_id = result.get("device_id", "Unknown")
                    cleared_count = result.get("cleared_count", 0)
                    deleted_count = result.get("deleted_count", 0)

                    if result["success"]:
                        if deleted_count > 0:
                            logger.info(f"{employee_name} - {employee_full_name} (ID: {attendance_device_id}) | Relieving: {relieving_date} | Action: {action_type} | Device: {device_id} | ✓ Deleted")
                        elif cleared_count > 0:
                            logger.info(f"{employee_name} - {employee_full_name} (ID: {attendance_device_id}) | Relieving: {relieving_date} | Action: {action_type} | Device: {device_id} | ✓ Cleared templates")
                        else:
                            logger.info(f"{employee_name} - {employee_full_name} (ID: {attendance_device_id}) | Relieving: {relieving_date} | Action: {action_type} | Device: {device_id} | • User not found on device (already processed)")
                    else:
                        logger.info(f"{employee_name} - {employee_full_name} (ID: {attendance_device_id}) | Relieving: {relieving_date} | Action: {action_type} | Device: {device_id} | ✗ {result.get('message', 'Failed')}")

                except Exception as e:
                    error_result = {
                        "device_id": device['device_id'],
                        "success": False,
                        "cleared_count": 0,
                        "deleted_count": 0,
                        "message": f"Error: {str(e)}",
                        "action_type": None
                    }
                    device_results.append(error_result)
                    logger.error(f"{employee_name} - {employee_full_name} (ID: {attendance_device_id}) | Relieving: {relieving_date} | Action: {action_type} | Device: {device['device_id']} | ✗ Error: {str(e)}")

            cleanup_result["device_results"] = device_results

            # Calculate summary
            total_cleared = sum(r.get("cleared_count", 0) for r in device_results)
            total_deleted = sum(r.get("deleted_count", 0) for r in device_results)
            successful_devices = sum(1 for r in device_results if r["success"] and (r.get("cleared_count", 0) > 0 or r.get("deleted_count", 0) > 0))

            # Determine overall success
            device_success = (total_cleared > 0 or total_deleted > 0)
            cleanup_result["success"] = device_success

            # =====================================================================
            # IMPORTANT: Write to JSON tracking file ONLY ONCE after all devices
            # This prevents race conditions and file corruption
            # =====================================================================

            # Determine final action type from device results
            final_action_type = None
            for result in device_results:
                if result.get("action_type"):
                    final_action_type = result["action_type"]
                    break  # Use first non-None action type

            # Write to tracking file if we successfully processed any device OR if user not found on any device
            if device_success or (not device_success and any(r["success"] for r in device_results)):
                if final_action_type:
                    self.add_processed_employee(employee_data, final_action_type)
                    logger.debug(f"  📝 Recorded {employee_name} to tracking file as '{final_action_type}'")
                elif not device_success:
                    # User not found on any device - still mark as processed (assume cleared by default)
                    self.add_processed_employee(employee_data, "cleared")
                    logger.debug(f"  📝 Recorded {employee_name} to tracking file as 'cleared' (not found on devices)")

            if device_success:
                cleanup_result["message"] = "Success"
            else:
                cleanup_result["message"] = "User not found (already processed)"

            return cleanup_result

        except Exception as e:
            cleanup_result["message"] = f"Error: {str(e)}"
            employee_full_name = employee_data.get('employee_name', 'N/A')
            logger.error(f"✗ {employee_name} - {employee_full_name} (ID: {attendance_device_id}) | Relieving: {relieving_date} | Error: {str(e)}")
            return cleanup_result
    
    def run_cleanup(self):
        """Main cleanup process for all Left employees"""
        start_time = time.time()
        logger.info("=" * 80)
        logger.info("STARTING LEFT EMPLOYEE DATA CLEANUP")
        logger.info("=" * 80)
        
        if not self.test_erpnext_connection():
            return {
                "success": False,
                "message": "Failed to connect to ERPNext API",
                "total_employees": 0,
                "cleaned_employees": 0,
                "execution_time": 0
            }
        
        # Get Left employees ready for cleanup
        left_employees = self.get_left_employees_for_cleanup()
        
        if not left_employees:
            logger.info("No Left employees found ready for cleanup")
            execution_time = time.time() - start_time
            logger.info("=" * 80)
            logger.info("LEFT EMPLOYEE CLEANUP COMPLETED")
            logger.info(f"Total execution time: {execution_time:.2f} seconds")
            logger.info("=" * 80)
            return {
                "success": True,
                "message": "No Left employees found ready for cleanup",
                "total_employees": 0,
                "cleaned_employees": 0,
                "execution_time": execution_time
            }
        
        logger.info(f"Found {len(left_employees)} Left employees ready for cleanup\n")

        # Process each employee
        cleanup_results = []
        successful_cleanups = 0

        for i, employee_data in enumerate(left_employees, 1):
            # Log handled by clean_left_employee_complete() - single line per employee
            result = self.clean_left_employee_complete(employee_data)
            cleanup_results.append(result)

            if result["success"]:
                successful_cleanups += 1

        execution_time = time.time() - start_time

        logger.info("\n" + "=" * 80)
        logger.info("LEFT EMPLOYEE CLEANUP COMPLETED")
        logger.info(f"Total: {len(left_employees)} | Success: {successful_cleanups} | Failed: {len(left_employees) - successful_cleanups} | Time: {execution_time:.2f}s")
        logger.info("=" * 80)
        
        return {
            "success": successful_cleanups > 0,
            "message": f"Cleanup completed: {successful_cleanups}/{len(left_employees)} employees processed successfully",
            "total_employees": len(left_employees),
            "cleaned_employees": successful_cleanups,
            "execution_time": execution_time,
            "detailed_results": cleanup_results
        }

def main():
    """Main function for command line usage"""
    import argparse
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from manual_input_utils import prompt_integer

    parser = argparse.ArgumentParser(description='Clean data for Left employees - Delete fingerprints from ERPNext and clear templates from devices')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be cleaned without actually doing it')
    parser.add_argument('--manual', action='store_true', help='Manual mode - prompt for configuration values')

    args = parser.parse_args()

    # Save original config values
    original_relieving_delay = local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS
    original_delete_after = local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS

    try:
        # Manual mode - prompt for values
        if args.manual:
            print("\n" + "="*60)
            print("MANUAL MODE - Clean Data Employee Left")
            print("="*60)

            relieving_delay = prompt_integer(
                f"Wait N days after relieving_date before clearing templates\n(Current: {original_relieving_delay} days)",
                default_value=original_relieving_delay,
                min_value=0
            )
            if relieving_delay is not None:
                local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = relieving_delay

            delete_after = prompt_integer(
                f"Permanently delete user from devices after N days since relieving_date\n(Current: {original_delete_after} days, 0 = disabled)",
                default_value=original_delete_after,
                min_value=0
            )
            if delete_after is not None:
                local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = delete_after

            print(f"\nConfiguration:")
            print(f"  Clear templates delay: {local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS} days")
            print(f"  Delete user delay: {local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS} days")
            print("="*60)

        if args.dry_run:
            logger.info("DRY RUN MODE - No actual changes will be made")
            # For dry run, just show what would be processed
            cleaner = CleanDataEmployeeLeft()
            if cleaner.test_erpnext_connection():
                left_employees = cleaner.get_left_employees_for_cleanup()
                if left_employees:
                    logger.info(f"Would clean {len(left_employees)} Left employees:")
                    for emp in left_employees:
                        logger.info(f"  - {emp['employee']}: {emp['employee_name']} (ID: {emp['attendance_device_id']}, Relieving: {emp['relieving_date']})")
                else:
                    logger.info("No Left employees found ready for cleanup")
            else:
                logger.error("ERPNext API connection failed")
            return

        # Run cleanup
        cleaner = CleanDataEmployeeLeft()
        result = cleaner.run_cleanup()

        if result["success"]:
            logger.info(f"Cleanup completed successfully: {result['message']}")
            exit(0)
        else:
            logger.error(f"Cleanup failed: {result['message']}")
            exit(1)

    except Exception as e:
        logger.error(f"Fatal error during cleanup: {str(e)}")
        raise
    finally:
        # Restore original config values
        local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = original_relieving_delay
        local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = original_delete_after

if __name__ == "__main__":
    main()