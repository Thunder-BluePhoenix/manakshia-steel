/* global sm_utils */
// Stage 2 — CC Coil Production
// Auto-fill thick/width/brand from GP/ALU/ROPP Batch via previous stage API
// Total weight summary (input: minl_net_wt, output: cc_coil_wt)

const CC_CFG = {
  entry_table: "entry_items",
  entry_wt: "minl_net_wt",
  exit_table: "exit_items",
  exit_wt: "cc_coil_wt",
};

frappe.ui.form.on("CC Coil Production", {
  refresh(frm) {
    sm_utils.refresh_totals(frm, CC_CFG);
  },
});

frappe.ui.form.on("CC Coil Entry", {
  coil_no(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row.coil_no) return;
    frappe.call({
      method: "manakshia_steel.steel_manufacturing.api.get_coil_details",
      args: { coil_no: row.coil_no },
      callback(r) {
        if (!r.message) return;
        const d = r.message;
        const updates = {};
        if (d.thick) updates.thick = d.thick;
        if (d.width) updates.width = d.width;
        if (d.brand) updates.brand = d.brand;
        if (d.length) updates.length = d.length;
        if (Object.keys(updates).length) {
          frappe.model.set_value(cdt, cdn, updates);
          frappe.show_alert(
            {
              message: __("Auto-filled from {0}: Thick={1}, Width={2}", [
                d.source_stage || "previous stage",
                d.thick,
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
  minl_net_wt(frm) {
    sm_utils.refresh_totals(frm, CC_CFG);
  },
});

frappe.ui.form.on("CC Coil Exit", {
  cc_coil_wt(frm) {
    sm_utils.refresh_totals(frm, CC_CFG);
  },
});
