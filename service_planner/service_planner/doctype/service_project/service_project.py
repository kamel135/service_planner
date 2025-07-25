import frappe
from frappe.model.document import Document
from service_planner.scripts.generate_tasks import generate_task_title  # ← تأكد من المسار الصحيح

class ServiceProject(Document):
    def before_save(self):
        for task in self.service_tasks:
            if not task.organization:
                task.organization = self.organization

        self.update_task_titles()  # ← استدعاء الدالة هنا مهم

    def update_task_titles(self):
        """تحديث العناوين تلقائيًا عند تغيير الـ Task Template"""
        if not self.get_doc_before_save():
            return

        old = self.get_doc_before_save()
        if self.task_template != old.task_template:
            for task in self.service_tasks:
                if task.due_date:
                    task.task_title = generate_task_title(self, task.due_date)

# فلترة المشاريع بحيث المستخدم يرى فقط المشاريع التي تنتمي لشركته
def permission_query_condition(user):
    user_doc = frappe.get_doc("User", user)
    user_org = getattr(user_doc, "organization", None)

    if not user_org:
        return "1=0"

    return f"`tabService Project`.organization = '{user_org}'"
