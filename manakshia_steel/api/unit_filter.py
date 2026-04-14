import frappe
from manakshia_steel.api.fiscal_year_filter import get_fiscal_year_condition

def _get_warehouse_condition(doctype, alias=None):
    """
    Returns a SQL WHERE condition that restricts rows to the user's unit (warehouse).
    """
    # System Manager can see all or if no unit is set
    warehouse = frappe.defaults.get_user_default("warehouse")
    if not warehouse:
        return ""

    tbl = alias or f"`tab{doctype}`"
    
    if doctype in ["Purchase Receipt", "Delivery Note", "Purchase Order", "Material Request", "Purchase Invoice"]:
        # These doctypes have `set_warehouse` field in the parent level
        # NOTE: Supplier Quotation does NOT have set_warehouse at parent level — excluded intentionally
        return f"{tbl}.`set_warehouse` = '{warehouse}'"
    
    elif doctype == "Stock Entry":
        # Stock Entry has `from_warehouse` and `to_warehouse`
        return f"({tbl}.`from_warehouse` = '{warehouse}' OR {tbl}.`to_warehouse` = '{warehouse}')"
        
    elif doctype == "Stock Ledger Entry":
        return f"{tbl}.`warehouse` = '{warehouse}'"
    
    return ""


def _combine_conditions(doctype, alias=None):
    """Combine both fiscal year and unit (warehouse) conditions."""
    fy_cond = get_fiscal_year_condition(doctype, alias)
    wh_cond = _get_warehouse_condition(doctype, alias)
    
    if fy_cond and wh_cond:
        return f"({fy_cond}) AND ({wh_cond})"
    elif fy_cond:
        return fy_cond
    elif wh_cond:
        return wh_cond
    return ""


# ── Per-doctype wrapper functions for hooks.py ────────────────────────────────
# These replace the ones in fiscal_year_filter.py in hooks.py

def pqc_stock_entry(user=None):
    return _combine_conditions("Stock Entry")

def pqc_purchase_receipt(user=None):
    return _combine_conditions("Purchase Receipt")

def pqc_delivery_note(user=None):
    return _combine_conditions("Delivery Note")

def pqc_purchase_order(user=None):
    return _combine_conditions("Purchase Order")

def pqc_material_request(user=None):
    return _combine_conditions("Material Request")

def pqc_supplier_quotation(user=None):
    return _combine_conditions("Supplier Quotation")

def pqc_purchase_invoice(user=None):
    return _combine_conditions("Purchase Invoice")

def pqc_stock_ledger_entry(user=None):
    return _combine_conditions("Stock Ledger Entry")
