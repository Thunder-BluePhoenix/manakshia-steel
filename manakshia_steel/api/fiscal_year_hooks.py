import frappe
from frappe.utils import getdate


YEAR_DOCTYPES_DATE_FIELD = {
    "Stock Entry": "posting_date",
    "Purchase Receipt": "posting_date",
    "Delivery Note": "posting_date",
    "Purchase Order": "transaction_date",
    "Material Request": "transaction_date",
    "Supplier Quotation": "transaction_date",
}


def fix_naming_year(doc, method=None):
    """
    before_naming hook — replaces .YYYY. / .YY. tokens in the document's
    naming_series with the year from posting_date / transaction_date.

    Frappe's parse_naming_series always uses now_datetime() for these tokens,
    ignoring the document date. This hook patches the naming_series string
    before Frappe reads it, so the correct fiscal year appears in the doc name.
    """
    if not getattr(doc, "naming_series", None):
        return

    date_field = YEAR_DOCTYPES_DATE_FIELD.get(doc.doctype)
    if not date_field:
        return

    date_val = doc.get(date_field)
    if not date_val:
        return

    try:
        date_obj = getdate(date_val)
    except Exception:
        return

    yyyy = str(date_obj.year)  # e.g. "2025"
    yy = yyyy[-2:]  # e.g. "25"

    ns = doc.naming_series

    # Replace the dot-delimited tokens (.YYYY. and .YY.) with the literal year.
    # This makes the Series counter prefix per-fiscal-year
    # e.g. "MAT-MIS-.YYYY.-.####" → "MAT-MIS-.2025.-.####"
    ns = ns.replace(".YYYY.", f".{yyyy}.")
    ns = ns.replace(".YY.", f".{yy}.")
    # Handle trailing tokens (no trailing dot)
    if ns.endswith(".YYYY"):
        ns = ns[:-5] + f".{yyyy}"
    if ns.endswith(".YY"):
        ns = ns[:-3] + f".{yy}"

    doc.naming_series = ns


def validate_fiscal_year(doc, method=None):
    """
    validate hook - ensures that the document's date field falls within
    the user's currently active financial year.
    """
    # System managers / background jobs might not have a fiscal year set, skip validation
    if frappe.flags.in_test or frappe.flags.in_migrate or frappe.flags.in_patch:
        return

    # User may be logged in without FY, or job may not have one
    fiscal_year = frappe.defaults.get_user_default("fiscal_year")
    if not fiscal_year:
        return

    date_field = YEAR_DOCTYPES_DATE_FIELD.get(doc.doctype)
    if not date_field:
        return
        
    date_val = doc.get(date_field)
    if not date_val:
        return
        
    try:
        date_obj = getdate(date_val)
    except Exception:
        return
        
    try:
        fy = frappe.get_cached_doc("Fiscal Year", fiscal_year)
    except Exception:
        return

    if date_obj < getdate(fy.year_start_date) or date_obj > getdate(fy.year_end_date):
        # Determine the label of the date field dynamically
        df_label = date_field.replace("_", " ").title()
        meta = frappe.get_meta(doc.doctype)
        field_meta = meta.get_field(date_field)
        if field_meta:
            df_label = field_meta.label

        frappe.throw(
            f"The <b>{df_label}</b> ({date_val}) does not belong to your currently active Fiscal Year "
            f"({fy.year_start_date} to {fy.year_end_date}). Please change it.",
            title="Fiscal Year Validation"
        )


def validate_warehouse(doc, method=None):
    """
    validate hook - ensures that the document's warehouse field matches
    the user's currently active unit (warehouse).
    """
    if frappe.flags.in_test or frappe.flags.in_migrate or frappe.flags.in_patch:
        return

    warehouse = frappe.defaults.get_user_default("warehouse")
    if not warehouse:
        return

    if doc.doctype in ["Purchase Receipt", "Delivery Note", "Purchase Order", "Material Request", "Supplier Quotation", "Purchase Invoice"]:
        if doc.get("set_warehouse") and doc.get("set_warehouse") != warehouse:
            frappe.throw(
                f"The <b>Target Warehouse</b> ({doc.get('set_warehouse')}) does not match your currently active Unit ({warehouse}). Please change it or switch units.",
                title="Unit Validation"
            )
            
    elif doc.doctype == "Stock Entry":
        from_wh = doc.get("from_warehouse")
        to_wh = doc.get("to_warehouse")
        
        # If neither matches the active warehouse
        if from_wh and from_wh != warehouse and to_wh and to_wh != warehouse:
            frappe.throw(
                f"Neither Source nor Target Warehouse match your currently active Unit ({warehouse}). At least one must match.",
                title="Unit Validation"
            )
        elif from_wh and not to_wh and from_wh != warehouse:
             frappe.throw(
                f"The <b>Source Warehouse</b> ({from_wh}) does not match your currently active Unit ({warehouse}).",
                title="Unit Validation"
            )
        elif to_wh and not from_wh and to_wh != warehouse:
             frappe.throw(
                f"The <b>Target Warehouse</b> ({to_wh}) does not match your currently active Unit ({warehouse}).",
                title="Unit Validation"
            )
