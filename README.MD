# Hệ Thống Đồng Bộ Chấm Công ERPNext

Hệ thống đồng bộ tự động giữa máy chấm công sinh trắc học và ERPNext với khả năng bypass thời gian và tính năng re-sync.

## 📁 Cấu Trúc Thư Mục

```
biometric-attendance-sync-tool/
├── README.MD                                    # Tài liệu chính
├── local_config.py                              # Cấu hình hệ thống
├── erpnext_sync_all.py                          # Service chính
├── sync_log_from_device_to_erpnext.py          # Sync log chấm công từ thiết bị đến ERPNext
├── sync_user_info_from_erpnext_to_device.py    # Sync thông tin nhân viên từ ERPNext đến thiết bị
├── start_erpnext_sync_all_manual.sh            # Script khởi động service
├── stop_erpnext_sync_all_manual.sh             # Script dừng service
├── status_erpnext_sync_all_manual.sh           # Script kiểm tra trạng thái
├── set_up_requirement.sh                       # Script cài đặt dependencies
└── logs/                                       # Thư mục chứa log files
```

## 🚀 Cách Sử Dụng

### Bước 1: Cài đặt
```bash
# Cài đặt dependencies và phân quyền
./set_up_requirement.sh
```

### Bước 2: Khởi động Service
```bash
# Khởi động service
./start_erpnext_sync_all_manual.sh

# Kiểm tra trạng thái
./status_erpnext_sync_all_manual.sh

# Dừng service
./stop_erpnext_sync_all_manual.sh
```

### Bước 3: Theo dõi Logs
```bash
# Theo dõi log chính
tail -f logs/logs.log

# Theo dõi log lỗi
tail -f logs/error.log
```

## ⚙️ Cấu Hình Chính

Chỉnh sửa file `local_config.py`:

### 🔧 Cấu hình Cơ bản
```python
# Thông tin ERPNext
ERPNEXT_URL = 'http://10.0.1.21'
ERPNEXT_API_KEY = '7c5bab33922d7f6'
ERPNEXT_API_SECRET = '2d379dbe1ef33ab'

# Tần suất đồng bộ (phút)
PULL_FREQUENCY = 3

# Danh sách máy chấm công (hiện tại: Machine_1 đến Machine_7)
devices = [
    {'device_id':'Machine_1','ip':'10.0.1.41', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    {'device_id':'Machine_2','ip':'10.0.1.42', 'punch_direction': None, 'clear_from_device_on_fetch': False, 'latitude':0.0000,'longitude':0.0000},
    # ... Machine_3 to Machine_7 (10.0.1.43-47)
]

# Master device cho sync fingerprints
devices_master = {'device_id':'Machine_1','ip':'10.0.1.41', ...}

# User IDs bị bỏ qua (tạp vụ)
user_id_inorged = ['55','58','161','623','916','920','3000','3001','3002','6004','6005']
```

### 🔄 Tính năng Re-sync

#### **Manual Re-sync**
**Mục đích**: Bổ sung các log chấm công còn thiếu trong khoảng thời gian cụ thể.

```python
# Bật re-sync cho khoảng thời gian cụ thể
re_sync_data_date_range = ['20250907','20250907']  # ['YYYYMMDD','YYYYMMDD']

# Tắt re-sync (chế độ normal)
re_sync_data_date_range = []
```

**Cách hoạt động**:
- ✅ **Không xóa** dữ liệu có sẵn trong ERPNext
- ✅ Sync **TẤT CẢ logs** từ máy chấm công trong khoảng thời gian
- ✅ **Tự động bỏ qua duplicate** (không tạo error log)
- ✅ Chỉ thêm các logs **còn thiếu** vào ERPNext

**Workflow sử dụng**:
1. Set `re_sync_data_date_range = ['20250907','20250907']`
2. Chạy service: `./start_erpnext_sync_all_manual.sh`
3. Sau khi hoàn thành, set `re_sync_data_date_range = []`

#### **🌙 End-of-Day Auto Re-sync** ⭐ **NEW**
**Mục đích**: Tự động re-sync toàn bộ logs trong ngày vào thời điểm cuối ngày để đảm bảo không thiếu dữ liệu.

