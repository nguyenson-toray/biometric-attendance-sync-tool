#!/usr/bin/env python3
"""
06.send_error_report.py
Rà soát log lỗi và gửi email cảnh báo qua Frappe API (frappe.sendmail).

Logic dedup:
- Chỉ lấy các dòng lỗi có timestamp > lần gửi mail cuối (.last_error_report_sent)
- Lần đầu chạy (chưa có marker): ghi nhận mốc thời gian hiện tại, bỏ qua
- Cooldown: không gửi quá 1 lần trong ERROR_REPORT_COOLDOWN_MINUTES phút
"""

import os
import re
import datetime
import json
import requests

current_dir = os.path.dirname(os.path.abspath(__file__))

# Regex parse dòng log: "2026-03-18 08:03:12,123\tLEVEL\tMessage"
_LOG_PATTERN = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+\t(\w+)\t(.+)$'
)


def _get_config():
    import local_config
    return local_config


# ---------------------------------------------------------------------------
# Collect & filter
# ---------------------------------------------------------------------------

def _read_log_file(filepath, after_dt, level_filter=None):
    """
    Đọc file log, chỉ trả về các dòng có timestamp > after_dt.
    level_filter: set of level strings, None = lấy tất cả.
    """
    lines = []
    if not os.path.exists(filepath):
        return lines
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for raw in f:
                raw = raw.rstrip('\n').rstrip('\r')
                if not raw.strip():
                    continue
                m = _LOG_PATTERN.match(raw)
                if not m:
                    # Dòng continuation (traceback) — gắn vào dòng trước
                    if lines:
                        lines[-1] = lines[-1] + '\n    ' + raw
                    continue
                dt_str, level = m.group(1), m.group(2)
                try:
                    dt = datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
                if dt <= after_dt:
                    continue
                if level_filter and level not in level_filter:
                    continue
                lines.append(raw)
    except Exception as e:
        print(f"[send_error_report] Cannot read {filepath}: {e}")
    return lines


def collect_new_errors(after_dt):
    """
    Đọc các dòng lỗi có timestamp > after_dt.

    Returns:
        dict: {
            'error_log': [dòng từ error.log],
            'main_log':  [dòng ERROR/CRITICAL từ logs.log]
        }
    """
    config = _get_config()
    logs_dir = os.path.join(current_dir, config.LOGS_DIRECTORY)

    return {
        'error_log': _read_log_file(
            os.path.join(logs_dir, 'error.log'),
            after_dt=after_dt
        ),
        'main_log': _read_log_file(
            os.path.join(logs_dir, 'logs.log'),
            after_dt=after_dt,
            level_filter={'ERROR', 'CRITICAL'}
        ),
    }


# ---------------------------------------------------------------------------
# Build email
# ---------------------------------------------------------------------------

def build_email_content(errors, after_dt):
    """Tạo subject và body email."""
    config = _get_config()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    after_str = after_dt.strftime('%Y-%m-%d %H:%M:%S')
    total = len(errors['error_log']) + len(errors['main_log'])

    subject = f"[Biometric Sync Tool] CẢNH BÁO: {total} lỗi mới lúc {now_str}"

    lines = [
        f"Thời gian phát hiện : {now_str}",
        f"Khoảng thời gian    : từ {after_str} đến {now_str}",
        f"Máy chủ ERPNext     : {config.ERPNEXT_URL}",
        f"Tổng số lỗi mới     : {total}",
        f"Xem chi tiết logs   : {config.ERPNEXT_URL}/erpnext-sync-all-logs",
        "",
    ]

    if errors['error_log']:
        lines.append(f"{'─'*70}")
        lines.append(f"[error.log] — {len(errors['error_log'])} dòng")
        lines.append(f"{'─'*70}")
        lines.extend(errors['error_log'])
        lines.append("")

    if errors['main_log']:
        lines.append(f"{'─'*70}")
        lines.append(f"[logs.log — ERROR/CRITICAL] — {len(errors['main_log'])} dòng")
        lines.append(f"{'─'*70}")
        lines.extend(errors['main_log'])
        lines.append("")

    lines.append("─" * 70)
    lines.append("Email này được gửi tự động bởi biometric-attendance-sync-tool.")
    lines.append("─" * 70)

    return subject, "\n".join(lines)


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------

def send_report(errors, after_dt):
    """Gửi email qua Frappe API. Trả về True nếu thành công."""
    config = _get_config()
    subject, body = build_email_content(errors, after_dt)
    recipients = getattr(config, 'ERROR_REPORT_RECIPIENTS', [])

    url = (f"{config.ERPNEXT_URL}/api/method/"
           "customize_erpnext.api.biometric.error_report.send_biometric_error_report")
    headers = {
        'Authorization': f'token {config.ERPNEXT_API_KEY}:{config.ERPNEXT_API_SECRET}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    payload = {
        'subject': subject,
        'body': body,
        'recipients': json.dumps(recipients),
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get('message', {}).get('status') == 'ok':
            print(f"[send_error_report] Email sent OK → {recipients}")
            return True
        else:
            print(f"[send_error_report] Unexpected response: {result}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[send_error_report] API call failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(force=False):
    """
    Hàm chính — gọi từ erpnext_sync_all.py hoặc chạy thủ công.

    Args:
        force (bool): Bỏ qua cooldown (dùng để test)

    Returns:
        dict: {'sent': bool, 'new_errors': int}
    """
    import local_config

    if not getattr(local_config, 'ENABLE_ERROR_REPORT_EMAIL', False):
        print("[send_error_report] Disabled (ENABLE_ERROR_REPORT_EMAIL=False)")
        return {'sent': False, 'new_errors': 0}

    last_sent = local_config.get_last_error_report_sent()

    # Lần đầu tiên: chưa có marker → ghi nhận mốc hiện tại, bỏ qua
    # (tránh gửi toàn bộ log cũ ngay lần đầu)
    if last_sent is None:
        print("[send_error_report] Lần đầu chạy — ghi nhận mốc thời gian, bỏ qua lần này")
        local_config.set_last_error_report_sent()
        return {'sent': False, 'new_errors': 0}

    # Cooldown: giới hạn tần suất gửi tối đa
    if not force and not local_config.should_send_error_report():
        elapsed = int((datetime.datetime.now() - last_sent).total_seconds() / 60)
        remaining = local_config.ERROR_REPORT_COOLDOWN_MINUTES - elapsed
        print(f"[send_error_report] Cooldown active — còn {remaining} phút")
        return {'sent': False, 'new_errors': 0}

    # Lấy lỗi mới: timestamp > last_sent
    errors = collect_new_errors(after_dt=last_sent)
    total_new = len(errors['error_log']) + len(errors['main_log'])

    if total_new == 0:
        print(f"[send_error_report] Không có lỗi mới kể từ {last_sent}")
        return {'sent': False, 'new_errors': 0}

    print(f"[send_error_report] Phát hiện {total_new} lỗi mới — đang gửi email...")
    success = send_report(errors, after_dt=last_sent)

    if success:
        local_config.set_last_error_report_sent()

    return {'sent': success, 'new_errors': total_new}


if __name__ == '__main__':
    import sys
    import importlib.util

    spec = importlib.util.spec_from_file_location("local_config",
        os.path.join(current_dir, "local_config.py"))
    local_config_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(local_config_mod)
    sys.modules['local_config'] = local_config_mod

    force = '--force' in sys.argv
    result = run(force=force)
    print(f"[send_error_report] Kết quả: {result}")
