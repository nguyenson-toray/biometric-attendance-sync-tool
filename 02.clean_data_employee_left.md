# Clean Data Employee Left - Dọn Dẹp Dữ Liệu Nhân Viên Nghỉ Việc

## 🎯 Chức Năng

Tool dọn dẹp toàn diện cho nhân viên có trạng thái "Left" (Nghỉ việc) với 2 chế độ xử lý:

### Chế độ 1: Xóa Template (Clear Templates)
- **Điều kiện**: Nhân viên nghỉ việc >= `CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS` ngày (mặc định: 60 ngày)
- **Hành động**:
  - Xóa hoàn toàn user khỏi thiết bị
  - Tạo lại user với cùng thông tin nhưng **KHÔNG có fingerprint templates**
  - Giữ nguyên `user_id` để bảo toàn lịch sử chấm công
- **Lợi ích**: Tiết kiệm bộ nhớ thiết bị, vẫn theo dõi được attendance history

### Chế độ 2: Xóa Vĩnh Viễn (Permanently Delete)
- **Điều kiện**: Nhân viên nghỉ việc > `ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS` ngày (mặc định: 120 ngày)
- **Hành động**: Xóa hoàn toàn user khỏi thiết bị (bao gồm cả `user_id`)
- **Ưu tiên**: Được kiểm tra **TRƯỚC** chế độ xóa template

### Xử lý ERPNext (Tùy chọn)
- **Điều kiện**: `ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_ERPNEXT = True`
- **Hành động**: Xóa tất cả fingerprint records trong ERPNext
- **Khuyến nghị**: Giữ `False` để bảo toàn dữ liệu lịch sử

## Thuật toán hoạt động

### Quy trình dọn dẹp (Sequential Processing)
```
1. KIỂM TRA KẾT NỐI
   ├── Kết nối ERPNext API
   └── Kiểm tra kết nối các máy chấm công

2. TÌM NHÂN VIÊN LEFT (với bộ lọc ưu tiên)
   ├── Query: status = "Left" AND attendance_device_id != ""
   ├── Bỏ qua: Nhân viên đã xử lý (từ tracking file JSON)
   ├── PRIORITY 1: Permanently delete (> DELETE_AFTER_DAYS)
   ├── PRIORITY 2: Clear templates (>= DELAY_DAYS)
   └── Kết quả: Danh sách nhân viên cần xử lý

3. XỬ LÝ TỪNG NHÂN VIÊN (Tuần Tự)
   ├── Xác định action type (Permanently delete hoặc Clear templates)
   │
   ├── Bước 1 (Tùy chọn): Xóa fingerprints trên ERPNext
   │   ├── Lấy danh sách custom_fingerprints
   │   ├── DELETE /api/resource/Fingerprint Data/{record_id}
   │   └── Ghi log kết quả
   │
   ├── Bước 2: Xử lý TUẦN TỰ từng thiết bị (không dùng threading)
   │   ├── Device 1:
   │   │   ├── Kết nối thiết bị
   │   │   ├── Kiểm tra user_id tồn tại
   │   │   ├── Xóa user/template tùy theo action type
   │   │   ├── Ghi log kết quả ngay lập tức
   │   │   └── Ngắt kết nối
   │   ├── Device 2: (tương tự)
   │   ├── Device 3: (tương tự)
   │   └── ... (tiếp tục với các thiết bị còn lại)
   │
   └── Bước 3: Ghi tracking file JSON (CHỈ 1 LẦN)
       ├── Xác định action type cuối cùng
       ├── Ghi vào processed_left_employees.json
       └── Tránh ghi đè và race condition

4. BÁO CÁO KẾT QUẢ
   ├── Tổng số nhân viên xử lý
   ├── Số thành công/thất bại
   ├── Thời gian thực thi
   └── Chi tiết từng thiết bị cho mỗi nhân viên
```

### Validation Logic
```python
def is_ready_for_cleanup(employee):
    """
    Kiểm tra nhân viên có sẵn sàng dọn dẹp không
    """
    # Điều kiện 1: Status phải là "Left"
    if employee.status != "Left":
        return False, "Not Left employee"
    
    # Điều kiện 2: Phải có attendance_device_id
    if not employee.attendance_device_id:
        return False, "No device ID"
    
    # Điều kiện 3: Phải có relieving_date
    if not employee.relieving_date:
        return False, "No relieving date"
    
    # Điều kiện 4: Ngày hiện tại phải sau relieving_date
    if current_date <= employee.relieving_date:
        return False, "Relieving date not passed"
    
    return True, "Ready for cleanup"
```

## Tính năng chính

