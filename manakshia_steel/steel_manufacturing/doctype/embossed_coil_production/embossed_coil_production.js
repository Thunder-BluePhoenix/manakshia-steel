/* global sm_utils */
// Stage 3 — Embossed Coil Production
// Auto-fill thick/colour/brand from CC/ALU Batch
// Total weight summary (input: minl_net_w, output: emb_nt_wt)

const EMB_CFG = {
  entry_table: "entry_items",
  entry_wt: "minl_net_w",
  exit_table: "exit_items",
  exit_wt: "emb_nt_wt",
};

frappe.ui.form.on("Embossed Coil Production", {
  refresh(frm) {
    sm_utils.refresh_totals(frm, EMB_CFG);
  },
});

frappe.ui.form.on("Embossed Coil Entry", {
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
        if (d.colour) updates.colour = d.colour;
        if (d.length) updates.length = d.length;
        if (Object.keys(updates).length) {
          frappe.model.set_value(cdt, cdn, updates);
          frappe.show_alert(
            {
              message: __("Auto-filled from {0}: Thick={1}, Colour={2}", [
                d.source_stage || "previous stage",
                d.thick,
                d.colour,
              ]),
              indicator: "green",
            },
            4
          );
        }
      },
    });
  },
  minl_net_w(frm) {
    sm_utils.refresh_totals(frm, EMB_CFG);
  },
});

frappe.ui.form.on("Embossed Coil Exit", {
  emb_nt_wt(frm) {
    sm_utils.refresh_totals(frm, EMB_CFG);
  },
});
