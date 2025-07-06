frappe.ui.form.on('Service Project', {
    onload: function(frm) {
        // تجاهل الفلترة للمسؤول
        if (!frappe.user_roles.includes("System Manager")) {
            const user = frappe.session.user;
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "User",
                    name: user
                },
                callback: function(r) {
                    if (r.message) {
                        const user_org = r.message.organization;
                        const user_roles = frappe.user_roles;

                        frm.doc.service_tasks = (frm.doc.service_tasks || []).filter(task => {
                            return (
                                user_roles.includes(task.assigned_role) &&
                                task.organization === user_org
                            );
                        });

                        frm.refresh_field("service_tasks");
                    }
                }
            });
        }
    }
});
