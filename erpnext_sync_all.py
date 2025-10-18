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
        print("\n" + "=" * 80)
        print(f"{self.service_name} v{self.version}")
        print(f"Started at: {self.start_time}")
        print(f"Pull frequency: {local_config.PULL_FREQUENCY} minutes")
        print(f"Working directory: {current_dir}")
        
        # Display re-sync configuration if available
        if hasattr(local_config, 're_sync_data_date_range') and local_config.re_sync_data_date_range:
            print(f"🔄 RE-SYNC MODE: Date range {local_config.re_sync_data_date_range[0]} to {local_config.re_sync_data_date_range[1]}")
            print("   - Will sync ALL logs in this period to fill missing entries")
            print("   - Duplicate entries will be automatically skipped (no error logs)")
            print("   - Existing records will NOT be deleted")
        else:
            print("📅 NORMAL MODE: Processing only new attendance logs")
        
        # Display end-of-day re-sync configuration
        if local_config.ENABLE_RESYNC_ON_DAY:
            print(f"🌙 END-OF-DAY RE-SYNC: ENABLED")
            print(f"   - Schedule: {', '.join(local_config.TIME_RESYNC_ON_DAY)} daily")
            print(f"   - Window: ±{local_config.RESYNC_WINDOW_MINUTES_ON_DAY//2} minutes")
            print(f"   - Will re-sync ALL logs for current day")
        else:
            print(f"🌙 END-OF-DAY RE-SYNC: DISABLED")

        # Display MongoDB sync configuration
        if getattr(local_config, 'ENABLE_SYNC_LOG_FROM_MONGODB_TO_ERPNEXT', False):
            print(f"🗃️ MONGODB SYNC: ENABLED")
            date_range = getattr(local_config, 'sync_log_from_mongodb_to_erpnext_date_range', [])
            if date_range and len(date_range) == 2:
                print(f"   - Date range: {date_range[0]} to {date_range[1]}")
            else:
                print(f"   - Mode: Current date only")
            print(f"   - Runs during end-of-day cycle")
        else:
            print(f"🗃️ MONGODB SYNC: DISABLED")

        # Display OT MongoDB sync configuration
        if getattr(local_config, 'ENABLE_SYNC_OT_FROM_MONGODB_TO_ERPNEXT', False):
            print(f"📋 OT MONGODB SYNC: ENABLED")
            start_date = getattr(local_config, 'SYNC_OT_FROM_MONGODB_TO_ERPNEXT_START_DATE', 'Not configured')
            print(f"   - Start date filter: {start_date}")
            print(f"   - Runs during end-of-day cycle (after MongoDB sync)")
        else:
            print(f"📋 OT MONGODB SYNC: DISABLED")

        print("=" * 80)
    
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
            print(f"✗ Failed to reload dynamic config: {e}")
            return False
    
    def execute_erpnext_sync(self, bypass_device_connection=False, force_resync=False):
        """Execute erpnext_sync.py with optional device bypass"""
        try:
            if force_resync:
                print(f"\n[{datetime.datetime.now()}] Starting FORCED ERPNext sync (End-of-day re-sync)...")
            else:
                print(f"\n[{datetime.datetime.now()}] Starting ERPNext sync...")
            
            # Import and execute sync_log_from_device_to_erpnext functionality
            import sync_log_from_device_to_erpnext
            
            if bypass_device_connection and not force_resync:
                print("⚠ Device connection bypassed - skipping device data fetch")
                return True
            else:
                # Execute single cycle (avoid infinite loop)
                success = sync_log_from_device_to_erpnext.run_single_cycle(bypass_device_connection=bypass_device_connection)
                if success:
                    if force_resync:
                        print("✓ FORCED Sync log từ device đến ERPNext hoàn thành")
                    else:
                        print("✓ Sync log từ device đến ERPNext hoàn thành")
                    return True
                else:
                    if force_resync:
                        print("✗ FORCED Sync log từ device đến ERPNext thất bại")
                    else:
                        print("✗ Sync log từ device đến ERPNext thất bại")
                    return False
                
        except Exception as e:
            print(f"✗ ERPNext sync failed: {e}")
            print(f"  Error details: {traceback.format_exc()}")
            return False
    
    def execute_sync_user_info_from_erpnext_to_device(self):
        """Execute sync_user_info_from_erpnext_to_device"""
        try:
            print(f"\n[{datetime.datetime.now()}] Bắt đầu sync user info từ ERPNext đến devices...")

            # Import the sync module
            from sync_user_info_from_erpnext_to_device import ERPNextSyncToDeviceStandalone

            # Create sync instance
            sync_tool = ERPNextSyncToDeviceStandalone()

            # Determine sync mode based on dynamic config
            sync_mode = local_config.SYNC_USER_INFO_MODE

            if sync_mode == 'full':
                print("  Chế độ: Full sync")
                result = sync_tool.sync_full()
            elif sync_mode == 'changed':
                hours_back = local_config.SYNC_CHANGED_HOURS_BACK
                since_datetime = datetime.datetime.now() - datetime.timedelta(hours=hours_back)
                print(f"  Chế độ: Changed sync (últimos {hours_back} horas)")
                result = sync_tool.sync_changed(since_datetime)
            else:  # auto mode
                print("  Chế độ: Auto sync")
                result = sync_tool.auto_sync()

            if result["success"]:
                print("✓ Sync user info từ ERPNext đến devices hoàn thành")
                print(f"  {result.get('message', 'Không có chi tiết')}")
                return True
            else:
                print(f"✗ Sync user info từ ERPNext đến devices thất bại: {result.get('message', 'Lỗi không xác định')}")
                return False

        except Exception as e:
            print(f"✗ Sync user info từ ERPNext đến devices thất bại: {e}")
            print(f"  Chi tiết lỗi: {traceback.format_exc()}")
            return False

    def execute_clear_left_templates(self):
        """Execute clear left employee templates (once per day)"""
        try:
            delay_days = getattr(local_config, 'CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS', 7)
            delete_after_days = getattr(local_config, 'ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS', 0)

            print(f"\n[{datetime.datetime.now()}] Bắt đầu xóa template/user nhân viên nghỉ việc...")
            print(f"  📋 Ưu tiên xử lý (kiểm tra theo thứ tự):")
            if delete_after_days > 0:
                print(f"     1. XÓA HOÀN TOÀN user: nhân viên nghỉ > {delete_after_days} ngày (ƯUTIÊN)")
            else:
                print(f"     1. Xóa hoàn toàn user: TẮT")
            print(f"     2. Xóa template (tạo lại user): nhân viên nghỉ >= {delay_days} ngày (nếu không thuộc mục 1)")

            # Import the cleanup module
            import sys
            import os
            manual_functions_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manual_run_functions')
            if manual_functions_path not in sys.path:
                sys.path.insert(0, manual_functions_path)

            from clean_data_employee_left import CleanDataEmployeeLeft

            # Create cleaner instance
            cleaner = CleanDataEmployeeLeft()

            # Check ERPNext connection
            if not cleaner.test_erpnext_connection():
                print("✗ Không thể kết nối ERPNext API")
                return False

            # Get left employees (filtered to only recently left employees)
            left_employees = cleaner.get_left_employees_for_cleanup()

            if not left_employees:
                print("  Không có nhân viên nghỉ việc nào đủ điều kiện xử lý")
                print(f"  (Không có nhân viên trong cửa sổ xử lý)")
                # Mark as run even if no employees to process
                local_config.set_last_clear_left_templates_date()
                return True

            print(f"  Tìm thấy {len(left_employees)} nhân viên đủ điều kiện xử lý")

            # Process each employee
            successful_cleanups = 0

            for i, employee_data in enumerate(left_employees, 1):
                employee_id = employee_data["employee_id"]
                employee_name = employee_data["employee"]

                print(f"\n  [{i}/{len(left_employees)}] Xử lý {employee_name}...")

                # Step 1: Delete from ERPNext if enabled
                if local_config.ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_ERPNEXT:
                    print(f"    Xóa fingerprints từ ERPNext...")
                    erpnext_result = cleaner.delete_employee_fingerprints_from_erpnext(employee_id)
                    if erpnext_result["success"]:
                        print(f"    ✓ ERPNext: Đã xóa {erpnext_result['deleted_count']} fingerprint records")
                    else:
                        print(f"    ✗ ERPNext: {erpnext_result['message']}")

                # Step 2: Clear templates from devices
                print(f"    Xóa templates từ devices...")
                result = cleaner.clean_left_employee_complete(employee_data)

                if result["success"]:
                    successful_cleanups += 1
                    print(f"    ✓ {result['message']}")
                else:
                    print(f"    ✗ {result['message']}")

            # Mark as run today
            local_config.set_last_clear_left_templates_date()

            print(f"\n✓ Hoàn thành xóa template: {successful_cleanups}/{len(left_employees)} nhân viên")
            return successful_cleanups > 0

        except Exception as e:
            print(f"✗ Lỗi khi xóa template nhân viên nghỉ việc: {e}")
            print(f"  Chi tiết lỗi: {traceback.format_exc()}")
            return False

    def execute_time_sync(self):
        """Execute time synchronization from server to devices""" 
        try:
            print(f"\n[{datetime.datetime.now()}] Bắt đầu đồng bộ giờ từ server đến devices...")

            # Check if time sync is enabled
            if not local_config.ENABLE_TIME_SYNC:
                print("  Time sync disabled in configuration")
                return True

            # Execute time sync
            results = local_config.sync_time_to_devices()

            # Display results
            print(f"📊 TIME SYNC SUMMARY:")
            print(f"   Total devices: {results['total_devices']}")
            print(f"   Successfully synced: {results['success_count']}")
            print(f"   Skipped (within tolerance): {results['skipped_count']}")
            print(f"   Failed: {results['failed_count']}")

            # Show details for failed or synced devices
            for detail in results['details']:
                if detail['success'] and detail['new_time']:
                    time_diff = detail['time_diff_seconds']
                    print(f"   ✅ {detail['device_id']}: Synced (diff: {time_diff:.1f}s)")
                elif detail['success'] and not detail['new_time']:
                    time_diff = detail['time_diff_seconds']
                    print(f"   ⏭️ {detail['device_id']}: Skipped (diff: {time_diff:.1f}s)")
                else:
                    print(f"   ❌ {detail['device_id']}: {detail['message']}")

            # Consider success if at least some devices were processed
            success_or_skipped = results['success_count'] + results['skipped_count']
            if success_or_skipped > 0:
                print("✓ Time sync hoàn thành")
                return True
            else:
                print("⚠ Time sync hoàn thành nhưng không có device nào được sync")
                return False

        except Exception as e:
            print(f"✗ Time sync thất bại: {e}")
            print(f"  Chi tiết lỗi: {traceback.format_exc()}")
            return False

    def execute_mongodb_sync(self):
        """Execute MongoDB to ERPNext sync"""
        try:
            print(f"\n[{datetime.datetime.now()}] Bắt đầu sync log từ MongoDB đến ERPNext...")

            # Check if MongoDB sync is enabled
            if not getattr(local_config, 'ENABLE_SYNC_LOG_FROM_MONGODB_TO_ERPNEXT', False):
                print("  MongoDB sync disabled in configuration")
                return True

            # Import the MongoDB sync module
            import sync_log_from_mongodb_to_erpnext

            # Execute MongoDB sync
            result = sync_log_from_mongodb_to_erpnext.run_mongodb_sync()

            # Display results
            if result['success']:
                details = result['details']
                print(f"📊 MONGODB SYNC SUMMARY:")
                print(f"   Total records found: {details['total_records']}")
                print(f"   Successfully processed: {details['processed']}")
                print(f"   Skipped (duplicates/missing employees): {details['skipped']}")
                print(f"   Failed: {details['errors']}")
                print("✓ Sync log từ MongoDB đến ERPNext hoàn thành")
                return True
            else:
                print(f"✗ Sync log từ MongoDB đến ERPNext thất bại: {result['message']}")
                return False

        except Exception as e:
            print(f"✗ MongoDB sync thất bại: {e}")
            print(f"  Chi tiết lỗi: {traceback.format_exc()}")
            return False

    def execute_ot_mongodb_sync(self):
        """Execute OT sync from MongoDB to ERPNext"""
        try:
            print(f"\n[{datetime.datetime.now()}] Bắt đầu sync OT từ MongoDB đến ERPNext...")

            # Check if OT sync is enabled
            if not getattr(local_config, 'ENABLE_SYNC_OT_FROM_MONGODB_TO_ERPNEXT', False):
                print("  OT MongoDB sync disabled in configuration")
                return True

            # Import the OT MongoDB sync module
            import sync_ot_from_mongodb_to_erpnext

            # Create syncer instance
            syncer = sync_ot_from_mongodb_to_erpnext.OTSyncFromMongoDB()

            # Execute OT sync
            result = syncer.sync_ot_to_erpnext()

            # Display results
            if result['success']:
                print(f"📊 OT MONGODB SYNC SUMMARY:")
                print(f"   Total records: {result['total_records']}")
                print(f"   Total requests: {result['total_requests']}")
                print(f"   Created: {result['created']}")
                print(f"   Skipped: {result['skipped']}")
                if result.get('skipped_exists', 0) > 0:
                    print(f"     - Already exists: {result['skipped_exists']}")
                if result.get('skipped_conflicts', 0) > 0:
                    print(f"     - Validation conflicts: {result['skipped_conflicts']}")
                print(f"   Failed: {result['failed']}")
                print(f"   Execution time: {result.get('execution_time', 0):.2f}s")
                print("✓ Sync OT từ MongoDB đến ERPNext hoàn thành")
                return True
            else:
                print(f"✗ Sync OT từ MongoDB đến ERPNext thất bại: {result['message']}")
                return False

        except Exception as e:
            print(f"✗ OT MongoDB sync thất bại: {e}")
            print(f"  Chi tiết lỗi: {traceback.format_exc()}")
            return False

    def should_run_clean_logs(self):
        """Check if should run log cleanup (once per day)"""
        try:
            import clean_old_logs
            return clean_old_logs.should_run_cleanup()
        except Exception as e:
            print(f"Error checking clean logs status: {e}")
            return False

    def execute_clean_logs(self):
        """Execute old log files cleanup (once per day)"""
        try:
            clean_days = getattr(local_config, 'CLEAN_OLD_LOGS_DAYS', 0)

            print(f"\n[{datetime.datetime.now()}] Bắt đầu dọn dẹp log files cũ...")
            print(f"  🧹 Cleaning logs older than {clean_days} days")

            # Import the cleanup module
            import clean_old_logs

            # Execute cleanup
            result = clean_old_logs.run_cleanup(dry_run=False, force=False)

            if result["success"]:
                print("✓ Dọn dẹp log files hoàn thành")
                print(f"  - Files cleaned: {result.get('cleaned_files', 0)}")
                print(f"  - Empty files deleted: {result.get('deleted_files', 0)}")
                print(f"  - Space freed: {clean_old_logs.format_size(result.get('total_size_freed', 0))}")
                return True
            else:
                print(f"• {result.get('message', 'No cleanup needed')}")
                return True  # Not an error if already ran today

        except Exception as e:
            print(f"✗ Dọn dẹp log files thất bại: {e}")
            print(f"  Chi tiết lỗi: {traceback.format_exc()}")
            return False
    
    def execute_cycle(self):
        """Execute one complete sync cycle"""
        cycle_start = datetime.datetime.now()
        self.cycle_count += 1
        
        # Check if this should be an end-of-day re-sync cycle
        if local_config.should_run_end_of_day_resync():
            return self.execute_end_of_day_resync_cycle()
        
        print("\n" + "🔄" * 40)
        print(f"CYCLE #{self.cycle_count} - {cycle_start}")
        print("🔄" * 40)
        
        # Reload dynamic configuration
        if not self.reload_dynamic_config():
            print("⚠ Using previous dynamic configuration")
        
        # Log current bypass status
        local_config.log_bypass_status()
        
        cycle_success = True
        
        # =========================================================================
        # STEP 1: ERPNext Sync (get logs from devices)
        # =========================================================================
        
        log_bypass, log_period = local_config.should_bypass_log_sync()
        
        if log_bypass:
            reason = log_period.get('reason', 'Time-based bypass')
            local_config.log_operation_decision("Sync Log từ Device đến ERPNext", False, reason)
        else:
            local_config.log_operation_decision("Sync Log từ Device đến ERPNext", True, "Thời gian hoạt động")
            if not self.execute_erpnext_sync(bypass_device_connection=log_bypass):
                cycle_success = False
        
        # =========================================================================
        # STEP 2: Sync from ERPNext to Device (if enabled)
        # =========================================================================
        
        if local_config.ENABLE_SYNC_USER_INFO_FROM_ERPNEXT_TO_DEVICE:
            user_bypass, user_period = local_config.should_bypass_user_info_sync()

            if user_bypass:
                reason = user_period.get('reason', 'Time-based bypass')
                local_config.log_operation_decision("Sync User Info từ ERPNext đến Device", False, reason)
            else:
                local_config.log_operation_decision("Sync User Info từ ERPNext đến Device", True, "Thời gian hoạt động")
                if not self.execute_sync_user_info_from_erpnext_to_device():
                    cycle_success = False
        else:
            local_config.log_operation_decision("Sync User Info từ ERPNext đến Device", False, "Chức năng bị tắt")

        # =========================================================================
        # STEP 3: Clear Left Employee Templates (once per day)
        # =========================================================================

        if local_config.should_run_clear_left_templates():
            local_config.log_operation_decision("Xóa Template Nhân Viên Nghỉ Việc", True, "Chạy lần đầu trong ngày")
            if not self.execute_clear_left_templates():
                print("⚠ Clear left templates failed but continuing cycle")
        elif local_config.ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES:
            local_config.log_operation_decision("Xóa Template Nhân Viên Nghỉ Việc", False, "Đã chạy hôm nay")

        # =========================================================================
        # STEP 4: Clean Old Logs (once per day)
        # =========================================================================

        if self.should_run_clean_logs():
            local_config.log_operation_decision("Dọn Dẹp Log Files Cũ", True, "Chạy lần đầu trong ngày")
            if not self.execute_clean_logs():
                print("⚠ Clean old logs failed but continuing cycle")
        elif getattr(local_config, 'CLEAN_OLD_LOGS_DAYS', 0) > 0:
            local_config.log_operation_decision("Dọn Dẹp Log Files Cũ", False, "Đã chạy hôm nay")

        # =========================================================================
        # CYCLE SUMMARY
        # =========================================================================
        
        cycle_end = datetime.datetime.now()
        cycle_duration = (cycle_end - cycle_start).total_seconds()
        
        if cycle_success:
            print(f"\n✓ Cycle #{self.cycle_count} completed successfully in {cycle_duration:.1f}s")
        else:
            print(f"\n✗ Cycle #{self.cycle_count} completed with errors in {cycle_duration:.1f}s")
            self.error_count += 1
            self.last_error = cycle_end
        
        return cycle_success
    
    def execute_end_of_day_resync_cycle(self):
        """Execute end-of-day comprehensive re-sync cycle"""
        cycle_start = datetime.datetime.now()
        self.cycle_count += 1
        
        # Initialize re-sync logging
        local_config.log_resync_operation("=" * 80)
        local_config.log_resync_operation(f"🌙 END-OF-DAY RE-SYNC CYCLE #{self.cycle_count} STARTED")
        local_config.log_resync_operation(f"🌙 Start time: {cycle_start}")
        local_config.log_resync_operation("=" * 80)
        
        print("\n" + "🌙" * 60)
        print(f"END-OF-DAY RE-SYNC CYCLE #{self.cycle_count} - {cycle_start}")
        print("🌙" * 60)
        
        # Reload dynamic configuration
        if not self.reload_dynamic_config():
            print("⚠ Using previous dynamic configuration")
        
        # Backup original re-sync configuration
        original_resync_config = getattr(local_config, 're_sync_data_date_range', [])
        
        try:
            # Set re-sync range for today
            today_range = local_config.get_end_of_day_resync_date_range()
            local_config.re_sync_data_date_range = today_range
            
            # Log configuration to dedicated re-sync log
            local_config.log_resync_operation(f"🔄 RE-SYNC CONFIGURATION:")
            local_config.log_resync_operation(f"   - Target date: {today_range[0]}")
            local_config.log_resync_operation(f"   - Mode: COMPREHENSIVE (ignoring bypass periods)")
            local_config.log_resync_operation(f"   - Original config backup: {original_resync_config}")
            local_config.log_resync_operation(f"   - Will sync ALL logs from ALL devices for today")
            local_config.log_resync_operation(f"   - Dedicated log file: {local_config.END_OF_DAY_RESYNC_LOG_FILE}")
            
            print(f"🔄 RE-SYNC CONFIGURATION:")
            print(f"   - Target date: {today_range[0]}")
            print(f"   - Mode: COMPREHENSIVE (ignoring bypass periods)")
            print(f"   - Original config backup: {original_resync_config}")
            print(f"   - Will sync ALL logs from ALL devices for today")
            print(f"   - Dedicated log file: {local_config.END_OF_DAY_RESYNC_LOG_FILE}")
            
            cycle_success = True
            
            # =====================================================================
            # FORCED SYNC: ERPNext Sync (get logs from devices) - NO BYPASS
            # =====================================================================
            
            print(f"\n[🌙 END-OF-DAY] FORCED Sync Log từ Device đến ERPNext")
            print("   ⚠ BYPASSING all time-based restrictions")
            print("   ⚠ FORCING connection to all devices")
            
            # Log to dedicated re-sync log
            local_config.log_resync_operation("🚀 STARTING FORCED SYNC FROM DEVICES TO ERPNEXT")
            local_config.log_resync_operation("   ⚠ BYPASSING all time-based restrictions")
            local_config.log_resync_operation("   ⚠ FORCING connection to all devices")
            local_config.log_resync_operation("   📋 Will filter duplicate error logs automatically")
            
            local_config.log_operation_decision(
                "END-OF-DAY Sync Log từ Device đến ERPNext", 
                True, 
                "Comprehensive end-of-day re-sync - ignoring all bypass periods"
            )
            
            if not self.execute_erpnext_sync(bypass_device_connection=False, force_resync=True):
                cycle_success = False
                print("✗ End-of-day sync failed - but continuing with summary")
                local_config.log_resync_operation("❌ End-of-day sync FAILED - check main logs for details", "ERROR")
            else:
                local_config.log_resync_operation("✅ End-of-day sync COMPLETED successfully")
            
            # =====================================================================
            # OPTIONAL: User Info Sync (if enabled)
            # =====================================================================

            if local_config.ENABLE_SYNC_USER_INFO_FROM_ERPNEXT_TO_DEVICE:
                print(f"\n[🌙 END-OF-DAY] User Info Sync từ ERPNext đến Device")
                print("   ℹ Using normal bypass logic for user sync")

                user_bypass, user_period = local_config.should_bypass_user_info_sync()

                if user_bypass:
                    reason = user_period.get('reason', 'Time-based bypass')
                    local_config.log_operation_decision("END-OF-DAY User Info Sync", False, reason)
                else:
                    local_config.log_operation_decision("END-OF-DAY User Info Sync", True, "Normal user sync logic")
                    if not self.execute_sync_user_info_from_erpnext_to_device():
                        print("⚠ User info sync failed during end-of-day cycle")
            else:
                local_config.log_operation_decision("END-OF-DAY User Info Sync", False, "Chức năng bị tắt")

            # =====================================================================
            # OPTIONAL: Clear Left Templates (if not run yet today)
            # =====================================================================

            if local_config.should_run_clear_left_templates():
                print(f"\n[🌙 END-OF-DAY] Xóa Template Nhân Viên Nghỉ Việc")
                print("   🗑️ Clearing templates for left employees")

                local_config.log_operation_decision("END-OF-DAY Clear Left Templates", True, "Chạy lần đầu trong ngày")
                local_config.log_resync_operation("🗑️ STARTING CLEAR LEFT EMPLOYEE TEMPLATES")

                if not self.execute_clear_left_templates():
                    print("⚠ Clear left templates failed during end-of-day cycle")
                    local_config.log_resync_operation("❌ Clear left templates FAILED during end-of-day cycle", "ERROR")
                else:
                    local_config.log_resync_operation("✅ Clear left templates COMPLETED successfully during end-of-day cycle")
            elif local_config.ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES:
                local_config.log_operation_decision("END-OF-DAY Clear Left Templates", False, "Đã chạy hôm nay")

            # =====================================================================
            # OPTIONAL: Time Sync (if enabled)
            # =====================================================================

            if local_config.ENABLE_TIME_SYNC and local_config.TIME_SYNC_AND_RESTART_AT_NIGHT:
                print(f"\n[🌙 END-OF-DAY] Time Sync từ Server đến Devices")
                print("   🕒 Synchronizing server time to all biometric devices")

                local_config.log_operation_decision("END-OF-DAY Time Sync", True, "End-of-day time synchronization")
                local_config.log_resync_operation("🕒 STARTING TIME SYNC FROM SERVER TO DEVICES")
                local_config.log_resync_operation("   📋 Will sync time to all configured devices")

                if not self.execute_time_sync():
                    print("⚠ Time sync failed during end-of-day cycle")
                    local_config.log_resync_operation("❌ Time sync FAILED during end-of-day cycle", "ERROR")
                else:
                    local_config.log_resync_operation("✅ Time sync COMPLETED successfully during end-of-day cycle")
            else:
                local_config.log_operation_decision("END-OF-DAY Time Sync", False, "Time sync disabled or not configured for end-of-day")

            # =====================================================================
            # OPTIONAL: MongoDB Sync (if enabled)
            # =====================================================================

            if getattr(local_config, 'ENABLE_SYNC_LOG_FROM_MONGODB_TO_ERPNEXT', False):
                print(f"\n[🌙 END-OF-DAY] MongoDB Sync từ MongoDB đến ERPNext")
                print("   🗃️ Syncing attendance logs from MongoDB to ERPNext")

                local_config.log_operation_decision("END-OF-DAY MongoDB Sync", True, "End-of-day MongoDB synchronization")
                local_config.log_resync_operation("🗃️ STARTING MONGODB SYNC FROM MONGODB TO ERPNEXT")

                date_range = getattr(local_config, 'sync_log_from_mongodb_to_erpnext_date_range', [])
                if date_range:
                    local_config.log_resync_operation(f"   📋 Date range: {date_range[0]} to {date_range[1]}")
                else:
                    local_config.log_resync_operation("   📋 Will sync current date only")

                if not self.execute_mongodb_sync():
                    print("⚠ MongoDB sync failed during end-of-day cycle")
                    local_config.log_resync_operation("❌ MongoDB sync FAILED during end-of-day cycle", "ERROR")
                else:
                    local_config.log_resync_operation("✅ MongoDB sync COMPLETED successfully during end-of-day cycle")
            else:
                local_config.log_operation_decision("END-OF-DAY MongoDB Sync", False, "MongoDB sync disabled in configuration")

            # =====================================================================
            # OPTIONAL: OT MongoDB Sync (if enabled)
            # =====================================================================

            if getattr(local_config, 'ENABLE_SYNC_OT_FROM_MONGODB_TO_ERPNEXT', False):
                print(f"\n[🌙 END-OF-DAY] OT MongoDB Sync từ MongoDB đến ERPNext")
                print("   📋 Syncing overtime registration from MongoDB to ERPNext")

                local_config.log_operation_decision("END-OF-DAY OT MongoDB Sync", True, "End-of-day OT MongoDB synchronization")
                local_config.log_resync_operation("📋 STARTING OT MONGODB SYNC FROM MONGODB TO ERPNEXT")
                local_config.log_resync_operation(f"   📋 Start date filter: {getattr(local_config, 'SYNC_OT_FROM_MONGODB_TO_ERPNEXT_START_DATE', 'Not configured')}")

                if not self.execute_ot_mongodb_sync():
                    print("⚠ OT MongoDB sync failed during end-of-day cycle")
                    local_config.log_resync_operation("❌ OT MongoDB sync FAILED during end-of-day cycle", "ERROR")
                else:
                    local_config.log_resync_operation("✅ OT MongoDB sync COMPLETED successfully during end-of-day cycle")
            else:
                local_config.log_operation_decision("END-OF-DAY OT MongoDB Sync", False, "OT MongoDB sync disabled in configuration")

            # =====================================================================
            # END-OF-DAY CYCLE SUMMARY
            # =====================================================================
            
            cycle_end = datetime.datetime.now()
            cycle_duration = (cycle_end - cycle_start).total_seconds()
            
            # Log final results to dedicated re-sync log
            local_config.log_resync_operation("=" * 80)
            if cycle_success:
                local_config.log_resync_operation(f"✅ END-OF-DAY RE-SYNC CYCLE #{self.cycle_count} COMPLETED SUCCESSFULLY")
                local_config.log_resync_operation(f"  Duration: {cycle_duration:.1f}s")
                local_config.log_resync_operation(f"  Date range synced: {today_range[0]} to {today_range[1]}")
                local_config.log_resync_operation(f"  All devices processed with bypass override")
            else:
                local_config.log_resync_operation(f"❌ END-OF-DAY RE-SYNC CYCLE #{self.cycle_count} COMPLETED WITH ERRORS")
                local_config.log_resync_operation(f"  Duration: {cycle_duration:.1f}s")
                local_config.log_resync_operation(f"  Date range attempted: {today_range[0]} to {today_range[1]}")
                local_config.log_resync_operation(f"  Check main logs for error details")
            local_config.log_resync_operation(f"🌙 End time: {cycle_end}")
            local_config.log_resync_operation("=" * 80)
            
            print("\n" + "🌙" * 60)
            if cycle_success:
                print(f"✓ END-OF-DAY RE-SYNC CYCLE #{self.cycle_count} COMPLETED SUCCESSFULLY")
                print(f"  Duration: {cycle_duration:.1f}s")
                print(f"  Date range synced: {today_range[0]} to {today_range[1]}")
                print(f"  All devices processed with bypass override")
                print(f"  📋 Detailed logs: {local_config.END_OF_DAY_RESYNC_LOG_FILE}")
            else:
                print(f"✗ END-OF-DAY RE-SYNC CYCLE #{self.cycle_count} COMPLETED WITH ERRORS")
                print(f"  Duration: {cycle_duration:.1f}s") 
                print(f"  Date range attempted: {today_range[0]} to {today_range[1]}")
                print(f"  Check logs above for error details")
                print(f"  📋 Detailed logs: {local_config.END_OF_DAY_RESYNC_LOG_FILE}")
                self.error_count += 1
                self.last_error = cycle_end
            print("🌙" * 60)
            
            return cycle_success
            
        except Exception as e:
            print(f"✗ CRITICAL ERROR in end-of-day re-sync cycle: {e}")
            print(f"  Error details: {traceback.format_exc()}")
            local_config.log_resync_operation(f"💥 CRITICAL ERROR in end-of-day re-sync cycle: {e}", "ERROR")
            local_config.log_resync_operation(f"  Error details: {traceback.format_exc()}", "ERROR")
            self.error_count += 1
            self.last_error = datetime.datetime.now()
            return False
            
        finally:
            # Always restore original configuration
            local_config.re_sync_data_date_range = original_resync_config
            local_config.log_resync_operation(f"🔄 Restored original re-sync config: {original_resync_config}")
            print(f"🔄 Restored original re-sync config: {original_resync_config}")
    
    def run(self):
        """Main service loop"""
        print(f"\n🚀 {self.service_name} started")
        print(f"Press Ctrl+C to stop the service gracefully")
        
        while self.running:
            try:
                # Execute one sync cycle
                self.execute_cycle()
                
                if not self.running:
                    break
                
                # Calculate sleep time
                sleep_seconds = local_config.PULL_FREQUENCY * 60
                next_run = datetime.datetime.now() + datetime.timedelta(seconds=sleep_seconds)
                
                print(f"\n⏰ Sleeping for {local_config.PULL_FREQUENCY} minutes...")
                print(f"   Next run scheduled at: {next_run.strftime('%H:%M:%S')}")
                
                # Sleep with interrupt check
                sleep_start = time.time()
                while (time.time() - sleep_start) < sleep_seconds and self.running:
                    time.sleep(1)
                
            except KeyboardInterrupt:
                print(f"\n[{datetime.datetime.now()}] Keyboard interrupt received")
                break
            except Exception as e:
                self.error_count += 1
                self.last_error = datetime.datetime.now()
                print(f"\n✗ Unexpected error in main loop: {e}")
                print(f"  Error details: {traceback.format_exc()}")
                print("  Service will retry in 15 seconds...")
                
                # Short sleep before retry
                time.sleep(15)
        
        self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown with summary"""
        end_time = datetime.datetime.now()
        runtime = end_time - self.start_time
        
        print("\n" + "🛑" * 40)
        print(f"{self.service_name} SHUTDOWN SUMMARY")
        print("🛑" * 40)
        print(f"Start time: {self.start_time}")
        print(f"End time: {end_time}")
        print(f"Total runtime: {runtime}")
        print(f"Total cycles: {self.cycle_count}")
        print(f"Total errors: {self.error_count}")
        if self.last_error:
            print(f"Last error: {self.last_error}")
        print("🛑" * 40)
        print("Service stopped gracefully")
    
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
        
        # Display end-of-day re-sync status
        if local_config.ENABLE_RESYNC_ON_DAY:
            print(f"  🌙 End-of-day re-sync: ENABLED")
            print(f"    Schedule: {', '.join(local_config.TIME_RESYNC_ON_DAY)} daily (±{local_config.RESYNC_WINDOW_MINUTES_ON_DAY//2}min)")
            print(f"    Next check: Every {local_config.PULL_FREQUENCY} minutes")
        else:
            print(f"  🌙 End-of-day re-sync: DISABLED")

        # Display time sync status
        if local_config.ENABLE_TIME_SYNC:
            print(f"  🕒 Time sync: ENABLED")
            print(f"    With night restart: {'YES' if local_config.TIME_SYNC_AND_RESTART_AT_NIGHT else 'NO'}")
            print(f"    Sync threshold: {local_config.TIME_SYNC_MAX_DIFF_SECONDS}s")
            print(f"    Connection timeout: {local_config.TIME_SYNC_TIMEOUT_SECONDS}s")
        else:
            print(f"  🕒 Time sync: DISABLED")

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