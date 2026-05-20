/* global sm_utils */
// Shared utility: compute and display total input/output weights
// Called by all 6 production DocType JS files

window.sm_utils = window.sm_utils || {};

/**
 * Recalculate total_input_wt and total_output_wt on the form.
 * @param {Object} frm - Frappe form object
 * @param {Object} cfg - { entry_table, entry_wt, exit_table, exit_wt }
 *   entry_table: child table fieldname for inputs (e.g. "entry_items")
 *   entry_wt:    weight field in entry child (e.g. "minl_gr_wt")
 *   exit_table:  child table fieldname for outputs (e.g. "exit_items")
 *   exit_wt:     weight field in exit child (e.g. "net_wt")
 *   single_table: if true, items table is used for both in/out
 *   input_wt_field: weight field for input in single table (e.g. "coil_weight")
 *   output_wt_field: weight field for output in single table (e.g. "packet_wt")
 */
sm_utils.refresh_totals = function (frm, cfg) {
  let in_total = 0,
    out_total = 0;

  if (cfg.single_table) {
    // e.g. CTL, Profile, Corrugated — same items table
    (frm.doc[cfg.entry_table] || []).forEach((row) => {
      in_total += flt(row[cfg.input_wt_field] || 0);
      out_total += flt(row[cfg.output_wt_field] || 0);
    });
  } else {
    (frm.doc[cfg.entry_table] || []).forEach((row) => {
      in_total += flt(row[cfg.entry_wt] || 0);
    });
    (frm.doc[cfg.exit_table] || []).forEach((row) => {
      out_total += flt(row[cfg.exit_wt] || 0);
    });
  }

  frm.set_value("total_input_wt", in_total);
  frm.set_value("total_output_wt", out_total);

  const variance = in_total - out_total;
  const indicator =
    Math.abs(variance) < 10 ? "green" : variance > 0 ? "orange" : "red";
  if (in_total > 0) {
    frm.dashboard.clear_comment();
    frm.dashboard.add_comment(
      `⚖ Input: <strong>${in_total.toFixed(
        2
      )} Kg</strong> &nbsp;|&nbsp; Output: <strong>${out_total.toFixed(
        2
      )} Kg</strong> &nbsp;|&nbsp; Variance: <strong style="color:${
        indicator === "green"
          ? "green"
          : indicator === "orange"
          ? "orange"
          : "red"
      }">${variance.toFixed(2)} Kg</strong>`,
      indicator,
      true
    );
  }
};
