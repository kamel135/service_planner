frappe.ui.form.on('Service Task', {
    refresh: function(frm) {
        // لا حاجة لزر مخصص، يمكننا عرض المعلومات مباشرة
        update_local_time_display(frm);
    }
});

function update_local_time_display(frm) {
    // حقل local_due_date يحتوي على التاريخ والوقت بتوقيت المستخدم الذي أنشأ المهمة
    // وحقل due_date يحتوي على توقيت UTC
    
    let local_dt_str = frm.doc.local_due_date;
    let utc_dt_str = frm.doc.due_date;
    let timezone = frm.doc.user_timezone;

    if (!local_dt_str) {
        return; // لا تفعل شيئًا إذا لم يكن هناك تاريخ
    }

    // استخدم moment.js المدمج في Frappe لتنسيق التاريخ بشكل جميل
    // moment(local_dt_str) سيفترض أن السلسلة بالتوقيت المحلي للمتصفح، وهو ما نريده
    let display_format = "dddd, MMMM Do YYYY, h:mm A"; // e.g., "Tuesday, July 22nd 2025, 3:00 PM"
    let formatted_local_time = moment(local_dt_str).format(display_format);

    // اعرض هذه المعلومات في حقل HTML المخصص (due_date_display)
    let html = `
        <div style="padding: 5px;">
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
