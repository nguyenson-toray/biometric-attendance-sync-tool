# Sync from ERPNext to Device - Đồng bộ vân tay

## Mô tả
Tool đồng bộ dữ liệu vân tay nhân viên từ ERPNext đến máy chấm công. **Tự động thông minh** - tự phát hiện chế độ sync và xử lý nhân viên nghỉ việc.

## Tính năng chính
- ✅ **Auto Sync Mode**: Tự động chọn chế độ đồng bộ
  - **Lần đầu**: Đồng bộ tất cả nhân viên Active
  - **Lần sau**: Chỉ đồng bộ nhân viên có thay đổi từ lần sync cuối
- ✅ **Left Employee Cleanup**: Tự động xóa vân tay nhân viên nghỉ việc
  - Chỉ xóa sau ngày nghỉ việc
  - Xóa template vân tay, giữ lại user_id trên máy
- ✅ **Template Optimization**: Chỉ gửi vân tay có dữ liệu thực tế
- ✅ **Per-Device State**: Theo dõi trạng thái sync từng máy riêng biệt
- ✅ **Threading**: Xử lý đồng thời nhiều máy chấm công

## Cấu trúc files
```
biometric-attendance-sync-tool/
├── sync_from_erpnext_to_device.py       # Logic đồng bộ chính
├── erpnext_api_client.py                 # ERPNext API client
├── sync_from_erpnext_to_device_state.py # Quản lý trạng thái sync 
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
5. Lưu trạng thái sync cho từng máy
```

### Lần chạy tiếp theo (Changed Sync)
```
1. Đọc last_sync từ last_sync_global.json
2. Lấy nhân viên có thay đổi từ lần sync cuối
3. Chế độ CHANGED SYNC
4. Đồng bộ chỉ nhân viên có thay đổi
5. Xóa vân tay nhân viên Left (nếu quá ngày nghỉ việc)
6. Cập nhật trạng thái sync
```

## Cách sử dụng

### Chạy đồng bộ
```bash
# Tự động phát hiện chế độ sync (khuyến nghị - đảm bảo môi trường đúng)
./sync_from_erpnext_to_device.sh

# Hoặc chạy trực tiếp Python (debug)
python3 sync_from_erpnext_to_device.py --mode=full    # Đồng bộ toàn bộ
python3 sync_from_erpnext_to_device.py --mode=auto    # Tự động (mặc định)
```
 

### Output mẫu

#### Lần đầu chạy (Full Sync)
```
2025-08-20 10:15:30 - INFO - STARTING FULL SYNC FROM ERPNEXT TO DEVICES
2025-08-20 10:15:31 - INFO - Found 778 employees with fingerprint data
2025-08-20 10:15:31 - INFO - Found 15 Left employees to clear templates
2025-08-20 10:15:31 - INFO - Starting optimized sync for 778 employees to 4 devices
✓ Machine_8: Synced 778/778 active, Cleared 3/15 Left employees
✓ Machine_10: Synced 778/778 active, Cleared 4/15 Left employees
✓ Machine_12: Synced 778/778 active, Cleared 2/15 Left employees
✓ Machine_14: Synced 778/778 active, Cleared 6/15 Left employees
2025-08-20 10:17:05 - INFO - FULL SYNC COMPLETED
Total execution time: 1.58 minutes (31x faster!)
```

#### Lần chạy tiếp theo (Changed Sync)
```
2025-08-20 14:30:15 - INFO - STARTING CHANGED SYNC FROM ERPNEXT TO DEVICES
2025-08-20 14:30:16 - INFO - Syncing changes since: 2025-08-20 10:17:05
2025-08-20 14:30:17 - INFO - Found 5 changed employees with fingerprint data
2025-08-20 14:30:17 - INFO - Found 2 Left employees to clear templates
✓ Machine_8: Synced 5/5 active, Cleared 1/2 Left employees
✓ Machine_10: Synced 5/5 active, Cleared 0/2 Left employees
✓ Machine_12: Synced 5/5 active, Cleared 1/2 Left employees
✓ Machine_14: Synced 5/5 active, Cleared 0/2 Left employees
2025-08-20 14:30:25 - INFO - CHANGED SYNC COMPLETED
Total execution time: 10 seconds
```

#### Xem trạng thái máy
```bash
$ python3 view_device_sync_states.py

================================================================================
DEVICE SYNC STATES
================================================================================
Global last sync: 2025-08-20 14:30:25

Device: machine_8
  Last sync: 2025-08-20 14:30:23
  Total users synced: 778
  Sync history: 5 entries
  Recent users (10 of 778):
    - User ID: 1001 | Employee: EMP-001 | Name: Nguyen Van A | Templates: 3
    - User ID: 1002 | Employee: EMP-002 | Name: Tran Thi B | Templates: 2
    ...
  Clear history: 3 entries
  Latest clear: 2025-08-20 14:30:23 (1 users)
    Cleared users:
      • EMP-999 (ID: 999) - Relieving: 2025-08-15

Device: machine_10
  Last sync: 2025-08-20 14:30:24
  Total users synced: 778
  ...
```