- ✅ **Priority-Based Processing**: Ưu tiên xóa vĩnh viễn trước, sau đó mới xóa template
- ✅ **Delay Configuration**: Linh hoạt cấu hình thời gian chờ (30 ngày / 60 ngày)
- ✅ **Sequential Processing**: Xử lý thiết bị tuần tự, tránh race condition và lỗi đa luồng
- ✅ **Smart Tracking**: File JSON tracking để tránh xử lý lại nhân viên đã xử lý
- ✅ **Per-Device Logging**: Log riêng biệt cho từng thiết bị, dễ debug
- ✅ **Single JSON Write**: Ghi tracking file chỉ 1 lần/nhân viên, tránh ghi đè
- ✅ **Safe User ID**: Giữ lại user_id trên máy (chế độ Clear templates)
- ✅ **Dual System Cleanup**: Xóa cả ERPNext và devices (tùy chọn)
- ✅ **Complete Audit**: Log chi tiết từng thiết bị và mọi thao tác
- ✅ **Error Recovery**: Xử lý lỗi và tiếp tục với nhân viên/thiết bị khác
- ✅ **Dry Run Mode**: Xem trước không thay đổi dữ liệu

## Cấu trúc files

```
biometric-attendance-sync-tool/
├── manual_run_functions/
│   ├── clean_data_employee_left.py          # Script chính
│   ├── clean_data_employee_left.sh          # Shell wrapper
│   └── clean_data_employee_left.md          # Documentation này
├── erpnext_api_client.py                    # ERPNext API (có delete method)
├── local_config.py                          # Cấu hình
└── logs/clean_data_employee_left/
    ├── clean_left_employees.log             # Log dọn dẹp (chi tiết từng device)
    └── processed_left_employees.json        # Tracking file (tránh xử lý lặp)
```

## Cấu hình trong local_config.py

```python
# Feature toggle - Bật/tắt tính năng
ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_DEVICES = True  # True = Bật, False = Tắt

# Chế độ 1: Xóa template (Clear Templates)
CLEAR_LEFT_USER_TEMPLATES_RELIEVING_DELAY_DAYS = 30  # 30 ngày sau khi nghỉ việc

# Chế độ 2: Xóa vĩnh viễn (Permanently Delete) - Ưu tiên cao hơn
ENABLE_DELETE_LEFT_USER_ON_DEVICES_AFTER_RELIEVING_DAYS = 60  # 60 ngày sau khi nghỉ việc

# Xóa fingerprints trên ERPNext (khuyến nghị: False)
ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_ERPNEXT = False

# File tracking để tránh xử lý lặp
PROCESSED_LEFT_EMPLOYEES_FILE = 'logs/clean_data_employee_left/processed_left_employees.json'
```

### Ví dụ timeline xử lý

```
Ngày nghỉ việc: 2025-01-01

├─ 2025-01-01 đến 2025-01-30 (0-29 ngày)
│  └─ Không xử lý gì (chưa đủ delay)
│
├─ 2025-01-31 đến 2025-03-01 (30-59 ngày)
│  └─ ✓ XÓA TEMPLATE (Chế độ 1)
│     ├─ Delete user khỏi thiết bị
│     └─ Recreate user không có template
│
└─ 2025-03-02 trở đi (60+ ngày)
   └─ ✓ XÓA VĨNH VIỄN (Chế độ 2 - Ưu tiên)
      └─ Delete user hoàn toàn khỏi thiết bị
```

## Cách sử dụng

### Dry Run (Xem trước)
```bash
# Xem nhân viên nào sẽ được dọn dẹp (không thay đổi gì)
./clean_data_employee_left.sh --dry-run
```

### Chạy thật
```bash
# Dọn dẹp thực tế (có cảnh báo 5 giây)
./clean_data_employee_left.sh
```

### Chạy trực tiếp Python (debug)
```bash
# Dry run
python3 clean_data_employee_left.py --dry-run

# Chạy thật
python3 clean_data_employee_left.py
```

## Output mẫu

### Dry Run Mode
```bash
$ ./clean_data_employee_left.sh --dry-run

[WARNING] DRY RUN MODE - No actual changes will be made
[INFO] Starting Left Employee Data Cleanup
================================================================================
STARTING LEFT EMPLOYEE DATA CLEANUP
================================================================================
2025-08-20 23:00:05 - INFO - ERPNext API connection successful
2025-08-20 23:00:06 - INFO - Found 3 Left employees ready for cleanup
Would clean 3 Left employees:
  - EMP-001: Nguyen Van A (ID: 1001, Relieving: 2025-08-15)
  - EMP-002: Tran Thi B (ID: 1002, Relieving: 2025-08-10)  
  - EMP-003: Le Van C (ID: 1003, Relieving: 2025-08-12)
================================================================================
LEFT EMPLOYEE CLEANUP COMPLETED
Total execution time: 2.34 seconds
================================================================================
[SUCCESS] Dry run completed successfully!
```

