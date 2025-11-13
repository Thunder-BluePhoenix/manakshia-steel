frappe.ui.form.on('Picking Slip', {
    custom_coil: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.custom_coil) {
            // Step 1: get Item Code from Serial No
            frappe.db.get_value("Serial No", row.custom_coil, "item_code")
                .then(res => {
                    if (res.message && res.message.item_code) {
                        let item_code = res.message.item_code;

                        // Step 2: get thickness & width from Item Master
                        frappe.db.get_value("Item", item_code, ["custom_thickness_in_mm", "custom_width_in_mm"])
                            .then(r => {
                                if (r.message) {
                                    frappe.model.set_value(cdt, cdn, "thickness", r.message.custom_thickness_in_mm || "");
                                    frappe.model.set_value(cdt, cdn, "width", r.message.custom_width_in_mm || "");
                                }
                            });
                    }
                });
        }
    }
});