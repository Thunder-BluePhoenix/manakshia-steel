/* global sm_utils */
// Stage 5A — Colour Profile Production
// Auto-fill thick/width/colour/brand/pattern from WIP Batch
// Total weight summary (input: coil_wt, output: qnty_kg) — single items table

const PRO_CFG = {
  single_table: true,
  entry_table: "items",
  input_wt_field: "coil_wt",
  output_wt_field: "qnty_kg",
};

frappe.ui.form.on("Colour Profile Production", {
  refresh(frm) {
    sm_utils.refresh_totals(frm, PRO_CFG);
  },
});

frappe.ui.form.on("Colour Profile Item", {
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
        if (d.pattern) updates.pattern = d.pattern;
        if (d.length) updates.length = d.length;
        if (d.weight) updates.coil_wt = d.weight;
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
  coil_wt(frm) {
    sm_utils.refresh_totals(frm, PRO_CFG);
  },
  qnty_kg(frm) {
    sm_utils.refresh_totals(frm, PRO_CFG);
  },
});
