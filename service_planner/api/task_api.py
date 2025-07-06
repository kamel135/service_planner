import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def get_todays_tasks():
    user = frappe.session.user

    return frappe.get_all("Service Task",
        filters={
            "assigned_to": user,
            "due_date": ["=", nowdate()]
        },
        fields=["name", "task_title", "due_date", "status", "assigned_role"]
    )
