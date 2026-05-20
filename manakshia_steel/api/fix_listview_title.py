"""
Apply Property Setters to make document number (name) the first column
in all affected DocType list views.

Run once:
  bench --site manakshia execute manakshia_steel.api.fix_listview_title.run
"""

import frappe

# DocType → current title_field that hides the doc number
FIX_TITLE_FIELD = {
    "Stock Entry": "stock_entry_type",  # shows SE type, not doc no.
    "Purchase Receipt": "title",  # shows auto-title, not doc no.
    "Purchase Receipt Return": "title",
    "Material Request": "title",
    "Supplier Quotation": "title",
    "Purchase Order": "supplier_name",  # shows supplier name, not doc no.
}

# DocTypes that already use name as title (no fix needed for title_field)
# but we want to ensure the naming_series column is hidden (it shows the
# series TEMPLATE like "GN/.YYYY./.#####" which is ugly in list view)
HIDE_NAMING_SERIES_COL = [
    "Adjustment",
    "Waybill",
    "Waybill Return",
    "Production Order",
    "Purchase Receipt Return",
]


def _upsert_ps(doc_type, field_name, doctype_or_field, prop, prop_type, value, ps_name):
    """Insert or update a single Property Setter."""
    if frappe.db.exists("Property Setter", ps_name):
        frappe.db.set_value("Property Setter", ps_name, "value", value)
    else:
        ps = frappe.new_doc("Property Setter")
        ps.name = ps_name
        ps.doc_type = doc_type
        ps.field_name = field_name
        ps.doctype_or_field = doctype_or_field
        ps.property = prop
        ps.property_type = prop_type
        ps.value = value
        ps.flags.ignore_mandatory = True
        ps.insert(ignore_permissions=True)


def run():
    frappe.set_user("Administrator")
    print("\n── Fixing list view title_field (making doc number first column)")

    # 1. Clear title_field for affected DocTypes → name becomes the title column
    for dt, old_tf in FIX_TITLE_FIELD.items():
        ps_name = f"{dt}-main-title_field"
        _upsert_ps(dt, None, "DocType", "title_field", "Data", "", ps_name)
        print(
            f"  ✓  {dt}: title_field cleared (was '{old_tf}') → name is now first column"
        )

    # 2. Hide the naming_series column from list view for custom DocTypes
    #    (it shows the ugly series template, not the actual doc number)
    for dt in HIDE_NAMING_SERIES_COL:
        ps_name = f"{dt}-naming_series-in_list_view"
        _upsert_ps(
            dt, "naming_series", "DocField", "in_list_view", "Check", "0", ps_name
        )
        print(f"  ✓  {dt}: naming_series removed from list view columns")

    # 3. For Stock Entry: hide stock_entry_type and purpose from list view
    #    (the doc number prefix already tells you the type: Issue/G/... or Receipt/G/...)
    #    Keep posting_date as the second column instead.
    for fn, label in [("stock_entry_type", "Stock Entry Type"), ("purpose", "Purpose")]:
        ps_name = f"Stock Entry-{fn}-in_list_view"
        _upsert_ps("Stock Entry", fn, "DocField", "in_list_view", "Check", "0", ps_name)
        print(f"  ✓  Stock Entry: '{fn}' removed from list view columns")

    frappe.db.commit()

    # 4. Clear meta cache so changes take effect immediately
    frappe.clear_cache()
    print("\n  ✓  Cache cleared — reload the browser to see changes")
    print("\n── Done ────────────────────────────────────────────────────────────")
