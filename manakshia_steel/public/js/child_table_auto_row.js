
// Auto-add new row when the last row is filled in child tables
// Auto-delete blank rows on save

// List of DocTypes to apply the logic to
const target_doctypes = [
    'Material Request',
    'Purchase Order',
    'Purchase Receipt',
    'Purchase Invoice',
    'Request for Quotation',
    'Supplier Quotation',
    'Sales Order',
    'Delivery Note',
    'Sales Invoice',
    'Quotation',
    'Stock Entry'
];

const bound_child_doctypes = new Set();
const patched_forms = new Set();

target_doctypes.forEach(doctype => {
    frappe.ui.form.on(doctype, {
        onload: function (frm) {
            if (patched_forms.has(frm.doctype)) return;

            // Monkey patch validate_form_action to remove blank rows BEFORE mandatory checking matches
            let original_validate = frm.validate_form_action;
            frm.validate_form_action = function (action, callback, btn) {
                if (action === 'Save') {
                    cleanup_blank_rows_global(frm);
                }
                return original_validate.call(this, action, callback, btn);
            };

            patched_forms.add(frm.doctype);
        },
        refresh: function (frm) {
            // Identify child tables that have 'item_code' and 'qty' fields
            if (!frm.custom_auto_row_tables) {
                frm.custom_auto_row_tables = [];
                const fields = frm.meta.fields;
                fields.forEach(field => {
                    if (field.fieldtype === 'Table') {
                        const child_doctype = field.options;
                        if (child_doctype) {
                            if (frappe.get_meta(child_doctype).fields.find(f => f.fieldname === 'item_code')) {
                                apply_auto_row_logic(doctype, child_doctype);
                                if (!frm.custom_auto_row_tables.includes(field.fieldname)) {
                                    frm.custom_auto_row_tables.push(field.fieldname);
                                }
                            }
                        }
                    }
                });
            }
        }
    });
});

function cleanup_blank_rows_global(frm) {
    if (frm.custom_auto_row_tables) {
        frm.custom_auto_row_tables.forEach(child_table_field => {
            remove_blank_rows(frm, child_table_field, ['item_code', 'qty']);
        });
    } else {
        // Fallback: Check all tables
        frm.meta.fields.forEach(field => {
            if (field.fieldtype === 'Table') {
                remove_blank_rows(frm, field.fieldname, ['item_code', 'qty']);
            }
        });
    }
}

function apply_auto_row_logic(parent_doctype, child_doctype) {
    if (bound_child_doctypes.has(child_doctype)) return;

    frappe.ui.form.on(child_doctype, {
        item_code: function (frm, cdt, cdn) {
            handle_auto_row(frm, cdt, cdn);
        },
        qty: function (frm, cdt, cdn) {
            handle_auto_row(frm, cdt, cdn);
        },
        custom_weight: function (frm, cdt, cdn) {
            handle_auto_row(frm, cdt, cdn);
        }
    });

    bound_child_doctypes.add(child_doctype);
}

// Generic handler for auto-adding rows
function handle_auto_row(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let parent_field = row.parentfield;
    let grid = frm.fields_dict[parent_field].grid;
    let grid_rows = grid.grid_rows;
    let last_row = grid_rows[grid_rows.length - 1].doc;

    // Check if the modified row is the last row
    if (row.name !== last_row.name) return;

    // Logic to determine if row is "completed" enough to add a new one
    if (row.item_code && row.qty > 0) {
        // Check if custom_weight is mandatory and missing
        if (options_check(frm, parent_field, 'custom_weight')) {
            if (row.custom_weight == null || row.custom_weight === "" || row.custom_weight === 0) {
                return;
            }
        }

        frm.add_child(parent_field);
        grid.refresh();
    }
}

function options_check(frm, parent_field, fieldname) {
    let grid_fields = frm.fields_dict[parent_field].grid.docfields;
    let field = grid_fields.find(f => f.fieldname === fieldname);
    if (!field) return false;

    // Explicitly require custom_weight as per user request, even if not DB mandatory
    if (fieldname === 'custom_weight') return true;

    return field.reqd;
}


function remove_blank_rows(frm, child_table_field, required_fields) {
    let items = frm.doc[child_table_field] || [];
    let to_remove = [];

    items.forEach(item => {
        let is_blank = true;
        required_fields.forEach(field => {
            if (item[field]) {
                is_blank = false;
            }
        });

        if (is_blank) {
            to_remove.push(item);
        }
    });

    to_remove.forEach(item => {
        frappe.model.remove_from_locals(item.parenttype, item.name);
        // Also remove from doc.items array
        const index = frm.doc[child_table_field].indexOf(item);
        if (index > -1) {
            frm.doc[child_table_field].splice(index, 1);
        }
    });

    if (to_remove.length > 0) {
        frm.refresh_field(child_table_field);
    }
}
