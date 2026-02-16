
// ============================================================================
// PURCHASE RECEIPT
// ============================================================================
frappe.ui.form.on('Purchase Receipt', {
    setup: function (frm) {
        // Run on setup/onload to catch defaults immediately
        frm.trigger('fix_warehouse_conflict');
    },
    onload: function (frm) {
        frm.trigger('fix_warehouse_conflict');
    },
    refresh: function (frm) {
        frm.trigger('fix_warehouse_conflict');
    },
    fix_warehouse_conflict: function (frm) {
        validate_pr_warehouses(frm);
    }
});

frappe.ui.form.on('Purchase Receipt Item', {
    items_add: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        // Wait for defaults to apply
        setTimeout(() => { validate_pr_row_logic(row); }, 500);
    },
    warehouse: function (frm, cdt, cdn) {
        validate_pr_row_logic(locals[cdt][cdn]);
    },
    rejected_warehouse: function (frm, cdt, cdn) {
        validate_pr_row_logic(locals[cdt][cdn]);
    }
});

function validate_pr_warehouses(frm) {
    if (frm.doc.items) {
        frm.doc.items.forEach(row => validate_pr_row_logic(row));
    }
}

function validate_pr_row_logic(row) {
    if (row.warehouse && row.rejected_warehouse && row.warehouse == row.rejected_warehouse) {
        frappe.model.set_value(row.doctype, row.name, "rejected_warehouse", "");
        // Silent fix - no msgprint to avoid annoying user on Load
        // frappe.show_alert(__("Cleared conflicting Rejected Warehouse"));
    }
}


// ============================================================================
// STOCK ENTRY
// ============================================================================
frappe.ui.form.on('Stock Entry', {
    setup: function (frm) {
        frm.trigger('fix_warehouse_conflict');
    },
    onload: function (frm) {
        frm.trigger('fix_warehouse_conflict');
    },
    refresh: function (frm) {
        frm.trigger('fix_warehouse_conflict');
    },
    from_warehouse: function (frm) { frm.trigger('fix_warehouse_conflict'); },
    to_warehouse: function (frm) { frm.trigger('fix_warehouse_conflict'); },

    fix_warehouse_conflict: function (frm) {
        validate_se_warehouses(frm);
    }
});

function validate_se_warehouses(frm) {
    // 1. Header Validation (From vs To)
    // Applies to ALL Stock Entry types where both might be set by default
    if (frm.doc.from_warehouse && frm.doc.to_warehouse && frm.doc.from_warehouse == frm.doc.to_warehouse) {
        frm.set_value("to_warehouse", "");
        // Silent fix
    }
}


// ============================================================================
// SUBCONTRACTING RECEIPT
// ============================================================================
frappe.ui.form.on('Subcontracting Receipt', {
    setup: function (frm) {
        frm.trigger('fix_warehouse_conflict');
    },
    onload: function (frm) {
        frm.trigger('fix_warehouse_conflict');
    },
    refresh: function (frm) {
        frm.trigger('fix_warehouse_conflict');
    },
    rejected_warehouse: function (frm) { frm.trigger('fix_warehouse_conflict'); },

    fix_warehouse_conflict: function (frm) {
        check_sub_receipt(frm);
    }
});

frappe.ui.form.on('Subcontracting Receipt Item', {
    items_add: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        setTimeout(() => { check_sub_receipt_row(row); }, 500);
    },
    warehouse: function (frm, cdt, cdn) { check_sub_receipt_row(locals[cdt][cdn]); }
});

function check_sub_receipt(frm) {
    if (frm.doc.items) {
        if (frm.doc.rejected_warehouse) {
            frm.doc.items.forEach(row => check_sub_receipt_row(row));
        }
    }
}

function check_sub_receipt_row(row) {
    let header_rejected = cur_frm.doc.rejected_warehouse;
    if (header_rejected && row.warehouse && row.warehouse == header_rejected) {
        cur_frm.set_value("rejected_warehouse", "");
        // Silent fix
    }
}
