import frappe
from frappe.utils import nowdate, getdate

@frappe.whitelist()
def get_my_tasks(status=None, due_filter=None):
    user = frappe.session.user
    roles = frappe.get_roles(user)
    user_company = frappe.db.get_value("User", user, "organization")

    filters = {
        "organization": user_company,
        "assigned_to": ["in", [user, None]],
        "assigned_role": ["in", roles],
    }

    # Filter by status
    if status and status != "All":
        filters["status"] = status

    # Filter by due date
    today = nowdate()
    if due_filter == "today":
        filters["due_date"] = today
    elif due_filter == "soon":
        soon_date = getdate(today).add_days(3)
        filters["due_date"] = ["between", [today, soon_date]]
    elif due_filter == "all":
        filters["due_date"] = [">=", today]
    else:
        filters["due_date"] = [">=", today]

    tasks = frappe.get_all("Service Task",
        filters=filters,
        fields=[
            "name", "task_title", "due_date", "status", 
            "assigned_to", "assigned_role", "organization"
        ]
    )

    return tasks


@frappe.whitelist()
def mark_task_completed(task_name):
    task = frappe.get_doc("Service Task", task_name)
    if not frappe.has_permission(task.doctype, "write", doc=task):
        frappe.throw("ليس لديك صلاحية تعديل هذه المهمة")
    task.status = "Completed"
    task.save()
    return {"success": True}
