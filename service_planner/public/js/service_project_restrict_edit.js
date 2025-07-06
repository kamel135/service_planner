frappe.ui.form.on('Service Project', {
    refresh: function(frm) {
        if (!frappe.user_roles.includes("System Manager")) {
            const grid = frm.fields_dict.service_tasks.grid;

            const protected_fields = ["assigned_role", "task_title", "due_date", "organization"];

            protected_fields.forEach(field => {
                grid.get_field(field).editable = false;
            });

            grid.wrapper.on('focusin', 'input, textarea, select', function(e) {
                let $input = $(e.target);
                let fieldname = $input.attr('data-fieldname');
                if (fieldname && fieldname !== "status") {
                    let row_name = $input.closest('[data-name]').attr('data-name');
                    let row = locals["Service Task"][row_name];
                    let value = row[fieldname];
                    if (value) {
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
