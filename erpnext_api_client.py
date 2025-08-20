#!/usr/bin/env python3

import requests
import json
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class ERPNextAPIClient:
    """
    ERPNext REST API Client for standalone operation
    """
    
    def __init__(self, base_url, api_key, api_secret):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        
        self.session.headers.update({
            'Authorization': f'token {api_key}:{api_secret}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def _make_request(self, method, endpoint, params=None, data=None):
        """Make HTTP request to ERPNext API"""
        url = urljoin(self.base_url, endpoint)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {url} - {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {str(e)}")
            raise
    

    def get_employees_with_fingerprints(self):
        """Get all active employees with fingerprint data - individual calls only"""
        try:
            logger.info("Fetching employees with fingerprint data from ERPNext API...")
            
            # Get employees first, then individual fingerprint calls
            endpoint = '/api/resource/Employee'
            params = {
                'filters': json.dumps({"status": "Active"}),
                'fields': json.dumps(["name", "employee", "employee_name", "attendance_device_id", 
                                    "custom_privilege", "custom_password", "status"]),
                'limit_page_length': 0
            }
            
            response = self._make_request('GET', endpoint, params=params)
            employees = response.get('data', [])
            
            employees_with_fingerprints = []
            
            for emp in employees:
                if not emp.get('attendance_device_id'):
                    continue
                
                # Get fingerprints using individual Employee document call
                fingerprints = self.get_fingerprint_data(emp['name'])
                
                if fingerprints:
                    privilege_str = emp.get('custom_privilege', 'USER_DEFAULT')
                    try:
                        from zk import const
                        privilege = const.USER_ADMIN if privilege_str == "USER_ADMIN" else const.USER_DEFAULT
                    except ImportError:
                        privilege = 14 if privilege_str == "USER_ADMIN" else 0
                    
                    password_int = emp.get('custom_password')
                    password = str(password_int) if password_int and password_int != 0 else ""
                    
                    employee_data = {
                        "employee_id": emp['name'],
                        "employee": emp['employee'],
                        "employee_name": emp['employee_name'],
                        "attendance_device_id": emp['attendance_device_id'],
                        "password": password,
                        "privilege": privilege,
                        "privilege_str": privilege_str,
                        "fingerprints": fingerprints
                    }
                    
                    employees_with_fingerprints.append(employee_data)
            
            logger.info(f"Found {len(employees_with_fingerprints)} employees with fingerprint data")
            return employees_with_fingerprints
            
        except Exception as e:
            logger.error(f"Error fetching employees with fingerprints: {str(e)}")
            return []
    
    
    def get_fingerprint_data(self, employee_id):
        """Get fingerprint data for an employee"""
        try:
            endpoint = f'/api/resource/Employee/{employee_id}'
            response = self._make_request('GET', endpoint)
            employee = response.get('data', {})
            
            fingerprints = []
            if 'custom_fingerprints' in employee:
                for fp in employee['custom_fingerprints']:
                    if fp.get('template_data'):
                        fingerprints.append({
                            'finger_index': fp.get('finger_index'),
                            'template_data': fp.get('template_data'),
                            'quality_score': fp.get('quality_score', 0),
                            'finger_name': fp.get('finger_name', '')
                        })
            
            return fingerprints
            
        except Exception as e:
            logger.error(f"Error getting fingerprint data for employee {employee_id}: {str(e)}")
            return []
    
    def get_changed_employees_with_fingerprints(self, since_datetime):
        """Get employees with fingerprint data modified since datetime - with fallback"""
        try:
            logger.info(f"Fetching employees with fingerprint changes since {since_datetime}...")
            
            # Get employees with fingerprints and check modification dates
            return self._get_changed_employees_fallback(since_datetime)
            
        except Exception as e:
            logger.error(f"Error fetching changed employees: {str(e)}")
            return []
    
    
    def _get_changed_employees_fallback(self, since_datetime):
        """Fallback method: check Employee modifications since datetime"""
        try:
            since_str = since_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            # Get employees modified since datetime
            endpoint = '/api/resource/Employee'
            params = {
                'filters': json.dumps({
                    "status": "Active",
                    "modified": [">=", since_str]
                }),
                'fields': json.dumps(["name", "employee", "employee_name", "attendance_device_id", 
                                    "custom_privilege", "custom_password", "status", "modified"]),
                'limit_page_length': 0
            }
            
            response = self._make_request('GET', endpoint, params=params)
            employees = response.get('data', [])
            
            employees_with_fingerprints = []
            
            for emp in employees:
                if not emp.get('attendance_device_id'):
                    continue
                
                fingerprints = self.get_fingerprint_data(emp['name'])
                
                if fingerprints:
                    privilege_str = emp.get('custom_privilege', 'USER_DEFAULT')
                    try:
                        from zk import const
                        privilege = const.USER_ADMIN if privilege_str == "USER_ADMIN" else const.USER_DEFAULT
                    except ImportError:
                        privilege = 14 if privilege_str == "USER_ADMIN" else 0
                    
                    password_int = emp.get('custom_password')
                    password = str(password_int) if password_int and password_int != 0 else ""
                    
                    employee_data = {
                        "employee_id": emp['name'],
                        "employee": emp['employee'],
                        "employee_name": emp['employee_name'],
                        "attendance_device_id": emp['attendance_device_id'],
                        "password": password,
                        "privilege": privilege,
                        "privilege_str": privilege_str,
                        "fingerprints": fingerprints
                    }
                    
                    employees_with_fingerprints.append(employee_data)
            
            logger.info(f"Fallback method found {len(employees_with_fingerprints)} employees with changes")
            return employees_with_fingerprints
            
        except Exception as e:
            logger.error(f"Fallback method failed: {str(e)}")
            return []
    
    def get_left_employees_with_device_id(self):
        """Get employees with status 'Left' who have attendance_device_id and relieving_date <= today"""
        try:
            logger.info("Fetching Left employees with device IDs (with date validation)...")
            
            endpoint = '/api/resource/Employee'
            params = {
                'filters': json.dumps({"status": "Left", "attendance_device_id": ["!=", ""]}),
                'fields': json.dumps(["name", "employee", "employee_name", "attendance_device_id", "status", "relieving_date"]),
                'limit_page_length': 0
            }
            
            response = self._make_request('GET', endpoint, params=params)
            employees = response.get('data', [])
            
            from datetime import datetime, date
            today = date.today()
            
            left_employees = []
            skipped_count = 0
            
            for emp in employees:
                if not emp.get('attendance_device_id'):
                    continue
                    
                # Check relieving_date - only process if current date > relieving_date
                relieving_date = emp.get('relieving_date')
                should_process = True
                
                if relieving_date:
                    try:
                        # Parse relieving_date (format: YYYY-MM-DD)
                        if isinstance(relieving_date, str):
                            relieving_dt = datetime.strptime(relieving_date, '%Y-%m-%d').date()
                        else:
                            relieving_dt = relieving_date
                        
                        # Only process if today > relieving_date
                        if today <= relieving_dt:
                            should_process = False
                            skipped_count += 1
                            logger.debug(f"Skipping {emp['employee']} - relieving date {relieving_date} not yet passed")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid relieving_date format for {emp['employee']}: {relieving_date} - {str(e)}")
                        # If can't parse date, skip for safety
                        should_process = False
                        skipped_count += 1
                else:
                    # No relieving_date specified - skip for safety
                    logger.warning(f"No relieving_date for Left employee {emp['employee']} - skipping")
                    should_process = False
                    skipped_count += 1
                
                if should_process:
                    employee_data = {
                        "employee_id": emp['name'],
                        "employee": emp['employee'],
                        "employee_name": emp['employee_name'],
                        "attendance_device_id": emp['attendance_device_id'],
                        "status": emp['status'],
                        "relieving_date": relieving_date
                    }
                    left_employees.append(employee_data)
            
            logger.info(f"Found {len(left_employees)} Left employees ready for template clearing")
            if skipped_count > 0:
                logger.info(f"Skipped {skipped_count} Left employees (relieving date not yet passed or missing)")
            
            return left_employees
            
        except Exception as e:
            logger.error(f"Error fetching Left employees: {str(e)}")
            return []

    def delete_employee_fingerprints(self, employee_id):
        """Delete all fingerprint records for an employee from ERPNext"""
        try:
            logger.info(f"Deleting fingerprint records for employee {employee_id} from ERPNext...")
            
            # First get all fingerprint records for this employee
            endpoint = f'/api/resource/Employee/{employee_id}'
            response = self._make_request('GET', endpoint)
            employee = response.get('data', {})
            
            fingerprint_records = employee.get('custom_fingerprints', [])
            
            if not fingerprint_records:
                logger.info(f"No fingerprint records found for employee {employee_id}")
                return {"success": True, "deleted_count": 0, "message": "No fingerprint records to delete"}
            
            deleted_count = 0
            failed_deletions = []
            
            # Delete each fingerprint record
            for fp_record in fingerprint_records:
                fp_name = fp_record.get('name')
                if fp_name:
                    try:
                        delete_endpoint = f'/api/resource/Fingerprint Data/{fp_name}'
                        self._make_request('DELETE', delete_endpoint)
                        deleted_count += 1
                        logger.debug(f"Deleted fingerprint record {fp_name}")
                    except Exception as e:
                        failed_deletions.append(f"{fp_name}: {str(e)}")
                        logger.error(f"Failed to delete fingerprint record {fp_name}: {str(e)}")
            
            if failed_deletions:
                logger.warning(f"Some fingerprint deletions failed for {employee_id}: {len(failed_deletions)} failures")
                return {
                    "success": False,
                    "deleted_count": deleted_count,
                    "failed_count": len(failed_deletions),
                    "failed_deletions": failed_deletions,
                    "message": f"Deleted {deleted_count} records, {len(failed_deletions)} failures"
                }
            else:
                logger.info(f"Successfully deleted {deleted_count} fingerprint records for employee {employee_id}")
                return {
                    "success": True,
                    "deleted_count": deleted_count,
                    "message": f"Successfully deleted {deleted_count} fingerprint records"
                }
                
        except Exception as e:
            logger.error(f"Error deleting fingerprints for employee {employee_id}: {str(e)}")
            return {
                "success": False,
                "deleted_count": 0,
                "message": f"Error deleting fingerprints: {str(e)}"
            }

    def test_connection(self):
        """Test API connection"""
        try:
            endpoint = '/api/method/frappe.auth.get_logged_user'
            self._make_request('GET', endpoint)
            logger.info("ERPNext API connection successful")
            return True
        except Exception as e:
            logger.error(f"ERPNext API connection failed: {str(e)}")
            return False