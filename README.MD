# Hệ Thống Đồng Bộ Chấm Công ERPNext

Hệ thống đồng bộ tự động giữa máy chấm công sinh trắc học và ERPNext.

## Cấu Trúc Dự Án

```
biometric-attendance-sync-tool/
│
├── erpnext_sync_all.py                          # Service chính (AUTO)
├── erpnext_re_sync_all.py                       # Công cụ manual với Interactive Menu
├── local_config.py                              # Cấu hình chung (shared for AUTO & MANUAL)
├── manual_input_utils.py                        # Utilities for user input prompts
├── erpnext_api_client.py                        # ERPNext API client
│
│── AUTO Functions (01-09)
├── 01.sync_log_from_device_to_erpnext.py        # Sync log Device → ERPNext
├── 02.clean_data_employee_left.py               # Xóa template NV nghỉ việc
├── 03.clean_old_logs.py                         # Dọn dẹp log cũ
├── 04.sync_log_from_mongodb_to_erpnext.py       # Sync log MongoDB → ERPNext
├── 05.sync_ot_from_mongodb_to_erpnext.py        # Sync OT MongoDB → ERPNext
│
│── MANUAL Functions (11-19)
├── 11.sync_user_info_from_erpnext_to_device.py  # Sync user/fingerprint ERPNext → Device
├── 12.sync_from_master_device_to_erpnext.py     # Sync từ master device
├── 13.clean_user_on_machine.py                  # Xóa user trên máy
├── 14.delete_ot_in_erpnext_db.py                # Xóa OT trong database ERPNext
│
└── logs/                                        # Thư mục log (relative paths)
    ├── logs.log                                 # Log chính
    ├── error.log                                # Log lỗi
    ├── logs_resync.log                          # Log resync
    ├── time_sync.log                            # Log time sync
    └── clean_data_employee_left/                # Log xóa NV nghỉ việc
```

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

### 3. Chạy Thủ Công - Interactive Menu

**Interactive Menu** - Khuyến nghị sử dụng
```bash
source venv/bin/activate
python erpnext_re_sync_all.py
```

Sẽ hiển thị menu chọn các chức năng:

```
================================================================================
 Manual Resync Data Tool v1.0.0 - Interactive Menu
================================================================================

Available Functions:
  1. Sync Log from Device to ERPNext
  2. Clean Data Employee Left
  3. Clean Old Logs
  4. Sync Log from MongoDB to ERPNext
  5. Sync OT from MongoDB to ERPNext
  6. Sync User Info from ERPNext to Device
  7. Sync from Master Device to ERPNext
  8. Clean User on Machine
  9. Delete OT in ERPNext Database
 10. Sync All from Master to Other Devices

  0. Exit
================================================================================
```

### Chi Tiết Các Chức Năng Manual

#### 1. Sync Log from Device to ERPNext
- **Mục đích**: Đồng bộ dữ liệu chấm công từ thiết bị sinh trắc học vào ERPNext
- **Prompt**: Yêu cầu nhập ngày bắt đầu và ngày kết thúc (YYYYMMDD)
- **Default**: Hôm nay (nếu bấm Enter)
- **Xác nhận**: Hiển thị khoảng ngày và yêu cầu xác nhận (y/n)

#### 2. Clean Data Employee Left
- **Mục đích**: Xóa template vân tay của nhân viên đã nghỉ việc
- **Prompt 1**: Nhập số ngày delay sau relieving_date trước khi xóa template
  - Current value: `CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS`
  - Default: 30 ngày
- **Prompt 2**: Nhập số ngày sau relieving_date để xóa vĩnh viễn user khỏi thiết bị
  - Current value: `ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS`
  - Default: 60 ngày
- **Lưu ý**:
  - Chạy tối đa 1 lần/ngày
  - Sử dụng `--force` để bỏ qua giới hạn này

#### 3. Clean Old Logs
- **Mục đích**: Dọn dẹp log files cũ
- **Prompt**: Nhập số ngày gần nhất cần giữ log
  - Current value: `CLEAN_OLD_LOGS_DAYS`
  - Default: 3 ngày
- **Xử lý**:
  - Xóa các dòng log cũ hơn N ngày
  - Xóa các rotated log files rỗng (*.log.1, *.log.2, etc.)

#### 4. Sync Log from MongoDB to ERPNext
- **Mục đích**: Đồng bộ dữ liệu chấm công từ MongoDB vào ERPNext
- **Prompt**: Yêu cầu nhập date range (YYYYMMDD)
- **Default**: 7 ngày gần nhất (nếu bấm Enter)
- **Xác nhận**: Hiển thị khoảng ngày và yêu cầu xác nhận (y/n)

