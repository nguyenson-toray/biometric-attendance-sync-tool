#!/usr/bin/env python3
"""
Sync fingerprint data from master device to ERPNext
Reads all users from master device and saves to ERPNext custom_fingerprints child table
"""

import local_config as config
from zk import ZK
import base64
import logging
from erpnext_api_client import ERPNextAPIClient

class MasterDeviceToERPNextSync:
    """Sync all fingerprint users from master device to ERPNext"""
    
    def __init__(self):
        self.setup_logging()
        self.master_device = config.devices_master
        self.erpnext_client = ERPNextAPIClient(
            base_url=config.ERPNEXT_URL,
            api_key=config.ERPNEXT_API_KEY,
            api_secret=config.ERPNEXT_API_SECRET
        )
        
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
        
        
    def get_all_users_from_master_device(self, limit=None):
        """Get users with fingerprints from master device, with optimized filtering"""
        # Check if we should use optimized filtering
        filter_ids = getattr(config, 'sync_from_master_device_to_erpnext_filters_id', [])
        
        if filter_ids:
            return self.get_specific_users_from_master_device(filter_ids, limit)
        else:
            return self.get_all_users_from_master_device_full_scan(limit)
            
    def get_specific_users_from_master_device(self, user_ids, limit=None):
        """Get specific users by user_id from master device (optimized)"""
        limit_text = f" (limit: {limit})" if limit else ""
        self.logger.info(f"🎯 Reading specific users from master device{limit_text}...")
        self.logger.info(f"Master: {self.master_device['device_id']} ({self.master_device['ip']})")
        self.logger.info(f"Target user IDs: {user_ids}")
        
        try:
            # Connect to master device
            zk = ZK(self.master_device['ip'], port=4370, timeout=10, force_udp=True, ommit_ping=True)
            conn = zk.connect()
            
            if not conn:
                self.logger.error("❌ Failed to connect to master device")
                return []
                
            conn.disable_device()
            
            # Get all users once and create a lookup dictionary
            self.logger.info("📋 Loading user list from device...")
            all_users = conn.get_users()
            self.logger.info(f"👥 Found {len(all_users)} total users on device")
            
            # Create lookup dictionary for faster searching
            user_lookup = {str(u.user_id): u for u in all_users}
            
            users_with_fingerprints = []
            found_count = 0
            
            for target_user_id in user_ids:
                # Check limit
                if limit and found_count >= limit:
                    self.logger.info(f"  🔢 Reached limit of {limit} users, stopping search")
                    break
                    
                try:
                    self.logger.info(f"🔍 Searching for user ID: {target_user_id}")
                    
                    # Look up user in dictionary
                    user = user_lookup.get(str(target_user_id))
                    
                    if not user:
                        self.logger.warning(f"  ❌ User {target_user_id} not found on device")
                        continue
                    
                    self.logger.info(f"  ✅ Found user: {user.user_id} - {user.name}")
                    
                    # Check for fingerprints
                    fingerprints = []
                    for finger_id in range(10):
                        try:
                            template = conn.get_user_template(user.uid, finger_id)
                            if (template and hasattr(template, 'valid') and 
                                template.valid and template.template and len(template.template) > 0):
                                template_data = base64.b64encode(template.template).decode('utf-8')
                                # Skip empty or invalid template data
                                if template_data and len(template_data.strip()) > 0:
                                    fingerprints.append({
                                        'finger_index': finger_id,
                                        'template_data': template_data
                                    })
                        except Exception:
                            # Skip individual finger errors
                            pass
                    
                    # Only include users with valid fingerprint data
                    if fingerprints:
                        user_data = {
                            'uid': user.uid,
                            'user_id': str(user.user_id),  # Ensure string for matching attendance_device_id
                            'name': user.name,
                            'privilege': user.privilege,
                            'password': user.password,
                            'group_id': user.group_id,
                            'fingerprints': fingerprints
                        }
                        users_with_fingerprints.append(user_data)
                        found_count += 1
                        self.logger.info(f"  ✅ {user.user_id}: {user.name} ({len(fingerprints)} fingerprints)")
                    else:
                        self.logger.warning(f"  ⚠️ User {target_user_id} has no fingerprints")
                        
                except Exception as e:
                    self.logger.error(f"  ❌ Error processing user {target_user_id}: {str(e)}")
                    continue
                    
            conn.enable_device()
            conn.disconnect()
            
            self.logger.info(f"📊 Found {len(users_with_fingerprints)} users with fingerprints (from {len(user_ids)} target IDs)")
            return users_with_fingerprints
            
        except Exception as e:
            self.logger.error(f"❌ Error reading from master device: {str(e)}")
            return []
            
    def get_all_users_from_master_device_full_scan(self, limit=None):
        """Get all users with fingerprints from master device (full scan)"""
        limit_text = f" (limit: {limit})" if limit else ""
        self.logger.info(f"🔍 Reading all users from master device{limit_text}...")
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
                # Check if we've reached the limit
                if limit and len(users_with_fingerprints) >= limit:
                    self.logger.info(f"  🔢 Reached limit of {limit} users with fingerprints, stopping scan")
                    break
                    
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
                                template_data = base64.b64encode(template.template).decode('utf-8')
                                # Skip empty or invalid template data
                                if template_data and len(template_data.strip()) > 0:
                                    fingerprints.append({
                                        'finger_index': finger_id,
                                        'template_data': template_data
                                    })
                        except Exception:
                            # Skip individual finger errors
                            pass
                                
                    # Only include users with valid fingerprint data
                    if fingerprints:
                        user_data = {
                            'uid': user.uid,
                            'user_id': str(user.user_id),  # Ensure string for matching attendance_device_id
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
            
    def find_active_employee_by_attendance_device_id(self, attendance_device_id):
        """Find active employee in ERPNext by attendance_device_id"""
        try:
            endpoint = '/api/resource/Employee'
            params = {
                'filters': f'[["attendance_device_id", "=", "{attendance_device_id}"], ["status", "=", "Active"]]',
                'fields': '["name", "employee", "employee_name", "attendance_device_id", "status"]',
                'limit_page_length': 1
            }
            
            response = self.erpnext_client._make_request('GET', endpoint, params=params)
            employees = response.get('data', [])
            if employees:
                return employees[0]
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding active employee with attendance_device_id {attendance_device_id}: {e}")
            return None
            
    def save_fingerprints_to_employee(self, employee_name, fingerprints_data):
        """Save fingerprint data to employee's custom_fingerprints child table using API client"""
        try:
            # Get the current employee document
            endpoint = f'/api/resource/Employee/{employee_name}'
            response = self.erpnext_client._make_request('GET', endpoint)
            
            if not response.get('data'):
                return {"success": False, "message": f"Employee {employee_name} not found"}
                
            employee_doc = response['data']
            
            # Clear existing fingerprints
            employee_doc['custom_fingerprints'] = []
            
            # Add new fingerprints (only non-empty templates)
            for fp in fingerprints_data:
                finger_index = fp['finger_index']
                template_data = fp['template_data']
                
                # Skip empty template data
                if not template_data or len(template_data.strip()) == 0:
                    continue
                    
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
            update_endpoint = f'/api/resource/Employee/{employee_name}'
            self.erpnext_client._make_request('PUT', update_endpoint, data=employee_doc)
            
            return {
                "success": True, 
                "message": f"Saved {len(employee_doc['custom_fingerprints'])} fingerprints",
                "fingerprints_count": len(employee_doc['custom_fingerprints'])
            }
                
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
            
    def get_finger_name(self, finger_index):
        """Get standardized finger name from index using local_config mapping"""
        return config.get_finger_name(finger_index)
        
        
    def sync_user_to_erpnext(self, user_data):
        """Sync single user from device to ERPNext (Active employees only)"""
        user_id = user_data['user_id']
        user_name = user_data['name']
        fingerprints = user_data['fingerprints']
        
        try:
            # Find corresponding active employee in ERPNext
            employee = self.find_active_employee_by_attendance_device_id(user_id)
            
            if not employee:
                return {
                    "success": False,
                    "user_id": user_id,
                    "user_name": user_name,
                    "message": f"No active employee found with attendance_device_id: {user_id}"
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
            
    def sync_all_users_to_erpnext(self, users_data=None):
        """Main sync function - sync all users from master device to ERPNext"""
        self.logger.info("🚀 Starting master device to ERPNext fingerprint sync...")
        self.logger.info(f"Master: {self.master_device['device_id']} ({self.master_device['ip']})")
        
        # Get all users with fingerprints from master device if not provided
        if users_data is None:
            users_data = self.get_all_users_from_master_device()
        
        if not users_data:
            self.logger.error("❌ No users with fingerprints found on master device")
            return False
            
        # Sync each user to ERPNext (filtering already applied during device reading)
        user_count = len(users_data)
        processed_users = 0
        successful_users = 0
        
        self.logger.info(f"📤 Syncing {user_count} users to ERPNext...")
        
        for i, user_data in enumerate(users_data, 1):
            user_id = user_data['user_id']
            user_name = user_data['name']
            fingerprint_count = len(user_data['fingerprints'])
            
            self.logger.info(f"Progress: {i}/{user_count} - {user_id}: {user_name} ({fingerprint_count} fingerprints)")
            
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
        self.logger.info(f"Users found and processed: {user_count}")
        self.logger.info(f"Users processed: {processed_users}")
        self.logger.info(f"Users successfully synced to ERPNext: {successful_users}")
        self.logger.info(f"Users skipped (no matching active employee): {processed_users - successful_users}")
        
        success_rate = (successful_users / user_count * 100) if user_count > 0 else 0
        self.logger.info(f"Success rate: {success_rate:.1f}%")
        
        if successful_users == user_count:
            self.logger.info("✅ All users synced successfully!")
            return True
        elif successful_users > 0:
            self.logger.warning(f"⚠️ Partial success: {successful_users}/{user_count} users synced")
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
    
    # Get users with limit applied during device reading
    users = sync_manager.get_all_users_from_master_device(limit=args.limit)
    
    if not users:
        print("❌ No users with fingerprints found")
        return 1
        
    # Pass the users data directly to avoid double reading from device
    success = sync_manager.sync_all_users_to_erpnext(users_data=users)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())