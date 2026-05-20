/* global sm_utils */
// Stage 5B — Corrugated Sheet Production
// Auto-fill thick/width/packet_wt/colour/brand from CTL packet Batch
// Total weight summary (input: packet_wt, output: qnty_kg) — single items table

const COR_CFG = {
  single_table: true,
  entry_table: "items",
  input_wt_field: "packet_wt",
  output_wt_field: "qnty_kg",
};

frappe.ui.form.on("Corrugated Sheet Production", {
  refresh(frm) {
    sm_utils.refresh_totals(frm, COR_CFG);
  },
});

frappe.ui.form.on("Corrugated Sheet Item", {
  packet_no(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row.packet_no) return;
    frappe.call({
      method: "manakshia_steel.steel_manufacturing.api.get_packet_details",
      args: { packet_no: row.packet_no },
      callback(r) {
        if (!r.message) return;
        const d = r.message;
        const updates = {};
        if (d.thick) updates.thick = d.thick;
        if (d.width) updates.width = d.width;
        if (d.packet_wt) updates.packet_wt = d.packet_wt;
        if (d.brand) updates.brand = d.brand;
        if (d.colour) updates.colour = d.colour;
        if (d.length) updates.length = d.length;
        if (d.qty_sheets) updates.scrap_sheets = 0; // reset scrap, keep qty
        if (Object.keys(updates).length) {
          frappe.model.set_value(cdt, cdn, updates);
          frappe.show_alert(
            {
              message: __(
                "Auto-filled from CTL: Thick={0} mm, Width={1} mm, Wt={2} Kg, Colour={3}",
                [d.thick, d.width, d.packet_wt, d.colour]
              ),
              indicator: "green",
            },
            4
          );
        }
      },
    });
  },
  packet_wt(frm) {
    sm_utils.refresh_totals(frm, COR_CFG);
  },
  qnty_kg(frm) {
    sm_utils.refresh_totals(frm, COR_CFG);
  },
});
