#!/usr/bin/env python3
"""
Sync all users with fingerprints from master device to target devices
"""

import local_config as config
from zk import ZK, const
from zk.base import Finger
import time
import base64
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from unidecode import unidecode

class MasterToTargetSync:
    """Sync all fingerprint users from master to target devices"""
    
    def __init__(self):
        self.setup_logging()
        self.master_device = config.devices_master
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
            
    def get_all_users_with_fingerprints(self):
        """Get all users with fingerprints from master device"""
        self.logger.info(f"🔍 Scanning master device for users with fingerprints...")
        self.logger.info(f"Master: {self.master_device['device_id']} ({self.master_device['ip']})")
        
        try:
            # Connect to master
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
                            'user_id': user.user_id,
                            'name': user.name,
                            'privilege': user.privilege,
                            'password': user.password,
                            'group_id': user.group_id,
                            'fingerprints': fingerprints
                        }
                        users_with_fingerprints.append(user_data)
                        
                        # Enhanced logging with finger details
                        finger_details = []
                        for fp in fingerprints:
                            finger_name = local_config.get_finger_name(fp['finger_index'])
                            finger_details.append(f"{fp['finger_index']}:{finger_name}")
                        
                        finger_list = ", ".join(finger_details)
                        self.logger.info(f"  ✅ {user.user_id}: {user.name} ({len(fingerprints)} fingerprints: {finger_list})")
                        
                except Exception as e:
                    # Skip users with errors
                    pass
                    
            conn.enable_device()
            conn.disconnect()
            
            self.logger.info(f"📊 Found {len(users_with_fingerprints)} users with fingerprints")
            return users_with_fingerprints
            
        except Exception as e:
            self.logger.error(f"❌ Error scanning master device: {str(e)}")
            return []
            
    def sync_user_to_device(self, user_data, target_device):
        """Sync single user to single target device"""
        user_id = user_data['user_id']
        device_id = target_device['device_id']
        
        try:
            # Connect to target
            zk = ZK(target_device['ip'], port=4370, timeout=10, force_udp=True, ommit_ping=True)
            conn = zk.connect()
            
            if not conn:
                return {
                    "success": False,
                    "user_id": user_id,
                    "device": device_id,
                    "message": "Failed to connect"
                }
                
            conn.disable_device()
            
            # Delete existing user if exists
            existing_users = conn.get_users()
            user_exists = any(u.user_id == user_id for u in existing_users)
            
            if user_exists:
                conn.delete_user(user_id=user_id)
                time.sleep(0.1)
                
            # Create user
            shortened_name = self.shorten_name(user_data['name'], 24)
            
            if user_data.get('password'):
                conn.set_user(
                    name=shortened_name,
                    privilege=user_data['privilege'],
                    password=user_data['password'],
                    group_id=user_data.get('group_id', ''),
                    user_id=user_id
                )
            else:
                conn.set_user(
                    name=shortened_name,
                    privilege=user_data['privilege'],
                    group_id=user_data.get('group_id', ''),
                    user_id=user_id
                )
                
            # Verify user creation
            users = conn.get_users()
            created_user = next((u for u in users if u.user_id == user_id), None)
            
            if not created_user:
                return {
                    "success": False,
                    "user_id": user_id,
                    "device": device_id,
                    "message": f"Failed to create user {user_id}"
                }
                
            # Prepare fingerprint templates
            decoded_templates = {}
            for fp in user_data['fingerprints']:
                try:
                    finger_index = fp['finger_index']
                    decoded_templates[finger_index] = base64.b64decode(fp['template_data'])
                except Exception:
                    pass
                    
            # Create 10 Finger objects
            templates_to_send = []
            fingerprint_count = 0
            
            for i in range(10):
                if i in decoded_templates:
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
                "user_id": user_id,
                "device": device_id,
                "message": f"Synced {fingerprint_count} fingerprints"
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": user_id,
                "device": device_id,
                "message": f"Error: {str(e)}"
            }
            
    def sync_user_to_all_targets(self, user_data):
        """Sync single user to all target devices using threading"""
        user_id = user_data['user_id']
        
        results = []
        success_count = 0
        
        # Use ThreadPoolExecutor for concurrent sync
        with ThreadPoolExecutor(max_workers=min(len(self.target_devices), 5)) as executor:
            future_to_device = {
                executor.submit(self.sync_user_to_device, user_data, device): device
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
                        "user_id": user_id,
                        "device": device['device_id'],
                        "message": f"Exception: {str(e)}"
                    }
                    results.append(error_result)
                    
        return {
            "user_id": user_id,
            "name": user_data['name'],
            "total_devices": len(self.target_devices),
            "success_count": success_count,
            "results": results
        }
        
    def sync_all_users(self):
        """Main sync function"""
        self.logger.info("🚀 Starting master-to-target fingerprint sync...")
        self.logger.info(f"Master: {self.master_device['device_id']} ({self.master_device['ip']})")
        self.logger.info(f"Targets: {[d['device_id'] for d in self.target_devices]}")
        
        # Get users with fingerprints from master
        users_data = self.get_all_users_with_fingerprints()
        
        if not users_data:
            self.logger.error("❌ No users with fingerprints found on master device")
            return False
            
        # Sync each user to all target devices
        total_users = len(users_data)
        processed_users = 0
        successful_users = 0
        
        self.logger.info(f"📤 Syncing {total_users} users to {len(self.target_devices)} target devices...")
        
        for i, user_data in enumerate(users_data, 1):
            user_id = user_data['user_id']
            user_name = user_data['name']
            
            self.logger.info(f"Progress: {i}/{total_users} - {user_id}: {user_name}")
            
            try:
                result = self.sync_user_to_all_targets(user_data)
                processed_users += 1
                
                if result["success_count"] > 0:
                    successful_users += 1
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
                self.logger.error(f"Error processing user {user_id}: {str(e)}")
                
        # Final summary
        self.logger.info("=" * 60)
        self.logger.info("🎯 SYNC SUMMARY")
        self.logger.info(f"Total users found: {total_users}")
        self.logger.info(f"Users processed: {processed_users}")
        self.logger.info(f"Users successfully synced: {successful_users}")
        self.logger.info(f"Target devices: {len(self.target_devices)}")
        
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
    
    parser = argparse.ArgumentParser(description='Sync all fingerprint users from master to targets')
    parser.add_argument('--limit', type=int, help='Limit number of users to sync (for testing)')
    
    args = parser.parse_args()
    
    sync_manager = MasterToTargetSync()
    
    # Get users first to show count
    users = sync_manager.get_all_users_with_fingerprints()
    
    if not users:
        print("❌ No users with fingerprints found")
        return 1
        
    if args.limit:
        users = users[:args.limit]
        print(f"🔢 Limited to {len(users)} users for testing")
        
    # Temporarily modify the sync manager's data
    original_method = sync_manager.get_all_users_with_fingerprints
    sync_manager.get_all_users_with_fingerprints = lambda: users
    
    success = sync_manager.sync_all_users()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())