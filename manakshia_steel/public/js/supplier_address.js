frappe.ui.form.on("Supplier", {
  after_save(frm) {
    if (
      !frm.doc.custom_address_line_1 ||
      !frm.doc.custom_citytown ||
      !frm.doc.country
    )
      return;

    const address_data = {
      doctype: "Address",
      address_title: frm.doc.supplier_name,
      address_type: frm.doc.custom_address_type || "Billing",
      address_line1: frm.doc.custom_address_line_1,
      address_line2: frm.doc.custom_address_line_2,
      city: frm.doc.custom_citytown,
      state: frm.doc.custom_state__province,
      country: frm.doc.country,
      pincode: frm.doc.custom_postal_code,
      email_id: frm.doc.custom_email,
      phone: frm.doc.custom_phone,
      is_primary_address: frm.doc.custom_is_billing_address ? 1 : 0,
      is_shipping_address: frm.doc.custom_is_shipping_address ? 1 : 0,
      links: [
        {
          link_doctype: "Supplier",
          link_name: frm.doc.name,
        },
      ],
    };

    // Create Address silently
    if (!frm.doc.custom_supplier_address) {
      frappe.flags.hide_message = true; // suppress messages
      frappe.call({
        method: "frappe.client.insert",
        args: { doc: address_data },
        callback: function (r) {
          frappe.flags.hide_message = false; // optional: reset flag
          if (!r.exc) {
            frm.set_value("custom_supplier_address", r.message.name);
            frm.save();
          }
        },
      });
    }
    // Update Address silently
    else {
      frappe.flags.hide_message = true;
      frappe.call({
        method: "frappe.client.set_value",
        args: {
          doctype: "Address",
          name: frm.doc.custom_supplier_address,
          fieldname: {
            address_type: frm.doc.custom_address_type || "Billing",
            address_line1: frm.doc.custom_address_line_1,
            address_line2: frm.doc.custom_address_line_2,
            city: frm.doc.custom_citytown,
            state: frm.doc.custom_state__province,
            country: frm.doc.country,
            pincode: frm.doc.custom_postal_code,
            email_id: frm.doc.custom_email,
            phone: frm.doc.custom_phone,
            is_primary_address: frm.doc.custom_is_billing_address ? 1 : 0,
            is_shipping_address: frm.doc.custom_is_shipping_address ? 1 : 0,
          },
        },
        callback: function () {
          frappe.flags.hide_message = false;
        },
      });
    }
  },

  custom_address_type(frm) {
    if (frm.doc.custom_address_type === "Billing") {
      frm.set_value("custom_is_billing_address", 1);
      frm.set_value("custom_is_shipping_address", 0);
    } else if (frm.doc.custom_address_type === "Shipping") {
      frm.set_value("custom_is_shipping_address", 1);
      frm.set_value("custom_is_billing_address", 0);
    } else {
      frm.set_value("custom_is_billing_address", 0);
      frm.set_value("custom_is_shipping_address", 0);
    }
  },
});
