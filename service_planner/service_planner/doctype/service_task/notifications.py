import frappe

def notify_users_by_assigned_role(doc, method=None):
    if not doc.assigned_role:
        return

    role = doc.assigned_role

    # Get all users who have that role
    users = frappe.get_all(
        "Has Role",
        filters={"role": role},
        fields=["parent"]
    )

    user_emails = []
    for user in users:
        user_doc = frappe.get_doc("User", user.parent)
        if user_doc.enabled and user_doc.email:
            user_emails.append(user_doc.email)

    # إذا فيه مستخدمين متوافقين مع الدور
    if user_emails:
        subject = f"🔔 مهمة جديدة: {doc.task_title}"
        message = f"""
        <p>تم تعيين مهمة جديدة مرتبطة بدور <b>{role}</b>.</p>
        <p><b>المهمة:</b> {doc.task_title}</p>
        <p><b>الموعد النهائي:</b> {doc.due_date}</p>
        <p><b>الحالة:</b> {doc.status}</p>
        """

        # إرسال الإشعار بالبريد
        frappe.sendmail(
            recipients=user_emails,
            subject=subject,
            message=message
        )

        frappe.msgprint(f"📤 تم إرسال إشعار إلى: {', '.join(user_emails)}")