```python
# Cấu hình End-of-Day Re-sync
ENABLE_END_OF_DAY_RESYNC = True          # Bật/tắt tính năng
END_OF_DAY_RESYNC_HOUR = 23              # Giờ thực hiện (0-23)
END_OF_DAY_RESYNC_MINUTE = 30            # Phút thực hiện (0-59)
END_OF_DAY_RESYNC_WINDOW_MINUTES = 10    # Cửa sổ thời gian ±5 phút
END_OF_DAY_RESYNC_LOG_FILE = 'logs/logs_resync.log'  # Log riêng cho re-sync
```

**🚀 Tính năng**:
- ✅ **Tự động chạy** mỗi ngày vào thời điểm cấu hình (mặc định 23:30)
- ✅ **Re-sync toàn bộ logs** trong ngày hiện tại từ tất cả máy chấm công
- ✅ **Bỏ qua tất cả bypass periods** để đảm bảo sync hoàn chỉnh
- ✅ **Log riêng biệt** trong `logs/logs_resync.log`
- ✅ **Filter duplicate errors** tự động, chỉ giữ log quan trọng
- ✅ **Comprehensive logging** với status chi tiết và duration

**🔍 Cách hoạt động**:
1. **Every cycle**: Service kiểm tra thời gian hiện tại
2. **At target time** (ví dụ 23:25-23:35): Trigger end-of-day re-sync
3. **Auto setup**: Tự động set `re_sync_data_date_range = [today, today]`
4. **Force sync**: Bỏ qua tất cả bypass logic, force kết nối tất cả devices
5. **Auto restore**: Khôi phục cấu hình gốc sau khi hoàn thành

**📋 Log Monitoring**:
```bash
# Theo dõi end-of-day re-sync
tail -f logs/logs_resync.log

# Kiểm tra lịch sử re-sync
grep "END-OF-DAY RE-SYNC CYCLE" logs/logs_resync.log
```

### ⏰ Cấu hình Bypass Time (trong local_config.py)
```python
# Bypass sync log (giờ rush) - hiện tại: TẮT
sync_log_by_pass_period = [
    # {"start": "07:30", "end": "07:55", "reason": "Morning rush - employees clocking in"},
    # {"start": "17:00", "end": "17:30", "reason": "Evening rush - employees clocking out"}
]

# Bypass sync user info (giờ rush) - hiện tại: TẮT
sync_user_info_by_pass_period = [
    # {"start": "07:30", "end": "07:55", "reason": "Morning rush - avoid device conflicts"},
    # {"start": "17:00", "end": "17:30", "reason": "Evening rush - avoid device conflicts"}
]
```

### 🎛️ Feature Toggles (trong local_config.py)
```python
# Bật/tắt sync thông tin nhân viên - hiện tại: TẮT
ENABLE_SYNC_USER_INFO_FROM_ERPNEXT_TO_DEVICE = False

# Bật/tắt clear left templates - hiện tại: BẬT
ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES = True  # Clear from devices (once per day)
CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = 7  # Wait N days after relieving before clearing (today >= relieving_date + 7 days)
ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = 1400  # Permanently delete users after N days (0 = disabled, PRIORITY 1 - checked FIRST)
ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_ERPNEXT = False  # Delete from database
PROCESSED_LEFT_EMPLOYEES_FILE = 'logs/processed_left_employees.json'  # Track processed employees (skip on subsequent runs)

# Chế độ sync: 'auto', 'full', 'changed'
SYNC_USER_INFO_MODE = 'auto'
SYNC_CHANGED_HOURS_BACK = 24

# End-of-Day Auto Re-sync (NEW) - hiện tại: BẬT
ENABLE_END_OF_DAY_RESYNC = True
END_OF_DAY_RESYNC_HOUR = 23
END_OF_DAY_RESYNC_MINUTE = 30
```

## 📊 Giám sát Hệ thống

