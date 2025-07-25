// Copyright (c) 2025, Kamel Elnemr and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Service Project", {
// 	refresh(frm) {

// 	},
// });


frappe.ui.form.on('Service Project', {
    schedule_type: function(frm) {
        // إعادة تقييم الحقول الإلزامية عند تغيير نوع الجدولة
        frm.refresh_field('weekly_days');
        
        if (frm.doc.schedule_type === 'Weekly') {
            if (!frm.doc.weekly_days) {
                // تعيين قيمة افتراضية إذا لم يتم اختيار أي يوم
                frm.set_value('weekly_days', 'Monday');
            }
            frm.set_df_property('weekly_days', 'reqd', 1);
        } else {
            frm.set_df_property('weekly_days', 'reqd', 0);
        }
    },

    validate: function(frm) {
        if (frm.doc.schedule_type === 'Weekly' && !frm.doc.weekly_days) {
            frappe.throw(__('Please select at least one day for weekly schedule'));
        }
    }
});
