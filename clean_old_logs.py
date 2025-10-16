#!/usr/bin/env python3

"""
Clean Old Logs - Automatic log file cleanup utility

This utility performs automatic cleanup of old log files:
1. Remove log lines older than CLEAN_OLD_LOGS_DAYS from active log files
2. Delete empty rotated log files (error.log.1, error.log.2, etc.)
3. Run once per day (tracked via marker file)

Usage:
    python3 clean_old_logs.py [--dry-run] [--force]
"""

import os
import sys
import datetime
import glob
import re

# Add parent directory to path to import local_config
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import local_config

# Log files to clean (with timestamp parsing)
LOG_FILES_TO_CLEAN = [
    'logs/time_sync.log',
    'logs/logs.log',
    'logs/logs_resync.log',
    'logs/error.log',
    'logs/error_duplicate.log',
    'logs/clean_data_employee_left/clean_left_employees.log'
]

# Marker file to track last run
MARKER_FILE = os.path.join(local_config.LOGS_DIRECTORY, '.last_clean_logs_date')


def get_last_clean_date():
    """Get the last date when log cleanup was executed"""
    if os.path.exists(MARKER_FILE):
        try:
            with open(MARKER_FILE, 'r') as f:
                date_str = f.read().strip()
                return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return None
    return None


def set_last_clean_date(date=None):
    """Set the last date when log cleanup was executed"""
    if date is None:
        date = datetime.date.today()

    os.makedirs(os.path.dirname(MARKER_FILE), exist_ok=True)

    with open(MARKER_FILE, 'w') as f:
        f.write(date.strftime('%Y-%m-%d'))


def should_run_cleanup():
    """Check if should run cleanup (once per day)"""
    clean_days = getattr(local_config, 'CLEAN_OLD_LOGS_DAYS', 0)

    if clean_days == 0:
        return False

    last_run_date = get_last_clean_date()
    today = datetime.date.today()

    # Run if never run before or last run was on a different day
    return last_run_date is None or last_run_date < today


def parse_log_timestamp(line):
    """Parse timestamp from log line

    Supports formats:
    - 2025-10-15 08:09:39,558
    - [2025-10-15 08:09:39]
    - 2025-10-15 08:09:39

    Returns:
        datetime.datetime or None if parsing fails
    """
    # Try format: 2025-10-15 08:09:39,558
    match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
    if match:
        try:
            return datetime.datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
        except:
            pass

    # Try format: [2025-10-15 08:09:39]
    match = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
    if match:
        try:
            return datetime.datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
        except:
            pass

    return None


