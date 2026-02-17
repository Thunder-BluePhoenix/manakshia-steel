
// Fix for Serial/Batch button visibility in Frappe v16
// Root cause: "Use Serial No / Batch Fields" checkbox is auto-checked, hiding the bundle button
// Solution: Auto-uncheck it to force use of Serial and Batch Bundle

// Apply to all relevant doctypes
['Purchase Receipt', 'Delivery Note', 'Stock Entry', 'Sales Invoice', 'Purchase Invoice'].forEach(doctype => {

    // Determine child table doctype
    const child_doctypes = {
        'Purchase Receipt': 'Purchase Receipt Item',
        'Delivery Note': 'Delivery Note Item',
        'Stock Entry': 'Stock Entry Detail',
        'Sales Invoice': 'Sales Invoice Item',
        'Purchase Invoice': 'Purchase Invoice Item'
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

            // Also uncheck when row is added
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
                    // Automatically uncheck it
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
            // Uncheck for all existing rows
            if (frm.doc.items) {
                frm.doc.items.forEach(row => {
                    if (row.use_serial_batch_fields) {
                        frappe.model.set_value(row.doctype, row.name, 'use_serial_batch_fields', 0);
                    }
                });
            }
        },

        items_add: function (frm, cdt, cdn) {
            // Uncheck when new row is added
            let row = locals[cdt][cdn];
            if (row.use_serial_batch_fields) {
                frappe.model.set_value(cdt, cdn, 'use_serial_batch_fields', 0);
            }
        }
    });
});
