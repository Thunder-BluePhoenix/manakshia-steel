// Auto-delete blank rows on save (before mandatory field validation)
// Auto-add row logic has been removed

const target_doctypes = [
  "Material Request",
  "Purchase Order",
  "Purchase Receipt",
  "Purchase Invoice",
  "Request for Quotation",
  "Supplier Quotation",
  "Sales Order",
  "Delivery Note",
  "Sales Invoice",
  "Quotation",
  "Stock Entry",
];

target_doctypes.forEach((doctype) => {
  frappe.ui.form.on(doctype, {
    onload: function (frm) {
      // Guard per frm instance so reloads are also covered
      if (frm.__blank_row_patched) return;

      // Patch validate_form_action: clean blank rows before ANY action
      // (Save, Submit, serial bundle saves, etc.) — runs before mandatory check
      let original_validate = frm.validate_form_action;
      frm.validate_form_action = function (action, callback, btn) {
        cleanup_blank_rows_global(frm);
        return original_validate.call(this, action, callback, btn);
      };

      // Also patch frm.save directly — catches programmatic saves
      // that bypass validate_form_action (e.g. "Add Serial Nos" dialog)
      let original_save = frm.save.bind(frm);
      frm.save = function (...args) {
        cleanup_blank_rows_global(frm);
        return original_save(...args);
      };

      frm.__blank_row_patched = true;
    },
  });
});

// Tables that use different key fields — exclude them from the generic
// item_code/qty blank-row check so their rows are not wrongly deleted.
const SKIP_TABLES_FROM_BLANK_CLEANUP = [
  "custom_packing_slip", // uses coil_number + weight, not item_code/qty
];

function cleanup_blank_rows_global(frm) {
  frm.meta.fields.forEach((field) => {
    if (field.fieldtype === "Table") {
      if (SKIP_TABLES_FROM_BLANK_CLEANUP.includes(field.fieldname)) return;
      remove_blank_rows(frm, field.fieldname, ["item_code", "qty"]);
    }
  });
}

function remove_blank_rows(frm, child_table_field, required_fields) {
  let items = frm.doc[child_table_field] || [];
  let to_remove = [];

  items.forEach((item) => {
    let is_blank = required_fields.every((field) => !item[field]);
    if (is_blank) to_remove.push(item);
  });

  to_remove.forEach((item) => {
    frappe.model.remove_from_locals(item.parenttype, item.name);
    const index = frm.doc[child_table_field].indexOf(item);
    if (index > -1) frm.doc[child_table_field].splice(index, 1);
  });

  if (to_remove.length > 0) frm.refresh_field(child_table_field);
}
