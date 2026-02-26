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
