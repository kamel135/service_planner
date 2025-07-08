import frappe
from frappe.utils import add_days, nowdate, getdate

def execute(doc, method):
    """
    يتم استدعاء هذه الدالة عند حفظ المستند (before_save)
    - توليد المهام تلقائياً عند أول حفظ إذا لم توجد مهام
    - إعادة توليد المهام إذا تغير الدور الافتراضي default_role
    """
    old_doc = doc.get_doc_before_save()

    # حالة أول حفظ: لو لا توجد مهام مولدهاش
    if not old_doc:
        if not doc.service_tasks:
            generate_service_tasks(doc)
        return

    # حالة تحديث الحقل default_role: إعادة توليد المهام مع الدور الجديد
    if doc.default_role != old_doc.default_role:
        generate_service_tasks(doc)


def generate_service_tasks(doc):
    """
    توليد المهام تلقائياً بناءً على نوع الجدولة والدور الافتراضي
    """
    schedule = doc.schedule_type
    start = getdate(doc.start_date) if doc.start_date else getdate(nowdate())
    interval = int(doc.interval_days or 1)
    task_role = doc.default_role or "Engineer"

    # مسح المهام السابقة
    doc.service_tasks = []

    # توليد المهام لمدة 7 أيام (يمكن تغيير العدد حسب الحاجة)
    for i in range(7):
        task_date = None

        if schedule == 'Daily':
            task_date = add_days(start, i)
        elif schedule == 'Weekly' and i % 7 == 0:
            task_date = add_days(start, i)
        elif schedule == 'Every X Days' and i % interval == 0:
            task_date = add_days(start, i)

        if task_date:
            doc.append('service_tasks', {
                'task_title': f'Auto Task for {task_date}',
                'due_date': task_date,
                'assigned_role': task_role,
                'status': 'Pending',
                'notes': f'Task generated for {schedule} on {task_date}'
                # يمكنك لاحقًا تحديد `assigned_to` حسب الدور
            })


@frappe.whitelist()
def regenerate_tasks(project_name):
    """
    API لإعادة توليد المهام يدوياً
    """
    doc = frappe.get_doc("Service Project", project_name)

    if not frappe.has_permission("Service Project", "write", doc):
        frappe.throw("You don’t have permission to regenerate tasks.")

    generate_service_tasks(doc)
    doc.save()

    return {
        "success": True,
        "message": f"Regenerated {len(doc.service_tasks)} tasks."
    }


def validate_schedule_configuration(doc, method):
    """
    التحقق من صحة إعدادات الجدولة
    """
    if doc.schedule_type == "Every X Days":
        if not doc.interval_days or doc.interval_days <= 0:
            frappe.throw("Interval Days must be a positive number when Schedule Type is 'Every X Days'")

    if doc.start_date and getdate(doc.start_date) < getdate(nowdate()):
        frappe.msgprint("⚠️ Warning: Start date is in the past. Tasks will be generated from the specified date.")
