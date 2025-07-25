import frappe
from frappe.utils import get_datetime
import pytz

def get_user_timezone():
    """Get user's timezone"""
    user_tz = frappe.db.get_value("User", frappe.session.user, "time_zone")
    if not user_tz:
        user_tz = frappe.utils.get_time_zone()
    return pytz.timezone(user_tz)

def convert_to_utc(local_dt):
    """Convert local datetime to UTC"""
    if not local_dt:
        return None
        
    user_tz = get_user_timezone()
    
    # Make sure datetime has timezone info
    if not local_dt.tzinfo:
        local_dt = user_tz.localize(local_dt)
    
    # Convert to UTC
    utc_dt = local_dt.astimezone(pytz.UTC)
    return utc_dt

def convert_to_local(utc_dt, user=None):
    """Convert UTC datetime to local timezone"""
    if not utc_dt:
        return None
        
    user_tz = get_user_timezone()
    
    # Make sure datetime has UTC timezone
    if not utc_dt.tzinfo:
        utc_dt = pytz.UTC.localize(utc_dt)
    
    # Convert to local timezone
    local_dt = utc_dt.astimezone(user_tz)
    return local_dt
