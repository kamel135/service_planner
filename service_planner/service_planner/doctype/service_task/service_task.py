import frappe
from frappe.model.document import Document
from service_planner.utils.timezone_utils import tz_manager
from datetime import datetime, timedelta

class ServiceTask(Document):
    def validate(self):
        self.handle_timezone()
        self.validate_assignments()
        
    def validate_assignments(self):
        """التحقق من صحة التعيينات"""
        if self.assigned_to:
            # التحقق من أن المستخدم المعين له الدور المطلوب
            user_roles = frappe.get_roles(self.assigned_to)
            if self.assigned_role not in user_roles:
                frappe.throw(
                    f"User {self.assigned_to} does not have the required role: {self.assigned_role}"
                )
                
    def handle_timezone(self):
        """معالجة فروق التوقيت والتوقيت الصيفي"""
        if not self.due_date:
            return
            
        try:
            # تحديد المنطقة الزمنية للمستخدم المعين
            if self.assigned_to:
                user_tz = tz_manager.get_user_timezone(self.assigned_to)
            else:
                user_tz = tz_manager.get_user_timezone()
                
            # حفظ معلومات المنطقة الزمنية
            self.user_timezone = str(user_tz)
            self.timezone_offset = tz_manager.get_timezone_offset(str(user_tz))
            self.original_timezone = str(user_tz)
            
            # تحويل التوقيت المحلي إلى UTC
            local_dt = frappe.utils.get_datetime(self.due_date)
            
            # حفظ التوقيت المحلي
            self.local_due_date = local_dt
            
            # تطبيق تعديلات التوقيت الصيفي إذا كان مفعلاً
            if self.dst_enabled and tz_manager.is_dst_active(str(user_tz)):
                dst_adjustment = timedelta(hours=1)
                local_dt = local_dt + dst_adjustment
            
            # تحويل إلى UTC
            utc_dt = tz_manager.convert_to_utc(local_dt, user_tz)
            self.due_date_utc = utc_dt.strftime('%Y-%m-%d %H:%M:%S')
            
        except Exception as e:
            frappe.log_error(f"Timezone conversion error: {str(e)}")
            
    def get_formatted_due_date(self, user=None):
        """الحصول على تاريخ الاستحقاق بالتوقيت المحلي"""
        if not self.due_date_utc:
            return ""
            
        try:
            if not user:
                user = self.assigned_to or frappe.session.user
                
            utc_dt = frappe.utils.get_datetime(self.due_date_utc)
            user_tz = tz_manager.get_user_timezone(user)
            local_dt = tz_manager.convert_to_local(utc_dt, user_tz)
            
            # تطبيق تعديلات التوقيت الصيفي
            if self.dst_enabled and tz_manager.is_dst_active(str(user_tz)):
                local_dt = local_dt + timedelta(hours=1)
            
            # تنسيق التاريخ مع معلومات المنطقة الزمنية
            formatted_date = tz_manager.format_datetime(
                local_dt, 
                user_tz, 
                format_str="%Y-%m-%d %H:%M:%S %Z (%z)"
            )
            
            return formatted_date
            
        except Exception as e:
            frappe.log_error(f"Date formatting error: {str(e)}")
            return str(self.due_date_utc)

    def on_update(self):
        """معالجة التحديثات"""
        self.update_timing_fields()
        self.notify_assignment_changes()
        
    def update_timing_fields(self):
        """تحديث حقول التوقيت"""
        now = frappe.utils.now_datetime()
        
        if self.status == "Completed" and not self.completion_time:
            self.completion_time = now
        elif self.status == "In Progress" and not self.start_time:
            self.start_time = now
            
    def notify_assignment_changes(self):
        """إرسال إشعارات عند تغيير التعيينات"""
        if self.has_value_changed('assigned_to') and self.assigned_to:
            self.notify_assignment()
            
    def notify_assignment(self):
        """إرسال إشعار للمستخدم المعين"""
        try:
            due_date_local = self.get_formatted_due_date(self.assigned_to)
            
            frappe.sendmail(
                recipients=[self.assigned_to],
                subject=f"New Task Assignment: {self.task_title}",
                message=f"""
                You have been assigned a new task:
                
                Task: {self.task_title}
                Due Date: {due_date_local}
                Priority: {self.priority}
                
                Please review the task details and update the status accordingly.
                """
            )
        except Exception as e:
            frappe.log_error(f"Task notification error: {str(e)}")

# توابع الصلاحيات
def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return ""

    user_roles = frappe.get_roles(user)
    user_org = frappe.get_cached_value("User", user, "organization")

    if not user_org or not user_roles:
        return "1=0"

    roles_str = "', '".join([frappe.db.escape(role) for role in user_roles])
    
    return f"""
        (assigned_to = {frappe.db.escape(user)}
        OR (assigned_role IN ('{roles_str}') AND IFNULL(assigned_to, '') = ''))
        AND organization = {frappe.db.escape(user_org)}
    """

def has_permission(doc, ptype, user):
    if "System Manager" in frappe.get_roles(user):
        return True

    user_roles = frappe.get_roles(user)
    user_org = frappe.get_cached_value("User", user, "organization")
    
    is_assigned = (
        doc.assigned_to == user or 
        (doc.assigned_role in user_roles and not doc.assigned_to)
    )
    
    return is_assigned and doc.organization == user_org

@frappe.whitelist()
def get_formatted_due_date(task):
    """Get formatted due date for display"""
    doc = frappe.get_doc("Service Task", task)
    return doc.get_formatted_due_date()

@frappe.whitelist()
def test_timezone_conversion(task_id=None):
    """اختبار تحويل المناطق الزمنية"""
    if not task_id:
        return
        
    task = frappe.get_doc("Service Task", task_id)
    
    result = {
        "original_due_date": str(task.due_date),
        "utc_due_date": str(task.due_date_utc),
        "local_due_date": str(task.local_due_date),
        "user_timezone": task.user_timezone,
        "timezone_offset": task.timezone_offset,
        "dst_enabled": task.dst_enabled
    }
    
    return result