#### 5. Sync OT from MongoDB to ERPNext
- **Mục đích**: Đồng bộ đơn đăng ký OT từ MongoDB vào ERPNext
- **Prompt**: Yêu cầu nhập ngày bắt đầu (YYYYMMDD)
- **Default**: Hôm nay (nếu bấm Enter)
- **Xác nhận**: Hiển thị ngày và yêu cầu xác nhận (y/n)

#### 6. Sync User Info from ERPNext to Device
- **Mục đích**: Đồng bộ thông tin user và template vân tay từ ERPNext xuống thiết bị
- **Hiển thị**: Cấu hình hiện tại của `sync_from_master_device_to_erpnext_filters_id`
  - Nếu có filter: Hiển thị danh sách ID
  - Nếu rỗng: Sync tất cả user
- **Options**:
  1. Sử dụng cấu hình hiện tại
  2. Nhập danh sách ID thủ công (comma-separated)
  3. Sync tất cả user (clear filter)
- **Example**: `100,200,300` → Chỉ sync 3 user IDs này

#### 7. Sync from Master Device to ERPNext
- **Mục đích**: Đồng bộ template vân tay từ master device vào ERPNext
- **Không cần prompt**: Chạy ngay với cấu hình từ `local_config.py`

#### 8. Clean User on Machine
- **Mục đích**: Xóa user khỏi thiết bị (giữ lại các user trong 13.keep_user_id.txt)
- **Hiển thị**:
  1. Danh sách user sẽ được GIỮ LẠI (từ 13.keep_user_id.txt)
  2. Preview từ thiết bị đầu tiên:
     - User sẽ bị XÓA (max 20)
     - User sẽ được GIỮ (max 20)
- **Xác nhận**: Phải gõ 'yes' để xác nhận xóa
- **LƯU Ý**: Thao tác này sẽ XÓA user khỏi thiết bị!

#### 9. Delete OT in ERPNext Database
- **Mục đích**: Xóa bản ghi OT trong database ERPNext
- **Prompt**: Yêu cầu nhập date range (YYYYMMDD)
- **Preview**: Hiển thị dry run trước khi xóa thật
  - Số detail records sẽ xóa
  - Số parent records sẽ xóa
- **Xác nhận**: Phải gõ 'DELETE' (chính xác) để xác nhận
- **LƯU Ý**: Thao tác này XÓA DỮ LIỆU từ database!

#### 10. Sync All from Master to Other Devices
- **Mục đích**: Đồng bộ TẤT CẢ users có template vân tay từ master device sang các devices khác
- **Hiển thị**:
  - Master device info (ID, IP)
  - Tổng số users có fingerprints
  - Danh sách target devices
- **Xác nhận**: Phải gõ 'yes' để bắt đầu sync
- **Use case**:
  - Thiết lập devices mới
  - Backup/restore fingerprints
  - Đồng bộ hàng loạt sau khi thêm nhiều users mới
- **LƯU Ý**: Quá trình có thể mất nhiều thời gian tùy số lượng users

### 4. Chạy Command Line (không dùng menu)

```bash
source venv/bin/activate

# Xem trạng thái cấu hình
python erpnext_re_sync_all.py --status

# Các lệnh chính
python erpnext_re_sync_all.py --resync                    # Sẽ prompt ngày
python erpnext_re_sync_all.py --clear-templates --force   # Sẽ prompt parameters
python erpnext_re_sync_all.py --mongodb-sync              # Sẽ prompt date range
python erpnext_re_sync_all.py --ot-mongodb-sync           # Sẽ prompt start date
python erpnext_re_sync_all.py --sync-user-info            # Sẽ prompt filter options
python erpnext_re_sync_all.py --sync-all-from-master      # Sync all users from master to others
python erpnext_re_sync_all.py --clean-user                # Sẽ show preview & confirm
python erpnext_re_sync_all.py --delete-ot                 # Sẽ prompt date range & confirm

# Time sync & restart (KHÔNG cần prompt)
python erpnext_re_sync_all.py --time-sync
python erpnext_re_sync_all.py --restart-devices
python erpnext_re_sync_all.py --time-sync-and-restart
```

## Cấu Hình

### 1. Cấu hình chung (local_config.py)

