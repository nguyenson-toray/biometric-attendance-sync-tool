import datetime
# ERPNext related configs

ERPNEXT_VERSION = 15 
SERVER_NAME = '10.0.1.20' 
ERPNEXT_API_KEY = '7c5bab33922d7f6'  
ERPNEXT_API_SECRET = '5df993705d12dd4' 


# Site Sonnt
# SERVER_NAME = '10.0.1.21'
# ERPNEXT_API_KEY = '7c5bab33922d7f6'
# ERPNEXT_API_SECRET = '2d379dbe1ef33ab'

# Site Vinhnt
# SERVER_NAME = 'erp-vinhnt.tiqn.local'
# ERPNEXT_API_KEY = '30a5bc81106bdf9'
# ERPNEXT_API_SECRET = 'c6345b4905ce725' 

ERPNEXT_URL = f'http://{SERVER_NAME}'



# operational configs
PULL_FREQUENCY = 3 # in minutes
LOGS_DIRECTORY = 'logs' # logs of this script is stored in this directory
IMPORT_START_DATE = '20251009' # format: '20190501'  

# Biometric device configs (all keys mandatory, except latitude and longitude they are mandatory only if 'Allow Geolocation Tracking' is turned on in Frappe HR)
    #- device_id - must be unique, strictly alphanumerical chars only. no space allowed.
    #- ip - device IP Address
    #- punch_direction - 'IN'/'OUT'/'AUTO'/None
    #- clear_from_device_on_fetch: if set to true then attendance is deleted after fetch is successful.
                                    #(Caution: this feature can lead to data loss if used carelessly.)
    #- latitude - float, latitude of the location of the device
    #- longitude - float, longitude of the location of the device
