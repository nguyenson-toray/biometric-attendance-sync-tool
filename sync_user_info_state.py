#!/usr/bin/env python3

import os
import json
import datetime
from pathlib import Path

class SyncState:
    """Manage sync state and last_sync timestamp - supports device-specific tracking"""
    
    def __init__(self, state_dir=None):
        if state_dir is None:
            state_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'sync_from_erpnext_to_device')
        
        self.state_dir = state_dir
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Global state file for overall sync
        self.global_state_file = os.path.join(self.state_dir, 'last_sync_global.json')
        
    def get_device_state_file(self, device_id):
        """Get device-specific state file path"""
        filename = f"last_sync_{device_id.lower()}.json"
        return os.path.join(self.state_dir, filename)
        
    def get_last_sync(self):
        """Get global last sync timestamp"""
        try:
            if os.path.exists(self.global_state_file):
                with open(self.global_state_file, 'r') as f:
                    data = json.load(f)
                    last_sync_str = data.get('last_sync')
                    if last_sync_str:
                        return datetime.datetime.strptime(last_sync_str, '%Y-%m-%d %H:%M:%S')
            return None
        except Exception:
            return None
    
    def set_last_sync(self, timestamp=None):
        """Set global last sync timestamp"""
        try:
            if timestamp is None:
                timestamp = datetime.datetime.now()
            
            data = {
                'last_sync': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.global_state_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            return True
        except Exception:
            return False
    
    def get_device_last_sync(self, device_id):
        """Get last sync timestamp for specific device"""
        try:
            device_file = self.get_device_state_file(device_id)
            if os.path.exists(device_file):
                with open(device_file, 'r') as f:
                    data = json.load(f)
                    last_sync_str = data.get('last_sync')
                    if last_sync_str:
                        return datetime.datetime.strptime(last_sync_str, '%Y-%m-%d %H:%M:%S')
            return None
        except Exception:
            return None
    
    def save_device_sync_result(self, device_id, synced_users, timestamp=None):
        """Save device-specific sync result with user details"""
        try:
            if timestamp is None:
                timestamp = datetime.datetime.now()
            
            device_file = self.get_device_state_file(device_id)
            
            # Load existing data if any
            existing_data = {}
            if os.path.exists(device_file):
                try:
                    with open(device_file, 'r') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = {}
            
            # Prepare synced users data
            users_data = []
            for user_data in synced_users:
                user_info = {
                    'user_id': user_data.get('attendance_device_id'),
                    'employee': user_data.get('employee'),
                    'employee_name': user_data.get('employee_name'),
                    'fingerprint_count': len([fp for fp in user_data.get('fingerprints', []) if fp.get('template_data')]),
                    'synced_at': timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                users_data.append(user_info)
            
            # Update device sync data
            data = {
                'device_id': device_id,
                'last_sync': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_users_synced': len(users_data),
                'users': users_data,
                'sync_history': existing_data.get('sync_history', [])
            }
            
            # Add to history (keep last 10 syncs)
            data['sync_history'].append({
                'sync_time': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'users_count': len(users_data),
                'success': True
            })
            data['sync_history'] = data['sync_history'][-10:]  # Keep only last 10
            
            with open(device_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception as e:
            print(f"Error saving device sync result for {device_id}: {str(e)}")
            return False
    
    def get_device_sync_info(self, device_id):
        """Get detailed sync info for specific device"""
        try:
            device_file = self.get_device_state_file(device_id)
            if os.path.exists(device_file):
                with open(device_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception:
            return None
    
    def is_first_run(self):
        """Check if this is the first run (no last_sync exists)"""
        return self.get_last_sync() is None
    
    def get_sync_mode(self):
        """Determine sync mode based on last_sync existence"""
        if self.is_first_run():
            return 'full'
        else:
            return 'changed'
    
    def list_device_states(self):
        """List all device state files and their info"""
        device_states = []
        try:
            for filename in os.listdir(self.state_dir):
                if filename.startswith('last_sync_') and filename.endswith('.json') and filename != 'last_sync_global.json':
                    device_id = filename.replace('last_sync_', '').replace('.json', '')
                    device_info = self.get_device_sync_info(device_id)
                    if device_info:
                        device_states.append(device_info)
        except Exception:
            pass
        return device_states
    
    def save_device_clear_result(self, device_id, cleared_users, timestamp=None):
        """Save device-specific clear result for Left employees"""
        try:
            if timestamp is None:
                timestamp = datetime.datetime.now()
            
            device_file = self.get_device_state_file(device_id)
            
            # Load existing data if any
            existing_data = {}
            if os.path.exists(device_file):
                try:
                    with open(device_file, 'r') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = {}
            
            # Prepare cleared users data
            cleared_data = []
            for user_data in cleared_users:
                clear_info = {
                    'user_id': user_data.get('attendance_device_id'),
                    'employee': user_data.get('employee'),
                    'employee_name': user_data.get('employee_name'),
                    'status': 'Left',
                    'relieving_date': user_data.get('relieving_date'),
                    'templates_cleared': True,
                    'cleared_at': timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                cleared_data.append(clear_info)
            
            # Add clear history to existing data
            if 'clear_history' not in existing_data:
                existing_data['clear_history'] = []
            
            existing_data['clear_history'].append({
                'clear_time': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'cleared_users_count': len(cleared_data),
                'cleared_users': cleared_data
            })
            
            # Keep only last 10 clear operations
            existing_data['clear_history'] = existing_data['clear_history'][-10:]
            
            # Update last_cleared timestamp
            existing_data['last_cleared'] = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            existing_data['updated_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(device_file, 'w') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception as e:
            print(f"Error saving device clear result for {device_id}: {str(e)}")
            return False