```python
# ERPNext connection
ERPNEXT_URL = 'http://10.0.1.20'
ERPNEXT_API_KEY = '7c5bab33922d7f6'
ERPNEXT_API_SECRET = '5df993705d12dd4'
PULL_FREQUENCY = 3  # phút

# Danh sách máy chấm công
devices = [
    {'device_id':'Machine 1','ip':'10.0.1.41', ...},
    {'device_id':'Machine 2','ip':'10.0.1.42', ...},
    # ... Machine 3-7
]

# MongoDB configuration
ENABLE_SYNC_LOG_FROM_MONGODB_TO_ERPNEXT = True
ENABLE_SYNC_OT_FROM_MONGODB_TO_ERPNEXT = True
MONGODB_HOST = "10.0.1.4"
MONGODB_DATABASE = "tiqn"

# Clear left employee templates
ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES = False    # True = Enable AUTO mode
CLEAR_LEFT_USER_TEMPLATES_ON_DATE_OF_MONTH = [10, 25]  # Run on 10th & 25th; [] = every day
CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = 30    # Wait 30 days after relieving
ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = 60  # Delete after 60 days

# Log cleanup
CLEAN_OLD_LOGS_DAYS = 3  # Giữ log 3 ngày gần nhất

# Sync filters
sync_from_master_device_to_erpnext_filters_id = []  # [] = sync all
user_id_inorged = ['55','58','161']  # IDs to ignore
```

### 2. File cấu hình khác

#### 13.keep_user_id.txt
Danh sách user IDs cần giữ lại khi clean user on machine:
```
100
200
300
```

## Đường Dẫn Log Files

**TẤT CẢ log files sử dụng đường dẫn tương đối** (không hardcode absolute path):

```
logs/
├── logs.log                                    # Main log
├── error.log                                   # Error log
├── logs_resync.log                             # Resync operations
├── time_sync.log                               # Time sync operations
├── sync_log_from_mongodb_to_erpnext.txt        # MongoDB sync
├── clear_left_templates.log                    # Clear left employee templates
│
├── clean_data_employee_left/
│   ├── clean_left_employees.log                # Clean left employees
│   └── processed_left_employees.json           # Tracking file
│
├── sync_from_erpnext_to_device/
│   └── sync_to_device.log                      # Sync to device
│
└── clean_user_on_machine/
    └── clean_users.log                         # Clean users
```

## Giám Sát Log

```bash
# Log chính
tail -f logs/logs.log

# Log lỗi
tail -f logs/error.log

# Log resync
tail -f logs/logs_resync.log

# Log MongoDB sync
tail -f logs/sync_log_from_mongodb_to_erpnext.txt

# Log clean left employees
tail -f logs/clean_data_employee_left/clean_left_employees.log
```

## Xử Lý Lỗi

