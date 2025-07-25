# service_planner/api/task_api.py

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, add_days, add_months, format_datetime, formatdate
from typing import Dict, List, Optional, Union
from datetime import datetime
import pytz
import json

class TaskAPI:
    def __init__(self):
        self.current_user = frappe.session.user
        self.user_roles = frappe.get_roles(self.current_user)
        self.is_admin = self._check_if_admin()

    def _check_if_admin(self) -> bool:
        """التحقق مما إذا كان المستخدم الحالي مدير نظام"""
        return any(role in self.user_roles for role in ["System Manager", "Administrator"])

    def _format_task(self, task: Dict) -> Dict:
        """تنسيق بيانات المهمة مع إضافة الترجمات"""
        # التنسيق الأساسي للبيانات
        formatted = {
            "name": task.get("name") or (task.name if hasattr(task, 'name') else None),
            "task_title": task.get("task_title") or (task.task_title if hasattr(task, 'task_title') else None) or _("Untitled"),
            "due_date": task.get("due_date") or (task.due_date if hasattr(task, 'due_date') else None),
            "local_due_date": task.get("local_due_date") or (task.local_due_date if hasattr(task, 'local_due_date') else None),
            "status": task.get("status") or (task.status if hasattr(task, 'status') else None) or "Pending",
            "assigned_to": task.get("assigned_to") or (task.assigned_to if hasattr(task, 'assigned_to') else None),
            "assigned_role": task.get("assigned_role") or (task.assigned_role if hasattr(task, 'assigned_role') else None),
            "notes": task.get("notes") or (task.notes if hasattr(task, 'notes') else None),
            "creation": task.get("creation") or (task.creation if hasattr(task, 'creation') else None),
            "modified": task.get("modified") or (task.modified if hasattr(task, 'modified') else None),
            "parent": task.get("parent") or (task.parent if hasattr(task, 'parent') else None),
            "can_edit": self._can_edit_task(task)
        }
        
        # إضافة الترجمات
        formatted["status_translated"] = _(formatted["status"])
        
        # ترجمة عنوان المهمة بناءً على النمط
        task_title = formatted["task_title"]
        
        # التحقق من المهام التلقائية وترجمتها
        if task_title.startswith("Auto Task for"):
            date_part = task_title.replace("Auto Task for ", "")
            formatted["task_title_translated"] = _("Auto Task for {0}").format(date_part)
        elif "Task generated for" in task_title:
            if "Daily" in task_title:
                date_part = task_title.split(" on ")[-1] if " on " in task_title else ""
                formatted["task_title_translated"] = _("Task generated for Daily on {0}").format(date_part)
            elif "Every X Days" in task_title:
                date_part = task_title.split(" on ")[-1] if " on " in task_title else ""
                formatted["task_title_translated"] = _("Task generated for Every X Days on {0}").format(date_part)
            else:
                formatted["task_title_translated"] = _(task_title)
        else:
            # للعناوين الأخرى، حاول الترجمة المباشرة
            formatted["task_title_translated"] = _(task_title)
        
        return formatted

    def _can_edit_task(self, task: Dict) -> bool:
        """التحقق من إمكانية تعديل المهمة"""
        if self.is_admin:
            return True
        
        # إذا كانت المهمة مسندة لشخص محدد
        assigned_to = task.get('assigned_to') or (task.assigned_to if hasattr(task, 'assigned_to') else None)
        if assigned_to:
            return assigned_to == self.current_user
            
        # إذا كانت المهمة مسندة لدور وليس لشخص محدد
        assigned_role = task.get('assigned_role') or (task.assigned_role if hasattr(task, 'assigned_role') else None)
        if assigned_role:
            return assigned_role in self.user_roles
            
        return False

    def get_task_stats(self, base_filters: Dict = None) -> Dict:
        """الحصول على إحصائيات المهام"""
        try:
            if base_filters is None:
                base_filters = {}

            # إجمالي المهام
            total = frappe.db.count('Service Task', filters=base_filters)

            # المهام المكتملة
            completed_filters = base_filters.copy()
            completed_filters['status'] = 'Completed'
            completed = frappe.db.count('Service Task', filters=completed_filters)

            # المهام قيد التنفيذ
            in_progress_filters = base_filters.copy()
            in_progress_filters['status'] = 'In Progress'
            in_progress = frappe.db.count('Service Task', filters=in_progress_filters)

            # المهام المتأخرة
            overdue_filters = base_filters.copy()
            overdue_filters['due_date'] = ['<', nowdate()]
            overdue_filters['status'] = ['!=', 'Completed']
            overdue = frappe.db.count('Service Task', filters=overdue_filters)

            # المهام قيد الانتظار
            pending_filters = base_filters.copy()
            pending_filters['status'] = 'Pending'
            pending = frappe.db.count('Service Task', filters=pending_filters)

            return {
                "success": True,
                "stats": {
                    "total": total,
                    "completed": completed,
                    "in_progress": in_progress,
                    "pending": pending,
                    "overdue": overdue
                }
            }
        except Exception as e:
            frappe.log_error(f"Error in get_task_stats: {str(e)}")
            return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_my_tasks(status=None, due_filter=None, search_term=None):
    """الحصول على المهام الخاصة بالمستخدم مع الترجمات"""
    try:
        task_api = TaskAPI()
        
        # بناء شرط WHERE clause
        where_conditions = []
        
        # فلتر المستخدم: إذا لم يكن مدير نظام
        if not task_api.is_admin:
            # بناء شرط صلاحيات المستخدم
            user_condition = f"assigned_to = {frappe.db.escape(task_api.current_user)}"
            
            # بناء شرط الأدوار
            role_conditions = []
            if task_api.user_roles:
                for role in task_api.user_roles:
                    role_conditions.append(f"assigned_role = {frappe.db.escape(role)}")
            
            # دمج الشروط مع التأكد من أن المهام المسندة لشخص محدد لا تظهر للآخرين
            if role_conditions:
                role_condition = f"({' OR '.join(role_conditions)}) AND assigned_to IS NULL"
                user_role_condition = f"({user_condition} OR {role_condition})"
            else:
                user_role_condition = user_condition
            
            where_conditions.append(user_role_condition)
        
        # فلتر الحالة
        if status and status != 'All':
            where_conditions.append(f"status = {frappe.db.escape(status)}")
            
        # فلتر التاريخ
        if due_filter and due_filter != 'all':
            today = nowdate()
            
            if due_filter == "today":
                where_conditions.append(f"due_date = {frappe.db.escape(today)}")
            elif due_filter == "week":
                week_end = add_days(today, 7)
                where_conditions.append(f"due_date BETWEEN {frappe.db.escape(today)} AND {frappe.db.escape(week_end)}")
            elif due_filter == "month":
                month_end = add_months(today, 1)
                where_conditions.append(f"due_date BETWEEN {frappe.db.escape(today)} AND {frappe.db.escape(month_end)}")
            elif due_filter == "overdue":
                where_conditions.append(f"due_date < {frappe.db.escape(today)}")
                where_conditions.append("status != 'Completed'")
        
        # فلتر البحث
        if search_term:
            search_escaped = frappe.db.escape(f"%{search_term}%")
            where_conditions.append(f"(task_title LIKE {search_escaped} OR notes LIKE {search_escaped})")
        
        # بناء الاستعلام النهائي
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        sql_query = f"""
            SELECT 
                name, task_title, due_date, local_due_date,
                assigned_to, assigned_role, status,
                notes, creation, modified, parent
            FROM `tabService Task`
            WHERE {where_clause}
            ORDER BY due_date ASC, creation DESC
        """
        
        # تنفيذ الاستعلام
        tasks = frappe.db.sql(sql_query, as_dict=True)
        
        # تنسيق المهام مع الترجمات
        formatted_tasks = []
        for task in tasks:
            try:
                formatted_task = task_api._format_task(task)
                formatted_tasks.append(formatted_task)
            except Exception as e:
                frappe.log_error(f"Error formatting task {task.get('name')}: {str(e)}")
                continue
        
        # حساب الإحصائيات
        stats_where_clause = where_clause
        # إزالة فلتر البحث من الإحصائيات
        if search_term:
            stats_conditions = [cond for cond in where_conditions if "task_title LIKE" not in cond and "notes LIKE" not in cond]
            stats_where_clause = " AND ".join(stats_conditions) if stats_conditions else "1=1"
        
        stats_query = f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN due_date < '{nowdate()}' AND status != 'Completed' THEN 1 ELSE 0 END) as overdue
            FROM `tabService Task`
            WHERE {stats_where_clause}
        """
        
        stats_result = frappe.db.sql(stats_query, as_dict=True)
        stats = stats_result[0] if stats_result else {
            'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0, 'overdue': 0
        }
        
        # تحويل القيم إلى int للتأكد من التوافق
        for key in stats:
            if stats[key] is None:
                stats[key] = 0
            else:
                stats[key] = int(stats[key])
        
        return {
            'success': True,
            'tasks': formatted_tasks,
            'count': len(formatted_tasks),
            'stats': stats
        }
        
    except Exception as e:
        frappe.log_error(str(e), 'Error in get_my_tasks')
        return {
            'success': False,
            'message': _("Error fetching tasks: {0}").format(str(e)),
            'tasks': [],
            'count': 0,
            'stats': {
                'total': 0,
                'completed': 0,
                'in_progress': 0,
                'pending': 0,
                'overdue': 0
            }
        }
@frappe.whitelist()
def mark_task_completed(task_name):
    """تحديث حالة المهمة إلى مكتملة"""
    try:
        task_api = TaskAPI()
        
        # جلب المهمة
        task = frappe.get_doc("Service Task", task_name)
        
        # التحقق من الصلاحيات
        if not task_api._can_edit_task(task):
            return {
                "success": False,
                "message": _("You don't have permission to modify this task")
            }
        
        # تحديث الحالة باستخدام frappe.db.set_value لتجاوز قيود سير العمل
        frappe.db.set_value("Service Task", task_name, "status", "Completed", update_modified=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Task completed successfully")
        }
        
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "message": _("Task does not exist")
        }
    except Exception as e:
        frappe.log_error(f"Error in mark_task_completed: {str(e)}")
        return {
            "success": False,
            "message": _("Error updating task: {0}").format(str(e))
        }

@frappe.whitelist()
def get_task_details(task_name):
    """الحصول على تفاصيل المهمة مع الترجمات"""
    try:
        task_api = TaskAPI()
        
        # جلب المهمة
        task = frappe.get_doc("Service Task", task_name)
        
        # التحقق من الصلاحيات
        can_view = task_api.is_admin or (
            task.assigned_to == task_api.current_user or 
            (task.assigned_role and task.assigned_role in task_api.user_roles and not task.assigned_to)
        )
        
        if not can_view:
            return {
                "success": False,
                "message": _("You don't have permission to view this task")
            }
            
        # تنسيق وإرجاع البيانات مع الترجمات
        formatted_task = task_api._format_task(task)
        
        return {
            "success": True,
            "task": formatted_task
        }
        
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "message": _("Task does not exist")
        }
    except Exception as e:
        frappe.log_error(f"Error in get_task_details: {str(e)}")
        return {
            "success": False,
            "message": _("Error fetching task details: {0}").format(str(e))
        }

@frappe.whitelist()
def get_user_timezone_info(user=None):
    """الحصول على معلومات المنطقة الزمنية للمستخدم"""
    try:
        if not user:
            user = frappe.session.user
        
        # الحصول على إعدادات المستخدم
        user_settings = frappe.get_doc("User", user)
        user_timezone = user_settings.time_zone or frappe.get_system_settings("time_zone") or "UTC"
        
        # حساب فرق التوقيت
        tz = pytz.timezone(user_timezone)
        now = datetime.now(tz)
        offset_hours = now.utcoffset().total_seconds() / 3600
        
        return {
            "success": True,
            "timezone": user_timezone,
            "offset": f"UTC{offset_hours:+.0f}",
            "is_dst": bool(now.dst()),
            "current_time": now.strftime('%Y-%m-%d %H:%M:%S %Z')
        }
    except Exception as e:
        frappe.log_error(f"Error in get_user_timezone_info: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timezone": "UTC",
            "offset": "UTC+0"
        }

@frappe.whitelist()
def convert_timezone(datetime_str, source_tz=None, target_tz=None):
    """تحويل التوقيت بين المناطق الزمنية"""
    try:
        # تحويل النص إلى كائن datetime
        dt = frappe.utils.get_datetime(datetime_str)
        
        # إذا كان التوقيت المصدر محدد
        if source_tz:
            source_timezone = pytz.timezone(source_tz)
            if dt.tzinfo is None:
                dt = source_timezone.localize(dt)
            else:
                dt = dt.astimezone(source_timezone)
        else:
            # افتراض UTC إذا لم يكن محدد
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
        
        # تحويل إلى التوقيت المستهدف
        if target_tz:
            target_timezone = pytz.timezone(target_tz)
            dt = dt.astimezone(target_timezone)
        else:
            # استخدام توقيت المستخدم الافتراضي
            user_tz_info = get_user_timezone_info()
            if user_tz_info.get("success"):
                target_timezone = pytz.timezone(user_tz_info["timezone"])
                dt = dt.astimezone(target_timezone)
        
        return {
            "success": True,
            "datetime": dt.strftime('%Y-%m-%d %H:%M:%S %Z'),
            "source_tz": source_tz or "UTC",
            "target_tz": target_tz or user_tz_info.get("timezone", "UTC")
        }
    except Exception as e:
        frappe.log_error(f"Error in convert_timezone: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def update_task_status(task_name, new_status):
    """تحديث حالة المهمة"""
    try:
        task_api = TaskAPI()
        
        # التحقق من الحالة المدخلة
        valid_statuses = ["Open", "In Progress", "Pending", "Completed", "Cancelled"]
        if new_status not in valid_statuses:
            return {
                "success": False,
                "message": _("Invalid status. Allowed statuses: {0}").format(', '.join(valid_statuses))
            }
        
        # جلب المهمة
        task = frappe.get_doc("Service Task", task_name)
        
        # التحقق من الصلاحيات
        if not task_api._can_edit_task(task):
            return {
                "success": False,
                "message": _("You don't have permission to modify this task")
            }
        
        # تحديث الحالة باستخدام frappe.db.set_value لتجاوز قيود سير العمل
        frappe.db.set_value("Service Task", task_name, "status", new_status, update_modified=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Task status updated to {0}").format(new_status)
        }
        
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "message": _("Task does not exist")
        }
    except Exception as e:
        frappe.log_error(f"Error in update_task_status: {str(e)}")
        return {
            "success": False,
            "message": _("Error updating task status: {0}").format(str(e))
        }

@frappe.whitelist()
def get_task_filters():
    """الحصول على خيارات الفلاتر المتاحة"""
    try:
        # خيارات الحالة
        status_options = [
            {"value": "All", "label": _("All Statuses")},
            {"value": "Open", "label": _("Open")},
            {"value": "In Progress", "label": _("In Progress")},
            {"value": "Pending", "label": _("Pending")},
            {"value": "Completed", "label": _("Completed")},
            {"value": "Cancelled", "label": _("Cancelled")}
        ]
        
        # خيارات التاريخ
        date_options = [
            {"value": "all", "label": _("All Dates")},
            {"value": "today", "label": _("Today")},
            {"value": "week", "label": _("This Week")},
            {"value": "month", "label": _("This Month")},
            {"value": "overdue", "label": _("Overdue")}
        ]
        
        return {
            "success": True,
            "status_options": status_options,
            "date_options": date_options
        }
    except Exception as e:
        frappe.log_error(f"Error in get_task_filters: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def search_tasks(search_term, status=None, due_filter=None):
    """البحث في المهام"""
    try:
        # استخدام get_my_tasks مع معاملات البحث
        return get_my_tasks(status=status, due_filter=due_filter, search_term=search_term)
        
    except Exception as e:
        frappe.log_error(f"Error in search_tasks: {str(e)}")
        return {
            "success": False,
            "message": _("Error in search: {0}").format(str(e)),
            "tasks": [],
            "count": 0,
            "stats": {
                'total': 0,
                'completed': 0,
                'in_progress': 0,
                'pending': 0,
                'overdue': 0
            }
        }

@frappe.whitelist()
def batch_update_tasks(task_names, updates):
    """تحديث مجموعة من المهام"""
    try:
        task_api = TaskAPI()
        
        if not task_names or not updates:
            return {
                "success": False,
                "message": _("No tasks or updates provided")
            }
        
        # تحويل البيانات إذا كانت نصية
        if isinstance(task_names, str):
            task_names = json.loads(task_names)
        if isinstance(updates, str):
            updates = json.loads(updates)
        
        success_count = 0
        failed_tasks = []
        
        for task_name in task_names:
            try:
                task = frappe.get_doc("Service Task", task_name)
                
                # التحقق من الصلاحيات
                if not task_api._can_edit_task(task):
                    failed_tasks.append({
                        "task": task_name,
                        "error": _("No permission")
                    })
                    continue
                
                # تطبيق التحديثات
                for field, value in updates.items():
                    if field in ["status", "assigned_to", "assigned_role", "notes"]:
                        setattr(task, field, value)
                
                task.save()
                success_count += 1
                
            except Exception as e:
                failed_tasks.append({
                    "task": task_name,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "updated": success_count,
            "failed": failed_tasks,
            "message": _("Updated {0} tasks successfully").format(success_count)
        }
        
    except Exception as e:
        frappe.log_error(f"Error in batch_update_tasks: {str(e)}")
        return {
            "success": False,
            "message": _("Error updating tasks: {0}").format(str(e))
        }

@frappe.whitelist()
def export_tasks(filters=None):
    """تصدير المهام إلى ملف CSV أو Excel"""
    try:
        # معالجة الفلاتر
        if filters and isinstance(filters, str):
            filters = json.loads(filters)
        
        # جلب المهام
        tasks_result = get_my_tasks(
            status=filters.get('status') if filters else None,
            due_filter=filters.get('due_filter') if filters else None,
            search_term=filters.get('search_term') if filters else None
        )
        
        if not tasks_result.get('success'):
            return tasks_result
        
        tasks = tasks_result.get('tasks', [])
        
        # إعداد البيانات للتصدير
        export_data = []
        for task in tasks:
            export_data.append({
                _("Task Title"): task.get('task_title_translated', task.get('task_title')),
                _("Status"): task.get('status_translated', task.get('status')),
                _("Due Date"): task.get('due_date'),
                _("Local Due Date"): task.get('local_due_date'),
                _("Assigned To"): task.get('assigned_to'),
                _("Assigned Role"): task.get('assigned_role'),
                _("Notes"): task.get('notes'),
                _("Created"): task.get('creation'),
                _("Modified"): task.get('modified')
            })
        
        return {
            "success": True,
            "data": export_data,
            "count": len(export_data)
        }
        
    except Exception as e:
        frappe.log_error(f"Error in export_tasks: {str(e)}")
        return {
            "success": False,
            "message": _("Error exporting tasks: {0}").format(str(e))
        }

@frappe.whitelist()
def get_task_history(task_name):
    """الحصول على تاريخ التغييرات للمهمة"""
    try:
        task_api = TaskAPI()
        
        # جلب المهمة للتحقق من الصلاحيات
        task = frappe.get_doc("Service Task", task_name)
        
        can_view = task_api.is_admin or (
            task.assigned_to == task_api.current_user or 
            (task.assigned_role and task.assigned_role in task_api.user_roles and not task.assigned_to)
        )
        
        if not can_view:
            return {
                "success": False,
                "message": _("You don't have permission to view this task history")
            }
        
        # جلب تاريخ التغييرات من Version doctype
        versions = frappe.get_all(
            "Version",
            filters={
                "ref_doctype": "Service Task",
                "docname": task_name
            },
            fields=["name", "owner", "creation", "data"],
            order_by="creation desc",
            limit=50
        )
        
        # تنسيق البيانات
        history = []
        for version in versions:
            try:
                data = json.loads(version.data) if version.data else {}
                
                history.append({
                    "user": version.owner,
                    "date": version.creation,
                    "changes": data.get("changed", [])
                })
            except:
                continue
        
        return {
            "success": True,
            "history": history
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_task_history: {str(e)}")
        return {
            "success": False,
            "message": _("Error fetching task history: {0}").format(str(e))
        }
@frappe.whitelist()
def get_dashboard_data():
    """الحصول على بيانات لوحة القيادة"""
    try:
        task_api = TaskAPI()
        
        # الإحصائيات الأساسية
        stats_result = get_my_tasks()
        if not stats_result.get('success'):
            return stats_result
        
        stats = stats_result.get('stats', {})
        
        # المهام القادمة
        upcoming_tasks = frappe.db.sql("""
            SELECT name, task_title, due_date, status
            FROM `tabService Task`
            WHERE due_date >= %s
            AND status != 'Completed'
            ORDER BY due_date ASC
            LIMIT 5
        """, (nowdate(),), as_dict=True)
        
        # تنسيق المهام القادمة
        formatted_upcoming = []
        for task in upcoming_tasks:
            formatted_task = task_api._format_task(task)
            formatted_upcoming.append({
                "name": formatted_task["name"],
                "title": formatted_task["task_title_translated"],
                "due_date": formatted_task["due_date"],
                "status": formatted_task["status_translated"]
            })
        
        return {
            "success": True,
            "stats": stats,
            "upcoming_tasks": formatted_upcoming,
            "chart_data": {
                "labels": [_("Completed"), _("In Progress"), _("Pending"), _("Overdue")],
                "data": [
                    stats.get('completed', 0),
                    stats.get('in_progress', 0),
                    stats.get('pending', 0),
                    stats.get('overdue', 0)
                ]
            }
        }

    except Exception as e:
        frappe.log_error(f"Error in get_dashboard_data: {str(e)}")
        return {
            "success": False,
            "message": _("Error fetching dashboard data: {0}").format(str(e))
        }


@frappe.whitelist()
def create_task(task_data):
    """إنشاء مهمة جديدة"""
    try:
        task_api = TaskAPI()
        
        # التحقق من البيانات المدخلة
        if isinstance(task_data, str):
            task_data = json.loads(task_data)
        
        # التحقق من الحقول المطلوبة
        required_fields = ["task_title", "due_date"]
        for field in required_fields:
            if not task_data.get(field):
                return {
                    "success": False,
                    "message": _("Field {0} is required").format(field)
                }
        
        # إنشاء المهمة
        task = frappe.new_doc("Service Task")
        task.task_title = task_data.get("task_title")
        task.due_date = task_data.get("due_date")
        task.local_due_date = task_data.get("local_due_date")
        task.assigned_to = task_data.get("assigned_to")
        task.assigned_role = task_data.get("assigned_role")
        task.notes = task_data.get("notes")
        task.status = task_data.get("status", "Open")
        task.parent = task_data.get("parent")
        
        task.insert()
        frappe.db.commit()
        
        # تنسيق وإرجاع البيانات
        formatted_task = task_api._format_task(task)
        
        return {
            "success": True,
            "message": _("Task created successfully"),
            "task": formatted_task
        }
        
    except Exception as e:
        frappe.log_error(f"Error in create_task: {str(e)}")
        return {
            "success": False,
            "message": _("Error creating task: {0}").format(str(e))
        }

@frappe.whitelist()
def update_task(task_name, updates):
    """تحديث مهمة موجودة"""
    try:
        task_api = TaskAPI()
        
        # التحقق من البيانات المدخلة
        if isinstance(updates, str):
            updates = json.loads(updates)
        
        # جلب المهمة
        task = frappe.get_doc("Service Task", task_name)
        
        # التحقق من الصلاحيات
        if not task_api._can_edit_task(task):
            return {
                "success": False,
                "message": _("You don't have permission to modify this task")
            }
        
        # الحقول المسموح بتحديثها
        allowed_fields = ["task_title", "due_date", "local_due_date", 
                         "assigned_to", "assigned_role", "notes", "status"]
        
        # تطبيق التحديثات
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(task, field, value)
        
        task.save()
        frappe.db.commit()
        
        # تنسيق وإرجاع البيانات
        formatted_task = task_api._format_task(task)
        
        return {
            "success": True,
            "message": _("Task updated successfully"),
            "task": formatted_task
        }
        
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "message": _("Task does not exist")
        }
    except Exception as e:
        frappe.log_error(f"Error in update_task: {str(e)}")
        return {
            "success": False,
            "message": _("Error updating task: {0}").format(str(e))
        }

@frappe.whitelist()
def delete_task(task_name):
    """حذف مهمة"""
    try:
        task_api = TaskAPI()
        
        # جلب المهمة
        task = frappe.get_doc("Service Task", task_name)
        
        # التحقق من الصلاحيات
        if not task_api.is_admin:
            return {
                "success": False,
                "message": _("Only administrators can delete tasks")
            }
        
        # حذف المهمة
        task.delete()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Task deleted successfully")
        }
        
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "message": _("Task does not exist")
        }
    except Exception as e:
        frappe.log_error(f"Error in delete_task: {str(e)}")
        return {
            "success": False,
            "message": _("Error deleting task: {0}").format(str(e))
        }

@frappe.whitelist()
def get_task_statistics_by_period(period="month"):
    """الحصول على إحصائيات المهام حسب الفترة الزمنية"""
    try:
        task_api = TaskAPI()
        
        # تحديد الفترة الزمنية
        if period == "week":
            start_date = add_days(nowdate(), -7)
        elif period == "month":
            start_date = add_months(nowdate(), -1)
        elif period == "quarter":
            start_date = add_months(nowdate(), -3)
        elif period == "year":
            start_date = add_months(nowdate(), -12)
        else:
            start_date = add_days(nowdate(), -30)
        
        # بناء شرط الصلاحيات
        permission_condition = ""
        if not task_api.is_admin:
            user_condition = f"assigned_to = {frappe.db.escape(task_api.current_user)}"
            role_conditions = []
            
            if task_api.user_roles:
                for role in task_api.user_roles:
                    role_conditions.append(f"assigned_role = {frappe.db.escape(role)}")
            
            if role_conditions:
                role_condition = f"({' OR '.join(role_conditions)}) AND assigned_to IS NULL"
                permission_condition = f"AND ({user_condition} OR {role_condition})"
            else:
                permission_condition = f"AND {user_condition}"
        
        # استعلام الإحصائيات
        stats_query = f"""
            SELECT 
                DATE(creation) as date,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending
            FROM `tabService Task`
            WHERE creation >= %s
            {permission_condition}
            GROUP BY DATE(creation)
            ORDER BY date ASC
        """
        
        stats = frappe.db.sql(stats_query, (start_date,), as_dict=True)
        
        # تحضير البيانات للرسم البياني
        dates = []
        completed_data = []
        in_progress_data = []
        pending_data = []
        
        for stat in stats:
            dates.append(str(stat['date']))
            completed_data.append(int(stat['completed'] or 0))
            in_progress_data.append(int(stat['in_progress'] or 0))
            pending_data.append(int(stat['pending'] or 0))
        
        return {
            "success": True,
            "period": period,
            "chart_data": {
                "labels": dates,
                "datasets": [
                    {
                        "label": _("Completed"),
                        "data": completed_data,
                        "backgroundColor": "rgba(40, 167, 69, 0.5)",
                        "borderColor": "rgba(40, 167, 69, 1)"
                    },
                    {
                        "label": _("In Progress"),
                        "data": in_progress_data,
                        "backgroundColor": "rgba(0, 123, 255, 0.5)",
                        "borderColor": "rgba(0, 123, 255, 1)"
                    },
                    {
                        "label": _("Pending"),
                        "data": pending_data,
                        "backgroundColor": "rgba(255, 193, 7, 0.5)",
                        "borderColor": "rgba(255, 193, 7, 1)"
                    }
                ]
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_task_statistics_by_period: {str(e)}")
        return {
            "success": False,
            "message": _("Error fetching task statistics: {0}").format(str(e))
        }

@frappe.whitelist()
def get_user_performance():
    """الحصول على أداء المستخدم"""
    try:
        task_api = TaskAPI()
        
        # إحصائيات المستخدم الحالي
        user_stats_query = """
            SELECT 
                COUNT(*) as total_assigned,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'Completed' AND due_date >= modified THEN 1 ELSE 0 END) as on_time,
                SUM(CASE WHEN status = 'Completed' AND due_date < modified THEN 1 ELSE 0 END) as late,
                SUM(CASE WHEN status != 'Completed' AND due_date < %s THEN 1 ELSE 0 END) as overdue
            FROM `tabService Task`
            WHERE assigned_to = %s
        """
        
        stats = frappe.db.sql(user_stats_query, 
                             (nowdate(), task_api.current_user), 
                             as_dict=True)[0]
        
        # حساب معدل الإنجاز
        total = int(stats['total_assigned'] or 0)
        completed = int(stats['completed'] or 0)
        on_time = int(stats['on_time'] or 0)
        late = int(stats['late'] or 0)
        overdue = int(stats['overdue'] or 0)
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        on_time_rate = (on_time / completed * 100) if completed > 0 else 0
        
        return {
            "success": True,
            "performance": {
                "total_assigned": total,
                "completed": completed,
                "on_time": on_time,
                "late": late,
                "overdue": overdue,
                "completion_rate": round(completion_rate, 2),
                "on_time_rate": round(on_time_rate, 2)
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_user_performance: {str(e)}")
        return {
            "success": False,
            "message": _("Error fetching user performance: {0}").format(str(e))
        }

# دوال مساعدة إضافية

@frappe.whitelist()
def get_task_reminders():
    """الحصول على تذكيرات المهام"""
    try:
        task_api = TaskAPI()
        
        # المهام التي تحتاج تذكير (مستحقة خلال 24 ساعة)
        tomorrow = add_days(nowdate(), 1)
        
        reminders_query = """
            SELECT name, task_title, due_date, assigned_to, assigned_role
            FROM `tabService Task`
            WHERE due_date BETWEEN %s AND %s
            AND status NOT IN ('Completed', 'Cancelled')
        """
        
        if not task_api.is_admin:
            reminders_query += f" AND (assigned_to = {frappe.db.escape(task_api.current_user)}"
            if task_api.user_roles:
                role_conditions = " OR ".join([f"assigned_role = {frappe.db.escape(role)}" 
                                             for role in task_api.user_roles])
                reminders_query += f" OR ({role_conditions} AND assigned_to IS NULL))"
            else:
                reminders_query += ")"
        
        reminders = frappe.db.sql(reminders_query, 
                                 (nowdate(), tomorrow), 
                                 as_dict=True)
        
        # تنسيق التذكيرات
        formatted_reminders = []
        for reminder in reminders:
            formatted_reminder = task_api._format_task(reminder)
            formatted_reminders.append({
                "name": formatted_reminder["name"],
                "title": formatted_reminder["task_title_translated"],
                "due_date": formatted_reminder["due_date"],
                "urgency": _("Due Tomorrow") if reminder['due_date'] == tomorrow else _("Due Today")
            })
        
        return {
            "success": True,
            "reminders": formatted_reminders,
            "count": len(formatted_reminders)
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_task_reminders: {str(e)}")
        return {
            "success": False,
            "message": _("Error fetching task reminders: {0}").format(str(e))
        }
