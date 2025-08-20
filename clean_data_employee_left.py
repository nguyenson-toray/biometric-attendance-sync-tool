#!/usr/bin/env python3

"""
Clean Data Employee Left - Cleanup tool for departed employees

This tool performs comprehensive cleanup for employees with status "Left":
1. Date validation: Only process employees where current date > relieving_date
2. Delete fingerprint records from ERPNext
3. Clear fingerprint templates from devices (keep user_id for attendance history)

Usage:
    python3 clean_data_employee_left.py
"""

import datetime
import logging
import os
import sys
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import socket
import time
import base64
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
        
    def get_left_employees_for_cleanup(self):
        """Get employees with status 'Left' ready for cleanup"""
        return self.api_client.get_left_employees_with_device_id()
    
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
        """Clear fingerprint templates for Left employees from single device"""
        device_id = device_config['device_id']
        ip_address = device_config['ip']
        
        logger.info(f"Clearing templates for {len(left_employees)} Left employees from device {device_id}")
        
        try:
            # Check connection
            if not self.check_device_connection(device_config):
                logger.warning(f"✗ Device {device_id} ({ip_address}) is not reachable")
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": False,
                    "cleared_count": 0,
                    "total_count": len(left_employees),
                    "message": f"Device {device_id} is not reachable"
                }
            
            # Connect to device
            zk = ZK(ip_address, port=4370, timeout=10, force_udp=True, ommit_ping=True)
            conn = zk.connect()
            
            if not conn:
                logger.warning(f"✗ Failed to connect to device {device_id}")
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": False,
                    "cleared_count": 0,
                    "total_count": len(left_employees),
                    "message": f"Failed to connect to device {device_id}"
                }
            
            try:
                # Disable device
                conn.disable_device()
                logger.info(f"Device {device_id} disabled, clearing templates for {len(left_employees)} Left employees...")
                
                cleared_count = 0
                failed_employees = []
                cleared_users = []
                
                # Get existing users on device
                existing_users = conn.get_users()
                existing_user_ids = {str(u.user_id): u for u in existing_users}
                
                # Process Left employees
                for i, employee_data in enumerate(left_employees, 1):
                    try:
                        attendance_device_id = str(employee_data["attendance_device_id"])
                        
                        # Check if user exists on device
                        if attendance_device_id in existing_user_ids:
                            user = existing_user_ids[attendance_device_id]
                            
                            # Clear all fingerprint templates (set empty templates)
                            empty_templates = []
                            for j in range(10):
                                finger_obj = Finger(uid=user.uid, fid=j, valid=False, template=b'')
                                empty_templates.append(finger_obj)
                            
                            conn.save_user_template(user, empty_templates)
                            cleared_count += 1
                            cleared_users.append(employee_data)
                            
                            logger.info(f"  ✓ Cleared templates for {employee_data['employee']} (ID: {attendance_device_id})")
                            
                        else:
                            logger.info(f"  • User {attendance_device_id} not found on device (already cleared)")
                            
                    except Exception as e:
                        failed_employees.append(f"{employee_data['employee']} ({str(e)})")
                        logger.error(f"  ✗ Error clearing {employee_data['employee']}: {str(e)}")
                
                logger.info(f"✓ Device {device_id}: Cleared templates for {cleared_count}/{len(left_employees)} Left employees")
                if failed_employees:
                    logger.warning(f"✗ Device {device_id} failed employees: {len(failed_employees)}")
                
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": True,
                    "cleared_count": cleared_count,
                    "total_count": len(left_employees),
                    "failed_employees": failed_employees,
                    "cleared_users": cleared_users,
                    "message": f"Cleared templates for {cleared_count}/{len(left_employees)} Left employees"
                }
                
            finally:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"✗ Device {device_id} clear error: {str(e)}")
            return {
                "device_id": device_id,
                "ip": ip_address,
                "success": False,
                "cleared_count": 0,
                "total_count": len(left_employees),
                "message": f"Device clear error: {str(e)}"
            }
    
    def clean_left_employee_complete(self, employee_data):
        """Complete cleanup for single Left employee: ERPNext + all devices"""
        employee_id = employee_data["employee_id"]
        employee_name = employee_data["employee"]
        attendance_device_id = employee_data["attendance_device_id"]
        
        logger.info(f"Processing complete cleanup for {employee_name} (ID: {attendance_device_id})")
        
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
            # Step 1: Delete fingerprint records from ERPNext
            logger.info(f"  Step 1: Deleting ERPNext fingerprints for {employee_name}")
            erpnext_result = self.delete_employee_fingerprints_from_erpnext(employee_id)
            cleanup_result["erpnext_deletion"] = erpnext_result
            
            if erpnext_result["success"]:
                logger.info(f"    ✓ ERPNext: Deleted {erpnext_result['deleted_count']} fingerprint records")
            else:
                logger.warning(f"    ✗ ERPNext: {erpnext_result['message']}")
            
            # Step 2: Clear templates from all devices in parallel
            logger.info(f"  Step 2: Clearing device templates for {employee_name}")
            
            device_results = []
            with ThreadPoolExecutor(max_workers=len(self.devices)) as executor:
                future_to_device = {
                    executor.submit(self.clear_employee_templates_from_device, device, [employee_data]): device 
                    for device in self.devices
                }
                
                for future in concurrent.futures.as_completed(future_to_device):
                    device = future_to_device[future]
                    try:
                        result = future.result()
                        device_results.append(result)
                        
                        if result["success"] and result["cleared_count"] > 0:
                            logger.info(f"    ✓ {device['device_id']}: Cleared templates")
                        elif result["success"]:
                            logger.info(f"    • {device['device_id']}: User not found (already cleared)")
                        else:
                            logger.warning(f"    ✗ {device['device_id']}: {result['message']}")
                            
                    except Exception as e:
                        error_result = {
                            "device_id": device['device_id'],
                            "success": False,
                            "cleared_count": 0,
                            "message": f"Thread execution error: {str(e)}"
                        }
                        device_results.append(error_result)
                        logger.error(f"    ✗ {device['device_id']}: Thread execution error: {str(e)}")
            
            cleanup_result["device_results"] = device_results
            
            # Determine overall success
            erpnext_success = erpnext_result["success"]
            device_success = any(r["success"] and r["cleared_count"] > 0 for r in device_results)
            
            cleanup_result["success"] = erpnext_success or device_success
            
            if erpnext_success and device_success:
                cleanup_result["message"] = "Complete cleanup successful (ERPNext + devices)"
            elif erpnext_success:
                cleanup_result["message"] = "ERPNext cleanup successful, devices already clean"
            elif device_success:
                cleanup_result["message"] = "Device cleanup successful, ERPNext had no data"
            else:
                cleanup_result["message"] = "Cleanup failed on all systems"
            
            logger.info(f"  ✓ Complete cleanup for {employee_name}: {cleanup_result['message']}")
            
            return cleanup_result
            
        except Exception as e:
            cleanup_result["message"] = f"Cleanup error: {str(e)}"
            logger.error(f"  ✗ Error processing {employee_name}: {str(e)}")
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
        
        logger.info(f"Found {len(left_employees)} Left employees ready for cleanup")
        logger.info(f"Starting cleanup process...")
        
        # Process each employee
        cleanup_results = []
        successful_cleanups = 0
        
        for i, employee_data in enumerate(left_employees, 1):
            logger.info(f"\n[{i}/{len(left_employees)}] Processing {employee_data['employee']}...")
            
            result = self.clean_left_employee_complete(employee_data)
            cleanup_results.append(result)
            
            if result["success"]:
                successful_cleanups += 1
        
        execution_time = time.time() - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("LEFT EMPLOYEE CLEANUP COMPLETED")
        logger.info(f"Total Left employees processed: {len(left_employees)}")
        logger.info(f"Successful cleanups: {successful_cleanups}")
        logger.info(f"Failed cleanups: {len(left_employees) - successful_cleanups}")
        logger.info(f"Total execution time: {execution_time:.2f} seconds")
        logger.info("=" * 80)
        
        # Show summary
        if successful_cleanups > 0:
            logger.info("\nSuccessful cleanups:")
            for result in cleanup_results:
                if result["success"]:
                    logger.info(f"  ✓ {result['employee']}: {result['message']}")
        
        if successful_cleanups < len(left_employees):
            logger.info("\nFailed cleanups:")
            for result in cleanup_results:
                if not result["success"]:
                    logger.info(f"  ✗ {result['employee']}: {result['message']}")
        
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
    
    parser = argparse.ArgumentParser(description='Clean data for Left employees - Delete fingerprints from ERPNext and clear templates from devices')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be cleaned without actually doing it')
    
    args = parser.parse_args()
    
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
    
    try:
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

if __name__ == "__main__":
    main()