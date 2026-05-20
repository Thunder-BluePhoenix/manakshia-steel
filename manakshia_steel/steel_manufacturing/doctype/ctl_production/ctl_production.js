/* global sm_utils */
// Stage 4 — CTL Production
// Auto-fill thick/width/colour/brand from WIP Batch
// Total weight summary (input: coil_weight, output: packet_wt) — single items table

const CTL_CFG = {
  single_table: true,
  entry_table: "items",
  input_wt_field: "coil_weight",
  output_wt_field: "packet_wt",
};

frappe.ui.form.on("CTL Production", {
  refresh(frm) {
    sm_utils.refresh_totals(frm, CTL_CFG);
  },
});

frappe.ui.form.on("CTL Production Item", {
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
        if (d.length) updates.coil_length = d.length;
        if (d.weight) updates.coil_weight = d.weight;
        if (Object.keys(updates).length) {
          frappe.model.set_value(cdt, cdn, updates);
          frappe.show_alert(
            {
              message: __(
                "Auto-filled from {0}: Thick={1} mm, Width={2} mm, Colour={3}",
                [d.source_stage || "previous stage", d.thick, d.width, d.colour]
              ),
              indicator: "green",
            },
            4
          );
        }
      },
    });
  },
  coil_weight(frm) {
    sm_utils.refresh_totals(frm, CTL_CFG);
  },
  packet_wt(frm) {
    sm_utils.refresh_totals(frm, CTL_CFG);
  },
});
