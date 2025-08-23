#!/bin/bash

# Test script to verify path detection logic
# Run this to check if paths will be detected correctly before installation

echo "=== PATH DETECTION TEST ==="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Auto-detect paths (same logic as install_service.sh)
echo "Script location: $SCRIPT_DIR"

# Detect app path (should be where this script is located)
APP_PATH="$SCRIPT_DIR"
echo "App path: $APP_PATH"

# Detect frappe-bench path by going up from apps/biometric-attendance-sync-tool
FRAPPE_BENCH_PATH="$(dirname "$(dirname "$SCRIPT_DIR")")"
echo "Frappe bench path: $FRAPPE_BENCH_PATH"

# Detect Python path in frappe env
PYTHON_PATH="$FRAPPE_BENCH_PATH/env/bin/python3"
FRAPPE_ENV_PATH="$FRAPPE_BENCH_PATH/env/bin"

echo "Python path: $PYTHON_PATH"
echo "Frappe env path: $FRAPPE_ENV_PATH"

# Detect current user (who owns the frappe-bench directory)
BENCH_OWNER=$(stat -c '%U' "$FRAPPE_BENCH_PATH")
echo "Frappe bench owner: $BENCH_OWNER"

echo ""
echo "=== VALIDATION ==="

# Validate paths
if [[ ! -d "$APP_PATH" ]]; then
    echo "❌ Error: App directory not found: $APP_PATH"
    exit 1
else
    echo "✅ App directory exists: $APP_PATH"
fi

if [[ ! -f "$APP_PATH/erpnext_sync_all_service.py" ]]; then
    echo "❌ Error: erpnext_sync_all_service.py not found in $APP_PATH"
    exit 1
else
    echo "✅ erpnext_sync_all_service.py found"
fi

if [[ ! -f "$PYTHON_PATH" ]]; then
    echo "❌ Error: Python not found at $PYTHON_PATH"
    echo "   Please ensure this script is run from frappe-bench/apps/biometric-attendance-sync-tool/"
    exit 1
else
    echo "✅ Python found: $PYTHON_PATH"
fi

if [[ ! -d "$FRAPPE_BENCH_PATH" ]]; then
    echo "❌ Error: Frappe bench directory not found: $FRAPPE_BENCH_PATH"
    exit 1
else
    echo "✅ Frappe bench directory exists: $FRAPPE_BENCH_PATH"
fi

echo ""
echo "=== GENERATED SERVICE FILE PREVIEW ==="

# Show what the service file would look like
echo "The service file will be generated with these values:"
echo ""
echo "User=%USER% → User=$BENCH_OWNER"
echo "Group=%USER% → Group=$BENCH_OWNER" 
echo "WorkingDirectory=%APP_PATH% → WorkingDirectory=$APP_PATH"
echo "Environment=PATH=%FRAPPE_ENV_PATH%:... → Environment=PATH=$FRAPPE_ENV_PATH:..."
echo "Environment=PYTHONPATH=%APP_PATH% → Environment=PYTHONPATH=$APP_PATH"
echo "ExecStart=%PYTHON_PATH% %APP_PATH%/erpnext_sync_all_service.py → ExecStart=$PYTHON_PATH $APP_PATH/erpnext_sync_all_service.py"
echo "StandardOutput=append:%APP_PATH%/logs/service.log → StandardOutput=append:$APP_PATH/logs/service.log"
echo "ReadWritePaths=%APP_PATH% → ReadWritePaths=$APP_PATH"

echo ""
echo "✅ All path validations passed!"
echo "✅ Ready for installation with: sudo ./install_service.sh"