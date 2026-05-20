/* Batch Traceability — client-side filters.
   Filters must match the fieldnames read in batch_traceability.py get_data(filters).
   coil_no  → filter for WIP Batch (any stage output)
   serial_no → filter for CR Coil Serial No (RM level, Galvanizing entry)
*/
frappe.query_reports["Batch Traceability"] = {
  filters: [
    {
      fieldname: "coil_no",
      label: __("Coil / Batch No."),
      fieldtype: "Link",
      options: "Batch",
      reqd: 0,
    },
    {
      fieldname: "serial_no",
      label: __("Serial No. (CR Coil RM)"),
      fieldtype: "Link",
      options: "Serial No",
      reqd: 0,
    },
  ],
  onload(report) {
    report.page.add_inner_button(__("Clear"), () => {
      report.set_filter_value("coil_no", "");
      report.set_filter_value("serial_no", "");
    });
  },
};
