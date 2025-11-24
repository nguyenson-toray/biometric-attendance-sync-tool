#!/usr/bin/env python3

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
try:
    from unidecode import unidecode
    UNIDECODE_AVAILABLE = True
except ImportError:
    UNIDECODE_AVAILABLE = False
    print("Warning: unidecode not available, using original Vietnamese names")

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import local_config
from erpnext_api_client import ERPNextAPIClient
import importlib.util
spec = importlib.util.spec_from_file_location("sync_user_info_state",
    os.path.join(current_dir, "11.sync_user_info_state.py"))
sync_user_info_state_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_user_info_state_module)
SyncState = sync_user_info_state_module.SyncState

# Setup logging to sync_from_erpnext_to_device folder
sync_logs_dir = os.path.join(local_config.LOGS_DIRECTORY, 'sync_from_erpnext_to_device')
os.makedirs(sync_logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(sync_logs_dir, 'sync_to_device.log')),
        # logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ERPNextSyncToDeviceStandalone:
    def __init__(self):
        self.base_url = local_config.ERPNEXT_URL
        self.api_key = local_config.ERPNEXT_API_KEY
        self.api_secret = local_config.ERPNEXT_API_SECRET
        self.devices = local_config.devices
        self.max_workers = min(len(self.devices), 10)
        
        self.api_client = ERPNextAPIClient(self.base_url, self.api_key, self.api_secret)
        self.sync_state = SyncState()
        self.setup_logging()
        
    def setup_logging(self):
        # Ensure sync logs directory exists
        os.makedirs(sync_logs_dir, exist_ok=True)
        
    def test_erpnext_connection(self):
        """Test ERPNext API connection"""
        return self.api_client.test_connection()
        
    def get_all_employees_with_fingerprints(self):
        """Get all active employees with fingerprint data from ERPNext via API"""
        return self.api_client.get_employees_with_fingerprints()
    
    def get_changed_employees_with_fingerprints(self, since_datetime=None):
        """Get employees with fingerprint data that have been modified since datetime"""
        if not since_datetime:
            since_datetime = datetime.datetime.now() - datetime.timedelta(hours=24)
        return self.api_client.get_changed_employees_with_fingerprints(since_datetime)
    
    def get_left_employees_with_device_id(self):
        """Get employees with status 'Left' who have device IDs"""
        return self.api_client.get_left_employees_with_device_id()
    
    def delete_employee_fingerprints_from_erpnext(self, employee_id):
        """Delete fingerprint records from ERPNext for an employee"""
        return self.api_client.delete_employee_fingerprints(employee_id)
    
    def get_employee_fingerprint_count(self, employee_id):
        """Get count of fingerprint records for an employee"""
        return self.api_client.get_employee_fingerprint_count(employee_id)
    
    
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
    
    def shorten_name(self, full_name, max_length=24):
        """Convert Vietnamese to non-accented characters and shorten if needed for device compatibility"""
        if not full_name:
            return full_name
            
        # Always normalize Vietnamese characters for device compatibility
        if UNIDECODE_AVAILABLE:
            text_processed = unidecode(full_name)  # 'Nguyễn Văn A' → 'Nguyen Van A'
        else:
            text_processed = full_name  # Fallback if unidecode not available
        text_processed = ' '.join(text_processed.split()).strip()
        
        if len(text_processed) > max_length:
            parts = text_processed.split()
            if len(parts) > 1:
                initials = "".join(part[0].upper() for part in parts[:-1])
                last_part = parts[-1]
                return f"{initials} {last_part}"
            else:
                return text_processed[:max_length]
        else:
            return text_processed
    
    def sync_employee_to_device(self, device_config, employee_data):
        """Sync single employee to single device"""
        device_id = device_config['device_id']
        ip_address = device_config['ip']
        
        try:
            if not self.check_device_connection(device_config):
                return {
                    "success": False,
                    "device_id": device_id,
                    "ip": ip_address,
                    "employee": employee_data["employee"],
                    "message": f"Device {device_id} ({ip_address}) is not reachable"
                }
            
            zk = ZK(ip_address, port=4370, timeout=10, force_udp=True, ommit_ping=True)
            conn = zk.connect()
            
            if not conn:
                return {
                    "success": False,
                    "device_id": device_id,
                    "ip": ip_address,
                    "employee": employee_data["employee"],
                    "message": f"Failed to connect to device {device_id}"
                }
                
            try:
                conn.disable_device()
                
                attendance_device_id = employee_data["attendance_device_id"]
                
                existing_users = conn.get_users()
                user_exists = any(str(u.user_id) == str(attendance_device_id) for u in existing_users)
                
                if user_exists:
                    conn.delete_user(user_id=attendance_device_id)
                    time.sleep(0.1)
                
                full_name = employee_data["employee_name"]
                shortened_name = self.shorten_name(full_name, 24)
                password = employee_data.get("password", "")
                privilege = employee_data.get("privilege", 0)
                
                if password:
                    conn.set_user(
                        name=shortened_name,
                        privilege=privilege,
                        password=password,
                        group_id='',
                        user_id=attendance_device_id
                    )
                else:
                    conn.set_user(
                        name=shortened_name,
                        privilege=privilege,
                        group_id='',
                        user_id=attendance_device_id
                    )
                
                users = conn.get_users()
                user = next((u for u in users if str(u.user_id) == str(attendance_device_id)), None)
                
                if not user:
                    return {
                        "success": False,
                        "device_id": device_id,
                        "ip": ip_address,
                        "employee": employee_data["employee"],
                        "message": f"Could not create or find user {attendance_device_id}"
                    }
                
                fingerprint_lookup = {fp.get("finger_index"): fp for fp in employee_data["fingerprints"] if fp.get("template_data")}
                
                decoded_templates = {}
                for finger_index, fp in fingerprint_lookup.items():
                    try:
                        decoded_templates[finger_index] = base64.b64decode(fp["template_data"])
                    except Exception:
                        pass
                
                # Only send templates that have actual data
                templates_to_send = []
                fingerprint_count = 0
                
                for finger_index, template_data in decoded_templates.items():
                    finger_obj = Finger(uid=user.uid, fid=finger_index, valid=True, template=template_data)
                    templates_to_send.append(finger_obj)
                    fingerprint_count += 1
                
                # Only save if we have templates to send
                if templates_to_send:
                    conn.save_user_template(user, templates_to_send)
                
                return {
                    "success": True,
                    "device_id": device_id,
                    "ip": ip_address,
                    "employee": employee_data["employee"],
                    "message": f"Successfully synced {fingerprint_count} fingerprints for user {attendance_device_id}"
                }
                
            finally:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except:
                    pass
                    
        except Exception as e:
            return {
                "success": False,
                "device_id": device_id,
                "ip": ip_address,
                "employee": employee_data["employee"],
                "message": f"Sync error: {str(e)}"
            }
    
    def sync_all_employees_to_device(self, device_config, employees_data):
        """Sync all employees to single device - optimized approach"""
        device_id = device_config['device_id']
        ip_address = device_config['ip']
        
        logger.info(f"Syncing {len(employees_data)} employees to device {device_id} ({ip_address})")
        
        try:
            # Check connection once
            if not self.check_device_connection(device_config):
                logger.warning(f"✗ Device {device_id} ({ip_address}) is not reachable")
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": False,
                    "synced_count": 0,
                    "total_count": len(employees_data),
                    "message": f"Device {device_id} is not reachable"
                }
            
            # Connect once
            zk = ZK(ip_address, port=4370, timeout=10, force_udp=True, ommit_ping=True)
            conn = zk.connect()
            
            if not conn:
                logger.warning(f"✗ Failed to connect to device {device_id}")
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": False,
                    "synced_count": 0,
                    "total_count": len(employees_data),
                    "message": f"Failed to connect to device {device_id}"
                }
            
            try:
                # Disable device once
                conn.disable_device()
                logger.info(f"Device {device_id} disabled, processing {len(employees_data)} employees...")
                
                synced_count = 0
                failed_employees = []
                synced_users = []
                
                # Process all employees in this connection
                for i, employee_data in enumerate(employees_data, 1):
                    try:
                        attendance_device_id = employee_data["attendance_device_id"]
                        
                        # Delete existing user
                        existing_users = conn.get_users()
                        user_exists = any(str(u.user_id) == str(attendance_device_id) for u in existing_users)
                        if user_exists:
                            conn.delete_user(user_id=attendance_device_id)
                            time.sleep(0.1)
                        
                        # Create user
                        full_name = employee_data["employee_name"]
                        shortened_name = self.shorten_name(full_name, 24)
                        password = employee_data.get("password", "")
                        privilege = employee_data.get("privilege", 0)
                        
                        if password:
                            conn.set_user(
                                name=shortened_name,
                                privilege=privilege,
                                password=password,
                                group_id='',
                                user_id=attendance_device_id
                            )
                        else:
                            conn.set_user(
                                name=shortened_name,
                                privilege=privilege,
                                group_id='',
                                user_id=attendance_device_id
                            )
                        
                        # Get user and save templates
                        users = conn.get_users()
                        user = next((u for u in users if str(u.user_id) == str(attendance_device_id)), None)
                        
                        if user:
                            fingerprint_lookup = {fp.get("finger_index"): fp for fp in employee_data["fingerprints"] if fp.get("template_data")}
                            
                            decoded_templates = {}
                            for finger_index, fp in fingerprint_lookup.items():
                                try:
                                    decoded_templates[finger_index] = base64.b64decode(fp["template_data"])
                                except Exception:
                                    pass
                            
                            # Only send templates that have actual data
                            templates_to_send = []
                            fingerprint_count = 0
                            
                            for finger_index, template_data in decoded_templates.items():
                                finger_obj = Finger(uid=user.uid, fid=finger_index, valid=True, template=template_data)
                                templates_to_send.append(finger_obj)
                                fingerprint_count += 1
                            
                            # Only save if we have templates to send
                            if templates_to_send:
                                conn.save_user_template(user, templates_to_send)
                            synced_count += 1
                            synced_users.append(employee_data)  # Track successful sync
                            
                            if i % 10 == 0:
                                logger.info(f"  {device_id}: {i}/{len(employees_data)} processed...")
                        else:
                            failed_employees.append(f"{employee_data['employee']} (user not found)")
                            
                    except Exception as e:
                        failed_employees.append(f"{employee_data['employee']} ({str(e)})")
                
                logger.info(f"✓ Device {device_id}: {synced_count}/{len(employees_data)} employees synced")
                if failed_employees:
                    logger.warning(f"✗ Device {device_id} failed employees: {len(failed_employees)}")
                
                # Save device-specific sync results
                self.sync_state.save_device_sync_result(device_id, synced_users)
                
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": True,
                    "synced_count": synced_count,
                    "total_count": len(employees_data),
                    "failed_employees": failed_employees,
                    "synced_users": synced_users,
                    "message": f"Synced {synced_count}/{len(employees_data)} employees"
                }
                
            finally:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"✗ Device {device_id} sync error: {str(e)}")
            return {
                "device_id": device_id,
                "ip": ip_address,
                "success": False,
                "synced_count": 0,
                "total_count": len(employees_data),
                "message": f"Device sync error: {str(e)}"
            }
    
    def clear_left_employees_from_device(self, device_config, left_employees):
        """Clear fingerprint templates for Left employees while keeping user_id"""
        device_id = device_config['device_id']
        ip_address = device_config['ip']
        
        logger.info(f"Clearing templates for {len(left_employees)} Left employees from device {device_id}")
        
        try:
            # Check connection once
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
            
            # Connect once
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
                # Disable device once
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
                            
                            logger.info(f"  Cleared templates for {employee_data['employee']} (ID: {attendance_device_id})")
                            
                            if i % 10 == 0:
                                logger.info(f"  {device_id}: {i}/{len(left_employees)} processed...")
                        else:
                            logger.info(f"  User {attendance_device_id} not found on device (already cleared)")
                            
                    except Exception as e:
                        failed_employees.append(f"{employee_data['employee']} ({str(e)})")
                        logger.error(f"  Error clearing {employee_data['employee']}: {str(e)}")
                
                logger.info(f"✓ Device {device_id}: Cleared templates for {cleared_count}/{len(left_employees)} Left employees")
                if failed_employees:
                    logger.warning(f"✗ Device {device_id} failed employees: {len(failed_employees)}")
                
                # Save device-specific clear results
                if cleared_users:
                    self.sync_state.save_device_clear_result(device_id, cleared_users)
                
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
    
    def sync_and_clear_device(self, device_config, employees_data, left_employees):
        """Sync active employees and clear Left employees in single connection"""
        device_id = device_config['device_id']
        ip_address = device_config['ip']
        
        logger.info(f"Syncing {len(employees_data)} employees and clearing {len(left_employees)} Left employees on device {device_id}")
        
        try:
            # Check connection once
            if not self.check_device_connection(device_config):
                logger.warning(f"✗ Device {device_id} ({ip_address}) is not reachable")
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": False,
                    "synced_count": 0,
                    "cleared_count": 0,
                    "total_sync_count": len(employees_data),
                    "total_clear_count": len(left_employees),
                    "message": f"Device {device_id} is not reachable"
                }
            
            # Connect once for both operations
            zk = ZK(ip_address, port=4370, timeout=10, force_udp=True, ommit_ping=True)
            conn = zk.connect()
            
            if not conn:
                logger.warning(f"✗ Failed to connect to device {device_id}")
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": False,
                    "synced_count": 0,
                    "cleared_count": 0,
                    "total_sync_count": len(employees_data),
                    "total_clear_count": len(left_employees),
                    "message": f"Failed to connect to device {device_id}"
                }
            
            try:
                # Disable device once
                conn.disable_device()
                logger.info(f"Device {device_id} disabled, processing {len(employees_data)} active and {len(left_employees)} Left employees...")
                
                synced_count = 0
                cleared_count = 0
                synced_users = []
                cleared_users = []
                failed_syncs = []
                failed_clears = []
                
                # Get existing users on device once
                existing_users = conn.get_users()
                existing_user_ids = {str(u.user_id): u for u in existing_users}
                
                # PART 1: Sync active employees
                for i, employee_data in enumerate(employees_data, 1):
                    try:
                        attendance_device_id = employee_data["attendance_device_id"]
                        
                        # Delete existing user if exists
                        if attendance_device_id in existing_user_ids:
                            conn.delete_user(user_id=attendance_device_id)
                            time.sleep(0.1)
                        
                        # Create user
                        full_name = employee_data["employee_name"]
                        shortened_name = self.shorten_name(full_name, 24)
                        password = employee_data.get("password", "")
                        privilege = employee_data.get("privilege", 0)
                        
                        if password:
                            conn.set_user(name=shortened_name, privilege=privilege, password=password, group_id='', user_id=attendance_device_id)
                        else:
                            conn.set_user(name=shortened_name, privilege=privilege, group_id='', user_id=attendance_device_id)
                        
                        # Get user and save templates
                        users = conn.get_users()
                        user = next((u for u in users if str(u.user_id) == str(attendance_device_id)), None)
                        
                        if user:
                            fingerprint_lookup = {fp.get("finger_index"): fp for fp in employee_data["fingerprints"] if fp.get("template_data")}
                            
                            decoded_templates = {}
                            for finger_index, fp in fingerprint_lookup.items():
                                try:
                                    decoded_templates[finger_index] = base64.b64decode(fp["template_data"])
                                except Exception:
                                    pass
                            
                            # Only send templates that have actual data
                            templates_to_send = []
                            for finger_index, template_data in decoded_templates.items():
                                finger_obj = Finger(uid=user.uid, fid=finger_index, valid=True, template=template_data)
                                templates_to_send.append(finger_obj)
                            
                            # Only save if we have templates to send
                            if templates_to_send:
                                conn.save_user_template(user, templates_to_send)
                            
                            synced_count += 1
                            synced_users.append(employee_data)
                            
                            if i % 10 == 0:
                                logger.info(f"  {device_id}: {i}/{len(employees_data)} active employees processed...")
                        else:
                            failed_syncs.append(f"{employee_data['employee']} (user not found)")
                            
                    except Exception as e:
                        failed_syncs.append(f"{employee_data['employee']} ({str(e)})")
                
                # PART 2: Clear Left employees (device templates only)
                if left_employees:
                    logger.info(f"  Processing {len(left_employees)} Left employees for template clearing...")
                    
                    # Refresh user list after syncing active employees
                    existing_users = conn.get_users()
                    existing_user_ids = {str(u.user_id): u for u in existing_users}
                    
                    for i, employee_data in enumerate(left_employees, 1):
                        try:
                            attendance_device_id = str(employee_data["attendance_device_id"])
                            
                            # Clear templates from device (if user exists)
                            logger.info(f"  Clearing device templates for {employee_data['employee']}")
                            if attendance_device_id in existing_user_ids:
                                user = existing_user_ids[attendance_device_id]
                                
                                # Clear all fingerprint templates (set empty templates)
                                empty_templates = []
                                for j in range(10):
                                    finger_obj = Finger(uid=user.uid, fid=j, valid=False, template=b'')
                                    empty_templates.append(finger_obj)
                                
                                conn.save_user_template(user, empty_templates)
                                logger.info(f"    ✓ Device: Cleared templates (kept user_id {attendance_device_id})")
                                
                                # Mark as successful clear
                                cleared_count += 1
                                cleared_users.append(employee_data)
                                
                            else:
                                logger.info(f"    • Device: User {attendance_device_id} not found (skipped)")
                                
                        except Exception as e:
                            failed_clears.append(f"{employee_data['employee']} ({str(e)})")
                            logger.error(f"    ✗ Error processing {employee_data['employee']}: {str(e)}")
                
                logger.info(f"✓ Device {device_id}: Synced {synced_count}/{len(employees_data)} active, Cleared {cleared_count}/{len(left_employees)} Left employees")
                if failed_syncs:
                    logger.warning(f"✗ Device {device_id} failed syncs: {len(failed_syncs)}")
                if failed_clears:
                    logger.warning(f"✗ Device {device_id} failed clears: {len(failed_clears)}")
                
                # Save device-specific results
                if synced_users:
                    self.sync_state.save_device_sync_result(device_id, synced_users)
                if cleared_users:
                    self.sync_state.save_device_clear_result(device_id, cleared_users)
                
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": True,
                    "synced_count": synced_count,
                    "cleared_count": cleared_count,
                    "total_sync_count": len(employees_data),
                    "total_clear_count": len(left_employees),
                    "failed_syncs": failed_syncs,
                    "failed_clears": failed_clears,
                    "synced_users": synced_users,
                    "cleared_users": cleared_users,
                    "message": f"Synced {synced_count}/{len(employees_data)} active, Cleared {cleared_count}/{len(left_employees)} Left"
                }
                
            finally:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"✗ Device {device_id} sync+clear error: {str(e)}")
            return {
                "device_id": device_id,
                "ip": ip_address,
                "success": False,
                "synced_count": 0,
                "cleared_count": 0,
                "total_sync_count": len(employees_data),
                "total_clear_count": len(left_employees),
                "message": f"Device sync+clear error: {str(e)}"
            }
    
    def sync_full(self):
        """Sync all employees with fingerprints to all devices"""
        start_time = time.time()
        logger.info("=" * 80)
        logger.info("STARTING FULL SYNC FROM ERPNEXT TO DEVICES (STANDALONE)")
        logger.info("=" * 80)
        
        if not self.test_erpnext_connection():
            return {
                "success": False,
                "message": "Failed to connect to ERPNext API",
                "total_employees": 0,
                "synced_employees": 0,
                "execution_time": 0
            }
        
        employees = self.get_all_employees_with_fingerprints()
        
        if not employees:
            logger.warning("No employees with fingerprint data found")
            return {
                "success": False,
                "message": "No employees with fingerprint data found",
                "total_employees": 0,
                "synced_employees": 0,
                "execution_time": 0
            }
        
        logger.info(f"Starting optimized sync for {len(employees)} employees to {len(self.devices)} devices")
        
        # Also clear Left employees during sync
        left_employees = self.get_left_employees_with_device_id()
        if left_employees:
            logger.info(f"Found {len(left_employees)} Left employees to clear templates")
        
        # Sync to all devices in parallel - one connection per device for all employees
        device_results = []
        with ThreadPoolExecutor(max_workers=len(self.devices)) as executor:
            future_to_device = {
                executor.submit(self.sync_and_clear_device, device, employees, left_employees): device 
                for device in self.devices
            }
            
            for future in concurrent.futures.as_completed(future_to_device):
                device = future_to_device[future]
                try:
                    result = future.result()
                    device_results.append(result)
                    
                    if result["success"]:
                        sync_msg = f"{result.get('synced_count', 0)}/{result.get('total_sync_count', 0)} synced"
                        clear_msg = f"{result.get('cleared_count', 0)}/{result.get('total_clear_count', 0)} cleared"
                        logger.info(f"✓ {device['device_id']}: {sync_msg}, {clear_msg}")
                    else:
                        logger.warning(f"✗ {device['device_id']}: {result['message']}")
                        
                except Exception as e:
                    error_result = {
                        "device_id": device['device_id'],
                        "success": False,
                        "synced_count": 0,
                        "total_count": len(employees),
                        "message": f"Thread execution error: {str(e)}"
                    }
                    device_results.append(error_result)
                    logger.error(f"✗ {device['device_id']}: Thread execution error: {str(e)}")
        
        # Calculate totals
        total_synced = sum(r["synced_count"] for r in device_results)
        successful_devices = sum(1 for r in device_results if r["success"])
        
        execution_time = time.time() - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("FULL SYNC COMPLETED")
        logger.info(f"Total employees: {len(employees)}")
        logger.info(f"Successful devices: {successful_devices}/{len(self.devices)}")
        logger.info(f"Total sync operations: {total_synced}")
        logger.info(f"Total execution time: {execution_time:.2f} seconds")
        logger.info("=" * 80)
        
        # Save last sync timestamp
        self.sync_state.set_last_sync()
        
        return {
            "success": successful_devices > 0,
            "message": f"Full sync completed: {successful_devices}/{len(self.devices)} devices successful, {total_synced} total operations",
            "total_employees": len(employees),
            "synced_employees": total_synced,
            "successful_devices": successful_devices,
            "execution_time": execution_time,
            "detailed_results": device_results
        }
    
    def classify_and_process_employees(self, changed_employees, since_datetime):
        """Classify changed employees and process according to new algorithm"""
        current_date = datetime.datetime.now().date()
        
        employees_to_sync = []  # Active employees needing fingerprint sync
        employees_to_clear_all = []  # Active employees needing all fingerprints cleared
        left_employees_to_cleanup = []  # Left employees needing complete cleanup
        
        logger.info(f"Classifying {len(changed_employees)} changed employees...")
        
        for employee in changed_employees:
            employee_id = employee.get("employee_id") or employee.get("employee")
            employee_status = employee.get("status", "Active")
            relieving_date = employee.get("relieving_date")
            modified = employee.get("modified")
            
            # Parse relieving_date if it's a string
            if relieving_date and isinstance(relieving_date, str):
                try:
                    relieving_date = datetime.datetime.strptime(relieving_date, "%Y-%m-%d").date()
                except:
                    relieving_date = None
            
            # Check if employee status is 'Left' and past relieving date
            if (employee_status == 'Left' and 
                relieving_date and 
                current_date > relieving_date):
                
                logger.info(f"Employee {employee.get('attendance_device_id')} {employee.get('employee')} {employee.get('employee_name')} marked for LEFT cleanup (past relieving date)")
                left_employees_to_cleanup.append(employee)
                
            elif modified and since_datetime:
                # Parse modified string to datetime for comparison
                try:
                    if isinstance(modified, str):
                        # Try different datetime formats
                        try:
                            modified_dt = datetime.datetime.strptime(modified, "%Y-%m-%d %H:%M:%S.%f")
                        except ValueError:
                            modified_dt = datetime.datetime.strptime(modified, "%Y-%m-%d %H:%M:%S")
                    else:
                        modified_dt = modified
                    
                    if modified_dt > since_datetime:
                        # Employee has changes, check fingerprint count
                        try:
                            fingerprint_count = self.get_employee_fingerprint_count(employee_id)
                            
                            if fingerprint_count <= 0:
                                logger.info(f"Employee {employee.get('attendance_device_id')} {employee.get('employee')} {employee.get('employee_name')} marked for CLEAR_ALL (no fingerprints)")
                                employees_to_clear_all.append(employee)
                            else:
                                logger.info(f"Employee {employee.get('attendance_device_id')} {employee.get('employee')} {employee.get('employee_name')} marked for SELECTIVE_SYNC ({fingerprint_count} fingerprints)")
                                employees_to_sync.append(employee)
                                
                        except Exception as e:
                            logger.warning(f"Could not get fingerprint count for {employee.get('attendance_device_id')} {employee.get('employee')} {employee.get('employee_name')}: {e}")
                            # Fallback: treat as selective sync
                            employees_to_sync.append(employee)
                            
                except ValueError as e:
                    logger.warning(f"Could not parse modified date for {employee.get('attendance_device_id')} {employee.get('employee')} {employee.get('employee_name')}: {e}")
                    # Fallback: treat as selective sync if we can't parse date
                    employees_to_sync.append(employee)
        
        logger.info(f"Classification result: {len(employees_to_sync)} for selective sync, "
                   f"{len(employees_to_clear_all)} for clear all, {len(left_employees_to_cleanup)} for LEFT cleanup")
        
        return employees_to_sync, employees_to_clear_all, left_employees_to_cleanup
    
    def clear_all_fingerprints_for_employee(self, device_config, employee_data):
        """Clear all fingerprints for an employee on a device"""
        device_id = device_config['device_id']
        ip_address = device_config['ip']
        attendance_device_id = employee_data["attendance_device_id"]
        
        try:
            if not self.check_device_connection(device_config):
                return {"success": False, "message": f"Device {device_id} not reachable"}
            
            zk = ZK(ip_address, port=4370, timeout=10, force_udp=True, ommit_ping=True)
            conn = zk.connect()
            
            if not conn:
                return {"success": False, "message": f"Failed to connect to device {device_id}"}
            
            try:
                conn.disable_device()
                
                # Check if user exists
                existing_users = conn.get_users()
                user = next((u for u in existing_users if str(u.user_id) == str(attendance_device_id)), None)
                
                if user:
                    # Clear all fingerprint templates using delete method
                    try:
                        # Method 1: Try to delete specific templates
                        for finger_index in range(10):
                            try:
                                conn.delete_user_template(user.uid, finger_index)
                            except:
                                pass  # Ignore if finger doesn't exist
                    except:
                        # Method 2: Fallback - recreate user without templates
                        try:
                            # Save user info
                            user_name = user.name
                            user_privilege = user.privilege
                            user_password = ""  # Get from employee data if needed
                            user_id = user.user_id
                            
                            # Delete and recreate user
                            conn.delete_user(user_id=user_id)
                            time.sleep(0.1)
                            conn.set_user(name=user_name, privilege=user_privilege, user_id=user_id)
                        except Exception as fallback_error:
                            logger.warning(f"    Fallback clear method failed: {fallback_error}")
                            # Last resort: set empty templates
                            empty_templates = []
                            for finger_index in range(10):
                                finger_obj = Finger(uid=user.uid, fid=finger_index, valid=False, template=b'')
                                empty_templates.append(finger_obj)
                            conn.save_user_template(user, empty_templates)
                    logger.info(f"  ✓ Cleared all fingerprints for {employee_data['attendance_device_id']} {employee_data['employee']} {employee_data['employee_name']} on device {device_id}")
                    return {"success": True, "message": "All fingerprints cleared"}
                else:
                    logger.info(f"  • User {attendance_device_id} not found on device {device_id}")
                    return {"success": True, "message": "User not found (already cleared)"}
                    
            finally:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except:
                    pass
                    
        except Exception as e:
            return {"success": False, "message": f"Clear error: {str(e)}"}
    
    def selective_sync_employee_fingerprints(self, device_config, employee_data):
        """Selectively sync employee fingerprints (clear deleted + sync existing)"""
        device_id = device_config['device_id']
        ip_address = device_config['ip']
        attendance_device_id = employee_data["attendance_device_id"]
        
        try:
            if not self.check_device_connection(device_config):
                return {"success": False, "message": f"Device {device_id} not reachable"}
            
            zk = ZK(ip_address, port=4370, timeout=10, force_udp=True, ommit_ping=True)
            conn = zk.connect()
            
            if not conn:
                return {"success": False, "message": f"Failed to connect to device {device_id}"}
            
            try:
                conn.disable_device()
                
                # Check if user exists
                existing_users = conn.get_users()
                user = next((u for u in existing_users if str(u.user_id) == str(attendance_device_id)), None)
                
                if not user:
                    logger.info(f"  • User {attendance_device_id} not found on device {device_id}, skipping selective sync")
                    return {"success": True, "message": "User not found"}
                
                # Get ERPNext fingerprints
                erpnext_fingers = {fp.get("finger_index"): fp for fp in employee_data["fingerprints"] if fp.get("template_data")}
                erpnext_finger_indexes = set(erpnext_fingers.keys())
                
                # Get device fingerprints (simplified - we'll clear all and re-sync for now)
                # In a full implementation, you'd get current device templates to compare
                device_finger_indexes = set(range(10))  # Assume all possible fingers might exist
                
                # Find fingers to clear (on device but not in ERPNext)
                fingers_to_clear = device_finger_indexes - erpnext_finger_indexes
                
                # Prepare templates to send
                templates_to_send = []
                
                # Clear deleted fingers
                for finger_index in fingers_to_clear:
                    finger_obj = Finger(uid=user.uid, fid=finger_index, valid=False, template=b'')
                    templates_to_send.append(finger_obj)
                
                # Add existing fingers from ERPNext
                for finger_index, fp in erpnext_fingers.items():
                    try:
                        decoded_template = base64.b64decode(fp["template_data"])
                        finger_obj = Finger(uid=user.uid, fid=finger_index, valid=True, template=decoded_template)
                        templates_to_send.append(finger_obj)
                    except Exception as e:
                        logger.warning(f"  Failed to decode template for finger {finger_index}: {e}")
                
                # Save all templates
                if templates_to_send:
                    conn.save_user_template(user, templates_to_send)
                    
                sync_count = len(erpnext_fingers)
                clear_count = len(fingers_to_clear)
                logger.info(f"  ✓ Selective sync for {employee_data['attendance_device_id']} {employee_data['employee']} {employee_data['employee_name']} on device {device_id}: "
                           f"{sync_count} synced, {clear_count} cleared")
                
                return {"success": True, "message": f"Selective sync: {sync_count} synced, {clear_count} cleared"}
                    
            finally:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except:
                    pass
                    
        except Exception as e:
            return {"success": False, "message": f"Selective sync error: {str(e)}"}
    
    def cleanup_left_employee_complete(self, device_config, employee_data):
        """Complete cleanup for Left employee: ERPNext + device templates"""
        device_id = device_config['device_id']
        employee_id = employee_data.get("employee_id") or employee_data.get("employee")
        
        # Step 1: Delete ERPNext fingerprints (only once, not per device)
        erpnext_result = {"success": True, "deleted_count": 0}
        if hasattr(self, '_left_employees_erpnext_cleaned'):
            if employee_id not in self._left_employees_erpnext_cleaned:
                try:
                    erpnext_result = self.delete_employee_fingerprints_from_erpnext(employee_id)
                    self._left_employees_erpnext_cleaned.add(employee_id)
                    logger.info(f"  ERPNext cleanup for {employee_data['attendance_device_id']} {employee_data['employee']} {employee_data['employee_name']}: {erpnext_result.get('message', 'completed')}")
                except Exception as e:
                    logger.warning(f"  ERPNext cleanup failed for {employee_data['attendance_device_id']} {employee_data['employee']} {employee_data['employee_name']}: {e}")
                    erpnext_result = {"success": False, "deleted_count": 0, "message": str(e)}
        else:
            self._left_employees_erpnext_cleaned = {employee_id}
            try:
                erpnext_result = self.delete_employee_fingerprints_from_erpnext(employee_id)
                logger.info(f"  ERPNext cleanup for {employee_data['employee']}: {erpnext_result.get('message', 'completed')}")
            except Exception as e:
                logger.warning(f"  ERPNext cleanup failed for {employee_data['employee']}: {e}")
                erpnext_result = {"success": False, "deleted_count": 0, "message": str(e)}
        
        # Step 2: Clear device templates
        device_result = self.clear_all_fingerprints_for_employee(device_config, employee_data)
        
        return {
            "success": erpnext_result["success"] or device_result["success"],
            "erpnext_result": erpnext_result,
            "device_result": device_result
        }
    
    def sync_changed(self, since_datetime=None):
        """Sync only employees with changes since given datetime to all devices - NEW ALGORITHM"""
        start_time = time.time()
        logger.info("=" * 80)
        logger.info("STARTING SMART CHANGED SYNC FROM ERPNEXT TO DEVICES")
        logger.info("=" * 80)
        
        if not self.test_erpnext_connection():
            return {
                "success": False,
                "message": "Failed to connect to ERPNext API",
                "total_employees": 0,
                "synced_employees": 0,
                "execution_time": 0
            }
        
        if not since_datetime:
            since_datetime = self.sync_state.get_last_sync() or (datetime.datetime.now() - datetime.timedelta(hours=24))
        
        logger.info(f"Syncing changes since: {since_datetime}")
        
        # Get changed employees
        changed_employees = self.get_changed_employees_with_fingerprints(since_datetime)
        
        if not changed_employees:
            logger.info("No employees with changes found")
            # Still save last sync timestamp
            self.sync_state.set_last_sync()
            return {
                "success": True,
                "message": "No employees with changes found",
                "total_employees": 0,
                "synced_employees": 0,
                "execution_time": time.time() - start_time
            }
        
        logger.info(f"Found {len(changed_employees)} changed employees")
        
        # Classify employees according to new algorithm
        employees_to_sync, employees_to_clear_all, left_employees_to_cleanup = self.classify_and_process_employees(
            changed_employees, since_datetime
        )
        
        # Process each category in parallel across devices
        device_results = []
        
        with ThreadPoolExecutor(max_workers=len(self.devices)) as executor:
            # Submit tasks for each device
            future_to_device = {}
            
            for device in self.devices:
                future = executor.submit(self.process_device_smart_sync, device, 
                                       employees_to_sync, employees_to_clear_all, left_employees_to_cleanup)
                future_to_device[future] = device
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_device):
                device = future_to_device[future]
                try:
                    result = future.result()
                    device_results.append(result)
                    
                    if result["success"]:
                        logger.info(f"✓ {device['device_id']}: {result['message']}")
                    else:
                        logger.warning(f"✗ {device['device_id']}: {result['message']}")
                        
                except Exception as e:
                    error_result = {
                        "device_id": device['device_id'],
                        "success": False,
                        "total_operations": 0,
                        "message": f"Thread execution error: {str(e)}"
                    }
                    device_results.append(error_result)
                    logger.error(f"✗ {device['device_id']}: Thread execution error: {str(e)}")
        
        # Calculate totals
        total_operations = sum(r.get("total_operations", 0) for r in device_results)
        successful_devices = sum(1 for r in device_results if r["success"])
        
        execution_time = time.time() - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("SMART CHANGED SYNC COMPLETED")
        logger.info(f"Total changed employees: {len(changed_employees)}")
        logger.info(f"  - Selective sync: {len(employees_to_sync)}")
        logger.info(f"  - Clear all: {len(employees_to_clear_all)}")
        logger.info(f"  - Left cleanup: {len(left_employees_to_cleanup)}")
        logger.info(f"Successful devices: {successful_devices}/{len(self.devices)}")
        logger.info(f"Total operations: {total_operations}")
        logger.info(f"Total execution time: {execution_time:.2f} seconds")
        logger.info("=" * 80)
        
        # Save last sync timestamp
        self.sync_state.set_last_sync()
        
        return {
            "success": successful_devices > 0,
            "message": f"Smart sync completed: {successful_devices}/{len(self.devices)} devices successful, {total_operations} total operations",
            "total_employees": len(changed_employees),
            "synced_employees": total_operations,
            "successful_devices": successful_devices,
            "execution_time": execution_time,
            "detailed_results": device_results
        }
    
    def process_device_smart_sync(self, device_config, employees_to_sync, employees_to_clear_all, left_employees_to_cleanup):
        """Process all employee categories for a single device"""
        device_id = device_config['device_id']
        
        total_operations = 0
        results = []
        
        logger.info(f"Device {device_id}: Processing {len(employees_to_sync)} selective, "
                   f"{len(employees_to_clear_all)} clear all, {len(left_employees_to_cleanup)} left cleanup")
        
        try:
            # Process selective sync employees
            for employee in employees_to_sync:
                result = self.selective_sync_employee_fingerprints(device_config, employee)
                results.append(f"Selective {employee['employee']}: {result['message']}")
                if result["success"]:
                    total_operations += 1
            
            # Process clear all employees
            for employee in employees_to_clear_all:
                result = self.clear_all_fingerprints_for_employee(device_config, employee)
                results.append(f"Clear all {employee['employee']}: {result['message']}")
                if result["success"]:
                    total_operations += 1
            
            # Process left employees cleanup
            for employee in left_employees_to_cleanup:
                result = self.cleanup_left_employee_complete(device_config, employee)
                results.append(f"Left cleanup {employee['employee']}: device={result['device_result']['message']}")
                if result["success"]:
                    total_operations += 1
            
            return {
                "device_id": device_id,
                "success": True,
                "total_operations": total_operations,
                "message": f"{total_operations} operations completed",
                "details": results
            }
            
        except Exception as e:
            return {
                "device_id": device_id,
                "success": False,
                "total_operations": total_operations,
                "message": f"Device processing error: {str(e)}",
                "details": results
            }
    
    def auto_sync(self):
        """Auto detect sync mode and execute"""
        if self.sync_state.is_first_run():
            logger.info("First run detected - starting full sync")
            return self.sync_full()
        else:
            last_sync = self.sync_state.get_last_sync()
            logger.info(f"Previous sync found at {last_sync} - starting changed sync")
            return self.sync_changed(last_sync)

def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Standalone sync of employee fingerprint data from ERPNext to attendance devices')
    parser.add_argument('--mode', choices=['full', 'changed', 'auto'], default='auto',
                       help='Sync mode: full (all employees), changed (only recent changes), or auto (detect based on last_sync)')
    parser.add_argument('--hours', type=int, default=24,
                       help='For changed mode: number of hours back to check for changes (default: 24)')
    
    args = parser.parse_args()
    
    try:
        sync_tool = ERPNextSyncToDeviceStandalone()
        
        if args.mode == 'full':
            result = sync_tool.sync_full()
        elif args.mode == 'changed':
            since_datetime = datetime.datetime.now() - datetime.timedelta(hours=args.hours)
            result = sync_tool.sync_changed(since_datetime)
        else:  # auto mode
            result = sync_tool.auto_sync()
        
        if result["success"]:
            logger.info(f"Sync completed successfully: {result['message']}")
            exit(0)
        else:
            logger.error(f"Sync failed: {result['message']}")
            exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error during sync: {str(e)}")
        raise

if __name__ == "__main__":
    main()