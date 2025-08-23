import datetime
# ERPNext related configs

ERPNEXT_VERSION = 15 
# SERVER_NAME = 'erp.tiqn.local' 
# ERPNEXT_API_KEY = '7c5bab33922d7f6'  
# ERPNEXT_API_SECRET = '0ac0d04cbda63b9' 


# Site Sonnt
SERVER_NAME = '10.0.1.21'
ERPNEXT_API_KEY = '7c5bab33922d7f6'
ERPNEXT_API_SECRET = '2d379dbe1ef33ab'

# Site Vinhnt
# SERVER_NAME = 'erp-vinhnt.tiqn.local'
# ERPNEXT_API_KEY = '30a5bc81106bdf9'
# ERPNEXT_API_SECRET = 'c6345b4905ce725' 

ERPNEXT_URL = f'http://{SERVER_NAME}'



# operational configs
PULL_FREQUENCY = 3 # in minutes
LOGS_DIRECTORY = 'logs' # logs of this script is stored in this directory
IMPORT_START_DATE = '20250726' # format: '20190501' , Kỳ lương tháng 8/25

# Biometric device configs (all keys mandatory, except latitude and longitude they are mandatory only if 'Allow Geolocation Tracking' is turned on in Frappe HR)
    #- device_id - must be unique, strictly alphanumerical chars only. no space allowed.
    #- ip - device IP Address
    #- punch_direction - 'IN'/'OUT'/'AUTO'/None
    #- clear_from_device_on_fetch: if set to true then attendance is deleted after fetch is successful.
                                    #(Caution: this feature can lead to data loss if used carelessly.)
    #- latitude - float, latitude of the location of the device
    #- longitude - float, longitude of the location of the device
devices = [
    # {'device_id':'Machine_1','ip':'10.0.1.41', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine_2','ip':'10.0.1.42', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine_3','ip':'10.0.1.43', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine_4','ip':'10.0.1.44', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine_5','ip':'10.0.1.45', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine_6','ip':'10.0.1.46', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # {'device_id':'Machine_7','ip':'10.0.1.47', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    {'device_id':'Machine_8','ip':'10.0.1.48', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    {'device_id':'Machine_10','ip':'10.0.1.50', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000}
]
devices_master =    {'device_id':'Machine_8','ip':'10.0.1.48', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000}

# user_id_inorged - list of user IDs to be ignored / STRING : Tạp vụ
user_id_inorged=['55','58','161','623','916','920','3000','3001','3002','6004','6005']
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

# Bypass việc xóa template của nhân viên đã nghỉ việc
# Chỉ cho phép thực hiện sau 22:00
clear_left_user_template_by_pass_period = [
    # {"start": "00:00", "end": "22:00", "reason": "Working hours - delay template cleanup until after 22:00"}
]

# Feature toggles
ENABLE_SYNC_USER_INFO_FROM_ERPNEXT_TO_DEVICE = False
ENABLE_CLEAR_LEFT_USER_TEMPLATES = False
SYNC_USER_INFO_MODE = 'auto'  # 'full', 'changed', 'auto'
SYNC_CHANGED_HOURS_BACK = 24

def should_bypass_log_sync():
    """Check if should bypass log sync to ERPNext"""
    bypassed, period = is_in_bypass_period(sync_log_by_pass_period)
    return bypassed, period

def should_bypass_user_info_sync():
    """Check if should bypass user info/template sync to device"""  
    bypassed, period = is_in_bypass_period(sync_user_info_by_pass_period)
    return bypassed, period

def should_bypass_clear_left_templates():
    """Check if should bypass clearing left user templates"""
    bypassed, period = is_in_bypass_period(clear_left_user_template_by_pass_period)
    return bypassed, period

def get_bypass_status():
    """Get current bypass status for all operations"""
    log_bypass, log_period = should_bypass_log_sync()
    user_bypass, user_period = should_bypass_user_info_sync()
    clear_bypass, clear_period = should_bypass_clear_left_templates()
    
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
        },
        'clear_left': {
            'bypassed': clear_bypass,
            'period': clear_period,
            'reason': clear_period.get('reason') if clear_period else None
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
    
    # Clear left templates status
    clear_status = "BỎ QUA" if status['clear_left']['bypassed'] else "HOẠT ĐỘNG"
    print(f"  Xóa Template Nhân Viên Nghỉ Việc: {clear_status}")
    if status['clear_left']['bypassed']:
        print(f"    Lý do: {status['clear_left']['reason']}")
        period = status['clear_left']['period']
        print(f"    Thời gian: {period['start']} - {period['end']}")
    
    # Feature toggles
    print(f"\n  Cấu Hình Chức Năng:")
    print(f"    Sync User Info từ ERPNext: {'BẬT' if ENABLE_SYNC_USER_INFO_FROM_ERPNEXT_TO_DEVICE else 'TẮT'}")
    print(f"    Xóa Template Nhân Viên Nghỉ Việc: {'BẬT' if ENABLE_CLEAR_LEFT_USER_TEMPLATES else 'TẮT'}")
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
    all_periods = (sync_log_by_pass_period + 
                  sync_user_info_by_pass_period + 
                  clear_left_user_template_by_pass_period)
    
    for period in all_periods:
        try:
            datetime.datetime.strptime(period["start"], "%H:%M")
            datetime.datetime.strptime(period["end"], "%H:%M")
        except ValueError as e:
            raise ValueError(f"Invalid time format in period {period}: {e}")
    
    return True

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