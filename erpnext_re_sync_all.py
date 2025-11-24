#!/usr/bin/env python3
"""
Manual Resync Data Tool for ERPNext Biometric Attendance Sync
This tool provides manual execution of resync and maintenance functions
that were previously automated in erpnext_sync_all.py

Usage:
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

import local_config


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
                       If None, uses today's date.

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

            # Get date range
            if date_range is None:
                date_range = local_config.get_end_of_day_resync_date_range()

            self.log_operation(f"Target date range: {date_range[0]} to {date_range[1]}")

            # Save original config
            original_resync_config = getattr(local_config, 're_sync_data_date_range', [])

            try:
                # Set date range for resync
                local_config.re_sync_data_date_range = date_range

                # Log to resync log file
                local_config.log_resync_operation(f"MANUAL RESYNC START - Date: {date_range[0]} to {date_range[1]}")

                # Execute sync
                self.log_operation("Executing sync from devices to ERPNext...")
                success = sync_log_from_device_to_erpnext.run_single_cycle(bypass_device_connection=False)

                if success:
                    local_config.log_resync_operation("MANUAL RESYNC OK")
                    self.log_operation("End-of-day resync completed successfully")
                else:
                    local_config.log_resync_operation("MANUAL RESYNC FAILED", "ERROR")
                    self.log_operation("End-of-day resync failed", "ERROR")

                self.log_section_end("END-OF-DAY RESYNC", success)
                return success

            finally:
                # Restore original config
                local_config.re_sync_data_date_range = original_resync_config

        except Exception as e:
            self.log_operation(f"End-of-day resync error: {e}", "ERROR")
            local_config.log_resync_operation(f"MANUAL RESYNC ERROR: {e}", "ERROR")
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
            self.log_operation(f"Max time diff threshold: {local_config.TIME_SYNC_MAX_DIFF_SECONDS}s")
            self.log_operation(f"Connection timeout: {local_config.TIME_SYNC_TIMEOUT_SECONDS}s")

            # Execute time sync
            results = local_config.sync_time_to_devices(force=force)

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
            results = local_config.restart_all_devices()

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
        """Execute MongoDB to ERPNext sync

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

            import importlib.util
            spec = importlib.util.spec_from_file_location("sync_log_from_mongodb_to_erpnext",
                os.path.join(current_dir, "04.sync_log_from_mongodb_to_erpnext.py"))
            sync_log_from_mongodb_to_erpnext = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_log_from_mongodb_to_erpnext)

            self.log_operation("Starting MongoDB sync...")
            self.log_operation(f"MongoDB Host: {local_config.MONGODB_HOST}:{local_config.MONGODB_PORT}")
            self.log_operation(f"Database: {local_config.MONGODB_DATABASE}")
            self.log_operation(f"Collection: {local_config.MONGODB_ATTLOG_COLLECTION}")

            date_range = getattr(local_config, 'sync_log_from_mongodb_to_erpnext_date_range', [])
            if date_range and len(date_range) == 2:
                self.log_operation(f"Date range: {date_range[0]} to {date_range[1]}")
            else:
                self.log_operation("Date range: Last 7 days (default)")

            result = sync_log_from_mongodb_to_erpnext.run_mongodb_sync()

            if result['success']:
                details = result['details']
                self.log_operation(f"Processed: {details['processed']}/{details['total_records']}")
                self.log_operation(f"Skipped: {details['skipped']}")
                self.log_operation(f"Errors: {details['errors']}")
                self.log_section_end("MONGODB TO ERPNEXT SYNC", True)
                return True
            else:
                self.log_operation(f"MongoDB sync failed: {result['message']}", "ERROR")
                self.log_section_end("MONGODB TO ERPNEXT SYNC", False)
                return False

        except Exception as e:
            self.log_operation(f"MongoDB sync error: {e}", "ERROR")
            self.log_section_end("MONGODB TO ERPNEXT SYNC", False)
            return False

    def execute_ot_mongodb_sync(self):
        """Execute OT sync from MongoDB to ERPNext

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

            import importlib.util
            spec = importlib.util.spec_from_file_location("sync_ot_from_mongodb_to_erpnext",
                os.path.join(current_dir, "05.sync_ot_from_mongodb_to_erpnext.py"))
            sync_ot_from_mongodb_to_erpnext = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_ot_from_mongodb_to_erpnext)

            self.log_operation("Starting OT MongoDB sync...")
            self.log_operation(f"MongoDB Host: {local_config.MONGODB_HOST}:{local_config.MONGODB_PORT}")
            self.log_operation(f"Database: {local_config.MONGODB_DATABASE}")
            self.log_operation(f"Collection: {local_config.MONGODB_OT_COLLECTION}")

            start_date = getattr(local_config, 'SYNC_OT_FROM_MONGODB_TO_ERPNEXT_START_DATE', 'Not configured')
            self.log_operation(f"Start date filter: {start_date}")

            syncer = sync_ot_from_mongodb_to_erpnext.OTSyncFromMongoDB()
            result = syncer.sync_ot_to_erpnext()

            if result['success']:
                self.log_operation(f"Total records: {result['total_records']}")
                self.log_operation(f"Created: {result['created']}")
                self.log_operation(f"Skipped: {result['skipped']}")
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

    def execute_clear_left_templates(self, force=False):
        """Execute clear left employee templates

        COPIED from erpnext_sync_all.py - available both here and in automated service

        Args:
            force: Force run even if already run today

        Returns:
            bool: True if successful
        """
        self.log_section_start("CLEAR LEFT EMPLOYEE TEMPLATES")

        try:
            # Check if should run (once per day)
            if not force and not local_config.should_run_clear_left_templates():
                last_run = local_config.get_last_clear_left_templates_date()
                self.log_operation(f"Already run today. Last run: {last_run}")
                self.log_operation("Use --force to run anyway")
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

            self.log_operation(f"Cleared {successful_cleanups}/{len(left_employees)} employees")
            success = successful_cleanups > 0 or len(left_employees) == 0
            self.log_section_end("CLEAR LEFT EMPLOYEE TEMPLATES", success)
            return success

        except Exception as e:
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

        print(f"\nEnd-of-Day Re-sync:")
        if local_config.ENABLE_RESYNC_ON_DAY:
            print(f"  Status: ENABLED (use --resync to run manually)")
            print(f"  Schedule: {', '.join(local_config.TIME_RESYNC_ON_DAY)}")
            print(f"  Window: +/- {local_config.RESYNC_WINDOW_MINUTES_ON_DAY // 2} minutes")
        else:
            print(f"  Status: DISABLED (use --resync to run manually)")

        print(f"\nTime Sync & Restart:")
        if local_config.ENABLE_TIME_SYNC_AND_RESTART_AT_23H_OF_SUNDAY:
            print(f"  Status: ENABLED (use --time-sync-and-restart to run manually)")
            print(f"  Schedule: Sunday 23:00")
            print(f"  Max time diff: {local_config.TIME_SYNC_MAX_DIFF_SECONDS}s")
        else:
            print(f"  Status: DISABLED (use --time-sync-and-restart to run manually)")

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
                     args.ot_mongodb_sync or args.clear_templates or args.all)

    if not any_operation:
        parser.print_help()
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
