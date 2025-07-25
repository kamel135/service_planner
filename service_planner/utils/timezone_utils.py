import frappe
from datetime import datetime, timedelta
import pytz
from typing import Optional, Dict, Any

class TimezoneManager:
    def __init__(self):
        self.utc = pytz.UTC
        self.cache = {}
        self._default_timezone = "UTC"
        
    def get_user_timezone(self, user: Optional[str] = None) -> pytz.timezone:
        """الحصول على المنطقة الزمنية للمستخدم"""
        if not user:
            user = frappe.session.user
            
        cache_key = f"timezone_{user}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        try:
            # محاولة الحصول على المنطقة الزمنية من إعدادات المستخدم
            user_tz = frappe.db.get_value("User", user, "time_zone")
            if not user_tz:
                user_tz = frappe.utils.get_time_zone() or self._default_timezone
                
            timezone = pytz.timezone(user_tz)
            self.cache[cache_key] = timezone
            return timezone
            
        except Exception as e:
            frappe.log_error(f"Error getting user timezone: {str(e)}")
            return pytz.timezone(self._default_timezone)
    
    def convert_to_utc(self, local_dt: datetime, source_tz: Optional[pytz.timezone] = None) -> datetime:
        """تحويل التوقيت المحلي إلى UTC"""
        try:
            if not source_tz:
                source_tz = self.get_user_timezone()
                
            if not local_dt.tzinfo:
                local_dt = source_tz.localize(local_dt)
                
            return local_dt.astimezone(self.utc)
            
        except Exception as e:
            frappe.log_error(f"Error converting to UTC: {str(e)}")
            return local_dt
    
    def convert_to_local(self, utc_dt: datetime, target_tz: Optional[pytz.timezone] = None) -> datetime:
        """تحويل UTC إلى التوقيت المحلي"""
        try:
            if not target_tz:
                target_tz = self.get_user_timezone()
                
            if not utc_dt.tzinfo:
                utc_dt = self.utc.localize(utc_dt)
                
            return utc_dt.astimezone(target_tz)
            
        except Exception as e:
            frappe.log_error(f"Error converting to local time: {str(e)}")
            return utc_dt
    
    def format_datetime(self, dt: datetime, timezone: Optional[pytz.timezone] = None, 
                       format_str: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
        """تنسيق التاريخ والوقت"""
        try:
            if not timezone:
                timezone = self.get_user_timezone()
                
            if not dt.tzinfo:
                dt = self.utc.localize(dt)
                
            local_dt = dt.astimezone(timezone)
            return local_dt.strftime(format_str)
            
        except Exception as e:
            frappe.log_error(f"Error formatting datetime: {str(e)}")
            return str(dt)

    def get_timezone_offset(self, timezone_id: str) -> str:
        """الحصول على فرق التوقيت"""
        try:
            tz = pytz.timezone(timezone_id)
            offset = tz.utcoffset(datetime.now())
            hours = int(offset.total_seconds() / 3600)
            minutes = int((offset.total_seconds() % 3600) / 60)
            
            sign = "+" if hours >= 0 else "-"
            return f"{sign}{abs(hours):02d}:{abs(minutes):02d}"
            
        except Exception as e:
            frappe.log_error(f"Error getting timezone offset: {str(e)}")
            return "+00:00"

    def is_dst_active(self, timezone_id: str) -> bool:
        """التحقق من التوقيت الصيفي"""
        try:
            tz = pytz.timezone(timezone_id)
            now = datetime.now(tz)
            return bool(now.dst())
            
        except Exception as e:
            frappe.log_error(f"Error checking DST: {str(e)}")
            return False

    def clear_cache(self):
        """مسح الذاكرة المؤقتة"""
        self.cache.clear()

# إنشاء نسخة عامة
tz_manager = TimezoneManager()
