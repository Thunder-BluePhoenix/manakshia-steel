// ============================================================================
// PURCHASE RECEIPT
// ============================================================================
frappe.ui.form.on("Purchase Receipt", {
  setup: function (frm) {
    frm.trigger("fix_warehouse_conflict");
  },
  onload: function (frm) {
    frm.trigger("fix_warehouse_conflict");
  },
  refresh: function (frm) {
    frm.trigger("fix_warehouse_conflict");
  },
  fix_warehouse_conflict: function (frm) {
    validate_pr_warehouses(frm);
  },
});

frappe.ui.form.on("Purchase Receipt Item", {
  items_add: function (frm, cdt, cdn) {
    setTimeout(() => {
      validate_pr_row_logic(locals[cdt][cdn]);
    }, 500);
  },
  warehouse: function (frm, cdt, cdn) {
    validate_pr_row_logic(locals[cdt][cdn]);
  },
  rejected_warehouse: function (frm, cdt, cdn) {
    validate_pr_row_logic(locals[cdt][cdn]);
  },
});

function validate_pr_warehouses(frm) {
  if (frm.doc.items) {
    frm.doc.items.forEach((row) => validate_pr_row_logic(row));
  }
}

function validate_pr_row_logic(row) {
  if (
    row.warehouse &&
    row.rejected_warehouse &&
    row.warehouse == row.rejected_warehouse
  ) {
    frappe.model.set_value(row.doctype, row.name, "rejected_warehouse", "");
  }
}

// ============================================================================
// STOCK ENTRY – Warehouse Conflict Fix
// Problem: ERPNext user defaults auto-fill BOTH s_warehouse and t_warehouse
//          from the same "default warehouse", causing "Same Warehouse" errors.
// Fix: On load and on row add, detect and clear conflicting row-level warehouses.
// ============================================================================
frappe.ui.form.on("Stock Entry", {
  setup: function (frm) {
    frm.trigger("fix_se_warehouse_conflict");
  },
  onload: function (frm) {
    frm.trigger("fix_se_warehouse_conflict");
  },
  refresh: function (frm) {
    frm.trigger("fix_se_warehouse_conflict");
  },
  purpose: function (frm) {
    frm.trigger("fix_se_warehouse_conflict");
  },
  from_warehouse: function (frm) {
    frm.trigger("fix_se_warehouse_conflict");
  },
  to_warehouse: function (frm) {
    frm.trigger("fix_se_warehouse_conflict");
  },

  fix_se_warehouse_conflict: function (frm) {
    fix_se_header(frm);
    fix_se_all_rows(frm);
  },
});

frappe.ui.form.on("Stock Entry Detail", {
  items_add: function (frm, cdt, cdn) {
    // Wait for user-default population to finish before fixing
    setTimeout(() => {
      fix_se_row(frm, locals[cdt][cdn]);
    }, 600);
  },
  form_render: function (frm, cdt, cdn) {
    fix_se_row(frm, locals[cdt][cdn]);
  },
  s_warehouse: function (frm, cdt, cdn) {
    fix_se_row(frm, locals[cdt][cdn]);
  },
  t_warehouse: function (frm, cdt, cdn) {
    fix_se_row(frm, locals[cdt][cdn]);
  },
});

function fix_se_header(frm) {
  // Only for non-Issue/Receipt entries where both header warehouses might conflict
  if (
    frm.doc.purpose === "Material Issue" ||
    frm.doc.purpose === "Material Receipt"
  )
    return;

  if (
    frm.doc.from_warehouse &&
    frm.doc.to_warehouse &&
    frm.doc.from_warehouse === frm.doc.to_warehouse
  ) {
    frm.set_value("to_warehouse", "");
  }
}

function fix_se_all_rows(frm) {
  if (!frm.doc.items) return;
  frm.doc.items.forEach((row) => fix_se_row(frm, row));
}

function fix_se_row(frm, row) {
  if (!row || !row.doctype) return; // row not yet populated in locals
  if (!row.s_warehouse && !row.t_warehouse) return; // nothing to fix yet

  const purpose = frm.doc.purpose;

  if (purpose === "Material Issue") {
    // Source = user warehouse, Target = transit / empty
    // If both are same → clear t_warehouse (target shouldn't equal source)
    if (
      row.s_warehouse &&
      row.t_warehouse &&
      row.s_warehouse === row.t_warehouse
    ) {
      frappe.model.set_value(row.doctype, row.name, "t_warehouse", "");
    }
  } else if (purpose === "Material Receipt") {
    // Source = transit, Target = user warehouse
    // If both are same → clear s_warehouse (source shouldn't equal target)
    if (
      row.s_warehouse &&
      row.t_warehouse &&
      row.s_warehouse === row.t_warehouse
    ) {
      frappe.model.set_value(row.doctype, row.name, "s_warehouse", "");
    }
  } else {
    // All other purposes: clear t_warehouse if same as s_warehouse
    if (
      row.s_warehouse &&
      row.t_warehouse &&
      row.s_warehouse === row.t_warehouse
    ) {
      frappe.model.set_value(row.doctype, row.name, "t_warehouse", "");
    }
  }
}

// ============================================================================
// SUBCONTRACTING RECEIPT
// ============================================================================
frappe.ui.form.on("Subcontracting Receipt", {
  setup: function (frm) {
    frm.trigger("fix_warehouse_conflict");
  },
  onload: function (frm) {
    frm.trigger("fix_warehouse_conflict");
  },
  refresh: function (frm) {
    frm.trigger("fix_warehouse_conflict");
  },
  rejected_warehouse: function (frm) {
    frm.trigger("fix_warehouse_conflict");
  },

  fix_warehouse_conflict: function (frm) {
    check_sub_receipt(frm);
  },
});

frappe.ui.form.on("Subcontracting Receipt Item", {
  items_add: function (frm, cdt, cdn) {
    setTimeout(() => {
      check_sub_receipt_row(locals[cdt][cdn]);
    }, 500);
  },
  warehouse: function (frm, cdt, cdn) {
    check_sub_receipt_row(locals[cdt][cdn]);
  },
});

function check_sub_receipt(frm) {
  if (frm.doc.items && frm.doc.rejected_warehouse) {
    frm.doc.items.forEach((row) => check_sub_receipt_row(row));
  }
}

function check_sub_receipt_row(row) {
  let header_rejected = cur_frm.doc.rejected_warehouse;
  if (header_rejected && row.warehouse && row.warehouse == header_rejected) {
    cur_frm.set_value("rejected_warehouse", "");
  }
}
