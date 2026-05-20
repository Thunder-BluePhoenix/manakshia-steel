function add_waybill_button(frm) {
  if (frm.doc.docstatus !== 1) return;

  // Check if Waybill already exists for this document
  frappe.db
    .get_value("Waybill", { delivery_order_no: frm.doc.name }, "name")
    .then((r) => {
      if (r.message && r.message.name) {
        // Waybill Exists -> View Button
        frm.add_custom_button(
          __("View Waybill"),
          function () {
            frappe.set_route("Form", "Waybill", r.message.name);
          },
          __("Waybill")
        );
      } else {
        // No Waybill -> Create Button
        frm.add_custom_button(
          __("Create Waybill"),
          function () {
            frappe.call({
              method: "manakshia_steel.api.waybill.create_from_source",
              args: {
                doctype: frm.doc.doctype,
                docname: frm.doc.name,
              },
              freeze: true,
              freeze_message: __("Creating Waybill..."),
              callback: function (r) {
                if (r.message) {
                  frappe.show_alert({
                    message: __("Waybill Created: ") + r.message,
                    indicator: "green",
                  });
                  // Refresh to update button
                  frm.reload_doc();
                }
              },
            });
          },
          __("Waybill")
        );
      }
    });
}

frappe.ui.form.on("Purchase Receipt", {
  refresh: function (frm) {
    add_waybill_button(frm);
  },
});

frappe.ui.form.on("Stock Entry", {
  refresh: function (frm) {
    add_waybill_button(frm);
  },
});

frappe.ui.form.on("Delivery Note", {
  refresh: function (frm) {
    add_waybill_button(frm);
  },
});
