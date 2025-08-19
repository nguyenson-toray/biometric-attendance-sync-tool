#!/usr/bin/env python3
"""
Sync fingerprint data from master device to ERPNext
Reads all users from master device and saves to ERPNext custom_fingerprints child table
"""

import local_config as config
from zk import ZK
import base64
import logging
import requests

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

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync fingerprint data from master device to ERPNext')
    parser.add_argument('--limit', type=int, help='Limit number of users to sync (for testing)')
    
    args = parser.parse_args()
    
    sync_manager = MasterDeviceToERPNextSync()
    
    # Get users first to show count
    users = sync_manager.get_all_users_from_master_device()
    
    if not users:
        print("❌ No users with fingerprints found")
        return 1
        
    if args.limit:
        users = users[:args.limit]
        print(f"🔢 Limited to {len(users)} users for testing")
        
    # Temporarily modify the sync manager's data  
    sync_manager.get_all_users_from_master_device = lambda: users
    
    success = sync_manager.sync_all_users_to_erpnext()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())