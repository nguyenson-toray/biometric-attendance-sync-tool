#!/usr/bin/env python3
"""
Delete Overtime Registration from ERPNext Database

This script deletes overtime registration records from ERPNext database based on date filter.
It removes child records (Overtime Registration Detail) matching the filter dates,
then removes parent records (Overtime Registration) that have no remaining children.

Usage:
    python 05.delete_ot_in_erpnext_db.py          # Dry run (default)
    python 05.delete_ot_in_erpnext_db.py --execute  # Actually delete records

Configuration:
    RANGE_DATE_FILTER - List of dates in 'YYYYMMDD' format to delete
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
import pymysql

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Date range to delete (format: ['YYYYMMDD', 'YYYYMMDD'] - [from_date, to_date])
RANGE_DATE_FILTER = ['20251115', '20251225']  # Delete all records from 2025-10-26 to 2025-11-25

# =============================================================================
# DATABASE CONNECTION
# =============================================================================

def get_site_config():
    """Get database configuration from site_config.json"""
    # Get current script directory and navigate to bench path
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    # From apps/biometric-attendance-sync-tool, go up 2 levels to reach bench root
    bench_path = os.path.abspath(os.path.join(current_script_dir, '..', '..'))
    sites_path = os.path.join(bench_path, 'sites')

    # Try to get current site from currentsite.txt
    current_site_file = os.path.join(sites_path, 'currentsite.txt')

    if os.path.exists(current_site_file):
        with open(current_site_file, 'r') as f:
            current_site = f.read().strip()
    else:
        # Find first site directory
        for item in os.listdir(sites_path):
            site_path = os.path.join(sites_path, item, 'site_config.json')
            if os.path.exists(site_path):
                current_site = item
                break
        else:
            raise FileNotFoundError("No site found in sites directory")

    # Read site_config.json
    site_config_path = os.path.join(sites_path, current_site, 'site_config.json')

    if not os.path.exists(site_config_path):
        raise FileNotFoundError(f"site_config.json not found at {site_config_path}")

    with open(site_config_path, 'r') as f:
        site_config = json.load(f)

    logger.info(f"Using site: {current_site}")

    return site_config


def get_db_connection():
    """Create database connection using site config"""
    site_config = get_site_config()

    db_host = site_config.get('db_host', 'localhost')
    db_name = site_config.get('db_name')
    db_password = site_config.get('db_password')

    # Default user is same as db_name for Frappe
    db_user = site_config.get('db_user', db_name)

    if not db_name or not db_password:
        raise ValueError("Database name or password not found in site_config.json")

    logger.info(f"Connecting to database: {db_name}@{db_host}")

    connection = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

    return connection


# =============================================================================
# DELETE OPERATIONS
# =============================================================================

def convert_date_format(date_str):
    """Convert YYYYMMDD to YYYY-MM-DD format"""
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"


def get_detail_records_to_delete(connection, RANGE_DATE_FILTER):
    """Get list of Overtime Registration Detail records to delete

    Args:
        connection: Database connection
        RANGE_DATE_FILTER: List of [from_date, to_date] in YYYYMMDD format

    Returns:
        list: List of detail records to delete
    """
    # Convert date format
    from_date = convert_date_format(RANGE_DATE_FILTER[0])
    to_date = convert_date_format(RANGE_DATE_FILTER[1])

    with connection.cursor() as cursor:
        # Query with date range (BETWEEN)
        query = """
            SELECT name, parent, employee, employee_name, date, begin_time, end_time
            FROM `tabOvertime Registration Detail`
            WHERE date BETWEEN %s AND %s
            ORDER BY parent, date, employee
        """

        cursor.execute(query, (from_date, to_date))
        records = cursor.fetchall()

    return records


def get_parent_records_with_no_children(connection, parent_names):
    """Check which parent records will have no children after deletion

    Args:
        connection: Database connection
        parent_names: Set of parent names that have children to be deleted

    Returns:
        list: List of parent names that will have no remaining children
    """
    if not parent_names:
        return []

    orphaned_parents = []

    with connection.cursor() as cursor:
        for parent_name in parent_names:
            # Count remaining children (excluding those to be deleted)
            query = """
                SELECT COUNT(*) as count
                FROM `tabOvertime Registration Detail`
                WHERE parent = %s
            """
            cursor.execute(query, (parent_name,))
            result = cursor.fetchone()

            # This count includes records to be deleted
            # We'll check after deletion which parents have 0 children

    return orphaned_parents


def delete_ot_records(dry_run=True):
    """Main function to delete OT records

    Args:
        dry_run: If True, only show what would be deleted without actually deleting

    Returns:
        dict: Summary of deletion results
    """
    logger.info("=" * 80)
    logger.info("DELETE OVERTIME REGISTRATION RECORDS FROM ERPNEXT")
    logger.info("=" * 80)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    logger.info(f"Date filter: {RANGE_DATE_FILTER}")
    logger.info("")

    # Convert dates for display
    formatted_dates = [convert_date_format(d) for d in RANGE_DATE_FILTER]
    logger.info(f"Dates to delete: {formatted_dates}")
    logger.info("")

    try:
        # Connect to database
        connection = get_db_connection()
        logger.info("Database connection established")
        logger.info("")

        # Get records to delete
        detail_records = get_detail_records_to_delete(connection, RANGE_DATE_FILTER)

        if not detail_records:
            logger.info("No Overtime Registration Detail records found for the specified dates")
            return {
                'success': True,
                'detail_records_deleted': 0,
                'parent_records_deleted': 0,
                'message': 'No records found to delete'
            }

        # Group by parent
        records_by_parent = {}
        for record in detail_records:
            parent = record['parent']
            if parent not in records_by_parent:
                records_by_parent[parent] = []
            records_by_parent[parent].append(record)

        logger.info(f"Found {len(detail_records)} detail record(s) to delete")
        logger.info(f"Affecting {len(records_by_parent)} parent registration(s)")
        logger.info("")

        # Display records to be deleted
        logger.info("-" * 80)
        logger.info("DETAIL RECORDS TO DELETE:")
        logger.info("-" * 80)

        for parent, records in records_by_parent.items():
            logger.info(f"\nParent: {parent} ({len(records)} record(s))")
            for rec in records:
                logger.info(f"  - {rec['name']}: {rec['employee']} ({rec['employee_name']}) | {rec['date']} | {rec['begin_time']}-{rec['end_time']}")

        logger.info("")

        # Check which parents will become orphaned
        with connection.cursor() as cursor:
            parents_to_delete = []
            draft_count = 0
            submitted_count = 0

            for parent_name, records in records_by_parent.items():
                # Count total children for this parent
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM `tabOvertime Registration Detail`
                    WHERE parent = %s
                """, (parent_name,))
                result = cursor.fetchone()
                total_children = result['total']

                # Get parent docstatus
                cursor.execute("""
                    SELECT docstatus
                    FROM `tabOvertime Registration`
                    WHERE name = %s
                """, (parent_name,))
                parent_result = cursor.fetchone()
                docstatus = parent_result['docstatus'] if parent_result else 0
                status_text = "Draft" if docstatus == 0 else "Submitted" if docstatus == 1 else "Cancelled"

                # If all children will be deleted, parent should be deleted too
                if total_children == len(records):
                    parents_to_delete.append(parent_name)
                    if docstatus == 0:
                        draft_count += 1
                    elif docstatus == 1:
                        submitted_count += 1
                    logger.info(f"Parent {parent_name} [{status_text}] will be deleted (all {total_children} children removed)")
                else:
                    remaining = total_children - len(records)
                    logger.info(f"Parent {parent_name} [{status_text}] will keep {remaining} of {total_children} children")

            logger.info("")
            logger.info(f"Summary: {draft_count} Draft + {submitted_count} Submitted = {len(parents_to_delete)} parent(s) to delete")

        logger.info("")

        if dry_run:
            logger.info("=" * 80)
            logger.info("DRY RUN COMPLETE - No changes made")
            logger.info("=" * 80)
            logger.info(f"Would delete {len(detail_records)} detail record(s)")
            logger.info(f"Would delete {len(parents_to_delete)} parent registration(s)")
            logger.info("")
            logger.info("Run with --execute to actually delete these records")

            connection.close()

            return {
                'success': True,
                'dry_run': True,
                'detail_records_to_delete': len(detail_records),
                'parent_records_to_delete': len(parents_to_delete),
                'parent_names_to_delete': parents_to_delete,
                'message': 'Dry run complete'
            }

        # Execute deletion
        logger.info("=" * 80)
        logger.info("EXECUTING DELETION...")
        logger.info("=" * 80)

        with connection.cursor() as cursor:
            # Delete detail records
            from_date = convert_date_format(RANGE_DATE_FILTER[0])
            to_date = convert_date_format(RANGE_DATE_FILTER[1])

            delete_detail_query = """
                DELETE FROM `tabOvertime Registration Detail`
                WHERE date BETWEEN %s AND %s
            """

            cursor.execute(delete_detail_query, (from_date, to_date))
            deleted_details = cursor.rowcount
            logger.info(f"Deleted {deleted_details} detail record(s)")

            # Delete orphaned parent records
            deleted_parents = 0
            if parents_to_delete:
                parent_placeholders = ', '.join(['%s'] * len(parents_to_delete))
                delete_parent_query = f"""
                    DELETE FROM `tabOvertime Registration`
                    WHERE name IN ({parent_placeholders})
                """

                cursor.execute(delete_parent_query, parents_to_delete)
                deleted_parents = cursor.rowcount
                logger.info(f"Deleted {deleted_parents} parent registration(s)")

        # Commit changes
        connection.commit()
        logger.info("")
        logger.info("Changes committed to database")

        connection.close()

        logger.info("")
        logger.info("=" * 80)
        logger.info("DELETION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Detail records deleted: {deleted_details}")
        logger.info(f"Parent records deleted: {deleted_parents}")

        return {
            'success': True,
            'dry_run': False,
            'detail_records_deleted': deleted_details,
            'parent_records_deleted': deleted_parents,
            'parent_names_deleted': parents_to_delete,
            'message': 'Deletion complete'
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Delete Overtime Registration records from ERPNext database'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually delete records (default is dry run)'
    )

    args = parser.parse_args()

    # Run deletion
    dry_run = not args.execute
    result = delete_ot_records(dry_run=dry_run)

    if result['success']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
