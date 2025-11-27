import datetime
# ERPNext related configs

ERPNEXT_VERSION = 15 
SERVER_NAME = '10.0.1.20' 
ERPNEXT_API_KEY = '7c5bab33922d7f6'  
ERPNEXT_API_SECRET = '5df993705d12dd4' 


# Site Sonnt
# SERVER_NAME = '10.0.1.21'
# ERPNEXT_API_KEY = '7c5bab33922d7f6'
# ERPNEXT_API_SECRET = 'c6f0ce7b745637a'

# Site Vinhnt
# SERVER_NAME = 'erp-vinhnt.tiqn.local'
# ERPNEXT_API_KEY = '30a5bc81106bdf9'
# ERPNEXT_API_SECRET = 'c6345b4905ce725' 

ERPNEXT_URL = f'http://{SERVER_NAME}'



# operational configs
PULL_FREQUENCY = 3 # in minutes
LOGS_DIRECTORY = 'logs' # logs of this script is stored in this directory
# Note: IMPORT_START_DATE removed - defaults to today in AUTO mode, prompted in MANUAL mode  

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
devices_master = {'device_id':'Machine_1','ip':'10.0.1.41', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000}
sync_from_master_device_to_erpnext_filters_id = []  # [] = sync all user IDs from master device
user_id_inorged = ['55','58','161','623','916','920','3000','3001','3002','6004','6005','6006','6007','6008']  # Tạp vụ IDs to ignore
# Feature toggles
ENABLE_SYNC_USER_INFO_FROM_ERPNEXT_TO_DEVICE = False

ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES = False  # Clear fingerprint templates from devices (once per day)
CLEAR_LEFT_USER_TEMPLATES_ON_DATE_OF_MONTH = [10] # Days of month to run clearing (e.g., [10,25] = run on 10th and 25th of each month; [] = every day)
CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = 50  # Wait N days after relieving_date before clearing templates (0 = disabled, no template clearing)
ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_ERPNEXT = False  # Delete fingerprint records from ERPNext database (keep False)
ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = 90  # Permanently delete user from devices after N days since relieving_date (0 = disabled, checked FIRST before clear templates)
CLEAR_LEFT_USER_TEMPLATES_LOG_FILE = 'logs/clear_left_templates.log'  # Dedicated log file
PROCESSED_LEFT_EMPLOYEES_FILE = 'logs/clean_data_employee_left/processed_left_employees.json'  # Tracking file for processed employees (skip on subsequent runs)

# Log cleanup configuration
CLEAN_OLD_LOGS_DAYS = 3  # Clean logs older than N days (0 = disabled)

# Log rotation configuration
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB per log file
LOG_BACKUP_COUNT = 5  # Keep only 5 backup files (reduced from 50 to save disk space)
                      # Total per log type: (5+1) files × 10MB = 60MB max

SYNC_USER_INFO_MODE = 'auto'  # 'full', 'changed', 'auto'
SYNC_CHANGED_HOURS_BACK = 24

# MongoDB sync feature toggle
ENABLE_SYNC_LOG_FROM_MONGODB_TO_ERPNEXT = True
sync_only_machines_0 = True  # If True, only sync from devices 0 ( add machineNo: 0 to MongoDB query filter)
# Note: sync_log_from_mongodb_to_erpnext_date_range removed - defaults to last 7 days in AUTO mode, prompted in MANUAL mode

# MongoDB OT sync configuration
ENABLE_SYNC_OT_FROM_MONGODB_TO_ERPNEXT = True
# Note: SYNC_OT_FROM_MONGODB_TO_ERPNEXT_START_DATE removed - defaults to today in AUTO mode, prompted in MANUAL mode
# =============================================================================
# MONGODB CONNECTION SETTINGS (Shared for both attendance log & OT sync)
# =============================================================================
MONGODB_HOST = "10.0.1.4"
MONGODB_PORT = 27017
MONGODB_DATABASE = "tiqn"
MONGODB_USER = "DB\\administrator"  # Optional - comment out if no auth
MONGODB_PASS = "itT0ray$"  # Optional - comment out if no auth
MONGODB_URI = f'mongodb://{MONGODB_HOST}:{MONGODB_PORT}/'  # Auto-generated from host:port

# MongoDB collection names
MONGODB_ATTLOG_COLLECTION = "AttLog"  # Attendance log collection
MONGODB_OT_COLLECTION = "OtRegister"  # Overtime registration collection



# NOTE: MANUAL MODE ONLY configs (ENABLE_RESYNC_ON_DAY, ENABLE_TIME_SYNC_AND_RESTART, etc.)
# have been moved to erpnext_re_sync_all.py
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
print(f'- User IDs (Finger ID) to be ignored: {user_id_inorged}')
print('------------------------------------------------------------------')

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


# Ignore exceptions: 1=Employee not found, 2=Employee inactive, 3=Duplicate checkin
allowed_exceptions = [1,2,3]

# =============================================================================
# DYNAMIC TIME-BASED BYPASS CONFIGURATIONS
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

# Bypass periods for sync operations (during rush hours)
sync_log_by_pass_period = []  # Format: [{"start": "07:30", "end": "07:55", "reason": "Morning rush"}]
sync_user_info_by_pass_period = []  # Format: [{"start": "17:00", "end": "17:30", "reason": "Evening rush"}]



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
    """Check if should run clear left templates (once per day on specific dates)

    Conditions:
    1. ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES must be True
    2. Not run today yet (last_run_date < today)
    3. Today's day-of-month must be in CLEAR_LEFT_USER_TEMPLATES_ON_DATE_OF_MONTH
       - If list is empty [] → run every day
       - If list has values [10,25] → only run on 10th and 25th of month
    """
    if not ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES:
        return False

    last_run_date = get_last_clear_left_templates_date()
    today = datetime.date.today()

    # Check if already run today
    if last_run_date is not None and last_run_date >= today:
        return False

    # Check date-of-month restriction
    # If empty list [] → run every day
    if not CLEAR_LEFT_USER_TEMPLATES_ON_DATE_OF_MONTH:
        return True

    # If has values → only run on specified days
    current_day = today.day
    return current_day in CLEAR_LEFT_USER_TEMPLATES_ON_DATE_OF_MONTH

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