# 🔄 Thuật Toán Sync From ERPNext To Device - Tóm Tắt

## 📋 Thuật Toán Chính

### 1. **Phân Loại Employee Thông Minh**
```
FOR EACH changed_employee:
    IF employee.status == 'Left' AND current_date > relieving_date THEN
        classification = "LEFT_CLEANUP"
        → Xóa fingerprints trên ERPNext + Xóa templates trên thiết bị
        
    ELSE IF employee.modified > since_datetime THEN
        fingerprint_count = get_employee_fingerprint_count(employee_id)
        
        IF fingerprint_count <= 0 THEN
            classification = "CLEAR_ALL_FINGERPRINTS"
            → Xóa tất cả fingerprints trên thiết bị
        ELSE
            classification = "SELECTIVE_SYNC"
            → Đồng bộ chính xác: xóa fingers đã xóa, thêm/cập nhật fingers mới
        END IF
    ELSE
        classification = "SKIP"
    END IF
END FOR
```

### 2. **Xử Lý Theo Classification**

#### **LEFT_CLEANUP** - Nhân viên nghỉ việc
- **Bước 1**: Xóa fingerprints khỏi ERPNext
- **Bước 2**: Xóa tất cả templates trên các thiết bị (song song)
- **Phương pháp**: `conn.delete_user_template(user.uid, finger_index)` cho tất cả 10 ngón tay

#### **CLEAR_ALL_FINGERPRINTS** - Xóa hết fingerprints
- Nhân viên không còn fingerprints nào trên ERPNext
- **Phương pháp**: Xóa từng finger từ 0-9 trên tất cả thiết bị

#### **SELECTIVE_SYNC** - Đồng bộ chọn lọc
- **Bước 1**: Lấy danh sách fingers hiện tại từ ERPNext
- **Bước 2**: Xóa fingers không còn tồn tại (device_fingers - erpnext_fingers)
- **Bước 3**: Cập nhật fingers từ ERPNext
- **Phương pháp**: `conn.save_user_template(user, templates_to_send)`

## 💡 Ví Dụ Thực Tế

### **Test Case 1: SELECTIVE_SYNC**
```
Employee: 1662 TIQN-1604 Triệu Thị Vân
- ERPNext: 1 fingerprint (finger_index = 2)
- Device: 10 fingers (0,1,2,3,4,5,6,7,8,9)
- Kết quả: 1 synced, 9 cleared
- Log: ✓ Selective sync for 1662 TIQN-1604 on device Machine_8: 1 synced, 9 cleared
```

### **Test Case 2: CLEAR_ALL**
```
Employee: 154 TIQN-0148 Nguyễn Thái Sơn
- ERPNext: 0 fingerprints
- Device: Có user_id 154
- Kết quả: Xóa tất cả fingerprints
- Log: ✓ Cleared all fingerprints for 154 TIQN-0148 on device Machine_8
```

### **Test Case 3: LEFT_CLEANUP**
```
Employee: 1649 TIQN-1591 Phan Quyn Son
- Status: Left, relieving_date: 2025-08-20 (< today)
- Kết quả: ERPNext cleanup + Device template clearing
- Log: ERPNext cleanup for TIQN-1591: Successfully deleted 1 fingerprint records
       ✓ Cleared all fingerprints for 1649 TIQN-1591 on device Machine_10
```
## Cấu trúc files
```
biometric-attendance-sync-tool/
├── sync_from_erpnext_to_device.py       # Logic đồng bộ chính
├── sync_from_erpnext_to_device.sh       # 
├── erpnext_api_client.py                 # ERPNext API client 
├── local_config.py                       # Cấu hình
└── logs/sync_from_erpnext_to_device/
    ├── sync_to_device.log                # Log chính
    ├── last_sync_global.json             # Trạng thái sync toàn cục
    ├── last_sync_machine_8.json          # Trạng thái sync máy 8
    ├── last_sync_machine_10.json         # Trạng thái sync máy 10
    └── ...
```

## Cách hoạt động

