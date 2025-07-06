import frappe

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    # Get user roles
    user_roles = frappe.get_roles(user)

    # Get user organization from custom field
    user_org = frappe.get_cached_value("User", user, "organization")

    if not user_org or not user_roles:
        return "1=0"  # Deny access if missing

    # Prepare condition: match assigned_role to any user role + same organization
    roles_str = "', '".join([frappe.db.escape(role) for role in user_roles])

    return f"""
        assigned_role IN ('{roles_str}')
        AND organization = {frappe.db.escape(user_org)}
    """

def has_permission(doc, ptype, user):
    # Get user roles
    user_roles = frappe.get_roles(user)

    # Get user organization
    user_org = frappe.get_cached_value("User", user, "organization")

    # Allow if assigned role matches user role AND same organization
    return (
        doc.assigned_role in user_roles and doc.organization == user_org
    )
