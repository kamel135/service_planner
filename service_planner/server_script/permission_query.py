import frappe

def get_permission_query_conditions(user, doctype=None):
    # صلاحيات خاصة بـ Service Project
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return ""

    user_org = frappe.db.get_value("User", user, "organization")
    if not user_org:
        return "1=0"

    return f"`tabService Project`.organization = '{user_org}'"


def task_permission_query_conditions(user, doctype=None):
    # صلاحيات خاصة بـ Service Task
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return ""

    user_org = frappe.db.get_value("User", user, "organization")
    if not user_org:
        return "1=0"

    user_roles = frappe.get_roles(user)
    role_conditions = []
    for role in ["Engineer", "Analyst", "Account Manager"]:
        if role in user_roles:
            role_conditions.append(f"`tabService Task`.`assigned_role` = '{role}'")

    conditions = [
        f"`tabService Task`.`parent` IN (SELECT name FROM `tabService Project` WHERE organization = '{user_org}')"
    ]

    if role_conditions:
        conditions.append(f"({' OR '.join(role_conditions)} OR `tabService Task`.`assigned_to` = '{user}')")

    return " AND ".join(conditions)
