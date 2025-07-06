frappe.ui.form.on('Service Project', {
    onload: function(frm) {
        const user_roles = frappe.user_roles || [];
        console.log("✅ User Roles:", user_roles);

        if (!user_roles.includes("System Manager")) {
            frm.trigger("restrict_service_tasks");
        }
    },

    restrict_service_tasks: function(frm) {
        const user_roles = frappe.user_roles || [];
        const allowed_fields = ["status", "notes", "completion_notes"];

        // ✅ فلترة المهام بناءً على الدور
        const allowed_tasks = (frm.doc.service_tasks || []).filter(task => {
            return user_roles.includes(task.assigned_role);
        });

        // ✅ تحديث قائمة المهام وإعادة عرضها
        frm.doc.service_tasks = allowed_tasks;
        frm.refresh_field("service_tasks");

        // 🔒 جعل الحقول غير المسموح بها Read-Only
        const grid = frm.fields_dict.service_tasks.grid;
        if (grid && grid.fields) {
            grid.fields.forEach(df => {
                df.read_only = !allowed_fields.includes(df.fieldname);
            });
        }

        // 🔁 تحديث الشبكة
        grid.refresh();
    }
});
