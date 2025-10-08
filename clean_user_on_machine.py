#!/usr/bin/env python3

import datetime
import logging
import os
import sys
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import socket
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import local_config

# Setup logging
clean_logs_dir = os.path.join(local_config.LOGS_DIRECTORY, 'clean_user_on_machine')
os.makedirs(clean_logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(clean_logs_dir, 'clean_users.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Devices configuration
devices = [
    # {'device_id':'Machine_1','ip':'10.0.1.41', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine_2','ip':'10.0.1.42', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine_3','ip':'10.0.1.43', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine_4','ip':'10.0.1.44', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine_5','ip':'10.0.1.45', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine_6','ip':'10.0.1.46', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine_7','ip':'10.0.1.47', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    {'device_id':'Machine_8','ip':'10.0.1.48', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
]

class UserCleaner:
    def __init__(self, keep_user_id_clean_template=False):
        self.devices = devices
        self.keep_user_id = self.load_keep_user_id()
        self.keep_user_id_clean_template = keep_user_id_clean_template
        self.max_workers = min(len(self.devices), 10)

    def load_keep_user_id(self):
        """Load user IDs to keep from keep_user_id.txt file"""
        keep_user_file = os.path.join(current_dir, 'keep_user_id.txt')
        keep_user_id = []

        try:
            with open(keep_user_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        # Each line contains just the user ID
                        keep_user_id.append(line)

            logger.info(f"Loaded {len(keep_user_id)} user IDs to keep from {keep_user_file}")
            return keep_user_id

        except FileNotFoundError:
            logger.error(f"keep_user_id.txt file not found at {keep_user_file}")
            return []
        except Exception as e:
            logger.error(f"Error reading keep_user_id.txt: {str(e)}")
            return []

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

    def clean_users_on_device(self, device_config):
        """Clean users on a single device, keeping only those in keep_user_id list"""
        device_id = device_config['device_id']
        ip_address = device_config['ip']

        logger.info(f"Starting user cleanup on device {device_id} ({ip_address})")

        try:
            # Check connection
            if not self.check_device_connection(device_config):
                logger.warning(f"✗ Device {device_id} ({ip_address}) is not reachable")
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": False,
                    "deleted_count": 0,
                    "total_users": 0,
                    "message": f"Device {device_id} is not reachable"
                }

            # Connect to device
            from zk import ZK
            zk = ZK(ip_address, port=4370, timeout=10, force_udp=True, ommit_ping=True)
            conn = zk.connect()

            if not conn:
                logger.warning(f"✗ Failed to connect to device {device_id}")
                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": False,
                    "deleted_count": 0,
                    "total_users": 0,
                    "message": f"Failed to connect to device {device_id}"
                }

            try:
                # Disable device
                conn.disable_device()
                logger.info(f"Device {device_id} disabled, checking users...")

                # Get all users from device
                existing_users = conn.get_users()
                total_users = len(existing_users)

                logger.info(f"Found {total_users} users on device {device_id}")

                deleted_count = 0
                deleted_users = []
                kept_users = []

                # Check each user
                for user in existing_users:
                    user_id_str = str(user.user_id)

                    if user_id_str not in self.keep_user_id:
                        # User not in keep list
                        if self.keep_user_id_clean_template:
                            # Backup user info, delete user, recreate without templates
                            try:
                                # Backup user information
                                backup_user_id = user.user_id
                                backup_name = user.name
                                backup_privilege = user.privilege

                                # Delete the existing user completely
                                conn.delete_user(user_id=backup_user_id)
                                time.sleep(0.1)

                                # Recreate user with same ID and name but no templates
                                conn.set_user(
                                    name=backup_name,
                                    privilege=backup_privilege,
                                    user_id=backup_user_id
                                )

                                deleted_count += 1
                                deleted_users.append({
                                    'user_id': backup_user_id,
                                    'name': backup_name,
                                    'uid': user.uid,
                                    'action': 'user_recreated_without_templates'
                                })
                                logger.info(f"  ✓ Recreated user {backup_user_id} ({backup_name}) without templates")
                                time.sleep(0.1)
                            except Exception as e:
                                logger.error(f"  ✗ Failed to recreate user {user.user_id} ({user.name}): {str(e)}")
                        else:
                            # Delete user completely
                            try:
                                conn.delete_user(user_id=user.user_id)
                                deleted_count += 1
                                deleted_users.append({
                                    'user_id': user.user_id,
                                    'name': user.name,
                                    'uid': user.uid,
                                    'action': 'user_deleted'
                                })
                                logger.info(f"  ✓ Deleted user {user.user_id} ({user.name})")
                                time.sleep(0.1)  # Small delay between deletions
                            except Exception as e:
                                logger.error(f"  ✗ Failed to delete user {user.user_id} ({user.name}): {str(e)}")
                    else:
                        # User is in keep list, keep them
                        kept_users.append({
                            'user_id': user.user_id,
                            'name': user.name,
                            'uid': user.uid
                        })
                        logger.info(f"  • Kept user {user.user_id} ({user.name})")

                action_msg = "Deleted" if not self.keep_user_id_clean_template else "Recreated without templates for"
                logger.info(f"✓ Device {device_id}: {action_msg} {deleted_count}/{total_users} users, Kept {len(kept_users)} users")

                return {
                    "device_id": device_id,
                    "ip": ip_address,
                    "success": True,
                    "deleted_count": deleted_count,
                    "total_users": total_users,
                    "kept_count": len(kept_users),
                    "deleted_users": deleted_users,
                    "kept_users": kept_users,
                    "message": f"{action_msg} {deleted_count}/{total_users} users"
                }

            finally:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except:
                    pass

        except Exception as e:
            logger.error(f"✗ Device {device_id} cleanup error: {str(e)}")
            return {
                "device_id": device_id,
                "ip": ip_address,
                "success": False,
                "deleted_count": 0,
                "total_users": 0,
                "message": f"Device cleanup error: {str(e)}"
            }

    def clean_all_devices(self):
        """Clean users on all devices in parallel"""
        start_time = time.time()
        logger.info("=" * 80)
        logger.info("STARTING USER CLEANUP ON ALL DEVICES")
        logger.info(f"Mode: {'Recreate users without templates' if self.keep_user_id_clean_template else 'Full user deletion'}")
        logger.info(f"Users to keep: {len(self.keep_user_id)}")
        logger.info("=" * 80)

        if not self.keep_user_id:
            logger.error("No users to keep found in keep_user_id.txt file")
            return {
                "success": False,
                "message": "No users to keep found in keep_user_id.txt file",
                "total_deleted": 0,
                "successful_devices": 0,
                "execution_time": 0
            }

        # Process all devices in parallel
        device_results = []
        with ThreadPoolExecutor(max_workers=len(self.devices)) as executor:
            future_to_device = {
                executor.submit(self.clean_users_on_device, device): device
                for device in self.devices
            }

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
                        "deleted_count": 0,
                        "total_users": 0,
                        "message": f"Thread execution error: {str(e)}"
                    }
                    device_results.append(error_result)
                    logger.error(f"✗ {device['device_id']}: Thread execution error: {str(e)}")

        # Calculate totals
        total_deleted = sum(r["deleted_count"] for r in device_results)
        successful_devices = sum(1 for r in device_results if r["success"])

        execution_time = time.time() - start_time

        logger.info("\n" + "=" * 80)
        logger.info("USER CLEANUP COMPLETED")
        logger.info(f"Mode: {'Recreate users without templates' if self.keep_user_id_clean_template else 'Full user deletion'}")
        logger.info(f"Successful devices: {successful_devices}/{len(self.devices)}")
        action_word = "users recreated without templates" if self.keep_user_id_clean_template else "users deleted"
        logger.info(f"Total {action_word}: {total_deleted}")
        logger.info(f"Total execution time: {execution_time:.2f} seconds")
        logger.info("=" * 80)

        return {
            "success": successful_devices > 0,
            "message": f"Cleanup completed: {successful_devices}/{len(self.devices)} devices successful, {total_deleted} total deletions",
            "total_deleted": total_deleted,
            "successful_devices": successful_devices,
            "execution_time": execution_time,
            "detailed_results": device_results
        }

