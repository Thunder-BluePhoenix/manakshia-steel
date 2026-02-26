
// Fix for Serial/Batch button visibility in Frappe v16
// Root cause: "Use Serial No / Batch Fields" checkbox is auto-checked, hiding the bundle button
// Solution: Auto-uncheck it to force use of Serial and Batch Bundle
// NOTE: Only applies to Purchase Receipt and Delivery Note.
//       Stock Entry does NOT use serial/batch at all – handled server-side.

['Purchase Receipt', 'Delivery Note'].forEach(doctype => {

    const child_doctypes = {
        'Purchase Receipt': 'Purchase Receipt Item',
        'Delivery Note': 'Delivery Note Item',
    };

    const child_doctype = child_doctypes[doctype];

    if (child_doctype) {
        frappe.ui.form.on(child_doctype, {
            // When item is selected, uncheck the "Use Serial No / Batch Fields" checkbox
            item_code: function (frm, cdt, cdn) {
                let row = locals[cdt][cdn];
                if (row.use_serial_batch_fields) {
                    frappe.model.set_value(cdt, cdn, 'use_serial_batch_fields', 0);
                }
            },

            // Also uncheck when row is rendered
            form_render: function (frm, cdt, cdn) {
                let row = locals[cdt][cdn];
                if (row.use_serial_batch_fields) {
                    frappe.model.set_value(cdt, cdn, 'use_serial_batch_fields', 0);
                }
            },

            // Prevent it from being checked
            use_serial_batch_fields: function (frm, cdt, cdn) {
                let row = locals[cdt][cdn];
                if (row.use_serial_batch_fields === 1) {
                    setTimeout(() => {
                        frappe.model.set_value(cdt, cdn, 'use_serial_batch_fields', 0);
                    }, 100);
                }
            }
        });
    }

    // Also handle on parent form refresh
    frappe.ui.form.on(doctype, {
        refresh: function (frm) {
            if (frm.doc.items) {
                frm.doc.items.forEach(row => {
                    if (row.use_serial_batch_fields) {
                        frappe.model.set_value(row.doctype, row.name, 'use_serial_batch_fields', 0);
                    }
                });
            }
        },

        items_add: function (frm, cdt, cdn) {
            let row = locals[cdt][cdn];
            if (row.use_serial_batch_fields) {
                frappe.model.set_value(cdt, cdn, 'use_serial_batch_fields', 0);
            }
        }
    });
});
