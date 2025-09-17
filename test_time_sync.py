#!/usr/bin/env python3
"""
Test script for time synchronization functionality
Allows testing time sync without running the full sync service
"""

import os
import sys
import datetime
import argparse

# Add current directory to path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import local_config

def main():
    parser = argparse.ArgumentParser(description='Test Time Sync to Biometric Devices')
    parser.add_argument('--force', action='store_true',
                       help='Force sync even if time difference is small')
    parser.add_argument('--device', type=str,
                       help='Sync time to specific device ID only')
    parser.add_argument('--threshold', type=int,
                       help=f'Override time difference threshold (default: {local_config.TIME_SYNC_MAX_DIFF_SECONDS}s)')

    args = parser.parse_args()

    print("🕒 ERPNext Time Sync Test Tool")
    print("=" * 50)
    print(f"Server time: {datetime.datetime.now()}")
    print(f"Time sync enabled: {local_config.ENABLE_TIME_SYNC}")
    print(f"Threshold: {local_config.TIME_SYNC_MAX_DIFF_SECONDS}s")
    print(f"Timeout: {local_config.TIME_SYNC_TIMEOUT_SECONDS}s")
    print("=" * 50)

    # Override threshold if specified
    if args.threshold:
        original_threshold = local_config.TIME_SYNC_MAX_DIFF_SECONDS
        local_config.TIME_SYNC_MAX_DIFF_SECONDS = args.threshold
        print(f"⚠️ Threshold overridden: {original_threshold}s → {args.threshold}s")

    # Filter devices if specific device requested
    devices_to_sync = local_config.devices
    if args.device:
        devices_to_sync = [d for d in local_config.devices if d['device_id'] == args.device]
        if not devices_to_sync:
            print(f"❌ Device '{args.device}' not found in configuration")
            print("Available devices:")
            for device in local_config.devices:
                print(f"  - {device['device_id']} ({device['ip']})")
            sys.exit(1)
        print(f"🎯 Syncing to specific device: {args.device}")

    # Execute time sync
    print("\n🚀 Starting time synchronization...")
    try:
        results = local_config.sync_time_to_devices(devices_list=devices_to_sync, force=args.force)

        # Display detailed results
        print(f"\n📊 RESULTS SUMMARY:")
        print(f"   Total devices: {results['total_devices']}")
        print(f"   Successfully synced: {results['success_count']}")
        print(f"   Skipped (within tolerance): {results['skipped_count']}")
        print(f"   Failed: {results['failed_count']}")

        if results['details']:
            print(f"\n📋 DEVICE DETAILS:")
            for detail in results['details']:
                device_id = detail['device_id']
                device_ip = detail['device_ip']

                if detail['success'] and detail['new_time']:
                    time_diff = detail['time_diff_seconds']
                    old_time = detail['old_time'].strftime('%H:%M:%S') if detail['old_time'] else 'N/A'
                    new_time = detail['new_time'].strftime('%H:%M:%S') if detail['new_time'] else 'N/A'
                    print(f"   ✅ {device_id} ({device_ip}): SYNCED")
                    print(f"      Old time: {old_time}, New time: {new_time}")
                    print(f"      Time difference: {time_diff:.1f}s")
                elif detail['success'] and not detail['new_time']:
                    time_diff = detail['time_diff_seconds']
                    device_time = detail['old_time'].strftime('%H:%M:%S') if detail['old_time'] else 'N/A'
                    print(f"   ⏭️ {device_id} ({device_ip}): SKIPPED")
                    print(f"      Device time: {device_time}")
                    print(f"      Time difference: {time_diff:.1f}s (within tolerance)")
                else:
                    print(f"   ❌ {device_id} ({device_ip}): FAILED")
                    print(f"      Error: {detail['message']}")

        # Overall result
        if results['success_count'] > 0:
            print(f"\n✅ Time sync completed successfully!")
        elif results['skipped_count'] > 0:
            print(f"\n⏭️ All devices skipped (time within tolerance)")
        else:
            print(f"\n❌ Time sync failed for all devices")
            sys.exit(1)

        # Log file location
        print(f"\n📝 Detailed logs: {local_config.TIME_SYNC_LOG_FILE}")

    except Exception as e:
        print(f"\n❌ Time sync failed with error: {e}")
        import traceback
        print(f"Error details: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()