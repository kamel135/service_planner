frappe.ui.form.on('Service Task', {
    refresh: function(frm) {
        // تطبيق القيود على الحقول
        if (!frappe.user.has_role('System Manager')) {
            frm.doc.meta.fields.forEach(field => {
                if (field.fieldname !== 'status') {
                    frm.set_df_property(field.fieldname, 'read_only', 1);
                }
            });

            // إضافة تحذير عند محاولة التعديل
            $('.frappe-control input, .frappe-control select, .frappe-control textarea').on('click', function(e) {
                let fieldname = $(this).attr('data-fieldname');
                if (fieldname && fieldname !== 'status') {
                    frappe.show_alert({
                        message: `لا يمكنك تعديل حقل ${fieldname}`,
                        indicator: 'red'
                    });
                    e.preventDefault();
                    return false;
                }
            });
        }
    },

    validate: function(frm) {
        if (!frappe.user.has_role('System Manager')) {
            let old_doc = frm.doc.__oldvalues || {};
            let changed_fields = [];

            // التحقق من الحقول المتغيرة
            Object.keys(frm.doc).forEach(field => {
                if (field !== 'status' && 
                    field !== 'modified' && 
                    field !== 'modified_by' &&
                    old_doc[field] !== frm.doc[field]) {
                    changed_fields.push(field);
                }
            });

            if (changed_fields.length > 0) {
                frappe.validated = false;
                frappe.throw(__(`لا يمكنك تعديل الحقول التالية: ${changed_fields.join(', ')}`));
            }
        }
    }
});

frappe.ui.form.on('Service Task', {
    refresh: function(frm) {
        // تطبيق القيود على الحقول
        if (!frappe.user.has_role('System Manager')) {
            // قفل كل الحقول ما عدا Status
            frm.doc.meta.fields.forEach(field => {
                if (field.fieldname !== 'status') {
                    frm.set_df_property(field.fieldname, 'read_only', 1);
                }
            });

            // إضافة مؤشر بصري للحقول المقفلة
            $('.frappe-control').not('[data-fieldname="status"]').each(function() {
                $(this).find('input, select, textarea').css('background-color', '#f8f9fa');
                $(this).append('<div class="lock-indicator">🔒</div>');
            });
        }
    },

    validate: function(frm) {
        if (!frappe.user.has_role('System Manager')) {
            let old_doc = frm.doc.__oldvalues || {};
            let changed_fields = [];

            Object.keys(frm.doc).forEach(field => {
                if (field !== 'status' && 
                    field !== 'modified' && 
                    field !== 'modified_by' &&
                    old_doc[field] !== frm.doc[field]) {
                    changed_fields.push(field);
                }
            });

            if (changed_fields.length > 0) {
                frappe.validated = false;
                frappe.throw(__(`لا يمكنك تعديل الحقول التالية: ${changed_fields.join(', ')}`));
            }
        }
    },

    status: function(frm) {
        // تحديث تلقائي عند تغيير الحالة
        frm.save();
    }
});