def main():
    """Main function for command line usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Clean users from biometric attendance devices, keeping only specified user IDs')
    parser.add_argument('--device', type=str, help='Clean specific device by device_id (optional, cleans all devices if not specified)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--clean-template-only', action='store_true', help='Backup and recreate users without fingerprint templates (keep user_id and name only)')

    args = parser.parse_args()

    try:
        cleaner = UserCleaner(keep_user_id_clean_template=args.clean_template_only)

        if args.device:
            # Clean specific device
            device_config = next((d for d in devices if d['device_id'] == args.device), None)
            if not device_config:
                logger.error(f"Device {args.device} not found in configuration")
                exit(1)

            if args.dry_run:
                logger.info("DRY RUN MODE - No actual deletions will be performed")
                # For dry run, we would need to implement a separate method
                logger.warning("Dry run mode not implemented yet")
                exit(1)

            result = cleaner.clean_users_on_device(device_config)
            if result["success"]:
                logger.info(f"Device cleanup completed: {result['message']}")
                exit(0)
            else:
                logger.error(f"Device cleanup failed: {result['message']}")
                exit(1)
        else:
            # Clean all devices
            if args.dry_run:
                logger.info("DRY RUN MODE - No actual deletions will be performed")
                logger.warning("Dry run mode not implemented yet")
                exit(1)

            result = cleaner.clean_all_devices()
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