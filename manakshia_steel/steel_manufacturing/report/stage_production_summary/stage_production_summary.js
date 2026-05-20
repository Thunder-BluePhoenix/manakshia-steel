/* Stage Production Summary — client-side filters.
   Filter fieldnames must match keys read in stage_production_summary.py get_data(filters).
   stage     → cfg["label"] values in STAGE_CONFIG
   from_date / to_date → date range filter on parent posting date
*/
frappe.query_reports["Stage Production Summary"] = {
  filters: [
    {
      fieldname: "stage",
      label: __("Stage"),
      fieldtype: "Select",
      options:
        "\nGalvanizing\nCC Coating\nEmbossing\nCut to Length\nColour Profiling\nCorrugation",
      reqd: 0,
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.month_start(),
      reqd: 0,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 0,
    },
  ],
};
