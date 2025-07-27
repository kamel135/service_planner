import frappe
from frappe.model.document import Document
from service_planner.utils.timezone_utils import tz_manager
from datetime import datetime
import pytz

class ServiceTask(Document):
    def validate(self):
        """التحقق والتحديث التلقائي"""
        if not self.user_timezone:
            # الحصول على المنطقة الزمنية من المستخدم المسؤول عن المهمة
            if self.assigned_to:
                user_tz = frappe.db.get_value("User", self.assigned_to, "time_zone")
            else:
                # إذا لم يكن هناك مستخدم محدد، استخدم منطقة صاحب المشروع
                project = frappe.get_doc(self.parenttype, self.parent)
                user_tz = frappe.db.get_value("User", project.owner, "time_zone")
            
            # إذا لم يتم العثور على منطقة زمنية، استخدم منطقة المستخدم الحالي
            if not user_tz:
                user_tz = frappe.db.get_value("User", frappe.session.user, "time_zone")
                
            # إذا لم يتم العثور على أي منطقة زمنية، استخدم منطقة النظام
            if not user_tz:
                user_tz = frappe.db.get_single_value("System Settings", "time_zone") or "UTC"
                
            self.user_timezone = user_tz
            
        if not self.due_date_utc and self.due_date:
            self.due_date_utc = self.due_date
            
        if not self.local_due_date and self.due_date:
            try:
                # تحويل التاريخ باستخدام المنطقة الزمنية المحددة
                local_dt = tz_manager.convert_to_local(
                    frappe.utils.get_datetime(self.due_date),
                    pytz.timezone(self.user_timezone)
                )
                self.local_due_date = local_dt
            except Exception as e:
                frappe.log_error(f"Error converting timezone: {str(e)}")
                # في حالة الخطأ، استخدم التاريخ الأصلي
                self.local_due_date = self.due_date
        
        # استدعاء الvalidations الأخرى
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
        """معالجة محسّنة للمناطق الزمنية - بدون DST يدوي"""
        if not self.due_date:
            return
            
        try:
            # 1. تحديد المنطقة الزمنية
            if self.assigned_to:
                user_tz = tz_manager.get_user_timezone(self.assigned_to)
            else:
                user_tz = tz_manager.get_user_timezone()
            
            # 2. حفظ المنطقة الزمنية فقط (بدون الحقول الزائدة)
            self.user_timezone = str(user_tz)
            
            # 3. معالجة التحويل حسب مصدر البيانات
            if hasattr(self, 'flags') and self.flags.get('due_date_is_utc'):
                # البيانات مُدخلة من generate_service_tasks - already UTC
                self.due_date_utc = self.due_date
            else:
                # البيانات مُدخلة من المستخدم - بحاجة لتحويل
                local_dt = frappe.utils.get_datetime(self.due_date)
                
                # تحويل إلى aware datetime
                if not local_dt.tzinfo:
                    local_aware_dt = user_tz.localize(local_dt)
                else:
                    local_aware_dt = local_dt
                
                # تحويل إلى UTC (pytz يعالج DST تلقائياً!)
                utc_dt = local_aware_dt.astimezone(pytz.utc)
                
                # حفظ النسختين
                self.due_date = utc_dt.replace(tzinfo=None)  # UTC للتخزين
                self.due_date_utc = self.due_date  # نفس القيمة
                self.local_due_date = local_aware_dt.replace(tzinfo=None)  # المحلي للعرض
            
            # 4. حساب وحفظ معلومات إضافية للعرض
            self.update_timezone_info()
            
        except Exception as e:
            frappe.log_error(f"Timezone conversion error: {str(e)}")
    
    def update_timezone_info(self):
        """تحديث معلومات المنطقة الزمنية للعرض"""
        if not self.user_timezone:
            return
        
        try:
            tz = pytz.timezone(self.user_timezone)
            now = datetime.now(tz)
            
            # حساب المعلومات ديناميكياً
            is_dst = bool(now.dst())
            utc_offset = now.utcoffset().total_seconds() / 3600
            
            # تحديث حقل العرض HTML
            html = f"""
            <div class="timezone-info" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">
                <p style="margin: 5px 0;"><strong>Timezone:</strong> {self.user_timezone}</p>
                <p style="margin: 5px 0;"><strong>Current UTC Offset:</strong> {utc_offset:+.0f}:00</p>
                <p style="margin: 5px 0;"><strong>DST Status:</strong> 
                    <span style="color: {'green' if is_dst else 'gray'};">
                        {'Active' if is_dst else 'Not Active'}
                    </span>
                </p>
            </div>
            """
            
            # حفظ في الذاكرة المؤقتة للعرض
            self._timezone_info_html = html
            
        except Exception as e:
            frappe.log_error(f"Timezone info update error: {str(e)}")
            
    def get_formatted_due_date(self, user=None):
        """عرض محسّن للتاريخ مع معالجة DST تلقائية"""
        if not self.due_date:
            return ""
            
        try:
            # 1. احصل على المنطقة الزمنية للعارض
            if not user:
                user = self.assigned_to or frappe.session.user
            
            viewer_tz = tz_manager.get_user_timezone(user)
            
            # 2. حوّل من UTC إلى المنطقة المحلية
            # استخدم due_date (المفترض أنه UTC)
            utc_dt = pytz.utc.localize(frappe.utils.get_datetime(self.due_date))
            local_dt = utc_dt.astimezone(viewer_tz)
            
            # pytz يعالج DST تلقائياً في التحويل!
            
            # 3. تنسيق مع معلومات DST
            is_dst = bool(local_dt.dst())
            dst_indicator = " (Summer Time)" if is_dst else ""
            
            # 4. تنسيق حسب اللغة
            if frappe.local.lang == "ar":
                formatted = local_dt.strftime("%d/%m/%Y الساعة %I:%M %p")
                dst_indicator = " (توقيت صيفي)" if is_dst else ""
            else:
                formatted = local_dt.strftime("%Y-%m-%d at %I:%M %p")
            
            # 5. أضف معلومات المنطقة الزمنية
            timezone_abbr = local_dt.strftime("%Z")  # مثل EET, EST, EDT
            
            return f"{formatted} {timezone_abbr}{dst_indicator}"
            
        except Exception as e:
            frappe.log_error(f"Date formatting error: {str(e)}")
            return str(self.due_date)

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
                Priority: {self.priority or 'Normal'}
                
                Please review the task details and update the status accordingly.
                """
            )
        except Exception as e:
            frappe.log_error(f"Task notification error: {str(e)}")
    
    def before_save(self):
        """قبل الحفظ - تحديث معلومات العرض"""
        if hasattr(self, '_timezone_info_html'):
            # احفظ HTML في due_date_display
            self.due_date_display = self._timezone_info_html

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
def diagnose_timezone(task_id):
    """تشخيص شامل للتوقيت - نسخة محسنة"""
    if not task_id:
        return {"error": "No task ID provided"}
        
    task = frappe.get_doc("Service Task", task_id)
    
    try:
        # معلومات أساسية
        result = {
            "task_info": {
                "name": task.name,
                "title": task.task_title,
                "timezone": task.user_timezone,
                "due_date_stored": str(task.due_date),
                "due_date_utc": str(task.due_date_utc) if hasattr(task, 'due_date_utc') else "N/A",
                "local_due_date": str(task.local_due_date) if hasattr(task, 'local_due_date') else "N/A"
            }
        }
        
        if task.user_timezone:
            tz = pytz.timezone(task.user_timezone)
            
            # فحص DST للتاريخ المحدد
            if task.due_date:
                dt = frappe.utils.get_datetime(task.due_date)
                aware_dt = pytz.utc.localize(dt).astimezone(tz)
                
                result["dst_analysis"] = {
                    "is_dst_active": bool(aware_dt.dst()),
                    "dst_offset": str(aware_dt.dst()) if aware_dt.dst() else "0:00:00",
                    "utc_offset": str(aware_dt.utcoffset()),
                    "timezone_abbr": aware_dt.strftime("%Z")
                }
            
            # مقارنة مع الوقت الحالي
            now = datetime.now(tz)
            result["current_time_info"] = {
                "current_time": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "current_dst": bool(now.dst()),
                "current_offset": str(now.utcoffset())
            }
            
            # فحص تواريخ مختلفة
            test_dates = [
                ("Winter", datetime(2024, 1, 15, 12, 0)),
                ("Summer", datetime(2024, 7, 15, 12, 0))
            ]
            
            result["seasonal_dst_check"] = {}
            for season, test_dt in test_dates:
                test_aware = tz.localize(test_dt)
                result["seasonal_dst_check"][season] = {
                    "date": test_dt.strftime("%Y-%m-%d"),
                    "is_dst": bool(test_aware.dst()),
                                        "offset": str(test_aware.utcoffset()),
                    "abbr": test_aware.strftime("%Z")
                }
        
        # عرض التاريخ بتنسيقات مختلفة
        if task.due_date:
            result["formatted_displays"] = {
                "for_creator": task.get_formatted_due_date(task.owner),
                "for_assignee": task.get_formatted_due_date(task.assigned_to) if task.assigned_to else "N/A",
                "for_current_user": task.get_formatted_due_date()
            }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "traceback": frappe.get_traceback()
        }

@frappe.whitelist()
def fix_timezone_data(task_id):
    """إصلاح بيانات التوقيت للمهام القديمة"""
    try:
        task = frappe.get_doc("Service Task", task_id)
        
        # إعادة معالجة التوقيت
        task.handle_timezone()
        task.save()
        
        return {
            "success": True,
            "message": "Timezone data fixed successfully",
            "new_data": {
                "due_date": str(task.due_date),
                "due_date_utc": str(task.due_date_utc),
                "local_due_date": str(task.local_due_date),
                "user_timezone": task.user_timezone
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def bulk_fix_timezones(project_name=None):
    """إصلاح جماعي لبيانات التوقيت"""
    try:
        filters = {}
        if project_name:
            filters['parent'] = project_name
        
        tasks = frappe.get_all("Service Task", 
            filters=filters,
            fields=['name', 'parent', 'parenttype', 'parentfield'],
            limit=100
        )
        
        fixed_count = 0
        errors = []
        
        for task_data in tasks:
            try:
                # Load the parent document
                parent_doc = frappe.get_doc(task_data['parenttype'], task_data['parent'])
                
                # Find and fix the specific task
                for task in parent_doc.service_tasks:
                    if task.name == task_data['name']:
                        # Set flag to indicate UTC
                        task.flags.due_date_is_utc = True
                        task.handle_timezone()
                        fixed_count += 1
                        break
                
                parent_doc.save()
                
            except Exception as e:
                errors.append({
                    "task": task_data['name'],
                    "error": str(e)
                })
        
        return {
            "success": True,
            "fixed": fixed_count,
            "errors": errors,
            "message": f"Fixed {fixed_count} tasks"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# في نهاية service_task.py، أضف:

@frappe.whitelist()
def verify_timezone_system():
    """التحقق من صحة نظام التوقيت"""
    import pytz
    
    # اختر مهمة عشوائية للفحص
    tasks = frappe.db.sql("""
        SELECT name, parent, parenttype, parentfield 
        FROM `tabService Task` 
        LIMIT 5
    """, as_dict=True)
    
    results = []
    for task_data in tasks:
        # جلب المهمة من خلال الـ parent document
        parent_doc = frappe.get_doc(task_data.parenttype, task_data.parent)
        
        # ابحث عن المهمة المحددة
        task = None
        for t in parent_doc.service_tasks:
            if t.name == task_data.name:
                task = t
                break
        
        if not task:
            continue
        
        # تحقق من وجود الحقول المطلوبة
        check = {
            "task": task.name,
            "has_due_date": bool(task.due_date),
            "has_timezone": bool(task.user_timezone),
            "has_local_date": bool(task.local_due_date),
            "timezone_valid": False,
            "conversion_correct": False
        }
        
        # تحقق من صحة المنطقة الزمنية
        if task.user_timezone:
            try:
                tz = pytz.timezone(task.user_timezone)
                check["timezone_valid"] = True
                
                # تحقق من صحة التحويل
                if task.due_date and task.local_due_date:
                    utc_dt = pytz.utc.localize(frappe.utils.get_datetime(task.due_date))
                    local_dt = utc_dt.astimezone(tz)
                    
                    # قارن مع المحفوظ
                    saved_local = frappe.utils.get_datetime(task.local_due_date)
                    
                    # السماح بفرق دقيقة واحدة
                    time_diff = abs((local_dt.replace(tzinfo=None) - saved_local).total_seconds())
                    check["conversion_correct"] = time_diff < 60
                    
            except:
                pass
        
        results.append(check)
    
    # ملخص
    all_valid = all(r["timezone_valid"] and r["conversion_correct"] for r in results if r["has_due_date"])
    
    return {
        "system_healthy": all_valid,
        "checked_tasks": len(results),
        "details": results,
        "recommendation": "System is working correctly!" if all_valid else "Some tasks need fixing"
    }

@frappe.whitelist() 
def migrate_old_tasks():
    """تحديث المهام القديمة للنظام الجديد"""
    
    # جلب كل المشاريع
    projects = frappe.get_all("Service Project", pluck="name")
    
    fixed = 0
    errors = []
    
    for project_name in projects:
        try:
            doc = frappe.get_doc("Service Project", project_name)
            modified = False
            
            for task in doc.service_tasks:
                # إذا لم يكن عندها due_date_utc
                if task.due_date and not task.due_date_utc:
                    task.due_date_utc = task.due_date
                    task.flags.due_date_is_utc = True
                    fixed += 1
                    modified = True
            
            if modified:
                doc.save()
                
        except Exception as e:
            errors.append(f"{project_name}: {str(e)}")
    
    return {
        "fixed": fixed,
        "errors": errors,
        "message": f"Fixed {fixed} tasks successfully"
    }
@frappe.whitelist()
def detailed_system_check():
    """فحص شامل ومفصل للنظام"""
    import pytz
    from collections import defaultdict
    
    issues = defaultdict(list)
    stats = {
        "total_tasks": 0,
        "tasks_with_utc": 0,
        "tasks_with_timezone": 0,
        "tasks_with_local_date": 0,
        "conversion_errors": 0
    }
    
    # فحص المهام
    tasks = frappe.db.sql("""
        SELECT 
            t.name, t.parent, t.parenttype, t.due_date, 
            t.due_date_utc, t.local_due_date, t.user_timezone
        FROM `tabService Task` t
        LIMIT 100
    """, as_dict=True)
    
    for task_data in tasks:
        stats["total_tasks"] += 1
        
        # فحص الحقول
        if task_data.due_date_utc:
            stats["tasks_with_utc"] += 1
        else:
            issues["missing_utc"].append(task_data.name)
            
        if task_data.user_timezone:
            stats["tasks_with_timezone"] += 1
            
            # فحص صحة التحويل
            try:
                tz = pytz.timezone(task_data.user_timezone)
                
                if task_data.due_date and task_data.local_due_date:
                    # تحقق من التحويل
                    utc_dt = pytz.utc.localize(frappe.utils.get_datetime(task_data.due_date))
                    expected_local = utc_dt.astimezone(tz)
                    saved_local = frappe.utils.get_datetime(task_data.local_due_date)
                    
                    time_diff = abs((expected_local.replace(tzinfo=None) - saved_local).total_seconds())
                    
                    if time_diff > 60:  # أكثر من دقيقة
                        stats["conversion_errors"] += 1
                        issues["conversion_error"].append({
                            "task": task_data.name,
                            "expected": str(expected_local),
                            "saved": str(saved_local),
                            "diff_seconds": time_diff
                        })
            except Exception as e:
                issues["timezone_error"].append({
                    "task": task_data.name,
                    "timezone": task_data.user_timezone,
                    "error": str(e)
                })
        else:
            issues["missing_timezone"].append(task_data.name)
            
        if task_data.local_due_date:
            stats["tasks_with_local_date"] += 1
    
    # فحص المشاريع
    project_issues = []
    projects = frappe.get_all("Service Project", 
        filters={"schedule_type": "Weekly"},
        fields=["name", "project_name"])
    
    for project in projects:
        doc = frappe.get_doc("Service Project", project.name)
        if not doc.weekly_days or len(doc.weekly_days) == 0:
            project_issues.append({
                "project": doc.name,
                "name": doc.project_name,
                "issue": "No weekly days selected"
            })
    
    return {
        "stats": stats,
        "issues": dict(issues),
        "project_issues": project_issues,
        "health_score": (stats["tasks_with_utc"] / stats["total_tasks"] * 100) if stats["total_tasks"] > 0 else 0
    }
# في نهاية ملف service_task.py أضف:

@frappe.whitelist()
def detailed_system_check():
    """فحص شامل ومفصل للنظام"""
    import pytz
    from collections import defaultdict
    
    issues = defaultdict(list)
    stats = {
        "total_tasks": 0,
        "tasks_with_utc": 0,
        "tasks_with_timezone": 0,
        "tasks_with_local_date": 0,
        "conversion_errors": 0
    }
    
    # فحص المهام
    tasks = frappe.db.sql("""
        SELECT 
            t.name, t.parent, t.parenttype, t.due_date, 
            t.due_date_utc, t.local_due_date, t.user_timezone
        FROM `tabService Task` t
        LIMIT 100
    """, as_dict=True)
    
    for task_data in tasks:
        stats["total_tasks"] += 1
        
        # فحص الحقول
        if task_data.due_date_utc:
            stats["tasks_with_utc"] += 1
        else:
            issues["missing_utc"].append(task_data.name)
            
        if task_data.user_timezone:
            stats["tasks_with_timezone"] += 1
            
            # فحص صحة التحويل
            try:
                tz = pytz.timezone(task_data.user_timezone)
                
                if task_data.due_date and task_data.local_due_date:
                    # تحقق من التحويل
                    utc_dt = pytz.utc.localize(frappe.utils.get_datetime(task_data.due_date))
                    expected_local = utc_dt.astimezone(tz)
                    saved_local = frappe.utils.get_datetime(task_data.local_due_date)
                    
                    time_diff = abs((expected_local.replace(tzinfo=None) - saved_local).total_seconds())
                    
                    if time_diff > 60:  # أكثر من دقيقة
                        stats["conversion_errors"] += 1
                        issues["conversion_error"].append({
                            "task": task_data.name,
                            "expected": str(expected_local),
                            "saved": str(saved_local),
                            "diff_seconds": time_diff
                        })
            except Exception as e:
                issues["timezone_error"].append({
                    "task": task_data.name,
                    "timezone": task_data.user_timezone,
                    "error": str(e)
                })
        else:
            issues["missing_timezone"].append(task_data.name)
            
        if task_data.local_due_date:
            stats["tasks_with_local_date"] += 1
        else:
            issues["missing_local_date"].append(task_data.name)
    
    # فحص المشاريع
    project_issues = []
    projects = frappe.get_all("Service Project", 
        filters={"schedule_type": "Weekly"},
        fields=["name", "project_name"])
    
    for project in projects:
        doc = frappe.get_doc("Service Project", project.name)
        if not doc.weekly_days or len(doc.weekly_days) == 0:
            project_issues.append({
                "project": doc.name,
                "name": doc.project_name,
                "issue": "No weekly days selected"
            })
    
    return {
        "stats": stats,
        "issues": dict(issues),
        "project_issues": project_issues,
        "health_score": (stats["tasks_with_utc"] / stats["total_tasks"] * 100) if stats["total_tasks"] > 0 else 0
    }

@frappe.whitelist()
def fix_remaining_issues():
    """إصلاح المشاكل المتبقية"""
    from service_planner.utils.timezone_utils import tz_manager
    import pytz
    
    fixed = {
        "missing_utc": 0,
        "missing_timezone": 0,
        "missing_local_date": 0,
        "weekly_projects": 0
    }
    
    # إصلاح المهام بدون UTC
    tasks = frappe.db.sql("""
        SELECT name, parent, parenttype, due_date
        FROM `tabService Task`
        WHERE due_date IS NOT NULL 
        AND (due_date_utc IS NULL OR due_date_utc = '')
    """, as_dict=True)
    
    for task in tasks:
        try:
            frappe.db.set_value("Service Task", task.name, 
                              "due_date_utc", task.due_date, 
                              update_modified=False)
            fixed["missing_utc"] += 1
        except:
            pass
    
    # إصلاح المهام بدون timezone و local_due_date
    tasks = frappe.db.sql("""
        SELECT name, parent, parenttype, due_date
        FROM `tabService Task`
        WHERE (user_timezone IS NULL OR user_timezone = ''
        OR local_due_date IS NULL OR local_due_date = '')
        AND due_date IS NOT NULL
    """, as_dict=True)
    
    for task in tasks:
        try:
            # احصل على timezone من المشروع
            project = frappe.get_doc(task.parenttype, task.parent)
            user_tz_str = tz_manager.get_user_timezone(project.owner)
            user_tz = pytz.timezone(user_tz_str)
            
            updates = {}
            
            # أضف timezone إذا مفقود
            if not frappe.db.get_value("Service Task", task.name, "user_timezone"):
                updates["user_timezone"] = str(user_tz_str)
                fixed["missing_timezone"] += 1
            
            # أضف local_due_date إذا مفقود
            if not frappe.db.get_value("Service Task", task.name, "local_due_date"):
                # افترض أن due_date هو UTC
                utc_dt = pytz.utc.localize(frappe.utils.get_datetime(task.due_date))
                local_dt = utc_dt.astimezone(user_tz)
                updates["local_due_date"] = local_dt.replace(tzinfo=None)
                fixed["missing_local_date"] += 1
            
            # حدث البيانات
            if updates:
                for field, value in updates.items():
                    frappe.db.set_value("Service Task", task.name, field, value, update_modified=False)
                    
        except Exception as e:
            frappe.log_error(f"Error fixing task {task.name}: {str(e)}")
    
    # إصلاح المشاريع الأسبوعية
    projects = frappe.get_all("Service Project",
        filters={"schedule_type": "Weekly"},
        pluck="name")
    
    for project_name in projects:
        try:
            doc = frappe.get_doc("Service Project", project_name)
            if not doc.weekly_days or len(doc.weekly_days) == 0:
                # أضف يوم افتراضي (الاثنين)
                doc.append("weekly_days", {"day": "Monday"})
                doc.save()
                fixed["weekly_projects"] += 1
        except:
            pass
    
    frappe.db.commit()
    
    return {
        "success": True,
        "fixed": fixed,
        "message": f"Fixed {sum(fixed.values())} issues"
    }

@frappe.whitelist()
def fix_specific_tasks(task_names=None):
    """إصلاح مهام محددة"""
    from service_planner.utils.timezone_utils import tz_manager
    import pytz
    
    if not task_names:
        # المهام من الفحص
        task_names = ["04uo4f64pv", "0d06cvr3rl", "0d076gecam", "0d0783cofb", "0d0f2g46cr"]
    
    fixed = []
    errors = []
    
    for task_name in task_names:
        try:
            # جلب معلومات المهمة
            task_data = frappe.db.get_value("Service Task", task_name, 
                ["name", "parent", "parenttype", "due_date"], as_dict=True)
            
            if not task_data:
                errors.append(f"Task {task_name} not found")
                continue
            
            # جلب المشروع
            project = frappe.get_doc(task_data.parenttype, task_data.parent)
            user_tz_str = tz_manager.get_user_timezone(project.owner)
            user_tz = pytz.timezone(user_tz_str)
            
            # حساب التواريخ
            utc_dt = pytz.utc.localize(frappe.utils.get_datetime(task_data.due_date))
            local_dt = utc_dt.astimezone(user_tz)
            
            # تحديث المهمة
            frappe.db.set_value("Service Task", task_name, {
                "due_date_utc": task_data.due_date,
                "user_timezone": str(user_tz_str),
                "local_due_date": local_dt.replace(tzinfo=None)
            }, update_modified=False)
            
            fixed.append(task_name)
            
        except Exception as e:
            errors.append(f"Task {task_name}: {str(e)}")
    
    frappe.db.commit()
    
    return {
        "success": len(fixed) > 0,
        "fixed": fixed,
        "errors": errors,
        "message": f"Fixed {len(fixed)} tasks, {len(errors)} errors"
    }
