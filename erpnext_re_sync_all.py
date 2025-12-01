#!/usr/bin/env python3
"""
Manual Resync Data Tool for ERPNext Biometric Attendance Sync
This tool provides manual execution and interactive menu for biometric sync functions.

Configuration: Shared local_config.py (same as AUTO mode)

Usage:
    ./venv/bin/python3 erpnext_re_sync_all.py                           # Interactive menu
    ./venv/bin/python3 erpnext_re_sync_all.py --help                    # Show help
    ./venv/bin/python3 erpnext_re_sync_all.py --resync                  # Run end-of-day resync
    ./venv/bin/python3 erpnext_re_sync_all.py --time-sync               # Sync time to devices
    ./venv/bin/python3 erpnext_re_sync_all.py --restart-devices         # Restart all devices
    ./venv/bin/python3 erpnext_re_sync_all.py --time-sync-and-restart   # Sync time and restart
    ./venv/bin/python3 erpnext_re_sync_all.py --mongodb-sync            # Sync log from MongoDB to ERPNext
    ./venv/bin/python3 erpnext_re_sync_all.py --ot-mongodb-sync         # Sync OT from MongoDB to ERPNext
    ./venv/bin/python3 erpnext_re_sync_all.py --clear-templates         # Clear left employee templates
    ./venv/bin/python3 erpnext_re_sync_all.py --all                     # Run all operations
    ./venv/bin/python3 erpnext_re_sync_all.py --status                  # Show configuration status
"""

import os
import sys
import datetime
import argparse
import traceback

# Add current directory to path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Load shared configuration
import local_config
from manual_input_utils import prompt_date_range, prompt_single_date, prompt_integer

# =============================================================================
# MANUAL MODE CONSTANTS
# =============================================================================
END_OF_DAY_RESYNC_LOG_FILE = 'logs/logs_resync.log'
TIME_SYNC_LOG_FILE = 'logs/time_sync.log'
TIME_SYNC_MAX_DIFF_SECONDS = 2
TIME_SYNC_TIMEOUT_SECONDS = 3

def get_end_of_day_resync_date_range():
    """Get date range for end-of-day re-sync (today only)"""
    today = datetime.datetime.now().strftime('%Y%m%d')
    return [today, today]

