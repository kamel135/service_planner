frappe.ui.form.on('Service Task', {
    refresh: function(frm) {
        update_local_time_display(frm);
        
        // إضافة مؤشر للتوضيح
        if (frm.doc.due_date) {
            frm.set_df_property('due_date', 'description', 
                'Stored in UTC. Local time shown below'
            );
        }
    }
});

function update_local_time_display(frm) {
    let local_dt_str = frm.doc.local_due_date;
    let utc_dt_str = frm.doc.due_date;
    let timezone = frm.doc.user_timezone;

    if (!local_dt_str) {
        return;
    }

    // تنسيق التاريخ
    let display_format = "dddd, MMMM Do YYYY, h:mm A";
    let formatted_local_time = moment(local_dt_str).format(display_format);

    // عرض المعلومات
    let html = `
        <div style="padding: 10px; background: #f5f5f5; border-radius: 5px;">
            <p style="margin-bottom: 5px;">
                <strong>${formatted_local_time}</strong>
            </p>
            <p class="text-muted small" style="margin-bottom: 0;">
                Timezone: ${timezone || 'N/A'} (UTC: ${moment.utc(utc_dt_str).format('h:mm A')})
            </p>
        </div>
    `;
    
    frm.set_df_property('due_date_display', 'options', html);
    frm.refresh_field('due_date_display');
}
