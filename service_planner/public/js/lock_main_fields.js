frappe.ui.form.on('Service Project', { 
    onload: function(frm) {
        const user_roles = frappe.user_roles || [];

        if (!user_roles.includes("System Manager")) {
            frm.trigger("lock_specific_main_fields");
        }
    },

    lock_specific_main_fields: function(frm) {
        // ✅ الحقول الأساسية فقط - لا تشمل service_tasks
        const locked_fields = [
            "project_name",
            "organization",
            "start_date",
            "schedule_type",
            "default_role"
        ];

        locked_fields.forEach(fieldname => {
            // لا تعمل set_df_property على الجداول الفرعية
            if (frm.fields_dict[fieldname]) {
                frm.set_df_property(fieldname, "read_only", 1);
            }
        });

        frm.refresh_fields();
    }
});