### Live Run Mode
```bash
$ ./clean_data_employee_left.sh

[WARNING] LIVE MODE - This will make actual changes to ERPNext and devices
[INFO] Starting in 5 seconds... (Ctrl+C to cancel)
[INFO] Starting Left Employee Data Cleanup
================================================================================
STARTING LEFT EMPLOYEE DATA CLEANUP
================================================================================
2025-08-20 23:00:15 - INFO - ERPNext API connection successful

Filtering employees (priority order):
  1. Permanently delete: left > 60 days ago
  2. Clear templates: today >= relieving_date + 30 days
  3. Skip already processed employees from tracking file
  ✓ TIQN-0108: Ready to PERMANENTLY DELETE (left 120 days ago, >60 days)
  ✓ TIQN-0025: Ready to CLEAR templates (left 45 days ago, >=30 days)
Filter results: 2 ready to process, 5 already processed (skipped), 3 not ready yet

2025-08-20 23:00:16 - INFO - Found 2 Left employees ready for cleanup

[1/2] Processing TIQN-0108...
2025-08-20 23:00:17 - INFO - TIQN-0108 - Hồ Thị Trầm (ID: 118) | Relieving: 2025-03-20 | Action: Permanently delete user | Device: Machine 1 | ✓ Deleted
2025-08-20 23:00:18 - INFO - TIQN-0108 - Hồ Thị Trầm (ID: 118) | Relieving: 2025-03-20 | Action: Permanently delete user | Device: Machine 2 | • User not found on device (already processed)
2025-08-20 23:00:19 - INFO - TIQN-0108 - Hồ Thị Trầm (ID: 118) | Relieving: 2025-03-20 | Action: Permanently delete user | Device: Machine 3 | ✓ Deleted
2025-08-20 23:00:20 - INFO - TIQN-0108 - Hồ Thị Trầm (ID: 118) | Relieving: 2025-03-20 | Action: Permanently delete user | Device: Machine 4 | • User not found on device (already processed)
2025-08-20 23:00:21 - INFO - TIQN-0108 - Hồ Thị Trầm (ID: 118) | Relieving: 2025-03-20 | Action: Permanently delete user | Device: Machine 5 | ✓ Deleted
2025-08-20 23:00:22 - INFO - TIQN-0108 - Hồ Thị Trầm (ID: 118) | Relieving: 2025-03-20 | Action: Permanently delete user | Device: Machine 6 | ✓ Deleted
2025-08-20 23:00:23 - INFO - TIQN-0108 - Hồ Thị Trầm (ID: 118) | Relieving: 2025-03-20 | Action: Permanently delete user | Device: Machine 7 | • User not found on device (already processed)

[2/2] Processing TIQN-0025...
2025-08-20 23:00:24 - INFO - TIQN-0025 - Nguyễn Văn A (ID: 201) | Relieving: 2025-06-15 | Action: Clear templates | Device: Machine 1 | ✓ Cleared templates
2025-08-20 23:00:25 - INFO - TIQN-0025 - Nguyễn Văn A (ID: 201) | Relieving: 2025-06-15 | Action: Clear templates | Device: Machine 2 | ✓ Cleared templates
2025-08-20 23:00:26 - INFO - TIQN-0025 - Nguyễn Văn A (ID: 201) | Relieving: 2025-06-15 | Action: Clear templates | Device: Machine 3 | ✓ Cleared templates
... (tiếp tục với các devices còn lại)

================================================================================
LEFT EMPLOYEE CLEANUP COMPLETED
Total: 2 | Success: 2 | Failed: 0 | Time: 18.45s
================================================================================

[SUCCESS] Left employee cleanup completed successfully!
```

### Log Format Mới (Per-Device)
```
Format: [Employee] - [Name] (ID: [DeviceID]) | Relieving: [Date] | Action: [Type] | Device: [DeviceName] | [Result]

Ví dụ:
TIQN-0108 - Hồ Thị Trầm (ID: 118) | Relieving: 2025-03-20 | Action: Permanently delete user | Device: Machine 1 | ✓ Deleted
TIQN-0025 - Nguyễn Văn A (ID: 201) | Relieving: 2025-06-15 | Action: Clear templates | Device: Machine 2 | ✓ Cleared templates
TIQN-0025 - Nguyễn Văn A (ID: 201) | Relieving: 2025-06-15 | Action: Clear templates | Device: Machine 3 | • User not found on device

Kết quả có thể:
✓ Deleted               - Đã xóa vĩnh viễn thành công
✓ Cleared templates     - Đã xóa template thành công
• User not found        - Không tìm thấy user (đã xử lý trước đó)
✗ Device unreachable    - Không kết nối được thiết bị
✗ Connection failed     - Kết nối thất bại
```

