#!/usr/bin/env python3
"""
ERPNext Biometric Attendance Sync Service
Master service that coordinates erpnext_sync and sync_from_erpnext_to_device
with time-based bypass logic and auto-restart capability
"""

import os
import sys
import time
import datetime
import signal
import traceback

# Add current directory to path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import local_config

class ERPNextSyncService:
    def __init__(self):
        self.service_name = "ERPNext Biometric Sync Service"
        self.version = "1.0.0"
        self.start_time = datetime.datetime.now()
        self.cycle_count = 0
        self.error_count = 0
        self.last_error = None
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.log_startup()
    
    def log_startup(self):
        """Log service startup information"""
        print(f"[{self.start_time}] Service started v{self.version}, freq={local_config.PULL_FREQUENCY}min")
    
    def signal_handler(self, signum, _frame):
        """Handle shutdown signals gracefully"""
        print(f"\n[{datetime.datetime.now()}] Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def reload_dynamic_config(self):
        """Reload dynamic configuration module"""
        try:
            import importlib
            importlib.reload(local_config)
            return True
        except Exception as e:
            return False
    
    def execute_erpnext_sync(self, bypass_device_connection=False, force_resync=False):
        """Execute erpnext_sync.py with optional device bypass"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("sync_log_from_device_to_erpnext",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "01.sync_log_from_device_to_erpnext.py"))
            sync_log_from_device_to_erpnext = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_log_from_device_to_erpnext)

            if bypass_device_connection and not force_resync:
                return True
            else:
                success = sync_log_from_device_to_erpnext.run_single_cycle(bypass_device_connection=bypass_device_connection)
                if not success:
                    print(f"[{datetime.datetime.now()}] Sync failed")
                return success

        except Exception as e:
            print(f"[{datetime.datetime.now()}] Sync error: {e}")
            return False
    
    def execute_clear_left_templates(self):
        """Execute clear left employee templates (once per day)"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("module",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "02.clean_data_employee_left.py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            CleanDataEmployeeLeft = module.CleanDataEmployeeLeft
            cleaner = CleanDataEmployeeLeft()

            if not cleaner.test_erpnext_connection():
                return False

            left_employees = cleaner.get_left_employees_for_cleanup()

            if not left_employees:
                local_config.set_last_clear_left_templates_date()
                return True

            successful_cleanups = 0

            for employee_data in left_employees:
                employee_id = employee_data["employee_id"]

                if local_config.ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_ERPNEXT:
                    cleaner.delete_employee_fingerprints_from_erpnext(employee_id)

                result = cleaner.clean_left_employee_complete(employee_data)
                if result["success"]:
                    successful_cleanups += 1

            local_config.set_last_clear_left_templates_date()
            print(f"[{datetime.datetime.now()}] Cleared {successful_cleanups}/{len(left_employees)} templates")
            return successful_cleanups > 0

        except Exception as e:
            print(f"[{datetime.datetime.now()}] Clear template error: {e}")
            return False

    def execute_mongodb_sync(self):
        """Execute MongoDB to ERPNext sync"""
        try:
            if not getattr(local_config, 'ENABLE_SYNC_LOG_FROM_MONGODB_TO_ERPNEXT', False):
                return True

            import importlib.util
            spec = importlib.util.spec_from_file_location("sync_log_from_mongodb_to_erpnext",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "04.sync_log_from_mongodb_to_erpnext.py"))
            sync_log_from_mongodb_to_erpnext = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_log_from_mongodb_to_erpnext)
            result = sync_log_from_mongodb_to_erpnext.run_mongodb_sync()

            if result['success']:
                details = result['details']
                print(f"[{datetime.datetime.now()}] MongoDB: {details['processed']}/{details['total_records']}, skip={details['skipped']}, err={details['errors']}")
                return True
            else:
                print(f"[{datetime.datetime.now()}] MongoDB sync failed: {result['message']}")
                return False

        except Exception as e:
            print(f"[{datetime.datetime.now()}] MongoDB error: {e}")
            return False

    def execute_ot_mongodb_sync(self):
        """Execute OT sync from MongoDB to ERPNext"""
        try:
            if not getattr(local_config, 'ENABLE_SYNC_OT_FROM_MONGODB_TO_ERPNEXT', False):
                return True

            import importlib.util
            spec = importlib.util.spec_from_file_location("sync_ot_from_mongodb_to_erpnext",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "05.sync_ot_from_mongodb_to_erpnext.py"))
            sync_ot_from_mongodb_to_erpnext = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_ot_from_mongodb_to_erpnext)
            syncer = sync_ot_from_mongodb_to_erpnext.OTSyncFromMongoDB()
            result = syncer.sync_ot_to_erpnext()

            if result['success']:
                print(f"[{datetime.datetime.now()}] OT MongoDB: {result['created']}/{result['total_records']}, skip={result['skipped']}, fail={result['failed']}")
                return True
            else:
                print(f"[{datetime.datetime.now()}] OT MongoDB failed: {result['message']}")
                return False

        except Exception as e:
            print(f"[{datetime.datetime.now()}] OT MongoDB error: {e}")
            return False

    def should_run_clean_logs(self):
        """Check if should run log cleanup (once per day)"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("clean_old_logs",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "03.clean_old_logs.py"))
            clean_old_logs = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(clean_old_logs)
            return clean_old_logs.should_run_cleanup()
        except Exception as e:
            print(f"Error checking clean logs status: {e}")
            return False

    def execute_clean_logs(self):
        """Execute old log files cleanup (once per day)"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("clean_old_logs",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "03.clean_old_logs.py"))
            clean_old_logs = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(clean_old_logs)
            result = clean_old_logs.run_cleanup(dry_run=False, force=False)

            if result["success"]:
                print(f"[{datetime.datetime.now()}] Cleaned {result.get('cleaned_files', 0)} files, freed {clean_old_logs.format_size(result.get('total_size_freed', 0))}")
            return True

        except Exception as e:
            print(f"[{datetime.datetime.now()}] Clean logs error: {e}")
            return False
    
    def execute_cycle(self):
        """Execute one complete sync cycle"""
        cycle_start = datetime.datetime.now()
        self.cycle_count += 1

        print(f"[{cycle_start}] Cycle #{self.cycle_count}")

        self.reload_dynamic_config()
        local_config.log_bypass_status()

        cycle_success = True

        log_bypass, log_period = local_config.should_bypass_log_sync()

        if not log_bypass:
            local_config.log_operation_decision("Sync Log", True, "Active")
            if not self.execute_erpnext_sync(bypass_device_connection=log_bypass):
                cycle_success = False
        else:
            local_config.log_operation_decision("Sync Log", False, log_period.get('reason', 'Bypass'))

        if local_config.should_run_clear_left_templates():
            local_config.log_operation_decision("Clear Templates", True, "First run")
            self.execute_clear_left_templates()

        if self.should_run_clean_logs():
            local_config.log_operation_decision("Clean Logs", True, "First run")
            self.execute_clean_logs()

        # MongoDB sync (if enabled)
        if getattr(local_config, 'ENABLE_SYNC_LOG_FROM_MONGODB_TO_ERPNEXT', False):
            local_config.log_operation_decision("MongoDB Sync", True, "Enabled")
            self.execute_mongodb_sync()

        # OT MongoDB sync (if enabled)
        if getattr(local_config, 'ENABLE_SYNC_OT_FROM_MONGODB_TO_ERPNEXT', False):
            local_config.log_operation_decision("OT MongoDB Sync", True, "Enabled")
            self.execute_ot_mongodb_sync()

        cycle_duration = (datetime.datetime.now() - cycle_start).total_seconds()

        if not cycle_success:
            print(f"[{datetime.datetime.now()}] Cycle #{self.cycle_count} errors, {cycle_duration:.1f}s")
            self.error_count += 1
            self.last_error = datetime.datetime.now()

        return cycle_success

    def run(self):
        """Main service loop"""
        print(f"[{self.start_time}] Service started")

        while self.running:
            try:
                self.execute_cycle()

                if not self.running:
                    break

                sleep_seconds = local_config.PULL_FREQUENCY * 60
                next_run = datetime.datetime.now() + datetime.timedelta(seconds=sleep_seconds)

                print(f"[{datetime.datetime.now()}] Sleep {local_config.PULL_FREQUENCY}min, next: {next_run.strftime('%H:%M:%S')}")

                sleep_start = time.time()
                while (time.time() - sleep_start) < sleep_seconds and self.running:
                    time.sleep(1)

            except KeyboardInterrupt:
                print(f"[{datetime.datetime.now()}] Interrupted")
                break
            except Exception as e:
                self.error_count += 1
                self.last_error = datetime.datetime.now()
                print(f"[{datetime.datetime.now()}] Error: {e}")
                time.sleep(15)

        self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown with summary"""
        end_time = datetime.datetime.now()
        runtime = end_time - self.start_time

        print(f"[{end_time}] Shutdown: runtime={runtime}, cycles={self.cycle_count}, errors={self.error_count}")
    
    def status(self):
        """Return service status information"""
        current_time = datetime.datetime.now()
        runtime = current_time - self.start_time
        
        return {
            "service_name": self.service_name,
            "version": self.version,
            "status": "running" if self.running else "stopped",
            "start_time": self.start_time,
            "current_time": current_time,
            "runtime": str(runtime),
            "cycle_count": self.cycle_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "pull_frequency": local_config.PULL_FREQUENCY
        }

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ERPNext Biometric Attendance Sync Service')
    parser.add_argument('--test-config', action='store_true', 
                       help='Test dynamic configuration and exit')
    parser.add_argument('--status', action='store_true',
                       help='Show service configuration status')
    parser.add_argument('--version', action='store_true',
                       help='Show version information')
    
    args = parser.parse_args()
    
    if args.version:
        print(f"ERPNext Biometric Sync Service v1.0.0")
        return
    
    if args.test_config:
        print("Testing dynamic configuration...")
        try:
            local_config.log_bypass_status()
            print("✓ Configuration test completed successfully")
        except Exception as e:
            print(f"✗ Configuration test failed: {e}")
            sys.exit(1)
        return
    
    if args.status:
        print("Service Configuration Status:")
        print(f"  Pull frequency: {local_config.PULL_FREQUENCY} minutes")
        print(f"  ERPNext URL: {local_config.ERPNEXT_URL}")
        print(f"  Number of devices: {len(local_config.devices)}")
        
        # Display re-sync status
        if hasattr(local_config, 're_sync_data_date_range') and local_config.re_sync_data_date_range:
            print(f"  🔄 Re-sync mode: ENABLED")
            print(f"    Date range: {local_config.re_sync_data_date_range[0]} to {local_config.re_sync_data_date_range[1]}")
            print(f"    Action: Sync ALL logs in this period (fill missing entries)")
        else:
            print(f"  📅 Re-sync mode: DISABLED (normal processing)")
        
        # Display end-of-day re-sync status (moved to resync_data_manual.py)
        print(f"  🌙 End-of-day re-sync: MOVED to resync_data_manual.py")
        print(f"    Run: python resync_data_manual.py --resync")

        # Display time sync & restart status (moved to resync_data_manual.py)
        print(f"  🕒 Time sync & restart: MOVED to resync_data_manual.py")
        print(f"    Run: python resync_data_manual.py --time-sync-and-restart")

        # Display MongoDB sync status
        if getattr(local_config, 'ENABLE_SYNC_LOG_FROM_MONGODB_TO_ERPNEXT', False):
            print(f"  🗃️ MongoDB sync: ENABLED")
            date_range = getattr(local_config, 'sync_log_from_mongodb_to_erpnext_date_range', [])
            if date_range and len(date_range) == 2:
                print(f"    Date range: {date_range[0]} to {date_range[1]}")
            else:
                print(f"    Mode: Current date only")
            print(f"    Runs during: End-of-day cycle")
        else:
            print(f"  🗃️ MongoDB sync: DISABLED")

        # Display OT MongoDB sync status
        if getattr(local_config, 'ENABLE_SYNC_OT_FROM_MONGODB_TO_ERPNEXT', False):
            print(f"  📋 OT MongoDB sync: ENABLED")
            start_date = getattr(local_config, 'SYNC_OT_FROM_MONGODB_TO_ERPNEXT_START_DATE', 'Not configured')
            print(f"    Start date filter: {start_date}")
            print(f"    Runs during: End-of-day cycle (after MongoDB sync)")
        else:
            print(f"  📋 OT MongoDB sync: DISABLED")

        local_config.log_bypass_status()
        return
    
    # Start the service
    service = ERPNextSyncService()
    try:
        service.run()
    except Exception as e:
        print(f"Fatal service error: {e}")
        print(f"Error details: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()