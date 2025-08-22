# Sync From Master Device To ERPNext

Đồng bộ dữ liệu vân tay từ thiết bị master lên ERPNext, lưu vào custom_fingerprints child table.

## 📋 Mô tả chức năng

Hệ thống này đọc tất cả user và dữ liệu vân tay từ thiết bị master, tìm employee tương ứng trong ERPNext theo `attendance_device_id` (chỉ Active employees), và lưu fingerprint templates vào `custom_fingerprints` child table.

### ⚡ Tính năng chính:
- ✅ **Đọc từ Master Device**: Scan tất cả users và fingerprints từ thiết bị master  
- ✅ **ERPNext API Client**: Sử dụng erpnext_api_client để chuẩn hóa API calls
- ✅ **Active Employee Only**: Chỉ sync vào employees có trạng thái Active
- ✅ **Template Storage**: Lưu vào custom_fingerprints child table với cấu trúc chuẩn
- ✅ **Finger Name Mapping**: Map finger_index thành finger_name (Left Thumb, Right Index, etc.)
- ✅ **Enhanced Data Validation**: Chỉ lưu templates hợp lệ, bỏ qua templates rỗng hoặc không hợp lệ
- ✅ **Progress Tracking**: Hiển thị tiến độ và kết quả chi tiết
- ✅ **Comprehensive Logging**: Log chi tiết với shell script wrapper

## 🗂️ Files liên quan

```
biometric-attendance-sync-tool/
├── sync_from_master_device_to_erpnext.py        # Core sync script
├── sync_from_master_device_to_erpnext.sh        # Shell script với logging  
├── erpnext_api_client.py                        # ERPNext API Client
├── sync_from_erpnext_to_device.py              # Script tích hợp (có --mode from-device)
├── local_config.py                              # Configuration
├── venv/                                        # Virtual environment (required)
│   ├── bin/python                               # Python binary
│   └── lib/python*/site-packages/               # Installed packages
└── logs/                                        # Log directory
    └── sync_from_master_device_to_erpnext/      # Sync-specific log folder
        ├── sync_master_device_to_erpnext.log        # Main log
        └── sync_master_device_to_erpnext_error.log  # Error log
```

## ⚙️ Thiết lập môi trường

### 1. Tạo Virtual Environment (Bắt buộc)

```bash
# Tạo virtual environment
python3 -m venv venv

# Kích hoạt virtual environment
source venv/bin/activate  # Linux/macOS
# hoặc: venv\Scripts\activate  # Windows

# Cài đặt các packages cần thiết
pip install pyzk requests

# Kiểm tra cài đặt
python -c "import pyzk, requests; print('All packages installed successfully')"
```

### 2. Cấu hình

#### local_config.py
```python
# ERPNext connection
ERPNEXT_URL = "http://10.0.1.21"
ERPNEXT_API_KEY = "your-api-key"
ERPNEXT_API_SECRET = "your-api-secret"

# Master device - nguồn dữ liệu vân tay
devices_master = {
    'device_id': 'Machine_8',
    'ip': '10.0.1.48',
    'punch_direction': None,
    'clear_from_device_on_fetch': False
}
```

### ERPNext Employee Structure
```
Employee doctype cần có:
- status: Must be "Active" (chỉ sync vào Active employees)
- attendance_device_id: Matching với user_id trên device
- custom_fingerprints: Child table với structure:
  * finger_index: 0-9
  * finger_name: Left Thumb, Right Index, etc.
  * template_data: Base64 encoded fingerprint template (skip nếu rỗng)
  * quality_score: Mặc định là 0
```

## 🚀 Cách sử dụng

### 1. Shell Script (Khuyến khích)

**Lưu ý**: Shell script tự động sử dụng virtual environment `./venv`

```bash
# Sync tất cả users từ master device lên ERPNext (chỉ Active employees)
./sync_from_master_device_to_erpnext.sh

# Sync với verbose output
./sync_from_master_device_to_erpnext.sh -v

# Sync với giới hạn số users (testing)
./sync_from_master_device_to_erpnext.sh --limit 10

# Test connectivity đến master device và ERPNext
./sync_from_master_device_to_erpnext.sh test

# Xem trạng thái sync
./sync_from_master_device_to_erpnext.sh status
```

### 2. Python Script trực tiếp

