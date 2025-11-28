# ERPNext Biometric Sync - Service Management

## 🎯 Tổng quan

ERPNext Sync chạy như **systemd service** với các tính năng:
- ✅ Tự động khởi động khi server reboot
- ✅ Auto-restart khi gặp lỗi
- ✅ Centralized logging
- ✅ Easy management

## 🚀 Lệnh quản lý nhanh

### Service Manager (Auto Password) - KHUYÊN DÙNG

```bash
# Xem trạng thái
./service_manager_auto.sh status

# Restart service
./service_manager_auto.sh restart

# Start/Stop service
./service_manager_auto.sh start
./service_manager_auto.sh stop

# Xem logs real-time
./service_manager_auto.sh logs follow

# Xem 100 dòng logs gần nhất
./service_manager_auto.sh logs tail 100

# Cài đặt service (chỉ cần 1 lần)
./service_manager_auto.sh install

# Gỡ bỏ service
./service_manager_auto.sh uninstall
```

### Update Service Configuration

```bash
# Sau khi sửa file erpnext-sync-all.service
./update_service_config_auto.sh
```

### Manual Sync (Không qua service)

```bash
# Chạy sync thủ công một lần
./venv/bin/python3 ./erpnext_re_sync_all.py
```

## 📊 Monitoring & Logs

### Kiểm tra trạng thái

```bash
# Trạng thái service
systemctl status erpnext-sync-all

# Kiểm tra service đang chạy
systemctl is-active erpnext-sync-all
```

### Xem logs

```bash
# Logs real-time (systemd journal)
journalctl -u erpnext-sync-all -f

# Logs 50 dòng cuối
journalctl -u erpnext-sync-all -n 50

# Application logs
tail -f logs/logs.log
tail -f logs/error.log
tail -f logs/service.log
```

### Kiểm tra sync status

```bash
# Xem status file
cat logs/status.json | python3 -m json.tool

# Đếm attendance records hôm nay
wc -l logs/attendance_success_log_Machine*.log

# Xem logs của một machine cụ thể
tail -f "logs/attendance_success_log_Machine 7.log"
```

## 🔧 Systemctl Commands

```bash
# Start/Stop/Restart
sudo systemctl start erpnext-sync-all
sudo systemctl stop erpnext-sync-all
sudo systemctl restart erpnext-sync-all

# Enable/Disable auto-start at boot
sudo systemctl enable erpnext-sync-all
sudo systemctl disable erpnext-sync-all

# Reload daemon (sau khi sửa service file)
sudo systemctl daemon-reload
```

## 🚨 Troubleshooting

### Service không khởi động

```bash
# Xem lỗi chi tiết
systemctl status erpnext-sync-all -l
journalctl -u erpnext-sync-all -n 50

# Kiểm tra service wrapper logs
tail -f logs/service.log

# Kiểm tra error logs
tail -f logs/error.log
```

### Network connectivity issues

```bash
# Test ping từ service user
sudo -u frappe ping -c 2 10.0.1.41

# Xem network logs
grep "Network" logs/service.log
journalctl -u erpnext-sync-all | grep "Network debug"
```

### Permission issues

```bash
# Fix quyền files
chown -R frappe:frappe /home/frappe/frappe-bench/apps/biometric-attendance-sync-tool
chmod +x service_manager_auto.sh
chmod +x update_service_config_auto.sh
chmod +x service_wrapper.sh
```

## 📁 Cấu trúc files quan trọng

```
biometric-attendance-sync-tool/
├── service_manager_auto.sh        # Quản lý service (có auto password)
├── update_service_config_auto.sh  # Update config (có auto password)
├── erpnext-sync-all.service       # Systemd service file
├── service_wrapper.sh             # Service wrapper
├── erpnext_sync_all.py            # Main script (AUTO mode)
├── erpnext_re_sync_all.py         # Interactive script (MANUAL mode)
└── logs/
    ├── service.log                # Service wrapper logs
    ├── logs.log                   # Application logs
    ├── error.log                  # Error logs
    ├── status.json                # Sync status
    └── attendance_success_log_*.log  # Attendance records per machine
```

## 📝 Lưu ý quan trọng

1. **Auto Password**: Scripts `*_auto.sh` đã có sẵn password sudo, không cần nhập lại
2. **Service User**: Chạy với user `frappe`
3. **Auto-restart**: Service tự động restart tối đa 3 lần/60s khi crash
4. **Logs**: Được ghi cả vào journalctl và files trong thư mục logs/

## 🔑 Đổi Sudo Password

Nếu đổi password sudo, cần update trong 2 files:
- `service_manager_auto.sh` (dòng 7: `SUDO_PASSWORD="..."`)
- `update_service_config_auto.sh` (dòng 7: `SUDO_PASSWORD="..."`)

## 📞 Quick Reference

```bash
# STATUS CHECK
./service_manager_auto.sh status
cat logs/status.json | python3 -m json.tool

# LOGS MONITORING
./service_manager_auto.sh logs follow
tail -f logs/logs.log

# RESTART SERVICE
./service_manager_auto.sh restart

# MANUAL SYNC
./venv/bin/python3 ./erpnext_re_sync_all.py
```
