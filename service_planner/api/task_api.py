# service_planner/api/task_api.py

import frappe
from frappe.utils import nowdate, getdate, add_days
from typing import Dict, List, Optional, Union
from datetime import datetime

class TaskAPI:
    def __init__(self):
        self.current_user = frappe.session.user
        self.user_roles = frappe.get_roles(self.current_user)
        self.is_admin = self._check_if_admin()

    def _check_if_admin(self) -> bool:
        """التحقق مما إذا كان المستخدم الحالي مدير نظام"""
        return any(role in self.user_roles for role in ["System Manager", "Administrator"])

    def _build_conditions(self, status: Optional[str] = None, due_filter: Optional[str] = None) -> tuple:
        """بناء شروط الاستعلام SQL"""
        conditions = []
        params = {}

        # شروط الصلاحيات
        if not self.is_admin:
            # تعديل شروط الصلاحيات
            assigned_conditions = []
            
            # المهام المسندة مباشرة للمستخدم
            assigned_conditions.append(f"assigned_to = '{self.current_user}'")
            
            # المهام التي ليس لها assigned_to ولكن دور المستخدم يطابق assigned_role
            roles_str = "', '".join(self.user_roles)
            assigned_conditions.append(f"(assigned_to IS NULL AND assigned_role IN ('{roles_str}'))")
            
            conditions.append(f"({' OR '.join(assigned_conditions)})")

        # فلتر الحالة
        if status and status != 'All':
            conditions.append("status = %(status)s")
            params['status'] = status

        # فلتر التاريخ المستحق
        if due_filter and due_filter != 'all':
            today = nowdate()
            if due_filter == "today":
                conditions.append("DATE(due_date) = %(today)s")
                params['today'] = today
            elif due_filter == "overdue":
                conditions.append("DATE(due_date) < %(today)s AND status != 'Completed'")
                params['today'] = today
            elif due_filter == "upcoming":
                conditions.append("DATE(due_date) > %(today)s")
                params['today'] = today
            elif due_filter == "week":
                week_end = add_days(today, 7)
                conditions.append("DATE(due_date) BETWEEN %(today)s AND %(week_end)s")
                params['today'] = today
                params['week_end'] = week_end

        where_clause = " AND ".join(conditions)
        return f"WHERE {where_clause}" if conditions else "", params

    def _format_task(self, task: Dict) -> Dict:
        """تنسيق بيانات المهمة"""
        return {
            "name": task.name,
            "task_title": task.task_title or "بدون عنوان",
            "due_date": task.due_date.strftime('%Y-%m-%d') if task.due_date else None,
            "status": task.status or "Pending",
            "assigned_to": task.assigned_to,
            "assigned_role": task.assigned_role,
            "notes": task.notes,
            "creation": task.creation.strftime('%Y-%m-%d %H:%M:%S') if task.creation else None,
            "modified": task.modified.strftime('%Y-%m-%d %H:%M:%S') if task.modified else None,
            "parent": task.parent,
            "can_edit": self._can_edit_task(task)
        }

    def _can_edit_task(self, task: Dict) -> bool:
        """التحقق من إمكانية تعديل المهمة"""
        if self.is_admin:
            return True
        
        # إذا كانت المهمة مسندة لشخص محدد
        if task.assigned_to:
            return task.assigned_to == self.current_user
            
        # إذا كانت المهمة مسندة لدور وليس لشخص محدد
        if task.assigned_role:
            return task.assigned_role in self.user_roles
            
        return False

    def get_task_stats(self) -> Dict:
        """الحصول على إحصائيات المهام"""
        try:
            conditions, params = self._build_conditions()
            
            stats_query = f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress,
                    SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN due_date < CURDATE() AND status != 'Completed' THEN 1 ELSE 0 END) as overdue
                FROM `tabService Task`
                {conditions}
            """
            
            stats = frappe.db.sql(stats_query, params, as_dict=True)[0]
            return {
                "success": True,
                "stats": stats
            }
        except Exception as e:
            frappe.log_error(f"Error in get_task_stats: {str(e)}")
            return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_my_tasks(status: Optional[str] = None, due_filter: Optional[str] = None) -> Dict:
    """الحصول على المهام الخاصة بالمستخدم"""
    try:
        task_api = TaskAPI()
        conditions, params = task_api._build_conditions(status, due_filter)
        
        query = f"""
            SELECT 
                name,
                task_title,
                due_date,
                assigned_role,
                assigned_to,
                status,
                notes,
                parent,
                creation,
                modified
            FROM `tabService Task`
            {conditions}
            ORDER BY due_date ASC, creation DESC
        """
        
        tasks = frappe.db.sql(query, params, as_dict=True)
        formatted_tasks = [task_api._format_task(task) for task in tasks]
        
        stats = task_api.get_task_stats()

        return {
            "success": True,
            "tasks": formatted_tasks,
            "count": len(formatted_tasks),
            "stats": stats.get("stats") if stats.get("success") else None,
            "user_info": {
                "user": task_api.current_user,
                "roles": task_api.user_roles,
                "is_admin": task_api.is_admin
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_my_tasks: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "حدث خطأ في جلب المهام"
        }

@frappe.whitelist()
def mark_task_completed(task_name: str) -> Dict:
    """تحديث حالة المهمة إلى مكتملة"""
    try:
        task_api = TaskAPI()
        task = frappe.get_doc("Service Task", task_name)
        
        # التحقق من الصلاحيات
        if not task_api._can_edit_task(task):
            return {
                "success": False,
                "message": "ليس لديك صلاحية لتعديل هذه المهمة"
            }
        
        task.status = "Completed"
        task.save()
        
        return {
            "success": True,
            "message": "تم تحديث حالة المهمة بنجاح"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in mark_task_completed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "حدث خطأ في تحديث حالة المهمة"
        }

@frappe.whitelist()
def get_task_details(task_name: str) -> Dict:
    """الحصول على تفاصيل المهمة"""
    try:
        task_api = TaskAPI()
        
        # استعلام SQL للحصول على تفاصيل المهمة
        query = """
            SELECT 
                name,
                task_title,
                due_date,
                assigned_role,
                assigned_to,
                status,
                notes,
                parent,
                creation,
                modified
            FROM `tabService Task`
            WHERE name = %(task_name)s
        """
        
        if not task_api.is_admin:
            # إضافة شروط الصلاحيات للمستخدمين غير المدراء
            roles_str = "', '".join(task_api.user_roles)
            query += f"""
                AND (
                    assigned_to = '{task_api.current_user}'
                    OR (assigned_to IS NULL AND assigned_role IN ('{roles_str}'))
                )
            """
        
        task = frappe.db.sql(query, {'task_name': task_name}, as_dict=True)
        
        if not task:
            return {
                "success": False,
                "message": "لم يتم العثور على المهمة أو ليس لديك صلاحية لعرضها"
            }
            
        formatted_task = task_api._format_task(task[0])
        
        return {
            "success": True,
            "task": formatted_task
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_task_details: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "حدث خطأ في جلب تفاصيل المهمة"
        }

@frappe.whitelist()
def mark_task_completed(task_name: str) -> Dict:
    """تحديث حالة المهمة إلى مكتملة"""
    try:
        task_api = TaskAPI()
        
        # التحقق من وجود المهمة وجلب تفاصيلها
        task_query = """
            SELECT 
                name,
                task_title,
                status,
                assigned_to,
                assigned_role,
                parent
            FROM `tabService Task`
            WHERE name = %(task_name)s
        """
        
        task = frappe.db.sql(task_query, {'task_name': task_name}, as_dict=True)
        
        if not task:
            return {
                "success": False,
                "message": "لم يتم العثور على المهمة"
            }
            
        task = task[0]
        
        # التحقق من الصلاحيات
        if not task_api.is_admin:
            if task.assigned_to and task.assigned_to != task_api.current_user:
                return {
                    "success": False,
                    "message": "ليس لديك صلاحية لتعديل هذه المهمة"
                }
            elif task.assigned_role and task.assigned_role not in task_api.user_roles:
                return {
                    "success": False,
                    "message": "ليس لديك الدور المطلوب لتعديل هذه المهمة"
                }

        # تحديث حالة المهمة
        frappe.db.sql("""
            UPDATE `tabService Task`
            SET status = 'Completed', modified = NOW(), modified_by = %(user)s
            WHERE name = %(task_name)s
        """, {
            'task_name': task_name,
            'user': task_api.current_user
        })
        
        frappe.db.commit()
        
        # إرسال إشعار (اختياري)
        try:
            frappe.publish_realtime('task_status_updated', {
                'task': task_name,
                'status': 'Completed'
            })
        except:
            pass  # تجاهل أي أخطاء في الإشعارات
        
        return {
            "success": True,
            "message": "تم إكمال المهمة بنجاح",
            "task_name": task_name
        }
        
    except Exception as e:
        frappe.log_error(f"Error in mark_task_completed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "فشل تحديث المهمة"
        }
