frappe.ui.form.on(['Purchase Receipt', 'Stock Entry', 'Delivery Note'], {
    refresh(frm) {

        if (frm.doc.docstatus !== 1) return;

        frm.clear_custom_buttons();

        // If WAYBILL exists → Show only "Show Waybill"
        if (frm.doc.custom_waybill) {

            frm.add_custom_button("Show Waybill", () => {
                frappe.set_route("Form", "Waybill", frm.doc.custom_waybill);
            }, __("Waybill"));

        } else {

            // Show CREATE button
            frm.add_custom_button("Create Waybill", () => {

                frappe.call({
                    method: "manakshia_steel.api.waybill.create_from_source",
                    args: {
                        doctype: frm.doc.doctype,
                        docname: frm.doc.name
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            const waybill_name = r.message;

                            // Save link to document
                            frm.set_value("custom_waybill", waybill_name);

                            frappe.show_alert("Waybill Created: " + waybill_name);

                            frm.save().then(() => {
                                frappe.set_route("Form", "Waybill", waybill_name);
                            });
                        }
                    }
                });

            }, __("Waybill"));
        }
    }
});
