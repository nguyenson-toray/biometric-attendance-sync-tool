# Hệ Thống Đồng Bộ Chấm Công ERPNext

Hệ thống đồng bộ tự động giữa máy chấm công sinh trắc học và ERPNext.

## Cấu Trúc Dự Án

```
biometric-attendance-sync-tool/
│
├── erpnext_sync_all.py                          # Service chính (AUTO)
├── erpnext_re_sync_all.py                       # Công cụ resync (MANUAL)
├── local_config.py                              # Cấu hình hệ thống
├── erpnext_api_client.py                        # ERPNext API client
├── sync_user_info_state.py                      # Quản lý trạng thái sync
│
│── AUTO Functions (01-09)
├── 01.sync_log_from_device_to_erpnext.py        # Sync log Device → ERPNext
├── 02.clean_data_employee_left.py               # Xóa template NV nghỉ việc (AUTO & MANUAL)
├── 03.clean_old_logs.py                         # Dọn dẹp log cũ
├── 04.sync_log_from_mongodb_to_erpnext.py       # Sync log MongoDB → ERPNext (AUTO & MANUAL)
├── 05.sync_ot_from_mongodb_to_erpnext.py        # Sync OT MongoDB → ERPNext (AUTO & MANUAL)
│
│── MANUAL Functions (11-19)
├── 11.sync_user_info_from_erpnext_to_device.py  # Sync user/fingerprint ERPNext → Device
├── 12.sync_from_master_device_to_erpnext.py     # Sync từ master device
├── 13.clean_user_on_machine.py                  # Xóa user trên máy
│
├── start_erpnext_sync_all_manual.sh             # Khởi động service
├── stop_erpnext_sync_all_manual.sh              # Dừng service
├── status_erpnext_sync_all_manual.sh            # Kiểm tra trạng thái
├── set_up_requirement.sh                        # Cài đặt dependencies
│
├── 02.clean_data_employee_left.sh               # Script chạy clean left
├── 12.sync_from_master_device_to_erpnext.sh     # Script chạy master sync
│
├── manual_run_functions/                        # Các script thủ công bổ sung
│   └── sync_all_from_master_device_to_other_devices.py
│
└── logs/                                        # Thư mục log
    ├── logs.log                                 # Log chính
    ├── error.log                                # Log lỗi
    ├── logs_resync.log                          # Log resync
    ├── time_sync.log                            # Log time sync
    └── clean_data_employee_left/                # Log xóa NV nghỉ việc
```

## Phân Loại Chức Năng

### AUTO Functions (01-09) - Chạy tự động trong erpnext_sync_all.py

| File | Chức năng | Tần suất |
|------|-----------|----------|
| `01.sync_log_from_device_to_erpnext.py` | Sync log chấm công từ Device → ERPNext | Mỗi 3 phút |
| `02.clean_data_employee_left.py` | Xóa template NV nghỉ việc | 1 lần/ngày |
| `03.clean_old_logs.py` | Dọn dẹp log files cũ | 1 lần/ngày |
| `04.sync_log_from_mongodb_to_erpnext.py` | Sync log từ MongoDB → ERPNext | Mỗi 3 phút (nếu enabled) |
| `05.sync_ot_from_mongodb_to_erpnext.py` | Sync OT từ MongoDB → ERPNext | Mỗi 3 phút (nếu enabled) |

### MANUAL Functions (11-19) - Chạy thủ công

| File | Chức năng | Lệnh |
|------|-----------|------|
| `erpnext_re_sync_all.py` | Công cụ resync tổng hợp | `python erpnext_re_sync_all.py --help` |
| `11.sync_user_info_from_erpnext_to_device.py` | Sync user/fingerprint ERPNext → Device | `python 11.sync_user_info_from_erpnext_to_device.py --mode auto` |
| `12.sync_from_master_device_to_erpnext.py` | Sync từ master device | `./12.sync_from_master_device_to_erpnext.sh` |
| `13.clean_user_on_machine.py` | Xóa user trên máy chấm công | `python 13.clean_user_on_machine.py` |

### AUTO & MANUAL - Chạy tự động và có thể chạy thủ công

| File | Chức năng | Auto | Manual |
|------|-----------|------|--------|
| `02.clean_data_employee_left.py` | Xóa template NV nghỉ việc | 1 lần/ngày | `python 02.clean_data_employee_left.py` |
| `04.sync_log_from_mongodb_to_erpnext.py` | Sync log MongoDB → ERPNext | Mỗi 3 phút | `python erpnext_re_sync_all.py --mongodb-sync` |
| `05.sync_ot_from_mongodb_to_erpnext.py` | Sync OT MongoDB → ERPNext | Mỗi 3 phút | `python erpnext_re_sync_all.py --ot-mongodb-sync` |

