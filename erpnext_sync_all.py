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
    
    def execute_erpnext_sync(self, bypass_device_connection=False):
        """Execute erpnext_sync.py with optional device bypass"""
        try:
            print(f"\n[{datetime.datetime.now()}] Starting ERPNext sync...")
            
            # Import and execute sync_log_from_device_to_erpnext functionality
            import sync_log_from_device_to_erpnext
            
            if bypass_device_connection:
                print("⚠ Device connection bypassed - skipping device data fetch")
                return True
            else:
                # Execute single cycle (avoid infinite loop)
                success = sync_log_from_device_to_erpnext.run_single_cycle(bypass_device_connection=bypass_device_connection)
                if success:
                    print("✓ Sync log từ device đến ERPNext hoàn thành")
                    return True
                else:
                    print("✗ Sync log từ device đến ERPNext thất bại")
                    return False
                
        except Exception as e:
            print(f"✗ ERPNext sync failed: {e}")
            print(f"  Error details: {traceback.format_exc()}")
            return False
    
    def execute_sync_user_info_from_erpnext_to_device(self, bypass_clear_left=False):
        """Execute sync_user_info_from_erpnext_to_device with optional bypass for clear left templates"""
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
            
            if bypass_clear_left:
                print("⚠ Xóa template nhân viên nghỉ việc bị bỏ qua do giới hạn thời gian")
            
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
    
    def execute_cycle(self):
        """Execute one complete sync cycle"""
        cycle_start = datetime.datetime.now()
        self.cycle_count += 1
        
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
                clear_bypass, clear_period = local_config.should_bypass_clear_left_templates()
                
                local_config.log_operation_decision("Sync User Info từ ERPNext đến Device", True, "Thời gian hoạt động")
                if clear_bypass:
                    clear_reason = clear_period.get('reason', 'Time-based bypass for clear left templates')
                    print(f"  Ghi chú: {clear_reason}")
                
                if not self.execute_sync_user_info_from_erpnext_to_device(bypass_clear_left=clear_bypass):
                    cycle_success = False
        else:
            local_config.log_operation_decision("Sync User Info từ ERPNext đến Device", False, "Chức năng bị tắt")
        
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