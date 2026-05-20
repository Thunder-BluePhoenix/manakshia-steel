import frappe

# Doctypes and their date fields for fiscal year filtering
FISCAL_YEAR_FILTER_DOCTYPES = {
    "Stock Entry": "posting_date",
    "Purchase Receipt": "posting_date",
    "Delivery Note": "posting_date",
    "Purchase Order": "transaction_date",
    "Material Request": "transaction_date",
    "Supplier Quotation": "transaction_date",
    "Request for Quotation": "transaction_date",
    "Purchase Invoice": "posting_date",
    "Stock Ledger Entry": "posting_date",
    "Adjustment": "posting_date",
    "Production Order": "date",
    "Purchase Receipt Return": "posting_date",
    "Waybill": "date",
    "Waybill Return": "date",
    # ── 6 Steel Manufacturing Production Doctypes ─────────────────────────────
    "Galvanized Coil Production": "date",
    "Embossed Coil Production": "date",
    "CC Coil Production": "date",
    "Colour Profile Production": "date",
    "Corrugated Sheet Production": "date",
    "CTL Production": "date",
}


def _get_fy_date_range():
    """
    Return (start, end) dates for the current user's selected fiscal year.
    Returns None if no fiscal year is set or if the user is exempt.
    """
    fiscal_year = frappe.defaults.get_user_default("fiscal_year")
    if not fiscal_year:
        return None

    try:
        fy = frappe.get_cached_doc("Fiscal Year", fiscal_year)
        return str(fy.year_start_date), str(fy.year_end_date)
    except Exception:
        return None


def get_fiscal_year_condition(doctype, alias=None):
    """
    Returns a SQL WHERE condition that restricts rows to the user's fiscal year.
    Used as permission_query_conditions for each doctype.

    alias   optional table alias (e.g. 'tabStock Entry')
    """
    date_range = _get_fy_date_range()
    if not date_range:
        return ""  # no filter — System Manager or no FY selected

    date_field = FISCAL_YEAR_FILTER_DOCTYPES.get(doctype)
    if not date_field:
        return ""

    start, end = date_range
    tbl = alias or f"`tab{doctype}`"
    return f"{tbl}.`{date_field}` BETWEEN '{start}' AND '{end}'"


# ── Per-doctype wrapper functions ─────────────────────────────────────────────
# Frappe's permission_query_conditions must be a dotted path to a callable
# that accepts no args (or just uses frappe.form_dict). Each function just
# delegates to the shared helper.


def pqc_stock_entry(user=None):
    return get_fiscal_year_condition("Stock Entry")


def pqc_purchase_receipt(user=None):
    return get_fiscal_year_condition("Purchase Receipt")


def pqc_delivery_note(user=None):
    return get_fiscal_year_condition("Delivery Note")


def pqc_purchase_order(user=None):
    return get_fiscal_year_condition("Purchase Order")


def pqc_material_request(user=None):
    return get_fiscal_year_condition("Material Request")


def pqc_supplier_quotation(user=None):
    return get_fiscal_year_condition("Supplier Quotation")


def pqc_purchase_invoice(user=None):
    return get_fiscal_year_condition("Purchase Invoice")


def pqc_stock_ledger_entry(user=None):
    return get_fiscal_year_condition("Stock Ledger Entry")


def pqc_adjustment(user=None):
    return get_fiscal_year_condition("Adjustment")


def pqc_production_order(user=None):
    return get_fiscal_year_condition("Production Order")


def pqc_purchase_receipt_return(user=None):
    return get_fiscal_year_condition("Purchase Receipt Return")


def pqc_waybill(user=None):
    return get_fiscal_year_condition("Waybill")


def pqc_waybill_return(user=None):
    return get_fiscal_year_condition("Waybill Return")


def pqc_request_for_quotation(user=None):
    return get_fiscal_year_condition("Request for Quotation")
