# Tài liệu: Sync Attendance Log từ MongoDB sang ERPNext

## 📋 Tổng quan

Script Python đồng bộ dữ liệu chấm công từ MongoDB collection `AttLog` sang ERPNext Employee Checkin.

**File:** `sync_log_from_mongodb_to_erpnext.py`

---

## 🎯 Mục đích

Đồng bộ dữ liệu chấm công từ hệ thống máy chấm công (lưu trong MongoDB) sang ERPNext để tạo Employee Checkin records.

---

## ⚙️ Cấu hình

### 1. MongoDB Connection
```python
MONGODB_HOST = "10.0.1.4"
MONGODB_PORT = 27017
MONGODB_DB = "tiqn"
MONGODB_COLLECTION = "AttLog"
```

### 2. ERPNext Connection
- URL, API Key, API Secret: Lấy từ `local_config.py`
- Tự động detect version (ERPNext 13 hoặc 14+)
- Endpoint:
  - ERPNext >= 14: `hrms.hr.doctype.employee_checkin.employee_checkin.add_log_based_on_employee_field`
  - ERPNext 13: `erpnext.hr.doctype.employee_checkin.employee_checkin.add_log_based_on_employee_field`

### 3. Performance Settings
```python
MAX_WORKERS = 100  # Số luồng xử lý song song
```

### 4. Cấu hình từ `local_config.py`
- `sync_log_from_mongodb_to_erpnext_date_range`: Khoảng ngày cần sync (format: `["YYYYMMDD", "YYYYMMDD"]`)
- `user_id_ignored`: Danh sách user ID bỏ qua (không sync)
- `sync_only_machines_0`: Chỉ sync từ machine số 0 (default: True)

---

## 🔄 Luồng xử lý

### 1. **Kết nối MongoDB**
```
connect_to_mongodb()
├─ Kết nối tới MongoDB server
├─ Test ping connection
└─ Return client object
```

### 2. **Xác định khoảng thời gian sync**

**Trường hợp 1:** Có cấu hình `sync_log_from_mongodb_to_erpnext_date_range`
```python
# Ví dụ: ["20251001", "20251005"]
start_date = 2025-10-01 00:00:00 UTC
end_date = 2025-10-05 23:59:59 UTC
```

**Trường hợp 2:** Không có cấu hình (default)
```python
# Sync 2 ngày: hôm qua + hôm nay
previous_date = yesterday 00:00:00 UTC
end_date = today 23:59:59 UTC
```

### 3. **Query MongoDB**
```javascript
query = {
    "timestamp": {
        "$gte": start_date,
        "$lte": end_date
    },
    "machineNo": 0  // Nếu sync_only_machines_0 = True
}

// Chỉ lấy các field cần thiết
projection = {
    "attFingerId": 1,
    "timestamp": 1,
    "machineNo": 1
}
```

### 4. **Map Machine Number → Device ID**
```python
machineNo 1-7 → "Machine 1", "Machine 2", ..., "Machine 7"
machineNo khác → None
```

### 5. **Xử lý song song với ThreadPoolExecutor**
```
┌─────────────────────────────────────┐
│   100 Worker Threads Parallel       │
├─────────────────────────────────────┤
│ Worker 1: Process record 1          │
│ Worker 2: Process record 2          │
│ ...                                 │
│ Worker 100: Process record 100      │
└─────────────────────────────────────┘
         ↓
   Send to ERPNext API
         ↓
   ┌────────────────┐
   │ Status Code    │
   ├────────────────┤
   │ 200 → processed│
   │ Duplicate → skipped
   │ Other → error  │
   └────────────────┘
```

### 6. **Logic xử lý mỗi record**
```python
def process_record(record, user_id_ignored):
    # Skip nếu:
    # 1. Không có attFingerId hoặc timestamp
    # 2. attFingerId nằm trong danh sách ignored
    if not att_finger_id or not timestamp or str(att_finger_id) in user_id_ignored:
        return 'skipped'

    # Map device_id
    device_id = map_machine_no_to_device_id(machineNo)

    # Send to ERPNext
    status_code, response = send_to_erpnext(att_finger_id, timestamp, device_id)

    # Classify result
    if status_code == 200:
        return 'processed'
    elif "already has a log" in response:
        return 'skipped'  # Duplicate
    else:
        return 'error'
```

---

## 📊 Kết quả sync

### Output Format
```json
{
    "processed": 150,      // Số record tạo thành công
    "skipped": 25,         // Số record bỏ qua (duplicate hoặc ignored)
    "errors": 5,           // Số record lỗi
    "total_records": 180   // Tổng số record
}
```

