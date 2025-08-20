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