```bash
# Kích hoạt virtual environment trước
source venv/bin/activate

# Sync tất cả users
python sync_from_master_device_to_erpnext.py

# Sync với giới hạn
python sync_from_master_device_to_erpnext.py --limit 5

# Hoặc chạy trực tiếp với venv (không cần activate)
venv/bin/python sync_from_master_device_to_erpnext.py
```

### 3. Script tích hợp

```bash
# Sử dụng script tích hợp với mode from-device
python sync_from_erpnext_to_device.py --mode from-device
```

## 📊 Quy trình xử lý

### 1. Đọc dữ liệu từ Master Device
```
🔍 Reading all users from master device...
Master: Machine_8 (10.0.1.48)
👥 Found 901 total users on master device
  Progress: 0/901
  ✅ 161: Truong Thi My Hoa (4 fingerprints)
  ✅ 295: Nguyen Thi Thuong (2 fingerprints)
📊 Found 200+ users with fingerprints
```

### 2. Matching và lưu vào ERPNext
```
📤 Syncing 200 users to ERPNext...
Progress: 1/200 - 161: Truong Thi My Hoa (4 fingerprints)
  ✅ Synced to ERPNext: TIQN-0161 - Truong Thi My Hoa (4 fingerprints)
Progress: 2/200 - 295: Nguyen Thi Thuong (2 fingerprints)
  ⚠️ Skipped: No active employee found with attendance_device_id: 295
```

### 3. Kết quả cuối cùng
```
🎯 SYNC SUMMARY - MASTER DEVICE TO ERPNEXT
Total users found on device: 200
Users processed: 200
Users successfully synced to ERPNext: 150
Users skipped (no matching active employee): 50
Success rate: 75.0%
⚠️ Partial success: 150/200 users synced
```

## 🗃️ Cấu trúc dữ liệu ERPNext

### Employee Document
```json
{
  "name": "EMP-0001",
  "employee": "TIQN-0161", 
  "employee_name": "Truong Thi My Hoa",
  "attendance_device_id": "161",
  "custom_fingerprints": [
    {
      "finger_index": 0,
      "finger_name": "Left Thumb",
      "template_data": "base64_encoded_template_data_here",
      "quality_score": 0
    },
    {
      "finger_index": 1,
      "finger_name": "Left Index", 
      "template_data": "base64_encoded_template_data_here",
      "quality_score": 0
    }
  ]
}
```

### Finger Name Mapping
```python
finger_names = {
    0: "Left Thumb",    1: "Left Index",     2: "Left Middle", 
    3: "Left Ring",     4: "Left Little",    5: "Right Thumb",
    6: "Right Index",   7: "Right Middle",   8: "Right Ring", 
    9: "Right Little"
}
```

## ⚡ Hiệu suất

### Thông số đo được:
- **Device Scan Speed**: ~2.4 users/second để detect fingerprints
- **ERPNext API Speed**: ~3-5 seconds/user để update employee
- **Success Rate**: 70-85% tùy số lượng employees có attendance_device_id
- **Total Time**: ~45-60 phút cho 200 users

### Bottlenecks:
- 🐌 **ERPNext API calls**: Mỗi employee cần 2 API calls (GET + PUT)
- 🐌 **Device scanning**: Phải quét từng finger (0-9) cho mỗi user
- 🐌 **Data validation**: Filter templates rỗng và không hợp lệ

## 🛠️ Xử lý lỗi

### Các lỗi phổ biến:

1. **Virtual environment not found**
   ```
   ERROR Virtual environment not found: ./venv
   ```
   - Tạo virtual environment: `python3 -m venv venv`
   - Cài packages: `venv/bin/pip install pyzk requests`

2. **Python modules not available**
   ```
   WARN Cannot verify Python modules availability in virtual environment
   ```
   - Cài đặt trong venv: `venv/bin/pip install pyzk requests`

3. **No active employee found with attendance_device_id**
   ```
   ⚠️ Skipped: No active employee found with attendance_device_id: 295
   ```
   - Employee chưa có attendance_device_id được set
   - Employee không có trạng thái "Active"
   - attendance_device_id không match với user_id trên device

4. **ERPNext API errors**
   ```bash
   # Test API connection
   ./sync_from_master_device_to_erpnext.sh test
   ```

5. **Device connection failed**
   ```
   ❌ Failed to connect to master device
   ```
   - Kiểm tra IP và port của master device
   - Firewall hoặc network issues