### Console Output Example
```
📅 Syncing date range: 20251001 to 20251005
🔍 Filter: Only machineNo = 0
🚫 Ignored user IDs: ['123', '456']
📊 Total records: 180
🚀 Processing with 100 parallel workers...

=== MongoDB to ERPNext Sync Results ===
Total records found: 180
Successfully processed: 150
Skipped: 25
Errors: 5
=== Sync Complete ===
```

---

## 🚀 Tối ưu hiệu suất

### 1. **Connection Pooling**
- Sử dụng `requests.Session()` global
- Pool size = MAX_WORKERS (100 connections)
- Retry logic: 2 lần

### 2. **MongoDB Indexing**
```python
# Tự động tạo index (nếu chưa có)
collection.create_index([("timestamp", -1), ("machineNo", 1)])
collection.create_index([("attFingerId", 1)])
```

### 3. **Parallel Processing**
- ThreadPoolExecutor với 100 workers
- Xử lý song song tối đa 100 records cùng lúc
- Tốc độ: ~1000-2000 records/phút (tùy network)

### 4. **Projection Query**
- Chỉ lấy 3 fields cần thiết: `attFingerId`, `timestamp`, `machineNo`
- Giảm băng thông MongoDB

---

## 🔧 Cách sử dụng

### 1. Chạy standalone
```bash
cd /home/frappe/frappe-bench/apps/biometric-attendance-sync-tool
python3 sync_log_from_mongodb_to_erpnext.py
```

### 2. Import vào script khác
```python
from sync_log_from_mongodb_to_erpnext import run_mongodb_sync

result = run_mongodb_sync()
if result['success']:
    print(f"Sync OK: {result['message']}")
else:
    print(f"Sync failed: {result['message']}")
```

---

## 📝 Logging

### File log
```
/home/frappe/frappe-bench/apps/biometric-attendance-sync-tool/sync_log_from_mongodb_to_erpnext.txt
```

### Log format
```
2025-10-06 10:30:00 - INFO - Successfully connected to MongoDB at 10.0.1.4
2025-10-06 10:30:01 - INFO - Syncing date range: 20251001 to 20251005
2025-10-06 10:30:02 - INFO - Found 180 records to process
2025-10-06 10:30:15 - INFO - Sync completed: 150 processed, 25 skipped, 5 errors
```

---

## ⚠️ Lưu ý

### 1. **Validation**
- Script **KHÔNG** validate dữ liệu
- Gửi trực tiếp sang ERPNext API
- ERPNext sẽ validate:
  - Employee tồn tại (dựa vào `attendance_device_id`)
  - Timestamp hợp lệ
  - Không duplicate

### 2. **Duplicate handling**
- ERPNext tự động reject nếu đã có log với cùng timestamp
- Script classify là "skipped"
- Không throw error

### 3. **Error handling**
- MongoDB connection error → raise exception, dừng script
- ERPNext API error → count vào `errors`, tiếp tục xử lý records khác
- Network timeout → retry 2 lần (HTTPAdapter config)

### 4. **Memory usage**
- Load tất cả records vào memory trước khi xử lý
- Nếu có hàng triệu records → cần cải tiến với batch processing
- Hiện tại: OK với <100k records

---

## 🔗 Tích hợp

Script này được gọi từ `erpnext_sync_all.py` để tích hợp vào luồng sync tổng thể.

```python
# Trong erpnext_sync_all.py
from sync_log_from_mongodb_to_erpnext import run_mongodb_sync

# Run MongoDB sync
mongodb_result = run_mongodb_sync()
```

---

## 📌 Dependencies

```python
- pymongo           # MongoDB driver
- requests          # HTTP client
- concurrent.futures # Parallel processing
- datetime          # Date/time handling
- logging           # Logging
- local_config.py   # Configuration
```

---

## 🎛️ Ví dụ cấu hình trong `local_config.py`

```python
# Sync từ 1/10/2025 đến 5/10/2025
sync_log_from_mongodb_to_erpnext_date_range = ["20251001", "20251005"]

# Bỏ qua user ID 123 và 456
user_id_ignored = ["123", "456"]

# Chỉ sync machine số 0
sync_only_machines_0 = True

# ERPNext connection
ERPNEXT_URL = "https://erp.tiqn.local"
ERPNEXT_API_KEY = "your_api_key"
ERPNEXT_API_SECRET = "your_api_secret"
ERPNEXT_VERSION = 14
```
