# ERPNext Sync All - Systemd Service Setup

## 🎯 Tổng quan

Thay vì chạy `start_erpnext_sync_all_manual.sh` thủ công, bạn có thể cài đặt ERPNext Sync All như một service của hệ điều hành với các tính năng:

- ✅ **Tự động khởi động** khi server reboot
- ✅ **Auto-restart** khi gặp lỗi (max 3 lần trong 60s)
- ✅ **Process monitoring** và status tracking
- ✅ **Centralized logging** qua systemd journal
- ✅ **Easy management** với systemctl commands
- ✅ **Network access** đầy đủ cho biometric devices
- ✅ **Environment isolation** nhưng không restrictive

## 📁 Cấu trúc files

```
biometric-attendance-sync-tool/
├── erpnext-sync-all.service      # Systemd service definition (với network config)
├── service_wrapper.sh            # Wrapper script với venv support & network test
├── service_manager.sh             # Quản lý service (install/start/stop/logs)
├── update_service_config.sh      # Script cập nhật service configuration
├── erpnext_sync_all.py           # Main Python script
├── venv/                         # Virtual environment
└── logs/
    ├── service.log               # Service wrapper logs
    ├── logs.log                  # Main application logs
    └── error.log                 # Error logs
```

## 🚀 Cài đặt Service

### Bước 1: Cài đặt service

```bash
# Cài đặt service (cần sudo)
sudo ./service_manager.sh install

# Hoặc cài đặt thủ công:
sudo cp erpnext-sync-all.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable erpnext-sync-all
```

**⚠️ Lưu ý về Network Access:**
Service đã được cấu hình để có full network access, tương tự manual script.

### Bước 2: Khởi động service

```bash
# Khởi động service
sudo ./service_manager.sh start

# Hoặc dùng systemctl trực tiếp:
sudo systemctl start erpnext-sync-all
```

### Bước 3: Kiểm tra trạng thái

```bash
# Xem status và logs
./service_manager.sh status

# Hoặc:
systemctl status erpnext-sync-all
```

## 🎮 Quản lý Service

### Script quản lý service_manager.sh

```bash
# Cài đặt service
sudo ./service_manager.sh install

# Khởi động service
sudo ./service_manager.sh start

# Dừng service
sudo ./service_manager.sh stop

# Restart service
sudo ./service_manager.sh restart

# Xem status và logs gần đây
./service_manager.sh status

# Xem logs (50 dòng cuối)
./service_manager.sh logs

# Theo dõi logs real-time
./service_manager.sh logs follow

# Xem 100 dòng logs cuối
./service_manager.sh logs tail 100

# Gỡ cài đặt service
sudo ./service_manager.sh uninstall

# Hiển thị help
./service_manager.sh help
```

### ⚡ Quick Update Service Configuration

```bash
# Cập nhật service config và restart (sau khi sửa file .service)
./update_service_config.sh

# Script này sẽ:
# 1. Copy file .service mới
# 2. Reload systemd daemon
# 3. Restart service
# 4. Hiển thị status và logs
```

### Systemctl commands trực tiếp

```bash
# Khởi động
sudo systemctl start erpnext-sync-all

# Dừng
sudo systemctl stop erpnext-sync-all

# Restart
sudo systemctl restart erpnext-sync-all

# Status
systemctl status erpnext-sync-all

# Enable auto-start at boot
sudo systemctl enable erpnext-sync-all

# Disable auto-start
sudo systemctl disable erpnext-sync-all

# Xem logs
journalctl -u erpnext-sync-all

# Theo dõi logs real-time
journalctl -u erpnext-sync-all -f

# Xem logs với số dòng cụ thể
journalctl -u erpnext-sync-all -n 100
```

## 📊 Monitoring & Logging

### 1. Service Status

```bash
# Kiểm tra service có đang chạy không
systemctl is-active erpnext-sync-all

# Kiểm tra service có enabled không
systemctl is-enabled erpnext-sync-all

# Xem chi tiết status
systemctl status erpnext-sync-all --no-pager
```

### 2. Logs

Service logs được lưu ở nhiều nơi:

**Systemd Journal:**
```bash
# Logs chính qua journalctl
journalctl -u erpnext-sync-all -f

# Logs từ thời điểm cụ thể
journalctl -u erpnext-sync-all --since "2025-09-17 08:00:00"

# Logs với priority cụ thể (ERROR, WARNING, INFO)
journalctl -u erpnext-sync-all -p err
```

**Application Logs:**
```bash
# Service wrapper logs
tail -f logs/service.log

# Main application logs
tail -f logs/logs.log

# Error logs
tail -f logs/error.log
```

### 3. Process Monitoring

```bash
# Xem process
ps aux | grep erpnext_sync_all

# Xem resource usage
systemctl show erpnext-sync-all --property=MainPID
top -p $(systemctl show erpnext-sync-all --property=MainPID --value)
```

## 🔧 Cấu hình Auto-restart

Service được cấu hình tự động restart khi gặp lỗi:

