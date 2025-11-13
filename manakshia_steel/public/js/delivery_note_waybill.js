frappe.ui.form.on('Delivery Note', {
    refresh(frm) {
        if (frm.doc.docstatus !== 1) return;

        frm.clear_custom_buttons();

        if (frm.doc.custom_waybill) {
            frm.add_custom_button("Show Waybill", () => {
                frappe.set_route("Form", "Waybill", frm.doc.custom_waybill);
            }, __("Waybill"));
        } else {
            frm.add_custom_button("Create Waybill", () => {
                frappe.call({
                    method: "manakshia_steel.api.waybill.create_from_source",
                    args: { doctype: frm.doc.doctype, docname: frm.doc.name },
                    callback(r) {
                        if (!r.exc) {
                            frm.set_value("custom_waybill", r.message);
                            frm.save().then(() => {
                                frappe.set_route("Form", "Waybill", r.message);
                            });
                        }
                    }
                });
            }, __("Waybill"));
        }
    }
});
