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


#def after_insert(doc, method):
 #   message = f"New Service Task Created: {doc.task_title}"

    # إشعار مباشر للمستخدم في assigned_to
 #   if doc.assigned_to:
  #      frappe.publish_realtime(event="task_notification", user=doc.assigned_to, message=message)

    # إشعار لكل الـ Engineers في نفس المنظمة
  # # users_with_role = frappe.db.sql(#"
      #  SELECT HR.parent FROM `tabHas Role` HR
     #   JOIN `tabUser` U ON HR.parent = U.name
    #    WHERE HR.role = %s AND U.organization = %s
 #   """, ("Engineer", doc.organization), as_dict=True)
#
   # for user in users_with_role:
    #    frappe.publish_realtime(event="task_notification", user=user.parent, message=message)