```ini
[Service]
Restart=always              # Luôn restart khi process exit
RestartSec=10               # Đợi 10 giây trước khi restart
StartLimitInterval=60       # Trong vòng 60 giây
StartLimitBurst=3          # Chỉ thử restart tối đa 3 lần
```

## 🚨 Troubleshooting

### Service không khởi động được

```bash
# Xem lỗi chi tiết
systemctl status erpnext-sync-all -l

# Xem logs từ boot
journalctl -u erpnext-sync-all --since today

# Kiểm tra file cấu hình
sudo systemctl cat erpnext-sync-all

# Kiểm tra service wrapper logs
tail -f logs/service.log
```

### Service bị restart liên tục

```bash
# Xem số lần restart
systemctl status erpnext-sync-all

# Xem logs để tìm nguyên nhân
journalctl -u erpnext-sync-all -n 50

# Kiểm tra application logs
tail -f logs/error.log

# Xem service wrapper logs
tail -f logs/service.log
```

### Network connectivity issues

```bash
# Test network từ service user context
sudo -u frappe ping -c 2 10.0.1.41

# Kiểm tra service có ping được không
# (xem trong logs/service.log)
grep "Network connectivity" logs/service.log

# Debug network environment trong service
journalctl -u erpnext-sync-all | grep "Network debug"
```

### ZKNetworkError: can't reach device

**Nguyên nhân thường gặp:**
1. **Systemd network restrictions** - Đã fix trong service config
2. **Environment differences** - Service chạy với user frappe
3. **Path issues** - Ping command không tìm thấy

**Giải pháp:**
```bash
# 1. Cập nhật service với network config mới
./update_service_config.sh

# 2. Kiểm tra ping command
which ping
ls -la /bin/ping /usr/bin/ping

# 3. Test manual connectivity
sudo -u frappe /bin/ping -c 1 10.0.1.41
```

### Permission issues

```bash
# Đảm bảo files có quyền đúng
chown -R frappe:frappe /home/frappe/frappe-bench/apps/biometric-attendance-sync-tool
chmod +x service_wrapper.sh
chmod +x service_manager.sh
chmod +x update_service_config.sh

# Kiểm tra service file permissions
ls -la /etc/systemd/system/erpnext-sync-all.service
```

## 🔄 Migration từ Manual Script

### Nếu đang chạy manual script:

1. **Dừng manual script:**
```bash
./stop_erpnext_sync_all_manual.sh
```

2. **Cài đặt service:**
```bash
sudo ./service_manager.sh install
sudo ./service_manager.sh start
```

3. **Verify hoạt động:**
```bash
./service_manager.sh status
./service_manager.sh logs follow
```

### So sánh Manual vs Service:

| Feature | Manual Script | Systemd Service |
|---------|---------------|-----------------|
| Auto-start at boot | ❌ | ✅ |
| Auto-restart on crash | ❌ | ✅ (max 3 lần/60s) |
| Centralized logging | ❌ | ✅ (journalctl + files) |
| Process monitoring | ❌ | ✅ (systemctl status) |
| Easy management | ❌ | ✅ (service_manager.sh) |
| Background running | ✅ | ✅ |
| Network access | ✅ | ✅ (đã fix) |
| Environment isolation | ❌ | ✅ (nhưng không restrictive) |
| Quick config update | ❌ | ✅ (update_service_config.sh) |

## 📝 Lưu ý quan trọng

1. **User Context:** Service chạy với user `frappe`, giống như manual script
2. **Virtual Environment:** Tự động sử dụng venv từ project
3. **Working Directory:** Tự động set đúng thư mục project
4. **Signal Handling:** Hỗ trợ graceful shutdown với SIGTERM
5. **Network Access:** Full network permissions cho biometric devices
6. **Security:** Tắt restrictive security để đảm bảo network access
7. **Environment Variables:** Đầy đủ PATH, HOME, LANG cho compatibility

## 🔧 Network Configuration Details

Service được cấu hình với:
```ini
# Network access configuration
PrivateNetwork=false                    # Cho phép full network access
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX  # Support IPv4, IPv6, Unix sockets
IPAddressAllow=any                      # Không hạn chế IP nào

# Disable restrictive security
ProtectSystem=false                     # Cho phép truy cập system files
ProtectHome=false                       # Cho phép truy cập home directory
```

## 🎯 Khuyến nghị

- ✅ **Sử dụng systemd service** cho production environment
- ⚠️ **Dùng manual script** chỉ khi debug hoặc testing
- 📊 **Monitor logs** thường xuyên để phát hiện sớm vấn đề
- 🔄 **Sử dụng update_service_config.sh** khi cần thay đổi cấu hình
- 💾 **Backup logs** định kỳ nếu cần thiết
- 🌐 **Test network connectivity** khi gặp device connection issues

## 📞 Quick Commands Reference

```bash
# Cài đặt và khởi động
sudo ./service_manager.sh install
sudo ./service_manager.sh start

# Monitor logs real-time
./service_manager.sh logs follow

# Update config và restart
./update_service_config.sh

# Debug network issues
sudo -u frappe ping -c 1 10.0.1.41
grep "Network" logs/service.log

# Emergency stop
sudo systemctl stop erpnext-sync-all
```