## Cách Sử Dụng

### 1. Cài đặt
```bash
./set_up_requirement.sh
```

### 2. Khởi động Service Tự Động
```bash
./start_erpnext_sync_all_manual.sh
./status_erpnext_sync_all_manual.sh
./stop_erpnext_sync_all_manual.sh
```

### 3. Chạy Thủ Công

#### Công cụ erpnext_re_sync_all.py
```bash
source venv/bin/activate

# Xem trạng thái cấu hình
python erpnext_re_sync_all.py --status

# Re-sync dữ liệu chấm công hôm nay
python erpnext_re_sync_all.py --resync

# Re-sync khoảng ngày cụ thể
python erpnext_re_sync_all.py --resync --date-range 20251101 20251115

# Sync time và restart devices
python erpnext_re_sync_all.py --time-sync-and-restart
python erpnext_re_sync_all.py --time-sync
python erpnext_re_sync_all.py --restart-devices

# Sync từ MongoDB
python erpnext_re_sync_all.py --mongodb-sync
python erpnext_re_sync_all.py --ot-mongodb-sync

# Xóa template NV nghỉ việc
python erpnext_re_sync_all.py --clear-templates
python erpnext_re_sync_all.py --clear-templates --force

# Chạy tất cả
python erpnext_re_sync_all.py --all
```

#### Các file chạy độc lập
```bash
source venv/bin/activate

# Sync user/fingerprint từ ERPNext xuống device
python 11.sync_user_info_from_erpnext_to_device.py --mode auto
python 11.sync_user_info_from_erpnext_to_device.py --mode full
python 11.sync_user_info_from_erpnext_to_device.py --mode changed --hours 24

# Xóa template NV nghỉ việc
python 02.clean_data_employee_left.py
python 02.clean_data_employee_left.py --dry-run

# Xóa user trên máy chấm công
python 13.clean_user_on_machine.py
```

## Cấu Hình (local_config.py)

### Thông tin ERPNext
```python
ERPNEXT_URL = 'http://10.0.1.20'
ERPNEXT_API_KEY = '7c5bab33922d7f6'
ERPNEXT_API_SECRET = '5df993705d12dd4'
PULL_FREQUENCY = 3  # phút
```

### Danh sách máy chấm công
```python
devices = [
    {'device_id':'Machine 1','ip':'10.0.1.41', ...},
    {'device_id':'Machine 2','ip':'10.0.1.42', ...},
    # ... Machine 3-7 (10.0.1.43-47)
]
```

### Feature Toggles
```python
# MongoDB Sync (AUTO & MANUAL)
ENABLE_SYNC_LOG_FROM_MONGODB_TO_ERPNEXT = True
ENABLE_SYNC_OT_FROM_MONGODB_TO_ERPNEXT = True

# Clear Left Employee Templates (AUTO & MANUAL)
ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES = False
CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = 30
ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = 60

# Resync Configuration (MANUAL qua erpnext_re_sync_all.py)
ENABLE_RESYNC_ON_DAY = False
TIME_RESYNC_ON_DAY = ["08:10:00","22:30:00"]

# Time Sync & Restart (MANUAL qua erpnext_re_sync_all.py)
ENABLE_TIME_SYNC_AND_RESTART_AT_23H_OF_SUNDAY = True
```

## Giám sát Log

```bash
# Log chính
tail -f logs/logs.log

# Log lỗi
tail -f logs/error.log

# Log resync
tail -f logs/logs_resync.log

# Log time sync
tail -f logs/time_sync.log

# Log xóa NV nghỉ việc
tail -f logs/clean_data_employee_left/clean_left_employees.log
```

## Xử lý Lỗi

### Service không chạy
```bash
./status_erpnext_sync_all_manual.sh
venv/bin/python3 erpnext_sync_all.py --test-config
tail -f logs/error.log
```

### Kết nối máy chấm công
```bash
ping 10.0.1.41
grep "Device.*not reachable" logs/logs.log
```

### Kill process
```bash
ps aux | grep erpnext_sync_all | grep -v grep
kill -9 <PID>
```

## Tóm Tắt

- **erpnext_sync_all.py**: Service chính chạy tự động mỗi 3 phút
- **erpnext_re_sync_all.py**: Công cụ chạy thủ công các chức năng resync, time sync, MongoDB sync
- **01-05.*.py**: AUTO functions - chạy tự động trong service
- **11-13.*.py**: MANUAL functions - chạy thủ công khi cần
- **02, 04, 05**: Vừa AUTO vừa MANUAL
