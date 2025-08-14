# Thuật Toán Đồng Bộ Dữ Liệu Chấm Công - ERPNext Sync

## Tổng Quan
Hệ thống đồng bộ dữ liệu chấm công từ máy chấm công ZKTeco sang ERPNext, chạy theo chu kỳ định kỳ và xử lý dữ liệu an toàn.

## Thuật Toán Chính

### 1. Hàm `infinite_loop()` - Vòng lặp chính
```
BẮT ĐẦU
  IN "Service Running..."
  LẶP VĨNH VIỄN:
    THỬ:
      GỌI main()
      NGỦ 15 giây (hoặc thời gian được cấu hình)
    BẮT LỖI:
      IN lỗi
      TIẾP TỤC vòng lặp
KẾT THÚC
```

### 2. Hàm `main()` - Xử lý chu kỳ đồng bộ
```
BẮT ĐẦU main():
  1. ĐỌC thời gian lift_off_timestamp cuối từ status.json
  
  2. KIỂM TRA điều kiện chạy:
     NẾU (chưa có timestamp HOẶC đã quá PULL_FREQUENCY phút):
       - CẬP NHẬT lift_off_timestamp = hiện tại
       - LƯU status.json
       - IN "Cleared for lift off!"
       
       3. XỬ LÝ TỪNG THIẾT BỊ:
          VỚI MỖI device trong config.devices:
            a) IN "Processing Device: [device_id]"
            b) TẠO tên file dump = "[device_id]_[ip]_last_fetch_dump.json"
            
            c) KIỂM TRA file dump tồn tại:
               NẾU có file dump:
                 - IN "Device Attendance Dump Found..."
                 - ĐỌC dữ liệu từ file dump
                 - CHUYỂN đổi timestamp
            
            d) THỬ xử lý thiết bị:
                 GỌI pull_process_and_push_data(device, dữ_liệu_dump)
                 NẾU THÀNH CÔNG:
                   - CẬP NHẬT [device_id]_push_timestamp = hiện tại
                   - LƯU status.json
                   - XÓA file dump (nếu có)
                   - IN "Successfully processed Device: [device_id]"
                 NẾU LỖI:
                   - GHI log lỗi
                   - GIỮ NGUYÊN file dump để retry sau
       
       4. CẬP NHẬT shift sync timestamp (nếu được cấu hình)
       5. CẬP NHẬT mission_accomplished_timestamp = hiện tại
       6. IN "Mission Accomplished!"
     
     NGƯỢC LẠI:
       - BỎ QUA chu kỳ này (chưa đủ thời gian)
       
  BẮT TẤT CẢ LỖI:
    GHI log lỗi vào error.log
KẾT THÚC main()
```

### 3. Hàm `pull_process_and_push_data()` - Xử lý dữ liệu thiết bị
```
BẮT ĐẦU pull_process_and_push_data(device, device_attendance_logs):
  1. TẠO logger cho success/failed riêng cho device
  
  2. LẤY DỮ LIỆU CHẤM CÔNG:
     NẾU không có device_attendance_logs:
       GỌI get_all_attendance_from_device()
       NẾU không có dữ liệu: THOÁT
  
  3. XÁC ĐỊNH VỊ TRÍ BẮT ĐẦU XỬ LÝ:
     a) ĐỌC dòng cuối của attendance_success_log
     b) LẤY import_start_date từ config
     c) TÌM index của bản ghi thành công cuối cùng
     d) SO SÁNH với import_start_date, lấy thời điểm muộn hơn
  
  4. XỬ LÝ TỪNG BẢN GHI (từ vị trí index_of_last+1):
     VỚI MỖI device_attendance_log:
       a) KIỂM TRA user_id có trong danh sách bỏ qua:
          NẾU user_id TRONG config.user_id_inorged:
            - GHI log vào user_id_inorged_log.txt
            - BỎ QUA bản ghi này (continue)
            - KHÔNG gửi sang ERPNext
       
       b) XÁC ĐỊNH hướng chấm công (IN/OUT/AUTO):
          NẾU punch_direction = 'AUTO':
            - KIỂM TRA punch value trong device_punch_values_OUT → 'OUT'
            - KIỂM TRA punch value trong device_punch_values_IN → 'IN'
            - KHÁC → None
       
       c) GỬI SANG ERPNext:
          GỌI send_to_erpnext(user_id, timestamp, device_id, punch_direction, tọa_độ)
          
          NẾU status_code = 200:
            - GHI success log: thông tin chi tiết bản ghi
          NGƯỢC LẠI:
            - KIỂM TRA loại lỗi:
              NẾU "This employee already has a log with the same timestamp":
                - GHI vào error_duplicate.log
              NGƯỢC LẠI:
                - GHI failed log: mã lỗi + thông tin chi tiết
            - KIỂM TRA lỗi có trong allowlisted_errors:
              NẾU KHÔNG: THROW Exception "API Call to ERPNext Failed"
              NẾU CÓ: TIẾP TỤC (bỏ qua lỗi)
KẾT THÚC
```

### 4. Hàm `get_all_attendance_from_device()` - Lấy dữ liệu từ máy chấm công
```
BẮT ĐẦU get_all_attendance_from_device(ip, port, timeout, device_id, clear_on_fetch):
  1. TẠO kết nối ZK(ip, port, timeout)
  
  2. THỬ KẾT NỐI:
     a) conn = zk.connect()
     b) TẮT thiết bị: conn.disable_device()
     c) LẤY dữ liệu: attendances = conn.get_attendance()
     d) IN số lượng bản ghi lấy được
     
     e) CẬP NHẬT status:
        - [device_id]_push_timestamp = None (reset)
        - [device_id]_pull_timestamp = hiện tại
        - LƯU status.json
     
     f) NẾU có dữ liệu:
        - TẠO file backup dump (phòng trường hợp crash)
        - GHI tất cả attendance vào file dump
        - NẾU clear_from_device_on_fetch = True:
          XÓA dữ liệu khỏi máy chấm công
     
     g) BẬT lại thiết bị: conn.enable_device()
  
  BẮT LỖI:
    - GHI log lỗi
    - THROW Exception "Device fetch failed"
  
  CUỐI CÙNG:
    - ĐÓNG kết nối nếu có
  
  TRẢ VỀ danh sách attendance (dict format)
KẾT THÚC
```

