# Clean Data Employee Left - Dọn dẹp dữ liệu nhân viên nghỉ việc

## Mô tả
Tool dọn dẹp dữ liệu hoàn chỉnh cho nhân viên có trạng thái "Left". **Tự động xử lý an toàn** - chỉ dọn dẹp nhân viên đã quá ngày nghỉ việc.

## Thuật toán hoạt động

### Quy trình dọn dẹp
```
1. KIỂM TRA KẾT NỐI
   ├── Kết nối ERPNext API
   └── Kết nối các máy chấm công

2. TÌM NHÂN VIÊN LEFT
   ├── Query: status = "Left" AND attendance_device_id != ""
   ├── Lọc: current_date > relieving_date
   └── Kết quả: Danh sách nhân viên cần dọn dẹp

3. XỬ LÝ TỪNG NHÂN VIÊN
   ├── Bước 1: Xóa fingerprints trên ERPNext
   │   ├── Lấy danh sách custom_fingerprints
   │   ├── DELETE /api/resource/Fingerprint Data/{record_id}
   │   └── Ghi log kết quả
   │
   ├── Bước 2: Xóa templates trên devices (song song)
   │   ├── Kết nối từng máy chấm công
   │   ├── Kiểm tra user_id tồn tại
   │   ├── Xóa templates (giữ lại user_id)
   │   └── Ghi log kết quả
   │
   └── Bước 3: Tổng hợp kết quả
       ├── ERPNext success + Device success = Hoàn thành
       ├── ERPNext success only = Đã dọn ERPNext
       ├── Device success only = Đã dọn Device
       └── Cả hai thất bại = Thất bại

4. BÁO CÁO KẾT QUẢ
   ├── Tổng số nhân viên xử lý
   ├── Số thành công/thất bại
   ├── Thời gian thực thi
   └── Chi tiết từng trường hợp
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

- ✅ **Date Validation**: Chỉ dọn dẹp sau ngày nghỉ việc
- ✅ **Dual System Cleanup**: Xóa cả ERPNext và devices
- ✅ **Safe User ID**: Giữ lại user_id trên máy (cho attendance history)
- ✅ **Parallel Processing**: Xử lý nhiều máy đồng thời
- ✅ **Complete Audit**: Log chi tiết mọi thao tác
- ✅ **Error Recovery**: Xử lý lỗi và tiếp tục với nhân viên khác
- ✅ **Dry Run Mode**: Xem trước không thay đổi dữ liệu

## Cấu trúc files

```
biometric-attendance-sync-tool/
├── clean_data_employee_left.py          # Script chính
├── clean_data_employee_left.sh          # Shell wrapper
├── clean_data_employee_left.md          # Documentation này
├── erpnext_api_client.py                # ERPNext API (có delete method)
├── local_config.py                      # Cấu hình
└── logs/clean_data_employee_left/
    └── clean_left_employees.log         # Log dọn dẹp
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
2025-08-20 23:00:16 - INFO - Found 3 Left employees ready for cleanup
2025-08-20 23:00:16 - INFO - Starting cleanup process...

[1/3] Processing EMP-001...
2025-08-20 23:00:17 - INFO - Processing complete cleanup for Nguyen Van A (ID: 1001)
2025-08-20 23:00:17 - INFO -   Step 1: Deleting ERPNext fingerprints for EMP-001
2025-08-20 23:00:18 - INFO -     ✓ ERPNext: Deleted 3 fingerprint records
2025-08-20 23:00:18 - INFO -   Step 2: Clearing device templates for EMP-001
2025-08-20 23:00:19 - INFO -     ✓ Machine_8: Cleared templates
2025-08-20 23:00:19 - INFO -     ✓ Machine_10: Cleared templates
2025-08-20 23:00:19 - INFO -     • Machine_12: User not found (already cleared)
2025-08-20 23:00:19 - INFO -     ✓ Machine_14: Cleared templates
2025-08-20 23:00:19 - INFO -   ✓ Complete cleanup for EMP-001: Complete cleanup successful (ERPNext + devices)

[2/3] Processing EMP-002...
... (similar output)

[3/3] Processing EMP-003...
... (similar output)

================================================================================
LEFT EMPLOYEE CLEANUP COMPLETED
Total Left employees processed: 3
Successful cleanups: 3
Failed cleanups: 0
Total execution time: 15.67 seconds
================================================================================

Successful cleanups:
  ✓ EMP-001: Complete cleanup successful (ERPNext + devices)
  ✓ EMP-002: Complete cleanup successful (ERPNext + devices)
  ✓ EMP-003: ERPNext cleanup successful, devices already clean

[SUCCESS] Left employee cleanup completed successfully!
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

## Kết luận

Tool `clean_data_employee_left` cung cấp giải pháp hoàn chỉnh và an toàn để dọn dẹp dữ liệu nhân viên nghỉ việc:

- ✅ **Tự động hóa**: Chạy cron job hàng ngày
- ✅ **An toàn**: Validation date, dry run, error handling
- ✅ **Toàn diện**: Dọn cả ERPNext và devices
- ✅ **Audit Trail**: Log chi tiết mọi thao tác
- ✅ **Flexible**: Có thể chạy thủ công khi cần

**Khuyến nghị**: Chạy cron job hàng ngày lúc 23:00 để tự động dọn dẹp nhân viên Left.