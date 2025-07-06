frappe.ui.form.on('Service Task', {
    refresh: function(frm) {
        frm.add_custom_button('Mark as Completed', function() {
            frm.set_value('status', 'Completed');
            frm.save();
        }, 'Actions');
    }
});

frappe.listview_settings['Service Task'] = {
    add_fields: ["status", "due_date"],
    filters: [["due_date", ">=", frappe.datetime.now_date()]],
    get_indicator: function(doc) {
        if (doc.status === "Pending") {
            return [__("Pending"), "orange", "status,=,Pending"];
        } else if (doc.status === "In Progress") {
            return [__("In Progress"), "blue", "status,=,In Progress"];
        } else if (doc.status === "Completed") {
            return [__("Completed"), "green", "status,=,Completed"];
        }
    }
};
