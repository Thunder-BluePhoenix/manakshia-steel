
frappe.ui.form.on('Purchase Receipt Item', {
    warehouse: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.warehouse && row.rejected_warehouse && row.warehouse == row.rejected_warehouse) {
            frappe.model.set_value(cdt, cdn, "rejected_warehouse", "");
        }
    },
    rejected_warehouse: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.warehouse && row.rejected_warehouse && row.warehouse == row.rejected_warehouse) {
            frappe.msgprint(__("Accepted and Rejected Warehouse cannot be the same."));
            frappe.model.set_value(cdt, cdn, "rejected_warehouse", "");
        }
    }
});

frappe.ui.form.on('Purchase Receipt', {
    refresh: function (frm) {
        // Also check on load if defaults caused this
        if (frm.doc.items) {
            frm.doc.items.forEach(row => {
                if (row.warehouse && row.rejected_warehouse && row.warehouse == row.rejected_warehouse) {
                    frappe.model.set_value(row.doctype, row.name, "rejected_warehouse", "");
                }
            });
        }
    }
});
