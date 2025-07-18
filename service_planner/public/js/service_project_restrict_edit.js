frappe.ui.form.on('Service Project', {
    refresh: function(frm) {
        if (!frappe.user_roles.includes("System Manager")) {
            const grid = frm.fields_dict.service_tasks.grid;

            // ✅ أضف 'assigned_to' هنا كمان
            const protected_fields = ["assigned_role", "task_title", "due_date", "organization", "assigned_to"];

            // ⛔ تعطيل التعديل على الحقول المحمية
            protected_fields.forEach(field => {
                grid.get_field(field).editable = false;
            });

            // ⛔ منع التعديل عند محاولة الكتابة في أي حقل غير مسموح
            grid.wrapper.on('focusin', 'input, textarea, select', function(e) {
                let $input = $(e.target);
                let fieldname = $input.attr('data-fieldname');

                // ✅ فقط المسموح بتعديله مثلاً: status, notes, completion_notes
                const allowed_fields = ["status", "notes", "completion_notes"];

                if (fieldname && !allowed_fields.includes(fieldname)) {
                    let row_name = $input.closest('[data-name]').attr('data-name');
                    let row = locals["Service Task"][row_name];
                    let value = row[fieldname];

                    if (value || fieldname === "assigned_to") {
                        setTimeout(() => {
                            frappe.utils.play_sound('cancel');
                            frappe.show_alert({
                                message: `❌ لا يمكنك تعديل الحقل: ${fieldname}`,
                                indicator: 'red'
                            });
                            $input.blur();
                        }, 100);
                    }
                }
            });
        }
    }
});