### Trường hợp không có nhân viên Left
```bash
$ ./clean_data_employee_left.sh

[INFO] Starting Left Employee Data Cleanup
================================================================================
STARTING LEFT EMPLOYEE DATA CLEANUP
================================================================================
2025-08-20 23:00:05 - INFO - ERPNext API connection successful
2025-08-20 23:00:06 - INFO - No Left employees found ready for cleanup
================================================================================
LEFT EMPLOYEE CLEANUP COMPLETED
Total execution time: 1.23 seconds
================================================================================
[SUCCESS] Left employee cleanup completed successfully!
```

## Cron Job Setup

### Chạy hàng ngày lúc 23:00
```bash
# Mở crontab
crontab -e

# Thêm dòng này
0 23 * * * cd /path/to/biometric-attendance-sync-tool && ./clean_data_employee_left.sh >/dev/null 2>&1
```

### Các option khác
```bash
# Chạy hàng tuần (Chủ nhật 23:00)
0 23 * * 0 cd /path/to/biometric-attendance-sync-tool && ./clean_data_employee_left.sh >/dev/null 2>&1

# Chạy cuối tháng (ngày 28, 23:00)
0 23 28 * * cd /path/to/biometric-attendance-sync-tool && ./clean_data_employee_left.sh >/dev/null 2>&1

# Chạy với email thông báo
0 23 * * * cd /path/to/biometric-attendance-sync-tool && ./clean_data_employee_left.sh
```

### Xóa cron job
```bash
# Mở crontab
crontab -e

# Xóa hoặc comment dòng cleanup
# 0 23 * * * cd /path/to/biometric-attendance-sync-tool && ./clean_data_employee_left.sh >/dev/null 2>&1

# Hoặc xóa toàn bộ crontab
crontab -r
```

## Kiểm tra và Debug

### Xem log
```bash
# Xem log realtime
tail -f logs/clean_data_employee_left/clean_left_employees.log

# Xem log của lần chạy cuối
tail -n 50 logs/clean_data_employee_left/clean_left_employees.log

# Tìm lỗi
grep "ERROR" logs/clean_data_employee_left/clean_left_employees.log
```

### Kiểm tra cron job
```bash
# Xem cron jobs hiện tại
crontab -l

# Xem log cron system
tail -f /var/log/cron
# Hoặc
journalctl -f -u cron
```

### Test thủ công
```bash
# Test dry run
./clean_data_employee_left.sh --dry-run

# Test ERPNext connection
python3 -c "
from erpnext_api_client import ERPNextAPIClient
import local_config
client = ERPNextAPIClient(local_config.ERPNEXT_URL, local_config.ERPNEXT_API_KEY, local_config.ERPNEXT_API_SECRET)
print('Connection:', client.test_connection())
print('Left employees:', len(client.get_left_employees_with_device_id()))
"

# Test device connections
python3 -c "
import local_config
import socket
for device in local_config.devices:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((device['ip'], 4370))
        sock.close()
        print(f'{device[\"device_id\"]}: {\"OK\" if result == 0 else \"FAIL\"}')
    except Exception as e:
        print(f'{device[\"device_id\"]}: ERROR - {e}')
"
```

## Troubleshooting

### Lỗi thường gặp

#### 1. ERPNext API connection failed
```bash
# Kiểm tra config
cat local_config.py | grep -E "(ERPNEXT_URL|API_KEY|API_SECRET)"

# Test connection
python3 -c "from erpnext_api_client import ERPNextAPIClient; import local_config; print(ERPNextAPIClient(local_config.ERPNEXT_URL, local_config.ERPNEXT_API_KEY, local_config.ERPNEXT_API_SECRET).test_connection())"
```

#### 2. Device connection failed
```bash
# Ping test
for ip in 10.0.1.48 10.0.1.50; do ping -c 1 $ip; done

# Port test
for ip in 10.0.1.48 10.0.1.50; do nc -zv $ip 4370; done
```

#### 3. Permission denied
```bash
# Fix permissions
chmod +x clean_data_employee_left.sh
chmod +r local_config.py
```