## File trạng thái
Tool tự động tạo và quản lý các file trạng thái:

### Global sync state (last_sync_global.json)
```json
{
  "last_sync": "2025-08-20 14:30:25",
  "updated_at": "2025-08-20 14:30:25"
}
```

### Per-device sync state (last_sync_machine_8.json)
```json
{
  "device_id": "machine_8",
  "last_sync": "2025-08-20 14:30:23",
  "updated_at": "2025-08-20 14:30:23",
  "total_users_synced": 778,
  "users": [
    {
      "user_id": "1001",
      "employee": "EMP-001", 
      "employee_name": "Nguyen Van A",
      "fingerprint_count": 3,
      "synced_at": "2025-08-20 14:30:23"
    }
  ],
  "sync_history": [...],
  "clear_history": [
    {
      "clear_time": "2025-08-20 14:30:23",
      "cleared_users_count": 1,
      "cleared_users": [...]
    }
  ]
}
```

**Lưu ý**: Không cần chỉnh sửa các file này manually.

## Tối ưu hóa

### Template Optimization
- **Trước**: Gửi tất cả 10 ngón tay (dù không có dữ liệu)
- **Sau**: Chỉ gửi ngón có template thực tế
- **Kết quả**: Giảm ~70% traffic mạng

### Left Employee Cleanup
- **Kiểm tra ngày**: Chỉ xóa sau `relieving_date`
- **Xóa template**: Giữ lại `user_id` trên máy
- **Tự động**: Chạy cùng với sync thông thường

### Performance
- **Trước**: 54 phút cho 778 nhân viên
- **Sau**: 1.7 phút cho 778 nhân viên  
- **Tăng tốc**: 31x nhanh hơn

### State Tracking
- **Global**: Thời điểm sync cuối cùng
- **Per-Device**: Chi tiết từng máy riêng biệt
- **History**: Lưu 10 lần sync/clear gần nhất

## Cron Job Setup (Tự động hóa)

```bash
# Mở crontab
crontab -e

# Chạy mỗi 15 phút (khuyến nghị - nhanh nên có thể chạy thường xuyên hơn)
*/15 * * * * cd /path/to/biometric-attendance-sync-tool && ./sync_from_erpnext_to_device.sh >/dev/null 2>&1

# Hoặc mỗi 30 phút
*/30 * * * * cd /path/to/biometric-attendance-sync-tool && ./sync_from_erpnext_to_device.sh >/dev/null 2>&1

# Chạy vào giờ cố định 11:00 và 15:00 hàng ngày
0 11,15 * * * cd /path/to/biometric-attendance-sync-tool && ./sync_from_erpnext_to_device.sh >/dev/null 2>&1
```

## Reset để Full Sync lại

Nếu muốn force Full Sync (ví dụ sau khi thay đổi lớn):
```bash
# Xóa file trạng thái global
rm logs/sync_from_erpnext_to_device/last_sync_global.json

# Chạy lại - sẽ auto detect là first run
./sync_from_erpnext_to_device.sh
```

## Troubleshooting

### 1. Debug mode
```bash
# Chạy với shell script (khuyến nghị)
./sync_from_erpnext_to_device.sh

# Chạy trực tiếp Python để thấy chi tiết
python3 sync_from_erpnext_to_device.py --mode=full

# Xem trạng thái chi tiết
python3 view_device_sync_states.py
```

### 2. Kiểm tra logs và state
```bash
# Xem log realtime
tail -f logs/sync_from_erpnext_to_device/sync_to_device.log

# Xem trạng thái global
cat logs/sync_from_erpnext_to_device/last_sync_global.json

# Xem trạng thái máy cụ thể
cat logs/sync_from_erpnext_to_device/last_sync_machine_8.json
```

### 3. Lỗi thường gặp
- **No last_sync_global.json**: Bình thường cho lần đầu chạy
- **API connection failed**: Kiểm tra config ERPNext trong `local_config.py`
- **Device offline**: Kiểm tra network đến máy chấm công
- **Template sync error**: Kiểm tra định dạng dữ liệu vân tay trong ERPNext

## Các tính năng nâng cao

### Left Employee Processing
- Tự động xóa vân tay nhân viên nghỉ việc
- Chỉ xóa sau ngày `relieving_date`
- Giữ lại `user_id` để không ảnh hưởng attendance history

### Smart Template Sync
- Chỉ gửi vân tay có dữ liệu thực tế
- Bỏ qua ngón tay trống
- Tối ưu băng thông mạng

### Per-Device State Management
- Theo dõi từng máy riêng biệt
- Lưu lịch sử sync và clear
- Audit trail đầy đủ

**Khuyến nghị**: Chạy mỗi 15-30 phút với cron job do tối ưu tốc độ.