def setup_resync_logger():
    """Setup dedicated logger for end-of-day re-sync operations"""
    import logging
    import os

    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Create dedicated logger for re-sync
    logger = logging.getLogger('resync_logger')
    logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicate logging
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create file handler for re-sync logs
    file_handler = logging.FileHandler(END_OF_DAY_RESYNC_LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s')
    file_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(file_handler)

    # Prevent propagation to root logger to avoid duplicate entries
    logger.propagate = False

    return logger

def log_resync_operation(message, level='INFO'):
    """Log re-sync operation to dedicated log file"""
    try:
        logger = setup_resync_logger()
        if level.upper() == 'ERROR':
            logger.error(message)
        elif level.upper() == 'WARNING':
            logger.warning(message)
        else:
            logger.info(message)
    except Exception as e:
        print(f"Failed to log re-sync operation: {e}")

def log_time_sync_operation(message, level="INFO"):
    """Log time sync operations to dedicated log file

    Args:
        message (str): Log message
        level (str): Log level (INFO, WARNING, ERROR)
    """
    import os

    # Ensure logs directory exists
    log_dir = os.path.dirname(TIME_SYNC_LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}\n"

    try:
        with open(TIME_SYNC_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write time sync log: {e}")

def sync_time_to_devices(devices_list=None, force=False):
    """Synchronize time from server to biometric devices (without restart)

    Args:
        devices_list (list): List of devices to sync time to. If None, uses all devices.
        force (bool): Force sync even if time difference is small

    Returns:
        dict: Summary of sync results
    """
    from zk import ZK
    import datetime

    if devices_list is None:
        devices_list = local_config.devices

    server_time = datetime.datetime.now()
    results = {
        "total_devices": len(devices_list),
        "success_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "details": []
    }

    log_time_sync_operation(f"Starting time sync to {len(devices_list)} devices (Sunday 23:00)")
    log_time_sync_operation(f"Server time: {server_time}")

    for device in devices_list:
        device_id = device['device_id']
        device_ip = device['ip']
        device_result = {
            "device_id": device_id,
            "device_ip": device_ip,
            "success": False,
            "message": "",
            "time_diff_seconds": None,
            "old_time": None,
            "new_time": None
        }

        try:
            log_time_sync_operation(f"Connecting to device {device_id} ({device_ip})")

            # Connect to device
            zk = ZK(device_ip, port=4370, timeout=TIME_SYNC_TIMEOUT_SECONDS, force_udp=True)
            conn = zk.connect()

            if not conn:
                device_result["message"] = "Failed to connect to device"
                results["failed_count"] += 1
                log_time_sync_operation(f"Failed to connect to {device_id}", "ERROR")
                results["details"].append(device_result)
                continue

            # Get current device time
            device_time = conn.get_time()
            device_result["old_time"] = device_time

            # Calculate time difference
            time_diff = abs((server_time - device_time).total_seconds())
            device_result["time_diff_seconds"] = time_diff

            log_time_sync_operation(f"Device {device_id} time: {device_time}, difference: {time_diff:.1f}s")

            # Check if sync is needed
            if not force and time_diff < TIME_SYNC_MAX_DIFF_SECONDS:
                device_result["message"] = f"Time difference ({time_diff:.1f}s) within tolerance"
                device_result["success"] = True
                results["skipped_count"] += 1
                log_time_sync_operation(f"Skipping {device_id} - time difference within tolerance")
            else:
                # Sync time to device (without restart)
                conn.set_time(server_time)
                device_result["new_time"] = server_time
                device_result["success"] = True
                device_result["message"] = f"Time synced successfully (diff: {time_diff:.1f}s)"
                results["success_count"] += 1
                log_time_sync_operation(f"Time synced to {device_id} successfully")

            # Disconnect from device
            try:
                conn.disconnect()
                log_time_sync_operation(f"Disconnected from {device_id}")
            except Exception as disc_error:
                log_time_sync_operation(f"Warning: Failed to disconnect from {device_id}: {disc_error}", "WARNING")

        except Exception as e:
            device_result["message"] = f"Error: {str(e)}"
            results["failed_count"] += 1
            log_time_sync_operation(f"Error syncing time to {device_id}: {e}", "ERROR")

        results["details"].append(device_result)

    # Log summary
    log_time_sync_operation(f"Time sync completed - Success: {results['success_count']}, Failed: {results['failed_count']}, Skipped: {results['skipped_count']}")

    return results

def restart_all_devices(devices_list=None):
    """Restart all biometric devices

    Args:
        devices_list (list): List of devices to restart. If None, uses all devices.

    Returns:
        dict: Summary of restart results
    """
    from zk import ZK

    if devices_list is None:
        devices_list = local_config.devices

    results = {
        "total_devices": len(devices_list),
        "success_count": 0,
        "failed_count": 0,
        "details": []
    }

    log_time_sync_operation(f"Starting restart for {len(devices_list)} devices")

    for device in devices_list:
        device_id = device['device_id']
        device_ip = device['ip']
        device_result = {
            "device_id": device_id,
            "device_ip": device_ip,
            "success": False,
            "message": ""
        }

        try:
            log_time_sync_operation(f"Restarting device {device_id} ({device_ip})")

            # Connect to device
            zk = ZK(device_ip, port=4370, timeout=TIME_SYNC_TIMEOUT_SECONDS, force_udp=True)
            conn = zk.connect()

            if not conn:
                device_result["message"] = "Failed to connect to device"
                results["failed_count"] += 1
                log_time_sync_operation(f"Failed to connect to {device_id} for restart", "ERROR")
                results["details"].append(device_result)
                continue

            # Send restart command
            conn.restart()
            device_result["success"] = True
            device_result["message"] = "Restart command sent successfully"
            results["success_count"] += 1
            log_time_sync_operation(f"Device {device_id} restart command sent successfully")

            # No need to disconnect as device will restart

        except Exception as e:
            device_result["message"] = f"Error: {str(e)}"
            results["failed_count"] += 1
            log_time_sync_operation(f"Error restarting device {device_id}: {e}", "ERROR")

        results["details"].append(device_result)

    # Log summary
    log_time_sync_operation(f"Restart completed - Success: {results['success_count']}, Failed: {results['failed_count']}")

    return results


class ManualResyncTool:
    def __init__(self):
        self.tool_name = "Manual Resync Data Tool"
        self.version = "1.0.0"
        self.start_time = datetime.datetime.now()

    def log_operation(self, message, level="INFO"):
        """Log operation with timestamp"""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    def log_section_start(self, section_name):
        """Log section start"""
        print(f"\n{'='*60}")
        print(f" {section_name}")
        print(f"{'='*60}")

    def log_section_end(self, section_name, success=True):
        """Log section end"""
        status = "COMPLETED" if success else "FAILED"
        print(f"\n[{section_name}] {status}")
        print(f"{'='*60}\n")

    # =========================================================================
    # MOVED FUNCTIONS - Previously automated, now manual only
    # =========================================================================

    def execute_end_of_day_resync(self, date_range=None):
        """Execute end-of-day comprehensive re-sync

        MOVED from erpnext_sync_all.py - now manual execution only

        Args:
            date_range: List of [start_date, end_date] in YYYYMMDD format.
                       If None, prompts user for date input.

        Returns:
            bool: True if successful
        """
        self.log_section_start("END-OF-DAY RESYNC")

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("sync_log_from_device_to_erpnext",
                os.path.join(current_dir, "01.sync_log_from_device_to_erpnext.py"))
            sync_log_from_device_to_erpnext = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_log_from_device_to_erpnext)

            # Get date range - prompt user if not provided
            if date_range is None:
                date_range = prompt_date_range(
                    prompt_message="Sync Log from Device to ERPNext",
                    allow_empty=True,
                    default_days_back=0  # Default to today only
                )
                if not date_range:
                    self.log_operation("Operation cancelled by user", "WARNING")
                    self.log_section_end("END-OF-DAY RESYNC", True)
                    return True

            self.log_operation(f"Target date range: {date_range[0]} to {date_range[1]}")

            # Save original config (support both old and new names)
            original_resync_config = getattr(local_config, 're_sync_log_from_att_machine_to_erpnext_date_range', [])
            original_resync_config_old = getattr(local_config, 're_sync_data_date_range', [])

            try:
                # Set date range for resync using NEW config name
                local_config.re_sync_log_from_att_machine_to_erpnext_date_range = date_range
                # Also set old name for backward compatibility with 01.sync script
                local_config.re_sync_data_date_range = date_range

                # Log to resync log file
                log_resync_operation(f"MANUAL RESYNC START - Date: {date_range[0]} to {date_range[1]}")

                # Execute sync
                self.log_operation("Executing sync from devices to ERPNext...")
                success = sync_log_from_device_to_erpnext.run_single_cycle(bypass_device_connection=False)

                if success:
                    log_resync_operation("MANUAL RESYNC OK")
                    self.log_operation("End-of-day resync completed successfully")
                else:
                    log_resync_operation("MANUAL RESYNC FAILED", "ERROR")
                    self.log_operation("End-of-day resync failed", "ERROR")

                self.log_section_end("END-OF-DAY RESYNC", success)
                return success

            finally:
                # Restore original config
                local_config.re_sync_log_from_att_machine_to_erpnext_date_range = original_resync_config
                local_config.re_sync_data_date_range = original_resync_config_old

        except Exception as e:
            self.log_operation(f"End-of-day resync error: {e}", "ERROR")
            log_resync_operation(f"MANUAL RESYNC ERROR: {e}", "ERROR")
            self.log_section_end("END-OF-DAY RESYNC", False)
            return False

    def execute_time_sync_to_devices(self, force=False):
        """Execute time synchronization to all devices

        MOVED from erpnext_sync_all.py - now manual execution only

        Args:
            force: Force sync even if time difference is small

        Returns:
            dict: Sync results
        """
        self.log_section_start("TIME SYNC TO DEVICES")

        try:
            self.log_operation(f"Force mode: {force}")
            self.log_operation(f"Max time diff threshold: {TIME_SYNC_MAX_DIFF_SECONDS}s")
            self.log_operation(f"Connection timeout: {TIME_SYNC_TIMEOUT_SECONDS}s")

            # Execute time sync
            results = sync_time_to_devices(force=force)

            # Log results
            self.log_operation(f"Total devices: {results['total_devices']}")
            self.log_operation(f"Successful: {results['success_count']}")
            self.log_operation(f"Failed: {results['failed_count']}")
            self.log_operation(f"Skipped: {results['skipped_count']}")

            # Log individual device results
            for detail in results.get('details', []):
                status = "OK" if detail['success'] else "FAIL"
                self.log_operation(f"  {detail['device_id']} ({detail['device_ip']}): {status} - {detail['message']}")

            success = results['failed_count'] == 0
            self.log_section_end("TIME SYNC TO DEVICES", success)
            return results

        except Exception as e:
            self.log_operation(f"Time sync error: {e}", "ERROR")
            self.log_section_end("TIME SYNC TO DEVICES", False)
            return {"success": False, "message": str(e)}

    def execute_restart_all_devices(self):
        """Execute restart for all devices

        MOVED from erpnext_sync_all.py - now manual execution only

        Returns:
            dict: Restart results
        """
        self.log_section_start("RESTART ALL DEVICES")

        try:
            self.log_operation(f"Restarting {len(local_config.devices)} devices...")

            # Execute restart
            results = restart_all_devices()

            # Log results
            self.log_operation(f"Total devices: {results['total_devices']}")
            self.log_operation(f"Successful: {results['success_count']}")
            self.log_operation(f"Failed: {results['failed_count']}")

            # Log individual device results
            for detail in results.get('details', []):
                status = "OK" if detail['success'] else "FAIL"
                self.log_operation(f"  {detail['device_id']} ({detail['device_ip']}): {status} - {detail['message']}")

            success = results['failed_count'] == 0
            self.log_section_end("RESTART ALL DEVICES", success)
            return results

        except Exception as e:
            self.log_operation(f"Restart devices error: {e}", "ERROR")
            self.log_section_end("RESTART ALL DEVICES", False)
            return {"success": False, "message": str(e)}

    def execute_time_sync_and_restart(self, force=False):
        """Execute time sync followed by restart for all devices

        MOVED from erpnext_sync_all.py - now manual execution only

        Args:
            force: Force sync even if time difference is small

        Returns:
            bool: True if both operations successful
        """
        self.log_section_start("TIME SYNC AND RESTART")

        try:
            # Execute time sync first
            self.log_operation("Step 1: Syncing time to devices...")
            sync_results = self.execute_time_sync_to_devices(force=force)

            # Execute restart
            self.log_operation("Step 2: Restarting all devices...")
            restart_results = self.execute_restart_all_devices()

            # Summary
            sync_ok = sync_results.get('failed_count', 0) == 0
            restart_ok = restart_results.get('failed_count', 0) == 0
            overall_success = sync_ok and restart_ok

            self.log_operation(f"Time sync: {'OK' if sync_ok else 'FAILED'}")
            self.log_operation(f"Restart: {'OK' if restart_ok else 'FAILED'}")

            self.log_section_end("TIME SYNC AND RESTART", overall_success)
            return overall_success

        except Exception as e:
            self.log_operation(f"Time sync and restart error: {e}", "ERROR")
            self.log_section_end("TIME SYNC AND RESTART", False)
            return False

    # =========================================================================
    # COPIED FUNCTIONS - Also available in erpnext_sync_all.py for automation
    # =========================================================================

    def execute_mongodb_sync(self):
        """Execute MongoDB to ERPNext sync (MANUAL MODE - with user prompts)

        COPIED from erpnext_sync_all.py - available both here and in automated service

        Returns:
            bool: True if successful
        """
        self.log_section_start("MONGODB TO ERPNEXT SYNC")

        try:
            if not getattr(local_config, 'ENABLE_SYNC_LOG_FROM_MONGODB_TO_ERPNEXT', False):
                self.log_operation("MongoDB sync is disabled in configuration", "WARNING")
                self.log_section_end("MONGODB TO ERPNEXT SYNC", True)
                return True

            # Prompt user for date range
            date_range = prompt_date_range(
                prompt_message="Sync Attendance Data from MongoDB to ERPNext",
                allow_empty=True,
                default_days_back=7
            )
            if not date_range:
                self.log_operation("Operation cancelled by user", "WARNING")
                self.log_section_end("MONGODB TO ERPNEXT SYNC", True)
                return True

            import importlib.util
            spec = importlib.util.spec_from_file_location("sync_log_from_mongodb_to_erpnext",
                os.path.join(current_dir, "04.sync_log_from_mongodb_to_erpnext.py"))
            sync_log_from_mongodb_to_erpnext = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_log_from_mongodb_to_erpnext)

            self.log_operation("Starting MongoDB sync...")
            self.log_operation(f"MongoDB Host: {local_config.MONGODB_HOST}:{local_config.MONGODB_PORT}")
            self.log_operation(f"Database: {local_config.MONGODB_DATABASE}")
            self.log_operation(f"Collection: {local_config.MONGODB_ATTLOG_COLLECTION}")
            self.log_operation(f"Date range: {date_range[0]} to {date_range[1]}")

            # Call sync_attendance_data directly with date_range parameter
            result_data = sync_log_from_mongodb_to_erpnext.sync_attendance_data(date_range)

            self.log_operation(f"Processed: {result_data['processed']}/{result_data['total_records']}")
            self.log_operation(f"Skipped: {result_data['skipped']}")
            self.log_operation(f"Errors: {result_data['errors']}")
            self.log_section_end("MONGODB TO ERPNEXT SYNC", True)
            return True

        except Exception as e:
            self.log_operation(f"MongoDB sync error: {e}", "ERROR")
            self.log_section_end("MONGODB TO ERPNEXT SYNC", False)
            return False

    def execute_ot_mongodb_sync(self):
        """Execute OT sync from MongoDB to ERPNext (MANUAL MODE - with user prompts)

        COPIED from erpnext_sync_all.py - available both here and in automated service

        Returns:
            bool: True if successful
        """
        self.log_section_start("OT MONGODB TO ERPNEXT SYNC")

        try:
            if not getattr(local_config, 'ENABLE_SYNC_OT_FROM_MONGODB_TO_ERPNEXT', False):
                self.log_operation("OT MongoDB sync is disabled in configuration", "WARNING")
                self.log_section_end("OT MONGODB TO ERPNEXT SYNC", True)
                return True

            # Prompt user for start date
            start_date = prompt_single_date(
                prompt_message="Sync OT from MongoDB to ERPNext - Enter Start Date",
                allow_today=True
            )
            if not start_date:
                self.log_operation("Operation cancelled by user", "WARNING")
                self.log_section_end("OT MONGODB TO ERPNEXT SYNC", True)
                return True

            import importlib.util
            spec = importlib.util.spec_from_file_location("sync_ot_from_mongodb_to_erpnext",
                os.path.join(current_dir, "05.sync_ot_from_mongodb_to_erpnext.py"))
            sync_ot_from_mongodb_to_erpnext = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_ot_from_mongodb_to_erpnext)

            self.log_operation("Starting OT MongoDB sync...")
            self.log_operation(f"MongoDB Host: {local_config.MONGODB_HOST}:{local_config.MONGODB_PORT}")
            self.log_operation(f"Database: {local_config.MONGODB_DATABASE}")
            self.log_operation(f"Collection: {local_config.MONGODB_OT_COLLECTION}")
            self.log_operation(f"Start date filter: {start_date}")

            # Create syncer with start_date parameter
            syncer = sync_ot_from_mongodb_to_erpnext.OTSyncFromMongoDB(start_date=start_date)
            result = syncer.sync_ot_to_erpnext()

            if result['success']:
                self.log_operation(f"Total records: {result['total_records']}")
                self.log_operation(f"Created: {result['created']}")
                self.log_operation(f"Skipped: {result.get('skipped_requests', 0)}")
                self.log_operation(f"Failed: {result['failed']}")
                self.log_section_end("OT MONGODB TO ERPNEXT SYNC", True)
                return True
            else:
                self.log_operation(f"OT MongoDB sync failed: {result['message']}", "ERROR")
                self.log_section_end("OT MONGODB TO ERPNEXT SYNC", False)
                return False

        except Exception as e:
            self.log_operation(f"OT MongoDB sync error: {e}", "ERROR")
            self.log_section_end("OT MONGODB TO ERPNEXT SYNC", False)
            return False

    def execute_clear_left_templates(self, force=False, delay_days=None, delete_after_days=None):
        """Execute clear left employee templates

        COPIED from erpnext_sync_all.py - available both here and in automated service

        Args:
            force: Force run even if already run today
            delay_days: Override CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS
            delete_after_days: Override ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS

        Returns:
            bool: True if successful
        """
        self.log_section_start("CLEAR LEFT EMPLOYEE TEMPLATES")

        try:
            # Prompt for delay_days if in manual mode and not provided
            if delay_days is None:
                delay_days = prompt_integer(
                    f"Enter delay days after relieving_date before clearing templates (current: {local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS})",
                    default_value=local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS,
                    min_value=0
                )
                if delay_days is None:
                    self.log_operation("Operation cancelled by user", "WARNING")
                    self.log_section_end("CLEAR LEFT EMPLOYEE TEMPLATES", True)
                    return True

            # Prompt for delete_after_days if in manual mode and not provided
            if delete_after_days is None:
                delete_after_days = prompt_integer(
                    f"Enter days after relieving_date to permanently delete user from devices (current: {local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS})",
                    default_value=local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS,
                    min_value=0
                )
                if delete_after_days is None:
                    self.log_operation("Operation cancelled by user", "WARNING")
                    self.log_section_end("CLEAR LEFT EMPLOYEE TEMPLATES", True)
                    return True

            # Temporarily override config values
            original_delay_days = local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS
            original_delete_after_days = local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS
            local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = delay_days
            local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = delete_after_days

            # MANUAL mode: Only check if already run today (bypass CLEAR_LEFT_USER_TEMPLATES_ON_DATE_OF_MONTH)
            # User explicitly runs manual → should be allowed regardless of schedule
            if not force:
                last_run = local_config.get_last_clear_left_templates_date()
                today = datetime.date.today()

                if last_run is not None and last_run >= today:
                    self.log_operation(f"Already run today. Last run: {last_run}")
                    self.log_operation("Use --force to run anyway")
                    # Restore config
                    local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = original_delay_days
                    local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = original_delete_after_days
                    self.log_section_end("CLEAR LEFT EMPLOYEE TEMPLATES", True)
                    return True

            import importlib.util
            spec = importlib.util.spec_from_file_location("clean_data_employee_left",
                os.path.join(current_dir, "02.clean_data_employee_left.py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            CleanDataEmployeeLeft = module.CleanDataEmployeeLeft
            cleaner = CleanDataEmployeeLeft()

            # Test ERPNext connection
            self.log_operation("Testing ERPNext connection...")
            if not cleaner.test_erpnext_connection():
                self.log_operation("Failed to connect to ERPNext", "ERROR")
                self.log_section_end("CLEAR LEFT EMPLOYEE TEMPLATES", False)
                return False

            self.log_operation("ERPNext connection OK")

            # Get left employees
            self.log_operation("Getting left employees for cleanup...")
            left_employees = cleaner.get_left_employees_for_cleanup()

            if not left_employees:
                self.log_operation("No left employees to clean up")
                local_config.set_last_clear_left_templates_date()
                # Restore config
                local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = original_delay_days
                local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = original_delete_after_days
                self.log_section_end("CLEAR LEFT EMPLOYEE TEMPLATES", True)
                return True

            self.log_operation(f"Found {len(left_employees)} employees to process")

            # Display configuration
            self.log_operation(f"Clear templates from devices: {local_config.ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES}")
            self.log_operation(f"Clear templates from ERPNext: {local_config.ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_ERPNEXT}")
            self.log_operation(f"Delay days: {local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS}")
            self.log_operation(f"Delete after days: {local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS}")

            successful_cleanups = 0

            for employee_data in left_employees:
                employee_id = employee_data["employee_id"]
                employee_name = employee_data.get("employee_name", "Unknown")
                relieving_date = employee_data.get("relieving_date", "Unknown")

                self.log_operation(f"Processing: {employee_id} ({employee_name}) - Relieved: {relieving_date}")

                # Delete from ERPNext if enabled
                if local_config.ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_ERPNEXT:
                    self.log_operation(f"  Deleting fingerprints from ERPNext...")
                    cleaner.delete_employee_fingerprints_from_erpnext(employee_id)

                # Clean from devices
                result = cleaner.clean_left_employee_complete(employee_data)
                if result["success"]:
                    successful_cleanups += 1
                    self.log_operation(f"  Cleanup successful")
                else:
                    self.log_operation(f"  Cleanup failed: {result.get('message', 'Unknown error')}", "ERROR")

            # Update last run date
            local_config.set_last_clear_left_templates_date()

            # Restore config
            local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = original_delay_days
            local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = original_delete_after_days

            self.log_operation(f"Cleared {successful_cleanups}/{len(left_employees)} employees")
            success = successful_cleanups > 0 or len(left_employees) == 0
            self.log_section_end("CLEAR LEFT EMPLOYEE TEMPLATES", success)
            return success

        except Exception as e:
            # Restore config even on error
            try:
                local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = original_delay_days
                local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = original_delete_after_days
            except:
                pass
            self.log_operation(f"Clear templates error: {e}", "ERROR")
            traceback.print_exc()
            self.log_section_end("CLEAR LEFT EMPLOYEE TEMPLATES", False)
            return False

    def execute_all_operations(self, date_range=None, force=False):
        """Execute all manual operations in sequence

        Args:
            date_range: Date range for resync
            force: Force run even for daily-limited operations

        Returns:
            bool: True if all operations successful
        """
        self.log_section_start("ALL MANUAL OPERATIONS")

        results = {
            "resync": False,
            "time_sync_restart": False,
            "mongodb_sync": False,
            "ot_mongodb_sync": False,
            "clear_templates": False
        }

        # 1. End-of-day resync
        self.log_operation("Running end-of-day resync...")
        results["resync"] = self.execute_end_of_day_resync(date_range)

        # 2. Time sync and restart
        self.log_operation("Running time sync and restart...")
        results["time_sync_restart"] = self.execute_time_sync_and_restart(force=force)

        # 3. MongoDB sync
        self.log_operation("Running MongoDB sync...")
        results["mongodb_sync"] = self.execute_mongodb_sync()

        # 4. OT MongoDB sync
        self.log_operation("Running OT MongoDB sync...")
        results["ot_mongodb_sync"] = self.execute_ot_mongodb_sync()

        # 5. Clear left templates
        self.log_operation("Running clear left templates...")
        results["clear_templates"] = self.execute_clear_left_templates(force=force)

        # Summary
        all_success = all(results.values())

        print(f"\n{'='*60}")
        print(" SUMMARY")
        print(f"{'='*60}")
        for op, success in results.items():
            status = "OK" if success else "FAILED"
            print(f"  {op}: {status}")
        print(f"{'='*60}")

        return all_success

    def execute_sync_user_info_from_erpnext_to_device(self):
        """Execute sync user info from ERPNext to devices

        Returns:
            bool: True if successful
        """
        self.log_section_start("SYNC USER INFO FROM ERPNEXT TO DEVICES")

        try:
            # Display current sync_from_master_device_to_erpnext_filters_id configuration
            filter_ids = local_config.sync_from_master_device_to_erpnext_filters_id

            print(f"\nCurrent Device Filter Configuration:")
            print(f"{'='*60}")
            if filter_ids:
                print(f"Sync ONLY these user IDs: {filter_ids}")
                print(f"Count: {len(filter_ids)} user(s)")
            else:
                print(f"Sync ALL users from master device (no filter)")
            print(f"{'='*60}")

            # Ask user to confirm or provide new list
            print("\nOptions:")
            print("  1. Use current configuration")
            print("  2. Enter custom user ID list (comma-separated)")
            print("  3. Sync ALL users (clear filter)")

            choice = input("\nSelect option (1-3): ").strip()

            if choice == '2':
                # Manual input
                user_input = input("Enter user IDs (comma-separated, e.g., 100,200,300): ").strip()
                if user_input:
                    # Parse comma-separated list
                    filter_ids = [uid.strip() for uid in user_input.split(',') if uid.strip()]
                    print(f"Will sync {len(filter_ids)} user(s): {filter_ids}")
                else:
                    print("No IDs entered, operation cancelled")
                    self.log_section_end("SYNC USER INFO FROM ERPNEXT TO DEVICES", True)
                    return True
            elif choice == '3':
                # Clear filter
                filter_ids = []
                print("Will sync ALL users from master device")
            elif choice != '1':
                print("Invalid choice, operation cancelled")
                self.log_section_end("SYNC USER INFO FROM ERPNEXT TO DEVICES", True)
                return True

            # Temporarily override config
            original_filter_ids = local_config.sync_from_master_device_to_erpnext_filters_id
            local_config.sync_from_master_device_to_erpnext_filters_id = filter_ids

            import importlib.util
            spec = importlib.util.spec_from_file_location("sync_user_info_from_erpnext_to_device",
                os.path.join(current_dir, "11.sync_user_info_from_erpnext_to_device.py"))
            sync_user_info = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_user_info)

            self.log_operation("Starting user info sync from ERPNext to devices...")
            result = sync_user_info.main()

            # Restore original config
            local_config.sync_from_master_device_to_erpnext_filters_id = original_filter_ids

            self.log_section_end("SYNC USER INFO FROM ERPNEXT TO DEVICES", True)
            return True

        except Exception as e:
            self.log_operation(f"Sync user info error: {e}", "ERROR")
            traceback.print_exc()
            self.log_section_end("SYNC USER INFO FROM ERPNEXT TO DEVICES", False)
            return False

    def execute_sync_from_master_device_to_erpnext(self):
        """Execute sync from master device to ERPNext

        Returns:
            bool: True if successful
        """
        self.log_section_start("SYNC FROM MASTER DEVICE TO ERPNEXT")

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("sync_from_master_device_to_erpnext",
                os.path.join(current_dir, "12.sync_from_master_device_to_erpnext.py"))
            sync_master = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_master)

            self.log_operation("Starting sync from master device to ERPNext...")
            result = sync_master.main()

            self.log_section_end("SYNC FROM MASTER DEVICE TO ERPNEXT", True)
            return True

        except Exception as e:
            self.log_operation(f"Sync from master device error: {e}", "ERROR")
            traceback.print_exc()
            self.log_section_end("SYNC FROM MASTER DEVICE TO ERPNEXT", False)
            return False

    def execute_sync_all_from_master_to_other_devices(self):
        """Execute sync all users from master device to other devices

        Returns:
            bool: True if successful
        """
        self.log_section_start("SYNC ALL FROM MASTER TO OTHER DEVICES")

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("sync_all_from_master",
                os.path.join(current_dir, "15.sync_all_from_master_device_to_other_devices.py"))
            sync_all = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_all)

            # Create sync manager instance
            sync_manager = sync_all.MasterToTargetSync()

            # Get users from master device
            self.log_operation("Scanning master device for users with fingerprints...")
            users = sync_manager.get_all_users_with_fingerprints()

            if not users:
                self.log_operation("No users with fingerprints found on master device", "WARNING")
                self.log_section_end("SYNC ALL FROM MASTER TO OTHER DEVICES", True)
                return True

            # Show summary and ask for confirmation
            print(f"\n{'='*80}")
            print(f"SYNC ALL USERS FROM MASTER TO OTHER DEVICES")
            print(f"{'='*80}")
            print(f"Master device: {local_config.devices_master['device_id']} ({local_config.devices_master['ip']})")
            print(f"Total users with fingerprints: {len(users)}")
            print(f"\nTarget devices ({len(local_config.devices)}):")
            for i, device in enumerate(local_config.devices, 1):
                print(f"  {i}. {device['device_id']} ({device['ip']})")
            print(f"{'='*80}")

            confirm = input("\nType 'yes' to start sync: ").strip().lower()

            if confirm != 'yes':
                self.log_operation("Operation cancelled by user")
                self.log_section_end("SYNC ALL FROM MASTER TO OTHER DEVICES", True)
                return True

            # Execute sync
            self.log_operation(f"Starting sync of {len(users)} users to {len(local_config.devices)} devices...")
            result = sync_manager.sync_all_to_targets(users)

            # Show results
            if result['success']:
                self.log_operation(f"Sync completed: {result['successful_targets']}/{len(local_config.devices)} devices")
                self.log_section_end("SYNC ALL FROM MASTER TO OTHER DEVICES", True)
                return True
            else:
                self.log_operation(f"Sync failed: {result.get('message', 'Unknown error')}", "ERROR")
                self.log_section_end("SYNC ALL FROM MASTER TO OTHER DEVICES", False)
                return False

        except Exception as e:
            self.log_operation(f"Sync all from master error: {e}", "ERROR")
            traceback.print_exc()
            self.log_section_end("SYNC ALL FROM MASTER TO OTHER DEVICES", False)
            return False

    def execute_clean_user_on_machine(self):
        """Execute clean user on machine

        Returns:
            bool: True if successful
        """
        self.log_section_start("CLEAN USER ON MACHINE")

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("clean_user_on_machine",
                os.path.join(current_dir, "13.clean_user_on_machine.py"))
            clean_user = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(clean_user)

            # Create cleaner instance to preview users
            cleaner = clean_user.UserCleaner(keep_user_id_clean_template=False)

            # Display users to keep
            print(f"\n{'='*80}")
            print(f"USERS TO KEEP (from 13.keep_user_id.txt):")
            print(f"{'='*80}")
            if cleaner.keep_user_id:
                for i, user_id in enumerate(cleaner.keep_user_id, 1):
                    print(f"  {i}. User ID: {user_id}")
                print(f"\nTotal: {len(cleaner.keep_user_id)} user(s) will be KEPT")
            else:
                print("  WARNING: No users in keep list!")
            print(f"{'='*80}")

            # Show preview of what will be deleted
            print(f"\nPREVIEW: Connecting to first device to show users that will be deleted...")
            if cleaner.devices:
                from zk import ZK
                preview_device = cleaner.devices[0]
                try:
                    zk = ZK(preview_device['ip'], port=4370, timeout=5, force_udp=True)
                    conn = zk.connect()
                    if conn:
                        users = conn.get_users()
                        to_delete = [u for u in users if str(u.user_id) not in cleaner.keep_user_id]
                        to_keep = [u for u in users if str(u.user_id) in cleaner.keep_user_id]

                        print(f"\nDevice: {preview_device['device_id']} ({preview_device['ip']})")
                        print(f"Total users on device: {len(users)}")
                        print(f"\nUsers that WILL BE DELETED ({len(to_delete)}):")
                        for user in to_delete[:20]:  # Show max 20
                            print(f"  - ID: {user.user_id}, Name: {user.name}")
                        if len(to_delete) > 20:
                            print(f"  ... and {len(to_delete) - 20} more")

                        print(f"\nUsers that will be KEPT ({len(to_keep)}):")
                        for user in to_keep[:20]:
                            print(f"  - ID: {user.user_id}, Name: {user.name}")
                        if len(to_keep) > 20:
                            print(f"  ... and {len(to_keep) - 20} more")

                        conn.disconnect()
                except Exception as e:
                    print(f"Could not preview device: {e}")

            # Ask for confirmation
            print(f"\n{'='*80}")
            print("WARNING: This operation will DELETE users from devices!")
            print(f"{'='*80}")
            confirm = input("\nType 'yes' to confirm deletion: ").strip().lower()

            if confirm != 'yes':
                self.log_operation("Operation cancelled by user")
                self.log_section_end("CLEAN USER ON MACHINE", True)
                return True

            self.log_operation("Starting clean user on machine...")
            result = clean_user.main()

            self.log_section_end("CLEAN USER ON MACHINE", True)
            return True

        except Exception as e:
            self.log_operation(f"Clean user on machine error: {e}", "ERROR")
            traceback.print_exc()
            self.log_section_end("CLEAN USER ON MACHINE", False)
            return False

    def execute_delete_ot_in_erpnext_db(self):
        """Execute delete OT in ERPNext database

        Returns:
            bool: True if successful
        """
        self.log_section_start("DELETE OT IN ERPNEXT DATABASE")

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("delete_ot_in_erpnext_db",
                os.path.join(current_dir, "14.delete_ot_in_erpnext_db.py"))
            delete_ot = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(delete_ot)

            self.log_operation("Starting delete OT in ERPNext database...")
            self.log_operation("WARNING: This will delete OT records from database!", "WARNING")

            # Prompt for date range
            date_range = prompt_date_range(
                prompt_message="Delete OT Records - Enter Date Range",
                allow_empty=False
            )
            if not date_range:
                self.log_operation("Operation cancelled by user")
                self.log_section_end("DELETE OT IN ERPNEXT DATABASE", True)
                return True

            # Update RANGE_DATE_FILTER in the module
            original_date_filter = delete_ot.RANGE_DATE_FILTER
            delete_ot.RANGE_DATE_FILTER = date_range

            # Show preview first (dry run)
            self.log_operation(f"Running preview for date range: {date_range[0]} to {date_range[1]}")
            preview_result = delete_ot.delete_ot_records(dry_run=True)

            if not preview_result.get('success'):
                self.log_operation(f"Preview failed: {preview_result.get('message')}", "ERROR")
                delete_ot.RANGE_DATE_FILTER = original_date_filter
                self.log_section_end("DELETE OT IN ERPNEXT DATABASE", False)
                return False

            # Ask for final confirmation
            print(f"\n{'='*80}")
            print("FINAL CONFIRMATION")
            print(f"{'='*80}")
            print(f"Will delete {preview_result.get('detail_records_to_delete', 0)} detail record(s)")
            print(f"Will delete {preview_result.get('parent_records_to_delete', 0)} parent registration(s)")
            print(f"Date range: {date_range[0]} to {date_range[1]}")
            print(f"{'='*80}")

            confirm = input("\nType 'DELETE' to confirm deletion: ").strip()
            if confirm != 'DELETE':
                self.log_operation("Operation cancelled by user")
                delete_ot.RANGE_DATE_FILTER = original_date_filter
                self.log_section_end("DELETE OT IN ERPNEXT DATABASE", True)
                return True

            # Execute actual deletion
            result = delete_ot.delete_ot_records(dry_run=False)

            # Restore original date filter
            delete_ot.RANGE_DATE_FILTER = original_date_filter

            if result.get('success'):
                self.log_operation(f"Deleted {result.get('detail_records_deleted', 0)} detail records")
                self.log_operation(f"Deleted {result.get('parent_records_deleted', 0)} parent records")
                self.log_section_end("DELETE OT IN ERPNEXT DATABASE", True)
                return True
            else:
                self.log_operation(f"Delete OT failed: {result.get('message', 'Unknown error')}", "ERROR")
                self.log_section_end("DELETE OT IN ERPNEXT DATABASE", False)
                return False

        except Exception as e:
            self.log_operation(f"Delete OT error: {e}", "ERROR")
            traceback.print_exc()
            self.log_section_end("DELETE OT IN ERPNEXT DATABASE", False)
            return False

    def show_interactive_menu(self):
        """Show interactive menu for selecting functions to run"""
        while True:
            print(f"\n{'='*80}")
            print(f" {self.tool_name} v{self.version} - Interactive Menu")
            print(f"{'='*80}")
            print("\nAvailable Functions:")
            print("  1. Sync Log from Device to ERPNext")
            print("  2. Clean Data Employee Left")
            print("  3. Clean Old Logs")
            print("  4. Sync Log from MongoDB to ERPNext")
            print("  5. Sync OT from MongoDB to ERPNext")
            print("  6. Sync User Info from ERPNext to Device")
            print("  7. Sync from Master Device to ERPNext")
            print("  8. Clean User on Machine")
            print("  9. Delete OT in ERPNext Database")
            print(" 10. Sync All from Master to Other Devices")
            print("\n  0. Exit")
            print(f"{'='*80}")

            choice = input("\nSelect function (0-10): ").strip()

            if choice == '0':
                print("Exiting...")
                break
            elif choice == '1':
                self.execute_end_of_day_resync()
            elif choice == '2':
                self.execute_clear_left_templates()
            elif choice == '3':
                # Execute clean old logs
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("clean_old_logs",
                        os.path.join(current_dir, "03.clean_old_logs.py"))
                    clean_logs = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(clean_logs)

                    # Prompt for number of days to keep
                    days_to_keep = prompt_integer(
                        f"Enter number of recent days to keep logs (current: {local_config.CLEAN_OLD_LOGS_DAYS})",
                        default_value=local_config.CLEAN_OLD_LOGS_DAYS,
                        min_value=0
                    )
                    if days_to_keep is None:
                        self.log_operation("Operation cancelled by user", "WARNING")
                        continue

                    # Temporarily override config
                    original_clean_days = local_config.CLEAN_OLD_LOGS_DAYS
                    local_config.CLEAN_OLD_LOGS_DAYS = days_to_keep

                    try:
                        clean_logs.run_cleanup(dry_run=False, force=True)
                    finally:
                        # Restore original config
                        local_config.CLEAN_OLD_LOGS_DAYS = original_clean_days

                except Exception as e:
                    self.log_operation(f"Clean old logs error: {e}", "ERROR")
            elif choice == '4':
                self.execute_mongodb_sync()
            elif choice == '5':
                self.execute_ot_mongodb_sync()
            elif choice == '6':
                self.execute_sync_user_info_from_erpnext_to_device()
            elif choice == '7':
                self.execute_sync_from_master_device_to_erpnext()
            elif choice == '8':
                self.execute_clean_user_on_machine()
            elif choice == '9':
                self.execute_delete_ot_in_erpnext_db()
            elif choice == '10':
                self.execute_sync_all_from_master_to_other_devices()
            else:
                print("Invalid choice. Please select 0-10.")

            input("\nPress Enter to continue...")

    def show_status(self):
        """Show current configuration status"""
        print(f"\n{'='*60}")
        print(f" {self.tool_name} v{self.version}")
        print(f" Configuration Status")
        print(f"{'='*60}")

        print(f"\nERPNext Configuration:")
        print(f"  URL: {local_config.ERPNEXT_URL}")
        print(f"  API Key: {local_config.ERPNEXT_API_KEY[:8]}...")
        print(f"  Devices: {len(local_config.devices)}")

        print(f"\nManual Operations:")
        print(f"  Resync: Run with --resync or menu option 1")
        print(f"  Time Sync: Run with --time-sync or menu option (max diff: {TIME_SYNC_MAX_DIFF_SECONDS}s)")
        print(f"  Time Sync & Restart: Run with --time-sync-and-restart")

        print(f"\nMongoDB Sync:")
        if getattr(local_config, 'ENABLE_SYNC_LOG_FROM_MONGODB_TO_ERPNEXT', False):
            print(f"  Attendance Log: ENABLED")
            print(f"    Host: {local_config.MONGODB_HOST}:{local_config.MONGODB_PORT}")
            print(f"    Database: {local_config.MONGODB_DATABASE}")
        else:
            print(f"  Attendance Log: DISABLED")

        if getattr(local_config, 'ENABLE_SYNC_OT_FROM_MONGODB_TO_ERPNEXT', False):
            print(f"  OT Sync: ENABLED")
            start_date = getattr(local_config, 'SYNC_OT_FROM_MONGODB_TO_ERPNEXT_START_DATE', 'Not set')
            print(f"    Start date: {start_date}")
        else:
            print(f"  OT Sync: DISABLED")

        print(f"\nClear Left Employee Templates:")
        if local_config.ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES:
            print(f"  Status: ENABLED")
            print(f"  Delay days: {local_config.CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS}")
            print(f"  Delete after days: {local_config.ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS}")

            # Show date-of-month restriction
            date_filter = getattr(local_config, 'CLEAR_LEFT_USER_TEMPLATES_ON_DATE_OF_MONTH', [])
            if date_filter:
                print(f"  Run on days: {date_filter} (of each month)")
            else:
                print(f"  Run on days: Every day")
        else:
            print(f"  Status: DISABLED (use --clear-templates to run manually)")

        last_run = local_config.get_last_clear_left_templates_date()
        if last_run:
            print(f"  Last run: {last_run}")
        else:
            print(f"  Last run: Never")

        print(f"\n{'='*60}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Manual Resync Data Tool for ERPNext Biometric Attendance Sync',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                             Show interactive menu
  %(prog)s --status                    Show configuration status
  %(prog)s --resync                    Run end-of-day resync for today
  %(prog)s --resync --date-range 20251101 20251115    Resync specific date range
  %(prog)s --time-sync                 Sync time to all devices
  %(prog)s --time-sync --force         Force time sync even if within tolerance
  %(prog)s --restart-devices           Restart all devices
  %(prog)s --time-sync-and-restart     Sync time and restart devices
  %(prog)s --mongodb-sync              Sync attendance from MongoDB
  %(prog)s --ot-mongodb-sync           Sync OT from MongoDB
  %(prog)s --clear-templates           Clear left employee templates
  %(prog)s --clear-templates --force   Force clear even if already run today
  %(prog)s --sync-user-info            Sync user info from ERPNext to devices
  %(prog)s --sync-from-master          Sync from master device to ERPNext
  %(prog)s --sync-all-from-master      Sync all users from master to other devices
  %(prog)s --clean-user                Clean user on machines
  %(prog)s --delete-ot                 Delete OT in ERPNext database
  %(prog)s --all                       Run all operations
        """
    )

    # Operation arguments
    parser.add_argument('--resync', action='store_true',
                       help='Run end-of-day resync cycle')
    parser.add_argument('--time-sync', action='store_true',
                       help='Sync time to all devices')
    parser.add_argument('--restart-devices', action='store_true',
                       help='Restart all devices')
    parser.add_argument('--time-sync-and-restart', action='store_true',
                       help='Sync time and restart all devices')
    parser.add_argument('--mongodb-sync', action='store_true',
                       help='Sync attendance logs from MongoDB to ERPNext')
    parser.add_argument('--ot-mongodb-sync', action='store_true',
                       help='Sync OT records from MongoDB to ERPNext')
    parser.add_argument('--clear-templates', action='store_true',
                       help='Clear left employee templates from devices')
    parser.add_argument('--sync-user-info', action='store_true',
                       help='Sync user info from ERPNext to devices')
    parser.add_argument('--sync-from-master', action='store_true',
                       help='Sync from master device to ERPNext')
    parser.add_argument('--sync-all-from-master', action='store_true',
                       help='Sync all users from master to other devices')
    parser.add_argument('--clean-user', action='store_true',
                       help='Clean user on machines')
    parser.add_argument('--delete-ot', action='store_true',
                       help='Delete OT in ERPNext database')
    parser.add_argument('--all', action='store_true',
                       help='Run all operations')

    # Options
    parser.add_argument('--status', action='store_true',
                       help='Show configuration status')
    parser.add_argument('--date-range', nargs=2, metavar=('START', 'END'),
                       help='Date range for resync in YYYYMMDD format')
    parser.add_argument('--force', action='store_true',
                       help='Force run even for daily-limited operations')
    parser.add_argument('--version', action='store_true',
                       help='Show version information')

    args = parser.parse_args()

    # Show version
    if args.version:
        print(f"Manual Resync Data Tool v1.0.0")
        return

    # Initialize tool
    tool = ManualResyncTool()

    # Show status
    if args.status:
        tool.show_status()
        return

    # Check if any operation is specified
    any_operation = (args.resync or args.time_sync or args.restart_devices or
                     args.time_sync_and_restart or args.mongodb_sync or
                     args.ot_mongodb_sync or args.clear_templates or
                     args.sync_user_info or args.sync_from_master or
                     args.clean_user or args.delete_ot or args.all)

    if not any_operation:
        # Show interactive menu if no arguments provided
        tool.show_interactive_menu()
        return

    # Process date range
    date_range = None
    if args.date_range:
        date_range = args.date_range

    # Run requested operations
    success = True

    try:
        if args.all:
            success = tool.execute_all_operations(date_range=date_range, force=args.force)
        else:
            if args.resync:
                if not tool.execute_end_of_day_resync(date_range):
                    success = False

            if args.time_sync:
                result = tool.execute_time_sync_to_devices(force=args.force)
                if result.get('failed_count', 0) > 0:
                    success = False

            if args.restart_devices:
                result = tool.execute_restart_all_devices()
                if result.get('failed_count', 0) > 0:
                    success = False

            if args.time_sync_and_restart:
                if not tool.execute_time_sync_and_restart(force=args.force):
                    success = False

            if args.mongodb_sync:
                if not tool.execute_mongodb_sync():
                    success = False

            if args.ot_mongodb_sync:
                if not tool.execute_ot_mongodb_sync():
                    success = False

            if args.clear_templates:
                if not tool.execute_clear_left_templates(force=args.force):
                    success = False

            if args.sync_user_info:
                if not tool.execute_sync_user_info_from_erpnext_to_device():
                    success = False

            if args.sync_from_master:
                if not tool.execute_sync_from_master_device_to_erpnext():
                    success = False

            if args.sync_all_from_master:
                if not tool.execute_sync_all_from_master_to_other_devices():
                    success = False

            if args.clean_user:
                if not tool.execute_clean_user_on_machine():
                    success = False

            if args.delete_ot:
                if not tool.execute_delete_ot_in_erpnext_db():
                    success = False

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