def clean_log_file(log_file_path, cutoff_date, dry_run=False):
    """Clean old lines from a log file

    Args:
        log_file_path (str): Path to log file
        cutoff_date (datetime.date): Remove lines older than this date
        dry_run (bool): If True, only show what would be cleaned

    Returns:
        dict: Statistics about cleaning operation
    """
    if not os.path.exists(log_file_path):
        return {
            "file": log_file_path,
            "exists": False,
            "lines_kept": 0,
            "lines_removed": 0,
            "size_before": 0,
            "size_after": 0
        }

    size_before = os.path.getsize(log_file_path)
    lines_kept = 0
    lines_removed = 0
    kept_lines = []

    try:
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line_timestamp = parse_log_timestamp(line)

                if line_timestamp is None:
                    # Keep lines without timestamp (continuation lines, etc.)
                    kept_lines.append(line)
                    lines_kept += 1
                elif line_timestamp.date() >= cutoff_date:
                    # Keep recent lines
                    kept_lines.append(line)
                    lines_kept += 1
                else:
                    # Remove old lines
                    lines_removed += 1

        if not dry_run and lines_removed > 0:
            # Write back only kept lines
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.writelines(kept_lines)

        size_after = os.path.getsize(log_file_path) if not dry_run else (size_before - (size_before * lines_removed // (lines_kept + lines_removed + 1)))

        return {
            "file": log_file_path,
            "exists": True,
            "lines_kept": lines_kept,
            "lines_removed": lines_removed,
            "size_before": size_before,
            "size_after": size_after if not dry_run else size_after,
            "size_freed": size_before - size_after
        }

    except Exception as e:
        return {
            "file": log_file_path,
            "exists": True,
            "error": str(e),
            "lines_kept": 0,
            "lines_removed": 0,
            "size_before": size_before,
            "size_after": size_before
        }


def delete_empty_rotated_logs(logs_directory, dry_run=False):
    """Delete empty rotated log files (*.log.1, *.log.2, etc.)

    Args:
        logs_directory (str): Path to logs directory
        dry_run (bool): If True, only show what would be deleted

    Returns:
        list: List of deleted files
    """
    deleted_files = []

    # Find all rotated log files (*.log.1, *.log.2, etc.)
    pattern = os.path.join(logs_directory, '**', '*.log.*')
    rotated_logs = glob.glob(pattern, recursive=True)

    for log_file in rotated_logs:
        # Check if it's a numbered rotation (e.g., error.log.1, not error.log.gz)
        if re.match(r'.*\.log\.\d+$', log_file):
            try:
                file_size = os.path.getsize(log_file)

                if file_size == 0:
                    if not dry_run:
                        os.remove(log_file)
                    deleted_files.append({
                        "file": log_file,
                        "size": file_size,
                        "reason": "empty"
                    })
            except Exception as e:
                print(f"Error processing {log_file}: {e}")

    return deleted_files


def format_size(bytes_size):
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def run_cleanup(dry_run=False, force=False):
    """Main cleanup function

    Args:
        dry_run (bool): If True, only show what would be cleaned
        force (bool): If True, run even if already ran today

    Returns:
        dict: Summary of cleanup operation
    """
    clean_days = getattr(local_config, 'CLEAN_OLD_LOGS_DAYS', 0)

    if clean_days == 0:
        return {
            "success": False,
            "message": "Log cleanup is disabled (CLEAN_OLD_LOGS_DAYS = 0)"
        }

    if not force and not should_run_cleanup():
        last_run = get_last_clean_date()
        return {
            "success": False,
            "message": f"Log cleanup already ran today (last run: {last_run})"
        }

    print("=" * 80)
    print(f"LOG CLEANUP {'(DRY RUN)' if dry_run else ''}")
    print("=" * 80)
    print(f"Configuration:")
    print(f"  - Clean logs older than: {clean_days} days")

    cutoff_date = datetime.date.today() - datetime.timedelta(days=clean_days)
    print(f"  - Cutoff date: {cutoff_date}")
    print(f"  - Mode: {'Dry run (no changes)' if dry_run else 'Active (will modify files)'}")
    print()

    # Clean log files
    print("Cleaning log files...")
    print("-" * 80)

    results = []
    total_size_freed = 0

    for log_file in LOG_FILES_TO_CLEAN:
        result = clean_log_file(log_file, cutoff_date, dry_run)
        results.append(result)

        if result.get("exists", False):
            if "error" in result:
                print(f"✗ {result['file']}: ERROR - {result['error']}")
            else:
                status = "✓" if result["lines_removed"] > 0 else "•"
                print(f"{status} {result['file']}")
                print(f"    Lines: {result['lines_kept']} kept, {result['lines_removed']} removed")
                print(f"    Size: {format_size(result['size_before'])} → {format_size(result['size_after'])} (freed {format_size(result['size_freed'])})")
                total_size_freed += result.get("size_freed", 0)
        else:
            print(f"• {result['file']}: File not found")

    print()
    print("-" * 80)

    # Delete empty rotated logs
    print("Deleting empty rotated log files...")
    print("-" * 80)

    deleted_files = delete_empty_rotated_logs(local_config.LOGS_DIRECTORY, dry_run)

    if deleted_files:
        for deleted in deleted_files:
            print(f"✓ Deleted: {deleted['file']} ({deleted['reason']})")
        print(f"\nDeleted {len(deleted_files)} empty rotated log file(s)")
    else:
        print("• No empty rotated log files found")

    print()
    print("=" * 80)
    print(f"CLEANUP COMPLETED {'(DRY RUN)' if dry_run else ''}")
    print(f"Total space freed: {format_size(total_size_freed)}")
    print(f"Empty files deleted: {len(deleted_files)}")
    print("=" * 80)

    # Update marker file
    if not dry_run:
        set_last_clean_date()

    return {
        "success": True,
        "cleaned_files": len([r for r in results if r.get("exists", False) and r.get("lines_removed", 0) > 0]),
        "deleted_files": len(deleted_files),
        "total_size_freed": total_size_freed,
        "results": results
    }


def main():
    """Main function for command line usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Clean old log files - Remove lines older than N days')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be cleaned without actually doing it')
    parser.add_argument('--force', action='store_true', help='Force cleanup even if already ran today')

    args = parser.parse_args()

    try:
        result = run_cleanup(dry_run=args.dry_run, force=args.force)

        if result["success"]:
            exit(0)
        else:
            print(result["message"])
            exit(1)

    except Exception as e:
        print(f"Fatal error during cleanup: {str(e)}")
        raise


if __name__ == "__main__":
    main()