### 🔍 Kiểm tra Service
```bash
# Trạng thái tổng quan
./status_erpnext_sync_all_manual.sh

# Kiểm tra process
ps aux | grep 'erpnext_sync_all.py'

# Test cấu hình và bypass status
python3 erpnext_sync_all.py --test-config
python3 -c "import local_config; print(local_config.get_bypass_status())"
```

### 📈 Log Analysis
```bash
# Theo dõi hoạt động real-time
tail -f logs/logs.log

# Theo dõi end-of-day re-sync (NEW)
tail -f logs/logs_resync.log

# Đếm số lần sync thành công hôm nay
grep "$(date +%Y-%m-%d)" logs/attendance_success_log_*.log | wc -l

# Xem lỗi gần đây
grep "ERROR" logs/error.log | tail -20

# Kiểm tra re-sync mode
grep "Re-sync mode" logs/logs.log | tail -5

# Kiểm tra lịch sử end-of-day re-sync (NEW)
grep "END-OF-DAY RE-SYNC CYCLE" logs/logs_resync.log

# Thống kê end-of-day re-sync (NEW)
grep "COMPLETED" logs/logs_resync.log | grep -E "(SUCCESSFULLY|WITH ERRORS)"
```

## 📋 Các File Log Quan trọng

```bash
# Log chính
logs/logs.log                              # Tổng quát
logs/error.log                             # Lỗi hệ thống
logs/logs_resync.log                       # End-of-day re-sync (NEW)

# Log theo máy chấm công
logs/attendance_success_log_Machine_*.log  # Thành công theo máy
logs/attendance_failed_log_Machine_*.log   # Thất bại theo máy

# Log đặc biệt
logs/user_id_inorged_log.txt               # User bị bỏ qua
logs/error_duplicate.log                   # Duplicate (normal mode)
```

## 🚨 Xử Lý Lỗi Thường Gặp

### 1. Service không khởi động
```bash
# Kiểm tra chi tiết
./status_erpnext_sync_all_manual.sh

# Test cấu hình
venv/bin/python3 erpnext_sync_all.py --test-config

# Xem log lỗi
tail -f logs/error.log
```

### 2. Kết nối máy chấm công thất bại
```bash
# Test network
ping 10.0.1.41
ping 10.0.1.42

# Xem log connectivity
grep "Device.*not reachable" logs/logs.log
```

### 3. ERPNext API lỗi
```bash
# Test API
curl -X GET "http://10.0.1.21/api/resource/Employee" \
  -H "Authorization: token 7c5bab33922d7f6:2d379dbe1ef33ab"

# Xem API errors  
grep "ERPNext API" logs/error.log
```

## 🔤 Xử Lý Tên Tiếng Việt

Hệ thống tự động normalize tên tiếng Việt khi sync từ ERPNext đến máy chấm công:

```
Nguyễn Văn A    → Nguyen Van A
Trần Thị Bích   → Tran Thi Bich  
Lê Hoàng Đức    → Le Hoang Duc
```

**Lý do**: Đảm bảo tương thích với firmware máy chấm công.

## 📞 Hỗ trợ

### Commands Hữu ích
```bash
# Kiểm tra trạng thái
./status_erpnext_sync_all_manual.sh

# Debug manual
./stop_erpnext_sync_all_manual.sh
venv/bin/python3 erpnext_sync_all.py

# Setup lại
./set_up_requirement.sh
```

---

**🎯 Lưu ý**: 
- Service tự động reload config mỗi 5 phút
- Manual re-sync: Dùng để bổ sung logs thiếu, set `[]` sau khi xong
- End-of-day auto re-sync: Tự động chạy mỗi ngày để đảm bảo đầy đủ dữ liệu
- Bypass time: Tránh conflict trong giờ rush
- Log monitoring: Theo dõi `logs/logs_resync.log` để xem kết quả end-of-day re-sync

**🚫 Kill processs **: 
- ps aux | grep erpnext_sync_all | grep -v grep
frappe    208657  1.3  0.1 116204 34176 pts/5    Sl+  16:37   0:00 ./venv/bin/python3 ./erpnext_sync_all.py
- kill -9 208657