devices = [
    {'device_id':'Machine 1','ip':'10.0.1.41', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    {'device_id':'Machine 2','ip':'10.0.1.42', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    {'device_id':'Machine 3','ip':'10.0.1.43', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    {'device_id':'Machine 4','ip':'10.0.1.44', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    {'device_id':'Machine 5','ip':'10.0.1.45', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    {'device_id':'Machine 6','ip':'10.0.1.46', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    {'device_id':'Machine 7','ip':'10.0.1.47', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine 8','ip':'10.0.1.48', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine 10','ip':'10.0.1.50', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000}
]
devices_master =    {'device_id':'Machine_1','ip':'10.0.1.41', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000}
sync_from_master_device_to_erpnext_filters_id=[]
# sync_from_master_device_to_erpnext_filters_id=['1735','1736','1737','1738','1739']
# sync_from_master_device_to_erpnext_filters_id=[] : sync all user IDs from master device to ERPNext
# user_id_inorged - list of user IDs to be ignored / STRING : Tạp vụ
user_id_inorged=['55','58','161','623','916','920','3000','3001','3002','6004','6005','6006','6007','6008']
re_sync_data_date_range = [] #=['from date','to date'] ['20250915','20250917'] ,  'YYYYMMDD'  or [] for no filter
# Add 'Employee Checkin'  between this date range on ERPNEXT, no error for dupplicate
#  set to [] to disable this feature after use
# Feature toggles
ENABLE_SYNC_USER_INFO_FROM_ERPNEXT_TO_DEVICE = False

ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES = True  # Clear fingerprint templates from devices (once per day)
CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = 30  # Wait N days after relieving_date before clearing templates (0 = disabled, no template clearing)
ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_ERPNEXT = False  # Delete fingerprint records from ERPNext database (keep False)
ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = 60  # Permanently delete user from devices after N days since relieving_date (0 = disabled, checked FIRST before clear templates)
CLEAR_LEFT_USER_TEMPLATES_LOG_FILE = 'logs/clear_left_templates.log'  # Dedicated log file
PROCESSED_LEFT_EMPLOYEES_FILE = 'logs/clean_data_employee_left/processed_left_employees.json'  # Tracking file for processed employees (skip on subsequent runs)

# Log cleanup configuration
CLEAN_OLD_LOGS_DAYS = 7  # Clean logs older than N days (0 = disabled)

SYNC_USER_INFO_MODE = 'auto'  # 'full', 'changed', 'auto'
SYNC_CHANGED_HOURS_BACK = 24

# MongoDB sync feature toggle
ENABLE_SYNC_LOG_FROM_MONGODB_TO_ERPNEXT = True
sync_only_machines_0 = True  # If True, only sync from devices 0 ( add machineNo: 0 to MongoDB query filter)
sync_log_from_mongodb_to_erpnext_date_range = []  # Format: ['YYYYMMDD', 'YYYYMMDD'] or [] for current+previous date

# End-of-day re-sync configuration
ENABLE_RESYNC_ON_DAY = True
TIME_RESYNC_ON_DAY = ["08:10:00","22:30:00"]  # các mốc thời điểm re-sync, bỏ qua sync nếu rỗng []
RESYNC_WINDOW_MINUTES_ON_DAY = 6  # ±3 phút từ thời điểm mục tiêu
END_OF_DAY_RESYNC_LOG_FILE = 'logs/logs_resync.log'  # Dedicated log file for re-sync operations

# Time synchronization configuration
ENABLE_TIME_SYNC = True  # Enable time sync to devices,  # Only run on Sunday if enabled
TIME_SYNC_AND_RESTART_AT_NIGHT = True  # Sync time and restart device during night process
TIME_SYNC_MAX_DIFF_SECONDS = 3  # Only sync if time difference > 60 seconds
TIME_SYNC_TIMEOUT_SECONDS = 3  # Connection timeout for time sync
TIME_SYNC_LOG_FILE = 'logs/time_sync.log'  # Dedicated log file for time sync operations
# FingerID	Code	Name
# 55	NK-01	NK-01-HT Hien
# 58	NK-02	NK-02-NT Thao
# 161	NK-03	NK-03-TTM Hoa
# 623	NK-04	NK-04-NTN Thu
# 916	NK-05	NK-05-NTT Vy
# 920	NK-06	NK-06-NT Luon
# 3000	NK-07	NK-07-TTM Hoa
# 3001	NK-08	NK-08-TT Can
# 3002	NK-09	NK-09-DT Yen
# 6004	NK-10	NK-10-NT Can
# 6005	NK-11	NK-11-DT Loan

print(f'\n------------------ START AT {datetime.datetime.now()} ------------------')
print(f'- ERPNext URL: {ERPNEXT_URL}')
print(f'- ERPNext API Key: {ERPNEXT_API_KEY}')
print(f'- ERPNext API Secret: {ERPNEXT_API_SECRET}')
print(f'- Devices: {devices}')
print(f'- Pull frequency: {PULL_FREQUENCY} minutes')
print(f'- Logs directory: {LOGS_DIRECTORY}')
print(f'- Import start date: {IMPORT_START_DATE}')
print(f'- User IDs (Finger ID) to be ignored: {user_id_inorged}')
# Dynamic bypass periods are defined below after validation
print('------------------------------------------------------------------')
# Configs updating sync timestamp in the Shift Type DocType 
# please, read this thread to know why this is necessary https://discuss.erpnext.com/t/v-12-hr-auto-attendance-purpose-of-last-sync-of-checkin-in-shift-type/52997

# shift_type_device_mapping = [
#     {
#         'shift_type_name': ['Day'], 
#         'related_device_id': [
#             'machine_1',
#             'machine_2', 
#             'machine_3',
#             'machine_4',
#             'machine_5',
#             'machine_6',
#             'machine_7'
#         ]
#     },
# ]


# Ignore following exceptions thrown by ERPNext and continue importing punch logs.
# Note: All other exceptions will halt the punch log import to erpnext.
#       1. No Employee found for the given employee User ID in the Biometric device.
#       2. Employee is inactive for the given employee User ID in the Biometric device.
#       3. Duplicate Employee Checkin found. (This exception can happen if you have cleared the logs/status.json of this script)
# Use the corresponding number to ignore the above exceptions. (Default: Ignores all the listed exceptions)
allowed_exceptions = [1,2,3]

# =============================================================================
# DYNAMIC TIME-BASED BYPASS CONFIGURATIONS
# Loaded every PULL_FREQUENCY cycle to support runtime configuration changes
# =============================================================================

def get_current_time():
    """Get current time in HH:MM format"""
    return datetime.datetime.now().strftime("%H:%M")

def get_current_datetime():
    """Get current datetime"""
    return datetime.datetime.now()

def is_in_bypass_period(bypass_periods):
    """Check if current time is in any bypass period"""
    current_time = get_current_time()
    current_dt = datetime.datetime.strptime(current_time, "%H:%M").time()
    
    for period in bypass_periods:
        start_time = datetime.datetime.strptime(period["start"], "%H:%M").time()
        end_time = datetime.datetime.strptime(period["end"], "%H:%M").time()
        
        if start_time <= end_time:  # Same day
            if start_time <= current_dt <= end_time:
                return True, period
        else:  # Cross midnight
            if current_dt >= start_time or current_dt <= end_time:
                return True, period
    
    return False, None

# Bypass việc kết nối máy chấm công để sync log đến ERPNext
# Thời gian bận rộn: giờ vào ca sáng và chiều
sync_log_by_pass_period = [
    # {"start": "07:30", "end": "07:55", "reason": "Morning rush - employees clocking in"},
    # {"start": "17:00", "end": "17:30", "reason": "Evening rush - employees clocking out"}
]

# Bypass việc kết nối máy chấm công để sync user info, template từ ERPNext đến máy chấm công
# Thời gian bận rộn: giờ vào ca sáng và chiều
sync_user_info_by_pass_period = [
    # {"start": "07:30", "end": "07:55", "reason": "Morning rush - avoid device conflicts"},
    # {"start": "17:00", "end": "17:30", "reason": "Evening rush - avoid device conflicts"}
]



def should_bypass_log_sync():
    """Check if should bypass log sync to ERPNext"""
    bypassed, period = is_in_bypass_period(sync_log_by_pass_period)
    return bypassed, period

def should_bypass_user_info_sync():
    """Check if should bypass user info/template sync to device"""
    bypassed, period = is_in_bypass_period(sync_user_info_by_pass_period)
    return bypassed, period

def get_bypass_status():
    """Get current bypass status for all operations"""
    log_bypass, log_period = should_bypass_log_sync()
    user_bypass, user_period = should_bypass_user_info_sync()

    return {
        'log_sync': {
            'bypassed': log_bypass,
            'period': log_period,
            'reason': log_period.get('reason') if log_period else None
        },
        'user_sync': {
            'bypassed': user_bypass,
            'period': user_period,
            'reason': user_period.get('reason') if user_period else None
        }
    }

def log_bypass_status():
    """Log current bypass status"""
    current_time = get_current_time()
    status = get_bypass_status()
    
    print(f"\n[{current_time}] Cấu Hình Động:")
    print("=" * 60)
    
    # Log sync status
    log_status = "BỎ QUA" if status['log_sync']['bypassed'] else "HOẠT ĐỘNG"
    print(f"  Sync Log từ Device đến ERPNext: {log_status}")
    if status['log_sync']['bypassed']:
        print(f"    Lý do: {status['log_sync']['reason']}")
        period = status['log_sync']['period']
        print(f"    Thời gian: {period['start']} - {period['end']}")
    
    # User sync status
    user_status = "BỎ QUA" if status['user_sync']['bypassed'] else "HOẠT ĐỘNG"
    print(f"  Sync User/Template từ ERPNext đến Device: {user_status}")
    if status['user_sync']['bypassed']:
        print(f"    Lý do: {status['user_sync']['reason']}")
        period = status['user_sync']['period']
        print(f"    Thời gian: {period['start']} - {period['end']}")

    # Feature toggles
    print(f"\n  Cấu Hình Chức Năng:")
    print(f"    Sync User Info từ ERPNext: {'BẬT' if ENABLE_SYNC_USER_INFO_FROM_ERPNEXT_TO_DEVICE else 'TẮT'}")
    print(f"    Xóa Template NV Nghỉ Việc (Devices): {'BẬT' if ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES else 'TẮT'}")
    print(f"    Xóa Template NV Nghỉ Việc (ERPNext): {'BẬT' if ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_ERPNEXT else 'TẮT'}")
    print(f"    Chế độ Sync: {SYNC_USER_INFO_MODE}")
    
    print("=" * 60)

def log_operation_decision(operation, will_execute, reason=""):
    """Log decision for each operation"""
    status = "THỰC HIỆN" if will_execute else "BỎ QUA"
    timestamp = get_current_time()
    print(f"[{timestamp}] {operation}: {status}")
    if reason:
        print(f"    Lý do: {reason}")

def should_run_end_of_day_resync():
    """Check if should run re-sync based on configured time points"""
    if not ENABLE_RESYNC_ON_DAY or not TIME_RESYNC_ON_DAY:
        return False

    current_time = datetime.datetime.now()
    current_time_str = current_time.strftime("%H:%M:%S")
    window_minutes = RESYNC_WINDOW_MINUTES_ON_DAY // 2  # ±5 minutes

    # Check each configured time point
    for target_time_str in TIME_RESYNC_ON_DAY:
        try:
            # Parse target time
            target_hour, target_minute, target_second = map(int, target_time_str.split(':'))

            # Create target time for today
            target_time = current_time.replace(
                hour=target_hour,
                minute=target_minute,
                second=target_second,
                microsecond=0
            )

            # Calculate time difference in minutes
            time_diff_minutes = abs((current_time - target_time).total_seconds()) / 60

            # Check if we're within the window
            if time_diff_minutes <= window_minutes:
                return True
        except ValueError:
            print(f"Warning: Invalid time format in TIME_RESYNC_ON_DAY: {target_time_str}")
            continue

    return False

def get_end_of_day_resync_date_range():
    """Get date range for end-of-day re-sync (today only)"""
    today = datetime.datetime.now().strftime('%Y%m%d')
    return [today, today]

def setup_resync_logger():
    """Setup dedicated logger for end-of-day re-sync operations"""
    import logging
    import os
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create dedicated logger for re-sync
    logger = logging.getLogger('resync_logger')
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicate logging
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create file handler for re-sync logs
    file_handler = logging.FileHandler(END_OF_DAY_RESYNC_LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    # Prevent propagation to root logger to avoid duplicate entries
    logger.propagate = False
    
    return logger

def log_resync_operation(message, level='INFO'):
    """Log re-sync operation to dedicated log file"""
    try:
        logger = setup_resync_logger()
        if level.upper() == 'ERROR':
            logger.error(message)
        elif level.upper() == 'WARNING':
            logger.warning(message)
        else:
            logger.info(message)
    except Exception as e:
        print(f"Failed to log re-sync operation: {e}")

def should_skip_duplicate_log(message):
    """Check if this is a duplicate error that should be skipped in re-sync logs"""
    skip_patterns = [
        'Re-sync mode: Skipping duplicate',
        'Duplicate Employee Checkin found',
        'already exists for employee',
        'DuplicateEntryError'
    ]
    
    for pattern in skip_patterns:
        if pattern.lower() in message.lower():
            return True
    return False

def validate_time_periods():
    """Validate that time periods are properly formatted"""
    all_periods = (sync_log_by_pass_period + sync_user_info_by_pass_period)

    for period in all_periods:
        try:
            datetime.datetime.strptime(period["start"], "%H:%M")
            datetime.datetime.strptime(period["end"], "%H:%M")
        except ValueError as e:
            raise ValueError(f"Invalid time format in period {period}: {e}")

    return True

def get_last_clear_left_templates_date():
    """Get the last date when clear left templates was executed"""
    import os

    marker_file = os.path.join(LOGS_DIRECTORY, 'clean_data_employee_left', '.last_clear_left_templates')
    if os.path.exists(marker_file):
        try:
            with open(marker_file, 'r') as f:
                date_str = f.read().strip()
                return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return None
    return None

def set_last_clear_left_templates_date(date=None):
    """Set the last date when clear left templates was executed"""
    import os

    if date is None:
        date = datetime.date.today()

    marker_file = os.path.join(LOGS_DIRECTORY, 'clean_data_employee_left', '.last_clear_left_templates')
    marker_dir = os.path.dirname(marker_file)
    os.makedirs(marker_dir, exist_ok=True)

    with open(marker_file, 'w') as f:
        f.write(date.strftime('%Y-%m-%d'))

def should_run_clear_left_templates():
    """Check if should run clear left templates (once per day)"""
    if not ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES:
        return False

    last_run_date = get_last_clear_left_templates_date()
    today = datetime.date.today()

    # Run if never run before or last run was on a different day
    return last_run_date is None or last_run_date < today

# Validate configuration on import
validate_time_periods()

# =============================================================================
# FINGER MAPPING UTILITIES
# =============================================================================
# Standardized finger mapping functions for consistent finger index/name conversion
# across all biometric sync operations

def get_finger_name(finger_index):
    """Get standardized finger name from index
    
    Args:
        finger_index (int): Finger index from biometric device (0-9)
        
    Returns:
        str: Standardized finger name
    """
    finger_names = {
        0: "Left Little",
        1: "Left Ring",
        2: "Left Middle", 
        3: "Left Index",
        4: "Left Thumb", 
        5: "Right Thumb",
        6: "Right Index",
        7: "Right Middle",
        8: "Right Ring",
        9: "Right Little"
    }
    return finger_names.get(finger_index, f"Finger {finger_index}")

def get_finger_index(finger_name):
    """Get finger index from standardized name
    
    Args:
        finger_name (str): Standardized finger name
        
    Returns:
        int: Finger index for biometric device (-1 if not found)
    """
    finger_map = {
        'Left Little': 0,
        'Left Ring': 1,
        'Left Middle': 2,
        'Left Index': 3,
        'Left Thumb': 4,  
        'Right Thumb': 5,
        'Right Index': 6,
        'Right Middle': 7,
        'Right Ring': 8,
        'Right Little': 9
    }
    return finger_map.get(finger_name, -1)

def get_all_finger_mappings():
    """Get complete finger index to name mapping
    
    Returns:
        dict: Complete mapping of finger indices to names
    """
    return {
        0: "Left Little",
        1: "Left Ring",
        2: "Left Middle", 
        3: "Left Index",
        4: "Left Thumb", 
        5: "Right Thumb",
        6: "Right Index",
        7: "Right Middle",
        8: "Right Ring",
        9: "Right Little"
    }

def validate_finger_index(finger_index):
    """Validate if finger index is within valid range
    
    Args:
        finger_index (int): Finger index to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    return isinstance(finger_index, int) and 0 <= finger_index <= 9

def validate_finger_name(finger_name):
    """Validate if finger name is a recognized standard name

    Args:
        finger_name (str): Finger name to validate

    Returns:
        bool: True if valid, False otherwise
    """
    valid_names = {
        'Left Little', 'Left Ring', 'Left Middle', 'Left Index', 'Left Thumb',
        'Right Thumb', 'Right Index', 'Right Middle', 'Right Ring', 'Right Little'
    }
    return finger_name in valid_names

def log_time_sync_operation(message, level="INFO"):
    """Log time sync operations to dedicated log file

    Args:
        message (str): Log message
        level (str): Log level (INFO, WARNING, ERROR)
    """
    import os

    # Ensure logs directory exists
    log_dir = os.path.dirname(TIME_SYNC_LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}\n"

    try:
        with open(TIME_SYNC_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write time sync log: {e}")

def should_run_time_sync():
    """Check if time sync should run based on night schedule

    Returns:
        bool: True if time sync should run now
    """
    if not ENABLE_TIME_SYNC or not TIME_SYNC_AND_RESTART_AT_NIGHT or datetime.date.today().weekday() <= 5:
        # Only run on Sunday if enabled
        return False

    # Use same logic as re-sync on day
    return should_run_end_of_day_resync()

def sync_time_to_devices(devices_list=None, force=False):
    """Synchronize time from server to biometric devices

    Args:
        devices_list (list): List of devices to sync time to. If None, uses all devices.
        force (bool): Force sync even if time difference is small

    Returns:
        dict: Summary of sync results
    """
    from zk import ZK
    import datetime

    if not ENABLE_TIME_SYNC and not force:
        log_time_sync_operation("Time sync disabled in configuration", "INFO")
        return {"success": False, "message": "Time sync disabled"}

    if devices_list is None:
        devices_list = devices

    server_time = datetime.datetime.now()
    results = {
        "total_devices": len(devices_list),
        "success_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "details": []
    }

    log_time_sync_operation(f"Starting time sync to {len(devices_list)} devices")
    log_time_sync_operation(f"Server time: {server_time}")

    for device in devices_list:
        device_id = device['device_id']
        device_ip = device['ip']
        device_result = {
            "device_id": device_id,
            "device_ip": device_ip,
            "success": False,
            "message": "",
            "time_diff_seconds": None,
            "old_time": None,
            "new_time": None
        }

        try:
            log_time_sync_operation(f"Connecting to device {device_id} ({device_ip})")

            # Connect to device
            zk = ZK(device_ip, port=4370, timeout=TIME_SYNC_TIMEOUT_SECONDS, force_udp=True)
            conn = zk.connect()

            if not conn:
                device_result["message"] = "Failed to connect to device"
                results["failed_count"] += 1
                log_time_sync_operation(f"Failed to connect to {device_id}", "ERROR")
                results["details"].append(device_result)
                continue

            # Get current device time
            device_time = conn.get_time()
            device_result["old_time"] = device_time

            # Calculate time difference
            time_diff = abs((server_time - device_time).total_seconds())
            device_result["time_diff_seconds"] = time_diff

            log_time_sync_operation(f"Device {device_id} time: {device_time}, difference: {time_diff:.1f}s")

            # Check if sync is needed
            if not force and time_diff < TIME_SYNC_MAX_DIFF_SECONDS:
                device_result["message"] = f"Time difference ({time_diff:.1f}s) within tolerance"
                device_result["success"] = True
                results["skipped_count"] += 1
                log_time_sync_operation(f"Skipping {device_id} - time difference within tolerance")

                # Disconnect before continuing to next device
                try:
                    conn.disconnect()
                except Exception as disc_error:
                    log_time_sync_operation(f"Warning: Failed to disconnect from {device_id}: {disc_error}", "WARNING")
            else:
                # Sync time to device
                conn.set_time(server_time)
                device_result["new_time"] = server_time
                device_result["success"] = True
                device_result["message"] = f"Time synced successfully (diff: {time_diff:.1f}s)"
                results["success_count"] += 1
                log_time_sync_operation(f"Time synced to {device_id} successfully")

                # Disconnect BEFORE restart (device will be disconnected after restart anyway)
                try:
                    conn.disconnect()
                    log_time_sync_operation(f"Disconnected from {device_id} before restart")
                except Exception as disc_error:
                    log_time_sync_operation(f"Warning: Failed to disconnect from {device_id}: {disc_error}", "WARNING")

                # Restart device after time sync and disconnect
                try:
                    # Reconnect briefly to send restart command
                    conn = zk.connect()
                    if conn:
                        conn.restart()
                        log_time_sync_operation(f"Device {device_id} restart command sent successfully")
                        device_result["message"] += " and device restarted"
                        # No need to disconnect again as device will restart
                    else:
                        log_time_sync_operation(f"Warning: Could not reconnect to restart {device_id}", "WARNING")
                        device_result["message"] += " (restart failed - reconnection failed)"
                except Exception as restart_error:
                    log_time_sync_operation(f"Warning: Failed to restart device {device_id}: {restart_error}", "WARNING")
                    device_result["message"] += " (restart failed)"

        except Exception as e:
            device_result["message"] = f"Error: {str(e)}"
            results["failed_count"] += 1
            log_time_sync_operation(f"Error syncing time to {device_id}: {e}", "ERROR")

        results["details"].append(device_result)

    # Log summary
    log_time_sync_operation(f"Time sync completed - Success: {results['success_count']}, Failed: {results['failed_count']}, Skipped: {results['skipped_count']}")

    return results