### 5. Hàm `send_to_erpnext()` - Gửi dữ liệu sang ERPNext
```
BẮT ĐẦU send_to_erpnext(employee_field_value, timestamp, device_id, log_type, tọa_độ):
  1. XÁC ĐỊNH endpoint:
     endpoint = "hrms" NẾU ERPNEXT_VERSION > 13 NGƯỢC LẠI "erpnext"
  
  2. TẠO URL API:
     url = "[ERPNEXT_URL]/api/method/[endpoint].hr.doctype.employee_checkin.employee_checkin.add_log_based_on_employee_field"
  
  3. TẠO headers với token authentication
  
  4. TẠO data payload:
     - employee_field_value
     - timestamp (string)
     - device_id
     - log_type (IN/OUT)
     - latitude, longitude (nếu có)
  
  5. GỬI POST request
  
  6. XỬ LÝ RESPONSE:
     NẾU status_code = 200:
       TRẢ VỀ (200, tên bản ghi được tạo)
     NGƯỢC LẠI:
       - PHÂN TÍCH chuỗi lỗi
       - NẾU lỗi "Employee not found":
         GHI error log với thông tin chi tiết
       - GHI error log chung
       - TRẢ VỀ (status_code, chuỗi_lỗi)
KẾT THÚC
```

## Cơ Chế Xử Lý Lỗi

### Lỗi Được Phép (Allowlisted Errors)
1. **"No Employee found"** - Thiết bị có ID không tồn tại trong ERPNext
2. **"Employee Inactive"** - Nhân viên đã bị vô hiệu hóa
3. **"Duplicate timestamp"** - Đã có bản ghi cùng thời gian

### Cơ Chế Recovery
1. **File Dump**: Tự động backup dữ liệu trước khi xử lý
2. **Status Tracking**: Theo dõi thời điểm pull/push cho từng device
3. **Log Phân Tầng**: Success/Failed logs riêng biệt cho từng device

### Điểm Khởi Động Lại
- **Bản ghi thành công cuối**: Đọc từ attendance_success_log
- **Import start date**: Cấu hình trong config.IMPORT_START_DATE
- **Lấy thời điểm muộn hơn** để đảm bảo không bỏ sót dữ liệu

## Luồng Dữ Liệu

```
Máy Chấm Công → [get_all_attendance] → File Dump → [pull_process_and_push_data] 
                                                         ↓
                                    [Lọc dữ liệu từ vị trí cuối thành công]
                                                         ↓
                                         [Kiểm tra user_id_inorged]
                                                    ↓           ↓
                                      [user_id_inorged_log.txt]  [send_to_erpnext]
                                                                       ↓
                                                               ERPNext API Response
                                                                       ↓
                                    ┌─────────────────────────────────┼─────────────────────────────────┐
                                    ↓                                 ↓                                 ↓
                            [Success Log]                    [Duplicate Error]                [Other Error]
                                                                       ↓                                 ↓
                                                          [error_duplicate.log]              [Failed Log]
```

## Cấu Hình Đặc Biệt

### Danh Sách User ID Bỏ Qua (local_config.py)
```python
# user_id_inorged - danh sách user ID cần bỏ qua : Tạp vụ
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
```

**Lưu ý**: user_id_inorged phải là danh sách string để khớp với dữ liệu từ máy chấm công.

## Tệp Cấu Hình Quan Trọng

### status.json
```json
{
  "lift_off_timestamp": "2025-08-13 16:27:37.470381",
  "[device_id]_pull_timestamp": "timestamp khi lấy dữ liệu",
  "[device_id]_push_timestamp": "timestamp khi push thành công",
  "mission_accomplished_timestamp": "timestamp hoàn thành chu kỳ"
}
```

### Log Files
- **logs.log** - Log thông tin chung
- **error.log** - Log lỗi hệ thống  
- **attendance_success_log_[device].log** - Log bản ghi thành công
- **attendance_failed_log_[device].log** - Log bản ghi thất bại (trừ duplicate và ignored)
- **user_id_inorged_log.txt** - Log user_id bị bỏ qua (tạp vụ)
- **error_duplicate.log** - Log lỗi duplicate timestamp
- **[device]_[ip]_last_fetch_dump.json** - Backup dữ liệu (tự xóa khi thành công)

### Định Dạng Log Đặc Biệt

#### user_id_inorged_log.txt
```
[timestamp]	IGNORED	[uid]	[user_id]	[timestamp_epoch]	[punch]	[status]	[json_data]
```

#### error_duplicate.log
```
[timestamp]	DUPLICATE	[status_code]	[uid]	[user_id]	[timestamp_epoch]	[punch]	[status]	[json_data]
```

## Lưu Ý Vận Hành

1. **Không tự động retry**: Bản ghi lỗi không được xử lý lại tự động
2. **Xử lý tuần tự**: Từng device được xử lý độc lập
3. **Recovery thủ công**: Cần can thiệp để xử lý lại dữ liệu cũ bị lỗi
4. **Chu kỳ cố định**: Dựa trên PULL_FREQUENCY trong cấu hình