#### 4. Python/venv not found
```bash
# Check paths
ls -la venv/bin/python3
which python3

# Recreate venv if needed
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Safety Features

#### Date Validation
- Chỉ xử lý nhân viên có `current_date > relieving_date`
- Bỏ qua nhân viên chưa đến ngày nghỉ việc
- Bỏ qua nhân viên không có `relieving_date`

#### Error Handling
- Lỗi 1 nhân viên không ảnh hưởng nhân viên khác
- Lỗi 1 máy không ảnh hưởng máy khác
- Log chi tiết mọi lỗi để debug

#### User ID Preservation
- Chỉ xóa fingerprint templates
- Giữ lại user_id trên máy chấm công
- Không ảnh hưởng attendance history

## Monitoring và Maintenance

### Weekly Check
```bash
# Kiểm tra hàng tuần
echo "=== Weekly Left Employee Cleanup Check ==="
echo "Last cleanup time:"
stat logs/clean_data_employee_left/clean_left_employees.log | grep Modify

echo "Recent cleanup summary:"
grep -E "(CLEANUP COMPLETED|Total Left employees)" logs/clean_data_employee_left/clean_left_employees.log | tail -5

echo "Recent errors:"
grep "ERROR" logs/clean_data_employee_left/clean_left_employees.log | tail -3
```

### Log Rotation
```bash
# Script tự động xoay log (tạo file rotate_cleanup_logs.sh)
#!/bin/bash
LOG_FILE="/path/to/logs/clean_data_employee_left/clean_left_employees.log"
if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE") -gt 10485760 ]; then
    mv "$LOG_FILE" "${LOG_FILE}.old"
    touch "$LOG_FILE"
fi
```

## Cải tiến phiên bản mới (v2.0)

### So sánh với phiên bản cũ

| Tính năng | Phiên bản cũ | Phiên bản mới (v2.0) |
|-----------|--------------|----------------------|
| **Xử lý thiết bị** | Song song (ThreadPoolExecutor) | Tuần tự (Sequential) |
| **Log format** | 1 dòng tổng hợp | 1 dòng per device |
| **JSON tracking** | Ghi nhiều lần (7 lần/employee) | Ghi 1 lần duy nhất |
| **Race condition** | Có thể xảy ra | Hoàn toàn an toàn |
| **Debug** | Khó xác định device nào lỗi | Rõ ràng từng device |
| **Chế độ xóa** | Chỉ có Clear templates | 2 chế độ (Clear + Permanently Delete) |
| **Ưu tiên xử lý** | Không có | Priority-based (Delete trước) |
| **File corruption** | Có thể xảy ra | Atomic write, an toàn |

### Lợi ích của Sequential Processing

1. **Stability**: Không còn race condition, file corruption
2. **Visibility**: Log chi tiết từng device, dễ debug
3. **Reliability**: Ghi JSON 1 lần, đảm bảo dữ liệu chính xác
4. **Maintainability**: Code đơn giản hơn, dễ bảo trì
5. **Trade-off**: Chậm hơn một chút nhưng đáng tin cậy hơn nhiều

### Performance Impact

```
7 devices × 1s/device = ~7-10 giây/employee (tuần tự)
vs
~2-3 giây/employee (song song nhưng có thể lỗi)

Đánh đổi hợp lý: Chậm hơn ~5-7 giây nhưng an toàn 100%
```

## Kết luận

Tool `clean_data_employee_left` v2.0 cung cấp giải pháp hoàn chỉnh và an toàn để dọn dẹp dữ liệu nhân viên nghỉ việc:

- ✅ **Tự động hóa**: Chạy cron job hàng ngày (tích hợp trong erpnext_sync_all.py)
- ✅ **An toàn tuyệt đối**: Sequential processing, atomic write, no race condition
- ✅ **2 chế độ xóa linh hoạt**: Clear templates (30 ngày) → Permanently delete (60 ngày)
- ✅ **Tracking thông minh**: JSON file tránh xử lý lặp
- ✅ **Toàn diện**: Dọn cả ERPNext và devices
- ✅ **Audit Trail chi tiết**: Log từng device, dễ debug
- ✅ **Flexible**: Có thể chạy thủ công khi cần

**Khuyến nghị**:
- Sử dụng cấu hình mặc định: 30 ngày (Clear) → 60 ngày (Delete)
- Để `ENABLE_CLEAR_LEFT_USER_TEMPLATES_ON_ERPNEXT = False` (bảo toàn lịch sử)
- Kiểm tra log định kỳ: `tail -f logs/clean_data_employee_left/clean_left_employees.log`
- Review tracking file: `cat logs/clean_data_employee_left/processed_left_employees.json`