import frappe
from frappe.utils import nowdate

def notify_task_update(doc, method=None):
    recipients = set()

    # 1️⃣ لكل مستخدم لديه نفس الدور المعين
    if doc.assigned_role:
        role_users = frappe.get_all(
            "Has Role",
            filters={"role": doc.assigned_role},
            fields=["parent"]
        )
        for user in role_users:
            recipients.add(user.parent)

    # 2️⃣ المستخدم المحدد مباشرة في "Assigned To"
    if doc.assigned_to:
        recipients.add(doc.assigned_to)

    # 🔃 إزالة المستخدمين غير المرغوبين
    recipients = [u for u in recipients if u not in ("Guest", "Administrator")]

    # 3️⃣ إرسال الإشعارات لكل مستلم
    if recipients:
        message = f"""
            📌 <b>تم إنشاء أو تعديل مهمة:</b><br>
            <b>العنوان:</b> {doc.task_title}<br>
            <b>التاريخ:</b> {doc.due_date}
        """
        for user in recipients:
            # إشعار فوري
            frappe.publish_realtime(
                event="task_notification",
                user=user,
                message=message
            )

            # بريد إلكتروني
            frappe.sendmail(
                recipients=user,
                subject="📋 إشعار مهمة جديدة أو محدثة",
                message=message,
                reference_doctype=doc.doctype,
                reference_name=doc.name
            )

            # إشعار داخل النظام 🔔
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": f"📋 مهمة: {doc.task_title}",
                "email_content": message,
                "for_user": user,
                "document_type": doc.doctype,
                "document_name": doc.name,
                "type": "Alert"
            }).insert(ignore_permissions=True)


def notify_scheduled_tasks():
    """تشغيل يومي لإرسال تذكير بالتاسكات المستحقة"""
    today = nowdate()
    tasks = frappe.get_all(
        "Service Task",
        filters={"due_date": today},
        fields=["name", "task_title", "assigned_role", "assigned_to", "due_date"]
    )

    for task in tasks:
        recipients = set()

        # حسب الدور
        if task.assigned_role:
            users_with_role = frappe.get_all(
                "Has Role",
                filters={"role": task.assigned_role},
                fields=["parent"]
            )
            for user in users_with_role:
                recipients.add(user.parent)

        # حسب المستخدم المخصص
        if task.assigned_to:
            recipients.add(task.assigned_to)

        recipients = [u for u in recipients if u not in ("Guest", "Administrator")]

        if recipients:
            message = f"""
                🕒 <b>تذكير بمهمة اليوم:</b><br>
                <b>المهمة:</b> {task.task_title}<br>
                <b>التاريخ:</b> {task.due_date}
            """
            for user in recipients:
                frappe.publish_realtime(
                    event="task_notification",
                    user=user,
                    message=message
                )

                frappe.sendmail(
                    recipients=user,
                    subject="📌 تذكير: مهمة مستحقة اليوم",
                    message=message,
                    reference_doctype="Service Task",
                    reference_name=task.name
                )

                frappe.get_doc({
                    "doctype": "Notification Log",
                    "subject": f"📌 تذكير: {task.task_title}",
                    "email_content": message,
                    "for_user": user,
                    "document_type": "Service Task",
                    "document_name": task.name,
                    "type": "Alert"
                }).insert(ignore_permissions=True)
