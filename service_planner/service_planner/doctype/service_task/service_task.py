import frappe

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    # جلب صلاحيات المستخدم
    user_roles = frappe.get_roles(user)
    user_org = frappe.get_cached_value("User", user, "organization")

    if not user_org or not user_roles:
        return "1=0"  # لا يوجد صلاحية

    roles_str = "', '".join([frappe.db.escape(role) for role in user_roles])

    return f"""
        assigned_role IN ('{roles_str}')
        AND organization = {frappe.db.escape(user_org)}
    """

def has_permission(doc, ptype, user):
    user_roles = frappe.get_roles(user)
    user_org = frappe.get_cached_value("User", user, "organization")

    return (
        doc.assigned_role in user_roles and doc.organization == user_org
    )
