# ERPNext Biometric Sync Service

Unified service that coordinates ERPNext sync and device sync operations with time-based bypass logic and auto-restart capability.

## Features

- **Unified Service**: Single service that manages both `erpnext_sync` and `sync_from_erpnext_to_device`
- **Time-based Bypass**: Avoid device conflicts during busy periods (rush hours)
- **Dynamic Configuration**: Runtime configuration changes without service restart
- **Auto-restart**: Automatic recovery from errors and crashes
- **Sequential Execution**: No device connection conflicts between operations
- **Comprehensive Logging**: Detailed logging with bypass status and operation tracking

## Installation

1. **Test path detection** (optional):
   ```bash
   ./test_paths.sh
   ```

2. **Install the service** (auto-detects paths):
   ```bash
   sudo ./install_service.sh
   ```
   
   The installer will automatically detect:
   - App path: `frappe-bench/apps/biometric-attendance-sync-tool`
   - Python path: `frappe-bench/env/bin/python3`
   - Frappe bench owner
   - All necessary paths for systemd service

3. **Start the service**:
   ```bash
   sudo systemctl start erpnext-sync
   ```

4. **Enable auto-start on boot**:
   ```bash
   sudo systemctl enable erpnext-sync
   ```

## Configuration

### Static Configuration
Edit `local_config.py` for basic settings:
- ERPNext connection details
- Device configurations  
- Pull frequency (PULL_FREQUENCY)
- Logging settings

### Dynamic Configuration
Edit `local_config_dynamic.py` for runtime settings:

#### Time-based Bypass Periods
```python
SYNC_LOG_BYPASS_PERIODS = [
    {"start": "07:30", "end": "07:55", "reason": "Morning rush"},
    {"start": "17:00", "end": "17:30", "reason": "Evening rush"}
]

SYNC_USER_INFO_BYPASS_PERIODS = [
    {"start": "07:30", "end": "07:55", "reason": "Morning rush"},
    {"start": "17:00", "end": "17:30", "reason": "Evening rush"}
]

CLEAR_LEFT_USER_TEMPLATE_BYPASS_PERIODS = [
    {"start": "00:00", "end": "22:00", "reason": "Working hours"}
]
```

#### Feature Toggles
```python
ENABLE_SYNC_FROM_ERPNEXT_TO_DEVICE = True
ENABLE_CLEAR_LEFT_USER_TEMPLATES = True
SYNC_FROM_ERPNEXT_TO_DEVICE_MODE = 'auto'  # 'full', 'changed', 'auto'
SYNC_CHANGED_HOURS_BACK = 24
```

## Service Management

### Basic Commands
```bash
# Start service
sudo systemctl start erpnext-sync

# Stop service
sudo systemctl stop erpnext-sync

# Restart service
sudo systemctl restart erpnext-sync

# Check status
sudo systemctl status erpnext-sync

# View logs (follow mode)
sudo journalctl -u erpnext-sync -f

# View service logs
tail -f logs/service.log
```

### Manual Testing
```bash
# Test dynamic configuration
python3 erpnext_service.py --test-config

# Check service status
python3 erpnext_service.py --status

# Show version
python3 erpnext_service.py --version

# Test dynamic config only
python3 local_config_dynamic.py
```

## Operation Flow

Every **3 minutes** (PULL_FREQUENCY), the service:

1. **Loads Dynamic Config**: Refreshes bypass settings from `local_config_dynamic.py`
2. **Logs Bypass Status**: Shows current time-based bypass status
3. **ERPNext Sync**: 
   - If NOT in bypass period → Execute `erpnext_sync.py` (get logs from devices)
   - If in bypass period → Skip with reason
4. **Device Sync** (if enabled):
   - If NOT in bypass period → Execute `sync_from_erpnext_to_device.py`
   - Check clear left templates bypass separately
   - If in bypass period → Skip with reason
5. **Sleep**: Wait for next PULL_FREQUENCY cycle

## Time-based Bypass Logic

### Log Sync Bypass
- **Purpose**: Avoid device connections during employee check-in/out rushes
- **Default Periods**: 07:30-07:55, 17:00-17:30
- **Effect**: Skip getting attendance logs from devices

### User Info Sync Bypass  
- **Purpose**: Avoid device conflicts during busy periods
- **Default Periods**: 07:30-07:55, 17:00-17:30
- **Effect**: Skip syncing employee/template data to devices

### Clear Left Templates Bypass
- **Purpose**: Delay template cleanup until after work hours
- **Default Period**: 00:00-22:00 (only allow after 22:00)
- **Effect**: Skip clearing templates of left employees during work hours

## Logging

### Service Logs
- `logs/service.log` - Main service output
- `logs/service_error.log` - Service errors
- System journal: `journalctl -u erpnext-sync`

### Application Logs
- `logs/logs.log` - ERPNext sync info
- `logs/error.log` - ERPNext sync errors  
- `logs/attendance_success_log_*.log` - Successful syncs per device
- `logs/attendance_failed_log_*.log` - Failed syncs per device
- `logs/sync_from_erpnext_to_device/` - Device sync logs

## Troubleshooting

### Service Won't Start
```bash
# Check service status
sudo systemctl status erpnext-sync

# Check service logs
sudo journalctl -u erpnext-sync -n 50

# Test configuration
python3 erpnext_service.py --test-config
```

### Configuration Issues
```bash
# Test dynamic config
python3 local_config_dynamic.py

# Check syntax
python3 -m py_compile local_config_dynamic.py
```

### Monitoring Performance
```bash
# Watch service activity
sudo journalctl -u erpnext-sync -f

# Check cycle frequency
tail -f logs/service.log | grep "CYCLE #"
```

### Manual Service Run (Debug)
```bash
# Stop service first
sudo systemctl stop erpnext-sync

# Run manually to see output
python3 erpnext_service.py

# Ctrl+C to stop, then restart service
sudo systemctl start erpnext-sync
```

## Benefits

1. **No Conflicts**: Sequential execution prevents device connection conflicts
2. **Flexible Timing**: Time-based bypass avoids busy periods
3. **Easy Management**: Single systemd service to manage
4. **Auto Recovery**: Service continues after errors with retry logic  
5. **Runtime Config**: Change settings without restarting service
6. **Comprehensive Monitoring**: Detailed logs and status reporting

## Files Structure

```
biometric-attendance-sync-tool/
├── erpnext_service.py              # Main service coordinator
├── local_config_dynamic.py         # Dynamic configuration
├── erpnext_sync.py                 # ERPNext sync (modified for bypass)
├── sync_from_erpnext_to_device.py  # Device sync
├── erpnext-sync.service            # Systemd service file
├── install_service.sh              # Installation script
├── README_SERVICE.md               # This documentation
└── logs/                           # Log directory
    ├── service.log
    ├── service_error.log
    └── ...
```