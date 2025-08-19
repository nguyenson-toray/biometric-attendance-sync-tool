#!/usr/bin/env python3
"""
Sync fingerprint data from ERPNext to devices
"""

import local_config as config
from zk import ZK
from zk.base import Finger
import time
import base64
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from unidecode import unidecode
import requests
from datetime import datetime, timedelta

class MasterDeviceToERPNextSync:
    """Sync all fingerprint users from master device to ERPNext"""
    
    def __init__(self):
        self.setup_logging()
        self.master_device = config.devices_master
        
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_headers(self):
        """Get API headers for ERPNext"""
        return {
            'Authorization': f'token {config.ERPNEXT_API_KEY}:{config.ERPNEXT_API_SECRET}',
            'Content-Type': 'application/json'
        }
        
    def get_all_users_from_master_device(self):
        """Get all users with fingerprints from master device"""
        self.logger.info(f"🔍 Reading all users from master device...")
        self.logger.info(f"Master: {self.master_device['device_id']} ({self.master_device['ip']})")
        
        try:
            # Connect to master device
            zk = ZK(self.master_device['ip'], port=4370, timeout=10, force_udp=True, ommit_ping=True)
            conn = zk.connect()
            
            if not conn:
                self.logger.error("❌ Failed to connect to master device")
                return []
                
            conn.disable_device()
            
            # Get all users
            users = conn.get_users()
            self.logger.info(f"👥 Found {len(users)} total users on master device")
            
            # Find users with fingerprints
            users_with_fingerprints = []
            
            for i, user in enumerate(users):
                if i % 100 == 0:
                    self.logger.info(f"  Progress: {i}/{len(users)}")
                    
                try:
                    # Check each finger individually to get all templates
                    fingerprints = []
                    for finger_id in range(10):
                        try:
                            template = conn.get_user_template(user.uid, finger_id)
                            if (template and hasattr(template, 'valid') and 
                                template.valid and template.template and len(template.template) > 0):
                                fingerprints.append({
                                    'finger_index': finger_id,
                                    'template_data': base64.b64encode(template.template).decode('utf-8')
                                })
                        except Exception:
                            # Skip individual finger errors
                            pass
                                
                    if fingerprints:
                        user_data = {
                            'uid': user.uid,
                            'user_id': user.user_id,  # This should match attendance_device_id in ERPNext
                            'name': user.name,
                            'privilege': user.privilege,
                            'password': user.password,
                            'group_id': user.group_id,
                            'fingerprints': fingerprints
                        }
                        users_with_fingerprints.append(user_data)
                        self.logger.info(f"  ✅ {user.user_id}: {user.name} ({len(fingerprints)} fingerprints)")
                        
                except Exception as e:
                    # Skip users with errors
                    self.logger.debug(f"Error processing user {user.user_id}: {e}")
                    pass
                    
            conn.enable_device()
            conn.disconnect()
            
            self.logger.info(f"📊 Found {len(users_with_fingerprints)} users with fingerprints")
            return users_with_fingerprints
            
        except Exception as e:
            self.logger.error(f"❌ Error reading from master device: {str(e)}")
            return []
            
    def find_employee_by_attendance_device_id(self, attendance_device_id):
        """Find employee in ERPNext by attendance_device_id"""
        try:
            url = f"{config.ERPNEXT_URL}/api/method/frappe.client.get_list"
            params = {
                'doctype': 'Employee',
                'fields': '["name", "employee", "employee_name", "attendance_device_id"]',
                'filters': f'[["attendance_device_id", "=", "{attendance_device_id}"]]',
                'limit_page_length': 1
            }
            
            headers = self.get_headers()
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                return None
                
            employees = response.json().get('message', [])
            if employees:
                return employees[0]
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding employee with attendance_device_id {attendance_device_id}: {e}")
            return None
            
    def save_fingerprints_to_employee(self, employee_name, fingerprints_data):
        """Save fingerprint data to employee's custom_fingerprints child table"""
        try:
            # First, get the current employee document
            url = f"{config.ERPNEXT_URL}/api/resource/Employee/{employee_name}"
            headers = self.get_headers()
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return {"success": False, "message": f"Employee {employee_name} not found"}
                
            employee_doc = response.json().get('data', {})
            
            # Clear existing fingerprints
            employee_doc['custom_fingerprints'] = []
            
            # Add new fingerprints
            for fp in fingerprints_data:
                finger_index = fp['finger_index']
                template_data = fp['template_data']
                
                # Get finger name from index
                finger_name = self.get_finger_name(finger_index)
                
                fingerprint_entry = {
                    'finger_index': finger_index,
                    'finger_name': finger_name,
                    'template_data': template_data,
                    'quality_score': 0  # Default quality score
                }
                
                employee_doc['custom_fingerprints'].append(fingerprint_entry)
            
            # Update employee document
            update_url = f"{config.ERPNEXT_URL}/api/resource/Employee/{employee_name}"
            update_response = requests.put(update_url, headers=headers, json=employee_doc, timeout=30)
            
            if update_response.status_code == 200:
                return {
                    "success": True, 
                    "message": f"Saved {len(fingerprints_data)} fingerprints",
                    "fingerprints_count": len(fingerprints_data)
                }
            else:
                return {
                    "success": False, 
                    "message": f"Failed to update employee: HTTP {update_response.status_code}"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
            
    def get_finger_name(self, finger_index):
        """Get standardized finger name from index"""
        finger_names = {
            0: "Left Thumb", 1: "Left Index", 2: "Left Middle", 3: "Left Ring", 4: "Left Little",
            5: "Right Thumb", 6: "Right Index", 7: "Right Middle", 8: "Right Ring", 9: "Right Little"
        }
        return finger_names.get(finger_index, f"Finger {finger_index}")
        
    def sync_user_to_erpnext(self, user_data):
        """Sync single user from device to ERPNext"""
        user_id = user_data['user_id']
        user_name = user_data['name']
        fingerprints = user_data['fingerprints']
        
        try:
            # Find corresponding employee in ERPNext
            employee = self.find_employee_by_attendance_device_id(user_id)
            
            if not employee:
                return {
                    "success": False,
                    "user_id": user_id,
                    "user_name": user_name,
                    "message": f"No employee found with attendance_device_id: {user_id}"
                }
            
            # Save fingerprints to employee
            result = self.save_fingerprints_to_employee(employee['name'], fingerprints)
            
            return {
                "success": result["success"],
                "user_id": user_id,
                "user_name": user_name,
                "employee_code": employee['employee'],
                "employee_name": employee['employee_name'],
                "message": result["message"],
                "fingerprints_count": result.get("fingerprints_count", 0)
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": user_id,
                "user_name": user_name,
                "message": f"Error: {str(e)}"
            }
            
    def sync_all_users_to_erpnext(self):
        """Main sync function - sync all users from master device to ERPNext"""
        self.logger.info("🚀 Starting master device to ERPNext fingerprint sync...")
        self.logger.info(f"Master: {self.master_device['device_id']} ({self.master_device['ip']})")
        
        # Get all users with fingerprints from master device
        users_data = self.get_all_users_from_master_device()
        
        if not users_data:
            self.logger.error("❌ No users with fingerprints found on master device")
            return False
            
        # Sync each user to ERPNext
        total_users = len(users_data)
        processed_users = 0
        successful_users = 0
        
        self.logger.info(f"📤 Syncing {total_users} users to ERPNext...")
        
        for i, user_data in enumerate(users_data, 1):
            user_id = user_data['user_id']
            user_name = user_data['name']
            fingerprint_count = len(user_data['fingerprints'])
            
            self.logger.info(f"Progress: {i}/{total_users} - {user_id}: {user_name} ({fingerprint_count} fingerprints)")
            
            try:
                result = self.sync_user_to_erpnext(user_data)
                processed_users += 1
                
                if result["success"]:
                    successful_users += 1
                    self.logger.info(f"  ✅ Synced to ERPNext: {result['employee_code']} - {result['employee_name']} ({result['fingerprints_count']} fingerprints)")
                else:
                    self.logger.warning(f"  ⚠️ Skipped: {result['message']}")
                    
            except Exception as e:
                self.logger.error(f"Error processing user {user_id}: {str(e)}")
                
        # Final summary
        self.logger.info("==" * 30)
        self.logger.info("🎯 SYNC SUMMARY - MASTER DEVICE TO ERPNEXT")
        self.logger.info(f"Total users found on device: {total_users}")
        self.logger.info(f"Users processed: {processed_users}")
        self.logger.info(f"Users successfully synced to ERPNext: {successful_users}")
        self.logger.info(f"Users skipped (no matching employee): {processed_users - successful_users}")
        
        success_rate = (successful_users / total_users * 100) if total_users > 0 else 0
        self.logger.info(f"Success rate: {success_rate:.1f}%")
        
        if successful_users == total_users:
            self.logger.info("✅ All users synced successfully!")
            return True
        elif successful_users > 0:
            self.logger.warning(f"⚠️ Partial success: {successful_users}/{total_users} users synced")
            return True
        else:
            self.logger.error("❌ No users were synced successfully")
            return False

class ERPNextToDeviceSync:
    """Sync fingerprint users from ERPNext to target devices"""
    
    def __init__(self):
        self.setup_logging()
        self.target_devices = config.devices
        
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
            
    def get_headers(self):
        """Get API headers for ERPNext"""
        return {
            'Authorization': f'token {config.ERPNEXT_API_KEY}:{config.ERPNEXT_API_SECRET}',
            'Content-Type': 'application/json'
        }
        
    def shorten_name(self, full_name, max_length=24):
        """Shorten name for device compatibility"""
        if not full_name:
            return full_name
            
        text_processed = unidecode(full_name)
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
            
    def get_all_employees_with_fingerprints(self):
        """Get all employees with fingerprints from ERPNext"""                
        self.logger.info("🔍 Fetching employees with fingerprints from ERPNext...")
        
        try:
            # Get employees with fingerprint data using SQL query
            # Based on utilities.py, fingerprints are stored in custom_fingerprints child table
            url = f"{config.ERPNEXT_URL}/api/method/frappe.client.get_list"
            params = {
                'doctype': 'Employee',
                'fields': '["name", "employee", "employee_name", "attendance_device_id", "status", "modified"]',
                'filters': '[["status", "=", "Active"], ["attendance_device_id", "is", "set"]]',
                'limit_page_length': 0
            }
            
            headers = self.get_headers()
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch employees: HTTP {response.status_code}")
                return []
                
            employees_data = response.json().get('message', [])
            self.logger.info(f"👥 Found {len(employees_data)} active employees with attendance_device_id")
            
            # Filter employees that actually have fingerprint data
            employees_with_fingerprints = []
            
            for employee in employees_data:
                # Check if employee has fingerprint data
                fingerprints = self.get_employee_fingerprints(employee['name'])
                if fingerprints:
                    employee['fingerprint_count'] = len(fingerprints)
                    employees_with_fingerprints.append(employee)
                    self.logger.debug(f"  ✅ {employee['employee']}: {employee['employee_name']} ({len(fingerprints)} fingerprints)")
                    
            self.logger.info(f"📊 Found {len(employees_with_fingerprints)} employees with fingerprints")
                
            return employees_with_fingerprints
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching employees: {str(e)}")
            return []
            
    def get_employees_changed_since(self, since_datetime):
        """Get employees changed since specific datetime"""
                
        self.logger.info(f"🔍 Fetching employees changed since {since_datetime}...")
        
        try:
            # Get employees modified since the given datetime
            url = f"{config.ERPNEXT_URL}/api/resource/Employee"
            params = {
                'fields': '["name", "employee", "employee_name", "status", "modified"]',
                'filters': f'[["status", "=", "Active"], ["modified", ">", "{since_datetime.isoformat()}"]]',
                'limit_page_length': 0
            }
            
            headers = self.get_headers()
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch changed employees: HTTP {response.status_code}")
                return []
                
            employees_data = response.json().get('data', [])
            self.logger.info(f"👥 Found {len(employees_data)} employees changed since {since_datetime}")
            
            # Also check for fingerprint data changes
            # Based on utilities.py, fingerprints are in custom_fingerprints child table
            # We'll query employees that have been modified or have modified fingerprint data
            fingerprint_url = f"{config.ERPNEXT_URL}/api/method/frappe.client.get_list"
            fingerprint_params = {
                'doctype': 'Fingerprint Data',
                'fields': '["parent", "modified"]',
                'filters': f'[["modified", ">", "{since_datetime.isoformat()}"]]',
                'limit_page_length': 0
            }
            
            fingerprint_response = requests.get(fingerprint_url, headers=headers, params=fingerprint_params, timeout=30)
            
            if fingerprint_response.status_code == 200:
                fingerprint_changes = fingerprint_response.json().get('message', [])
                self.logger.info(f"📱 Found {len(fingerprint_changes)} fingerprint data changes")
                
                # Add employees with fingerprint changes
                changed_employee_names = set(emp['name'] for emp in employees_data)
                for fp_change in fingerprint_changes:
                    employee_name = fp_change['parent']  # parent is the Employee doctype name
                    if employee_name not in changed_employee_names:
                        # Fetch full employee data
                        emp_response = requests.get(
                            f"{config.ERPNEXT_URL}/api/resource/Employee/{employee_name}",
                            headers=headers, timeout=10
                        )
                        if emp_response.status_code == 200:
                            emp_data = emp_response.json().get('data', {})
                            if emp_data.get('status') == 'Active' and emp_data.get('attendance_device_id'):
                                employees_data.append(emp_data)
                                changed_employee_names.add(emp_data['name'])
            
            # Filter employees that actually have fingerprint data
            employees_with_fingerprints = []
            
            for employee in employees_data:
                fingerprints = self.get_employee_fingerprints(employee['name'])
                if fingerprints:
                    employee['fingerprint_count'] = len(fingerprints)
                    employees_with_fingerprints.append(employee)
                    
            self.logger.info(f"📊 Found {len(employees_with_fingerprints)} changed employees with fingerprints")
                
            return employees_with_fingerprints
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching changed employees: {str(e)}")
            return []
            
    def get_employee_fingerprints(self, employee_name):
        """Get fingerprint data for a specific employee from custom_fingerprints child table"""
                
        try:
            # Get employee document with custom_fingerprints child table
            # Based on utilities.py structure
            url = f"{config.ERPNEXT_URL}/api/resource/Employee/{employee_name}"
            headers = self.get_headers()
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                self.logger.debug(f"No employee found: {employee_name}")
                return []
                
            employee_data = response.json().get('data', {})
            
            # Get fingerprint data from custom_fingerprints child table
            fingerprints_data = employee_data.get('custom_fingerprints', [])
            
            # Filter out empty templates and convert to the expected format
            valid_fingerprints = []
            for fp in fingerprints_data:
                template_data = fp.get('template_data', '').strip()
                if template_data and len(template_data) > 0:
                    valid_fingerprints.append({
                        'finger_index': fp.get('finger_index', 0),  # Note: finger_index not finger_id
                        'template': template_data
                    })
                    
            self.logger.debug(f"Found {len(valid_fingerprints)} valid fingerprints for {employee_name}")
                
            return valid_fingerprints
            
        except Exception as e:
            self.logger.error(f"Error fetching fingerprints for {employee_name}: {e}")
            return []
            
    def sync_employee_to_device(self, employee_data, target_device):
        """Sync single employee to single target device"""
        employee_code = employee_data['employee']
        attendance_device_id = employee_data['attendance_device_id']  # This is the actual ID used on devices
        device_id = target_device['device_id']
        
        try:
            # Get fingerprint data
            fingerprints = self.get_employee_fingerprints(employee_data['name'])
            if not fingerprints:
                return {
                    "success": False,
                    "employee_id": employee_code,
                    "device": device_id,
                    "message": "No fingerprint data found"
                }
                
            # Connect to target device
            zk = ZK(target_device['ip'], port=4370, timeout=10, force_udp=True, ommit_ping=True)
            conn = zk.connect()
            
            if not conn:
                return {
                    "success": False,
                    "employee_id": employee_code,
                    "device": device_id,
                    "message": "Failed to connect"
                }
                
            conn.disable_device()
            
            # Delete existing user if exists (use attendance_device_id)
            existing_users = conn.get_users()
            user_exists = any(u.user_id == attendance_device_id for u in existing_users)
            
            if user_exists:
                conn.delete_user(user_id=attendance_device_id)
                time.sleep(0.1)
                
            # Create user
            shortened_name = self.shorten_name(employee_data['employee_name'], 24)
            
            conn.set_user(
                name=shortened_name,
                privilege=0,  # Regular user
                group_id='',
                user_id=attendance_device_id  # Use attendance_device_id, not employee code
            )
                
            # Verify user creation
            users = conn.get_users()
            created_user = next((u for u in users if u.user_id == attendance_device_id), None)
            
            if not created_user:
                return {
                    "success": False,
                    "employee_id": employee_code,
                    "device": device_id,
                    "message": f"Failed to create user {attendance_device_id}"
                }
                
            # Prepare fingerprint templates
            decoded_templates = {}
            for fp in fingerprints:
                try:
                    finger_index = int(fp['finger_index'])  # Changed from finger_id to finger_index
                    # Ensure finger_index is in valid range (0-9)
                    if 0 <= finger_index <= 9:
                        decoded_templates[finger_index] = base64.b64decode(fp['template'])
                except Exception:
                    pass
                    
            # Create 10 Finger objects (only valid ones will have templates)
            templates_to_send = []
            fingerprint_count = 0
            
            for i in range(10):
                if i in decoded_templates and len(decoded_templates[i]) > 0:
                    finger_obj = Finger(uid=created_user.uid, fid=i, valid=True, template=decoded_templates[i])
                    fingerprint_count += 1
                else:
                    finger_obj = Finger(uid=created_user.uid, fid=i, valid=False, template=b'')
                templates_to_send.append(finger_obj)
                
            # Send templates to device
            conn.save_user_template(created_user, templates_to_send)
            
            conn.enable_device()
            conn.disconnect()
            
            return {
                "success": True,
                "employee_id": employee_code,
                "device": device_id,
                "message": f"Synced {fingerprint_count} fingerprints"
            }
            
        except Exception as e:
            return {
                "success": False,
                "employee_id": employee_code,
                "device": device_id,
                "message": f"Error: {str(e)}"
            }
            
    def sync_employee_to_all_targets(self, employee_data):
        """Sync single employee to all target devices using threading"""
        
        results = []
        success_count = 0
        
        # Use ThreadPoolExecutor for concurrent sync
        with ThreadPoolExecutor(max_workers=min(len(self.target_devices), 5)) as executor:
            future_to_device = {
                executor.submit(self.sync_employee_to_device, employee_data, device): device
                for device in self.target_devices
            }
            
            for future in as_completed(future_to_device):
                device = future_to_device[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result["success"]:
                        success_count += 1
                        
                except Exception as e:
                    error_result = {
                        "success": False,
                        "employee_id": employee_data['employee'],  # Use employee code from data
                        "device": device['device_id'],
                        "message": f"Exception: {str(e)}"
                    }
                    results.append(error_result)
                    
        return {
            "employee_id": employee_data['employee'],
            "name": employee_data['employee_name'],
            "total_devices": len(self.target_devices),
            "success_count": success_count,
            "results": results
        }
        
            
    def sync_all_employees(self):
        """Sync all employees with fingerprints to all target devices"""
        self.logger.info("🚀 Starting ERPNext-to-device fingerprint sync (ALL EMPLOYEES)...")
        self.logger.info(f"Targets: {[d['device_id'] for d in self.target_devices]}")
        
        # Get all employees with fingerprints
        employees_data = self.get_all_employees_with_fingerprints()
        
        if not employees_data:
            self.logger.error("❌ No employees with fingerprints found in ERPNext")
            return False
            
        return self._sync_employees_list(employees_data, "ALL EMPLOYEES")
        
    def sync_changed_employees(self):
        """Sync only changed employees since specific date (default: 7 days ago)"""
        self.logger.info("🚀 Starting ERPNext-to-device fingerprint sync (CHANGED EMPLOYEES)...")
        self.logger.info(f"Targets: {[d['device_id'] for d in self.target_devices]}")
        
        # Default to 7 days ago
        since_datetime = datetime.now() - timedelta(days=7)
        self.logger.info(f"🕐 Checking changes since: {since_datetime}")
        
        # Get changed employees
        employees_data = self.get_employees_changed_since(since_datetime)
        
        if not employees_data:
            self.logger.info("✅ No changed employees with fingerprints found")
            return True
            
        return self._sync_employees_list(employees_data, "CHANGED EMPLOYEES")
        
    def _sync_employees_list(self, employees_data, sync_type):
        """Sync a list of employees to all target devices"""
        total_employees = len(employees_data)
        processed_employees = 0
        successful_employees = 0
        
        self.logger.info(f"📤 Syncing {total_employees} employees to {len(self.target_devices)} target devices...")
        
        for i, employee_data in enumerate(employees_data, 1):
            employee_id = employee_data['employee']
            employee_name = employee_data['employee_name']
            fingerprint_count = employee_data.get('fingerprint_count', 0)
            
            self.logger.info(f"Progress: {i}/{total_employees} - {employee_id}: {employee_name} ({fingerprint_count} fingerprints)")
            
            try:
                result = self.sync_employee_to_all_targets(employee_data)
                processed_employees += 1
                
                if result["success_count"] > 0:
                    successful_employees += 1
                    # Show successful devices
                    success_devices = [r["device"] for r in result["results"] if r["success"]]
                    self.logger.info(f"  ✅ Synced to {result['success_count']}/{result['total_devices']} devices: {', '.join(success_devices)}")
                else:
                    self.logger.error(f"  ❌ Failed to sync to any devices")
                    
                # Show details for failed devices
                for device_result in result["results"]:
                    if not device_result["success"]:
                        self.logger.error(f"    {device_result['device']}: {device_result['message']}")
                        
            except Exception as e:
                self.logger.error(f"Error processing employee {employee_id}: {str(e)}")
                
        # Final summary
        self.logger.info("==" * 30)
        self.logger.info(f"🎯 SYNC SUMMARY - {sync_type}")
        self.logger.info(f"Total employees found: {total_employees}")
        self.logger.info(f"Employees processed: {processed_employees}")
        self.logger.info(f"Employees successfully synced: {successful_employees}")
        self.logger.info(f"Target devices: {len(self.target_devices)}")
        
        success_rate = (successful_employees / total_employees * 100) if total_employees > 0 else 0
        self.logger.info(f"Success rate: {success_rate:.1f}%")
        
        if successful_employees == total_employees:
            self.logger.info("✅ All employees synced successfully!")
            return True
        elif successful_employees > 0:
            self.logger.warning(f"⚠️ Partial success: {successful_employees}/{total_employees} employees synced")
            return True
        else:
            self.logger.error("❌ No employees were synced successfully")
            return False

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync fingerprint data from ERPNext to devices')
    parser.add_argument('--mode', choices=['all', 'changed', 'from-device'], default='changed',
                      help='Sync mode: all employees, changed since 7 days ago, or from master device to ERPNext')
    
    args = parser.parse_args()
    
    # Choose sync manager based on mode
    if args.mode == 'from-device':
        sync_manager = MasterDeviceToERPNextSync()
        success = sync_manager.sync_all_users_to_erpnext()
    else:
        sync_manager = ERPNextToDeviceSync()
        
        # Run sync based on mode
        if args.mode == 'all':
            success = sync_manager.sync_all_employees()
        else:
            success = sync_manager.sync_changed_employees()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())