6. **Template save errors**
   ```
   Error: Failed to update employee: HTTP 500
   ```
   - ERPNext permissions issues
   - custom_fingerprints table chưa được tạo

### Debug mode:
```bash
# Chạy với verbose để xem chi tiết
./sync_from_master_device_to_erpnext.sh -v sync

# Test với 1 user
./sync_from_master_device_to_erpnext.sh --limit 1 -v sync

# Kiểm tra logs
tail -f logs/sync_from_master_device_to_erpnext/sync_master_device_to_erpnext.log
```

## 📋 ERPNext Setup Requirements

### 1. Custom Fields in Employee Doctype
```
attendance_device_id: Data field
custom_fingerprints: Table field
```

### 2. Child Table: Fingerprint Data
```
finger_index: Int
finger_name: Data  
template_data: Long Text
quality_score: Int
```

### 3. API Permissions
API User cần có quyền:
- Read Employee
- Write Employee
- Read/Write custom_fingerprints child table

### 4. API Keys
```python
# Tạo API Keys trong ERPNext
User → API Access → Generate Keys
ERPNEXT_API_KEY = "generated_key"
ERPNEXT_API_SECRET = "generated_secret"
```

## 🔒 Bảo mật

### Lưu ý quan trọng:
- ⚠️ **ERPNext credentials**: API key/secret trong local_config.py  
- ⚠️ **Fingerprint templates**: Transmitted as base64 over network
- ⚠️ **Employee data**: PII được truyền qua API calls
- ⚠️ **Data overwrite**: Script sẽ xóa existing fingerprints và tạo mới
- ⚠️ **Active employees only**: Chỉ sync vào employees có status="Active"

### Best practices:
- 🔐 Secure API credentials và config files
- 🔐 Use HTTPS for ERPNext API calls
- 🔐 Backup employee data trước khi sync
- 🔐 Monitor API access logs
- 🔐 Limit API user permissions

## 📞 Troubleshooting

### Kiểm tra ERPNext connection:
```bash
# Test API connectivity
curl -H "Authorization: token API_KEY:API_SECRET" \
     http://your-erpnext-server/api/method/frappe.auth.get_logged_user
```

### Kiểm tra Employee data:
```bash
# Kiểm tra employees có attendance_device_id
curl -H "Authorization: token API_KEY:API_SECRET" \
     "http://erpnext/api/resource/Employee?fields=[\"name\",\"attendance_device_id\"]&filters=[[\"attendance_device_id\",\"is\",\"set\"]]"
```

### Performance optimization:
- Batch API calls nếu có thể
- Implement caching cho employee lookups  
- Parallel processing cho multiple employees
- Use database connections thay vì API nếu có thể

## 🕐 Scheduling

### Cron job setup:
```bash
# Sync từ device lên ERPNext mỗi 4 giờ
0 */4 * * * /path/to/sync_from_master_device_to_erpnext.sh

# Sync vào lúc 4:00 AM mỗi ngày
0 4 * * * /path/to/sync_from_master_device_to_erpnext.sh
```

### Workflow integration:
```
Device Updates → Master Device Sync → ERPNext Update → Notification
```

---

## 📝 Changelog

### Version 1.1 (2025-01-21)
- ✅ **NEW**: Sử dụng erpnext_api_client thay vì requests trực tiếp
- ✅ **NEW**: Chỉ sync vào Active employees (status="Active")
- ✅ **NEW**: Logs được lưu vào folder riêng `logs/sync_from_master_device_to_erpnext/`
- ✅ **NEW**: Bắt buộc sử dụng virtual environment `./venv`
- ✅ **IMPROVED**: Enhanced data validation - skip empty/invalid templates
- ✅ **IMPROVED**: Better error messages về active employee requirements
- ✅ **IMPROVED**: API client hỗ trợ PUT/DELETE methods
- ✅ **IMPROVED**: Shell script tự động kiểm tra và sử dụng virtual environment

### Version 1.0 (2025-01-19)
- Initial release với basic sync functionality

---

**Lưu ý**: Đây là sync một chiều từ Master Device → ERPNext (Active employees only). Để sync ngược lại từ ERPNext → Devices, sử dụng các modes khác.

**Version**: 1.1  
**Last updated**: 2025-01-21