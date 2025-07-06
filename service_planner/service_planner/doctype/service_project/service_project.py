import frappe
from frappe.model.document import Document

class ServiceProject(Document):
    def before_save(self):
        for task in self.service_tasks:
            if not task.organization:
                task.organization = self.organization

# فلترة المشاريع بحيث المستخدم يرى فقط المشاريع التي تنتمي لشركته
def permission_query_condition(user):
    user_doc = frappe.get_doc("User", user)
    user_org = getattr(user_doc, "organization", None)

    if not user_org:
        return "1=0"

    return f"`tabService Project`.organization = '{user_org}'"
