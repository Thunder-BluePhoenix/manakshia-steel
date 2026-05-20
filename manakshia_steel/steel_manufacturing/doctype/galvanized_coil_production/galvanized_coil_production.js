/* global sm_utils */
// Stage 1 — Galvanized Coil Production
// Auto-fill thick/width/supplier from CR Coil Serial No
// Total weight summary (input: minl_gr_wt, output: net_wt)

const GCP_CFG = {
  entry_table: "entry_items",
  entry_wt: "minl_gr_wt",
  exit_table: "exit_items",
  exit_wt: "net_wt",
};

frappe.ui.form.on("Galvanized Coil Production", {
  refresh(frm) {
    if (frm.doc.docstatus === 0) {
      frm.set_intro(
        __(
          "Select CR Coil Serial Nos in Entry. Thickness and Width auto-fill from Item master."
        ),
        "blue"
      );
    }
    sm_utils.refresh_totals(frm, GCP_CFG);
  },
});

frappe.ui.form.on("Galvanized Coil Entry", {
  coil_no(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row.coil_no) return;
    frappe.call({
      method: "manakshia_steel.steel_manufacturing.api.get_serial_no_details",
      args: { serial_no: row.coil_no },
      callback(r) {
        if (!r.message) return;
        const d = r.message;
        frappe.model.set_value(cdt, cdn, {
          thick: d.thickness || row.thick,
          width: d.width || row.width,
          supplier: d.supplier || row.supplier,
        });
        if (d.thickness || d.width) {
          frappe.show_alert(
            {
              message: __("Auto-filled: Thick={0} mm, Width={1} mm", [
                d.thickness,
                d.width,
              ]),
              indicator: "green",
            },
            4
          );
        }
      },
    });
  },
  minl_gr_wt(frm) {
    sm_utils.refresh_totals(frm, GCP_CFG);
  },
});

frappe.ui.form.on("Galvanized Coil Exit", {
  net_wt(frm) {
    sm_utils.refresh_totals(frm, GCP_CFG);
  },
});