### Service không chạy
```bash
./status_erpnext_sync_all_manual.sh
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

## Phân Loại Chức Năng

### AUTO Functions (01-09) - Chạy tự động

| File | Chức năng | Tần suất |
|------|-----------|----------|
| `01.sync_log_from_device_to_erpnext.py` | Sync log từ Device → ERPNext | Mỗi 3 phút |
| `02.clean_data_employee_left.py` | Xóa template NV nghỉ việc | 1 lần/ngày (ngày 10 & 25 nếu cấu hình) |
| `03.clean_old_logs.py` | Dọn dẹp log cũ | 1 lần/ngày |
| `04.sync_log_from_mongodb_to_erpnext.py` | Sync log MongoDB → ERPNext | Mỗi cycle (nếu enabled) |
| `05.sync_ot_from_mongodb_to_erpnext.py` | Sync OT MongoDB → ERPNext | Mỗi cycle (nếu enabled) |

### MANUAL Functions (11-19) - Chạy thủ công

| File | Chức năng | User Prompts |
|------|-----------|--------------|
| `erpnext_re_sync_all.py` (1) | Sync Log from Device | Date range |
| `erpnext_re_sync_all.py` (2) | Clean Data Employee Left | Delay days, Delete after days |
| `erpnext_re_sync_all.py` (3) | Clean Old Logs | Days to keep |
| `erpnext_re_sync_all.py` (4) | MongoDB Sync | Date range |
| `erpnext_re_sync_all.py` (5) | OT MongoDB Sync | Start date |
| `erpnext_re_sync_all.py` (6) | Sync User Info | Device filter options |
| `erpnext_re_sync_all.py` (7) | Sync from Master | None (uses config) |
| `erpnext_re_sync_all.py` (8) | Clean User on Machine | Preview + confirmation |
| `erpnext_re_sync_all.py` (9) | Delete OT | Date range + preview + confirmation |
| `erpnext_re_sync_all.py` (10) | Sync All from Master to Others | Preview + confirmation |

## Tóm Tắt

### Điểm Khác Biệt Chính

1. **Đường dẫn tương đối**: Tất cả log files sử dụng relative paths
2. **Interactive prompts**: Tất cả manual functions có user prompts phù hợp
3. **Preview & confirmation**: Các thao tác nguy hiểm (xóa data) có preview và xác nhận
4. **Validation**: Tất cả input đều được validate
5. **Default values**: Gợi ý giá trị mặc định cho mọi prompt

### Files và Chức Năng

- **erpnext_sync_all.py**: Service AUTO
  - Chạy mỗi 3 phút
  - Sử dụng intelligent defaults

- **erpnext_re_sync_all.py**: Công cụ MANUAL
  - Interactive menu dễ sử dụng
  - User prompts cho tất cả parameters
  - Preview và confirmation cho thao tác nguy hiểm
  - Command line mode với đầy đủ options

### Configuration Management

- `local_config.py`: Shared configuration
- `manual_input_utils.py`: Input validation utilities
- Không còn hardcode date ranges
- Sử dụng prompts cho flexibility

### Clear Left Employee Templates - Scheduling

**Cấu hình ngày chạy AUTO:**

```python
CLEAR_LEFT_USER_TEMPLATES_ON_DATE_OF_MONTH = [10, 25]  # Chạy ngày 10 & 25 hàng tháng
CLEAR_LEFT_USER_TEMPLATES_ON_DATE_OF_MONTH = []        # Chạy mỗi ngày
```

**⚠️ QUAN TRỌNG: AUTO vs MANUAL Mode**

| Mode | Check Schedule? | Check "Đã chạy hôm nay"? | Bypass với --force? |
|------|----------------|-------------------------|---------------------|
| **AUTO** (`erpnext_sync_all.py`) | ✅ YES - Chỉ chạy ngày được cấu hình | ✅ YES - 1 lần/ngày | ❌ NO |
| **MANUAL** (`erpnext_re_sync_all.py`) | ❌ NO - Luôn cho phép chạy | ✅ YES - 1 lần/ngày | ✅ YES |

**Logic hoạt động AUTO mode:**

1. **Check enabled**: `ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES = True`
2. **Check chưa chạy hôm nay**: Kiểm tra marker file `.last_clear_left_templates`
3. **Check ngày trong tháng** (CHỈ AUTO mode):
   - Nếu `[]` (rỗng) → Chạy mỗi ngày
   - Nếu `[10, 25]` → CHỈ chạy ngày 10 và 25
   - Chạy vào **cycle đầu tiên** của ngày đó

**Logic hoạt động MANUAL mode:**

1. **KHÔNG check ngày trong tháng** - User muốn chạy → luôn cho phép
2. **CHỈ check "đã chạy hôm nay"**:
   - Chưa chạy → Cho phép
   - Đã chạy → Chặn (trừ khi dùng `--force`)

**Ví dụ với `[10, 25]`:**

```
AUTO Mode (erpnext_sync_all.py):
├─ Ngày 9:  SKIP (không phải 10 hoặc 25)
├─ Ngày 10: RUN trong cycle đầu tiên (00:00 - 00:03)
│           Các cycle sau SKIP (đã chạy rồi)
├─ Ngày 11-24: SKIP (không phải 10 hoặc 25)
└─ Ngày 25: RUN trong cycle đầu tiên

MANUAL Mode (erpnext_re_sync_all.py):
├─ Ngày 9:  ✅ CHO PHÉP chạy (bypass schedule)
├─ Ngày 10: ✅ CHO PHÉP chạy
│           Lần 2 trong ngày: CHẶN (đã chạy)
│           Dùng --force: ✅ CHO PHÉP
├─ Ngày 11: ✅ CHO PHÉP chạy (bypass schedule)
└─ Mọi ngày: ✅ LUÔN CHO PHÉP (không quan tâm schedule)
```

**Use cases:**

- `[10, 25]`: Chạy 2 lần/tháng AUTO (tiết kiệm resources), MANUAL luôn được phép
- `[1]`: Chạy đầu tháng AUTO, MANUAL không bị ảnh hưởng
- `[]`: Chạy mỗi ngày AUTO (aggressive cleanup), MANUAL giống như bình thường
