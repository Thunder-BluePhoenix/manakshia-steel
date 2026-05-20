/* WIP Batch Stock — client-side filters.
   Filter fieldnames must match keys read in wip_batch_stock.py get_data(filters).
   stage        → maps to PATTERN_A label (Galvanizing / Embossing / CC Coating)
   show_wip_only → checkbox: hide consumed coils
   from_date / to_date → date range for production records
*/
frappe.query_reports["WIP Batch Stock"] = {
  filters: [
    {
      fieldname: "stage",
      label: __("Origin Stage"),
      fieldtype: "Select",
      options: "\nGalvanizing\nEmbossing\nCC Coating",
      reqd: 0,
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      reqd: 0,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      reqd: 0,
    },
    {
      fieldname: "show_wip_only",
      label: __("WIP Only (exclude consumed)"),
      fieldtype: "Check",
      default: 1,
    },
  ],
};
