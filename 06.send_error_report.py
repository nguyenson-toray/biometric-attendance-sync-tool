#!/usr/bin/env python3
"""
06.send_error_report.py
Rà soát log lỗi và gửi email cảnh báo qua Frappe API (frappe.sendmail).

- Đọc logs/error.log và logs/logs.log (lọc ERROR/CRITICAL)
- Lọc các dòng trong khoảng ERROR_REPORT_COOLDOWN_MINUTES phút gần nhất
- Nếu có lỗi → gọi customize_erpnext.api.biometric.error_report.send_biometric_error_report
- Cooldown: không gửi lặp lại nếu chưa đủ ERROR_REPORT_COOLDOWN_MINUTES phút
"""

import os
import re
import datetime
import json
import requests
import socket

current_dir = os.path.dirname(os.path.abspath(__file__))


def _get_config():
    import local_config
    return local_config


def collect_recent_errors(minutes=60):
    """
    Đọc log lỗi trong N phút gần nhất.

    Returns:
        dict: {
            'error_log': [dòng từ error.log],
            'main_log': [dòng ERROR/CRITICAL từ logs.log]
        }
    """
    config = _get_config()
    logs_dir = os.path.join(current_dir, config.LOGS_DIRECTORY)
    cutoff = datetime.datetime.now() - datetime.timedelta(minutes=minutes)

    # Regex parse dòng log: "2026-03-18 08:03:12,123\tLEVEL\tMessage"
    log_pattern = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+\t(\w+)\t(.+)$'
    )

    def parse_and_filter(filepath, level_filter=None):
        """Đọc file log, trả về các dòng gần đây theo cutoff."""
        lines = []
        if not os.path.exists(filepath):
            return lines
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                for raw in f:
                    raw = raw.rstrip('\n').rstrip('\r')
                    if not raw.strip():
                        continue
                    m = log_pattern.match(raw)
                    if not m:
                        # Dòng continuation (traceback) — gắn vào dòng trước nếu có
                        if lines:
                            lines[-1] = lines[-1] + '\n    ' + raw
                        continue
                    dt_str, level, _ = m.group(1), m.group(2), m.group(3)
                    try:
                        dt = datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        continue
                    if dt < cutoff:
                        continue
                    if level_filter and level not in level_filter:
                        continue
                    lines.append(raw)
        except Exception as e:
            print(f"[send_error_report] Cannot read {filepath}: {e}")
        return lines

    error_log_path = os.path.join(logs_dir, 'error.log')
    main_log_path  = os.path.join(logs_dir, 'logs.log')

    error_lines = parse_and_filter(error_log_path, level_filter=None)
    main_lines  = parse_and_filter(main_log_path, level_filter={'ERROR', 'CRITICAL'})

    return {
        'error_log': error_lines,
        'main_log': main_lines
    }


def build_email_content(errors, minutes=60):
    """
    Tạo subject và body email từ dict lỗi.

    Returns:
        tuple: (subject: str, body: str)
    """
    config = _get_config()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total = len(errors['error_log']) + len(errors['main_log'])

    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = 'unknown'

    subject = f"[Biometric Sync Tool] CẢNH BÁO: {total} lỗi phát hiện lúc {now_str}"

    lines = [
        f"Thời gian phát hiện : {now_str}",
        f"Máy chủ ERPNext     : {config.ERPNEXT_URL}",
        f"Tổng số lỗi         : {total}",       
        f"Xem chi tiết logs : {config.ERPNEXT_URL}/erpnext-sync-all-logs",
        f"(Không gửi lại trong  : {minutes} phút tiếp theo)",
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

    lines.append("=" * 70)
    lines.append("Email này được gửi tự động bởi biometric-attendance-sync-tool.")
    lines.append("=" * 70)

    return subject, "\n".join(lines)


def send_report(errors):
    """
    Gửi email báo cáo lỗi qua Frappe API.

    Args:
        errors (dict): Kết quả từ collect_recent_errors()

    Returns:
        bool: True nếu gửi thành công
    """
    config = _get_config()
    minutes = getattr(config, 'ERROR_REPORT_COOLDOWN_MINUTES', 60)
    subject, body = build_email_content(errors, minutes=minutes)
    recipients = getattr(config, 'ERROR_REPORT_RECIPIENTS', [])

    url = f"{config.ERPNEXT_URL}/api/method/customize_erpnext.api.biometric.error_report.send_biometric_error_report"
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


def run(force=False):
    """
    Hàm chính — được gọi từ erpnext_sync_all.py hoặc chạy thủ công.

    Args:
        force (bool): Nếu True bỏ qua kiểm tra cooldown (dùng để test)

    Returns:
        dict: {'sent': bool, 'error_count': int}
    """
    import local_config

    if not getattr(local_config, 'ENABLE_ERROR_REPORT_EMAIL', False):
        print("[send_error_report] Disabled (ENABLE_ERROR_REPORT_EMAIL=False)")
        return {'sent': False, 'error_count': 0}

    if not force and not local_config.should_send_error_report():
        last = local_config.get_last_error_report_sent()
        elapsed = int((datetime.datetime.now() - last).total_seconds() / 60) if last else 0
        remaining = local_config.ERROR_REPORT_COOLDOWN_MINUTES - elapsed
        print(f"[send_error_report] Cooldown active — còn {remaining} phút")
        return {'sent': False, 'error_count': 0}

    minutes = getattr(local_config, 'ERROR_REPORT_COOLDOWN_MINUTES', 60)
    errors = collect_recent_errors(minutes=minutes)
    total = len(errors['error_log']) + len(errors['main_log'])

    if total == 0:
        print(f"[send_error_report] Không có lỗi trong {minutes} phút qua")
        return {'sent': False, 'error_count': 0}

    print(f"[send_error_report] Phát hiện {total} lỗi — đang gửi email...")
    success = send_report(errors)

    if success:
        local_config.set_last_error_report_sent()

    return {'sent': success, 'error_count': total}


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