### Lần đầu chạy (Full Sync)
```
1. Kiểm tra last_sync_global.json
2. Không có → Chế độ FULL SYNC
3. Đồng bộ tất cả nhân viên Active có vân tay
4. Xóa vân tay nhân viên Left (nếu quá ngày nghỉ việc)
5. Lưu 
## 🚀 Cách Sử Dụng

### **1. Chạy Script**
```bash
# Chạy sync tự động
./sync_from_erpnext_to_device.sh

# Hoặc chạy trực tiếp Python
/venv/bin/python3 sync_from_erpnext_to_device.py
```

### **2. Logs và Monitoring**
```bash
File : apps/biometric-attendance-sync-tool/logs/sync_from_erpnext_to_device/last_sync_global.json
{
  "last_sync": "2025-08-22 13:12:35",
  "updated_at": "2025-08-22 13:12:35"
}
# Xem logs real-time
tail -f logs/sync_from_erpnext_to_device/sync_to_device.log

# Kiểm tra last sync timestamp
cat logs/sync_from_erpnext_to_device/last_sync_global.json

# Xóa file last_sync_global.json để force sync all 
# Edit file last_sync_global.json để  chạy theo thời gian mong muốn
```

### **3. Kết Quả Mong Đợi**
```
2025-08-22 13:10:41 - Employee 1649 TIQN-1591 Phan Quyn Son marked for CLEAR_ALL (no fingerprints)
2025-08-22 13:10:41 - Employee 1663 TIQN-1605 Lê Thị Bích Thảo marked for SELECTIVE_SYNC (1 fingerprints)
2025-08-22 13:10:43 - ✓ Selective sync for 1663 TIQN-1605 on device Machine_10: 1 synced, 9 cleared
2025-08-22 13:10:46 - ✓ Cleared all fingerprints for 1649 TIQN-1591 on device Machine_8
2025-08-22 13:10:46 - SMART CHANGED SYNC COMPLETED
2025-08-22 13:10:46 - Total changed employees: 2, Successful devices: 2/2, Total operations: 4
```

## ⚙️ Cấu Hình Quan Trọng

### **local_config.py**
```python
devices = [
    {'device_id':'Machine_8','ip':'10.0.1.48'},
    {'device_id':'Machine_10','ip':'10.0.1.50'}
]

SERVER_NAME = '10.0.1.21'
ERPNEXT_API_KEY = '7c5bab33922d7f6'
ERPNEXT_API_SECRET = '2d379dbe1ef33ab'
```

### **ERPNext Employee Fields**
- `attendance_device_id`: User ID trên thiết bị chấm công
- `custom_fingerprints`: Child table chứa fingerprint data
- `status`: Active/Left
- `relieving_date`: Ngày nghỉ việc (cho LEFT classification)

## 🎯 Lợi Ích

1. **Đồng Bộ Thông Minh**: Chỉ xử lý employees có thay đổi
2. **Xử Lý Đầy Đủ**: Add/Edit/Delete fingerprints và LEFT cleanup
3. **Hiệu Suất Cao**: Xử lý song song nhiều thiết bị
4. **Logs Chi Tiết**: Theo dõi từng operation một cách rõ ràng
5. **Fault Tolerant**: Xử lý lỗi API, kết nối thiết bị gracefully
6. **Production Ready**: Đã test với dữ liệu thực tế, success rate 100%

## ✅ Checklist Triển Khai

- ✅ **Algorithm Correctness**: Tất cả classification cases hoạt động đúng
- ✅ **Error Resilience**: Xử lý lỗi API/thiết bị gracefully  
- ✅ **Performance**: Thời gian thực hiện < 10 giây cho multiple operations
- ✅ **Logging**: Logs comprehensive, dễ đọc với thông tin employee
- ✅ **Data Integrity**: Không có orphaned data, cleanup sequences đúng
- ✅ **Scalability**: Xử lý song song nhiều thiết bị
- ✅ **Maintainability**: Cấu trúc code rõ ràng với classification logic 