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
    if doctype in ["Purchase Receipt", "Purchase Receipt Return", "Delivery Note", "Purchase Order", "Material Request", "Purchase Invoice"]:
        # These doctypes have `set_warehouse` field in the parent level
        # NOTE: Supplier Quotation does NOT have set_warehouse at parent level — excluded intentionally
        return f"{tbl}.`set_warehouse` = '{warehouse}'"
    
    elif doctype in ["Stock Entry", "Production Order", "Waybill", "Waybill Return"]:
        return f"({tbl}.`source_warehouse` = '{warehouse}' OR {tbl}.`target_warehouse` = '{warehouse}')" if doctype == "Production Order" else f"({tbl}.`from_warehouse` = '{warehouse}' OR {tbl}.`to_warehouse` = '{warehouse}')"
        
    elif doctype == "Stock Ledger Entry":
        return f"{tbl}.`warehouse` = '{warehouse}'"
        
    elif doctype == "Adjustment":
        return f"{tbl}.`name` IN (SELECT `parent` FROM `tabAdjustment Item` WHERE `warehouse` = '{warehouse}')"
    
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

def pqc_adjustment(user=None):
    return _combine_conditions("Adjustment")

def pqc_production_order(user=None):
    return _combine_conditions("Production Order")

def pqc_purchase_receipt_return(user=None):
    return _combine_conditions("Purchase Receipt Return")

def pqc_waybill(user=None):
    return _combine_conditions("Waybill")

def pqc_waybill_return(user=None):
    return _combine_conditions("Waybill Return")

def pqc_request_for_quotation(user=None):
    return _combine_conditions("Request for Quotation")


# ── has_permission wrappers (to block URL access) ─────────────────────────────

def _check_hp(doc, doctype, user=None):
    """
    Evaluates both Unit and Fiscal Year for a specific document.
    """
    # System Manager is typically exempt, but Frappe does basic role checks first.
    warehouse = frappe.defaults.get_user_default("warehouse")
    fiscal_year = frappe.defaults.get_user_default("fiscal_year")
    
    if not warehouse and not fiscal_year:
        return True
        
    # Check Unit
    if warehouse:
        if doctype in ["Purchase Receipt", "Purchase Receipt Return", "Delivery Note", "Purchase Order", "Material Request", "Purchase Invoice"]:
            doc_wh = doc.get("set_warehouse")
            if doc_wh and doc_wh != warehouse:
                return False
        elif doctype in ["Stock Entry", "Waybill", "Waybill Return"]:
            if doc.get("from_warehouse") != warehouse and doc.get("to_warehouse") != warehouse:
                return False
        elif doctype == "Production Order":
            if doc.get("source_warehouse") != warehouse and doc.get("target_warehouse") != warehouse:
                return False
        elif doctype == "Adjustment":
            if not any(item.get("warehouse") == warehouse for item in doc.get("items", [])):
                return False

    # Check Fiscal Year
    if fiscal_year:
        from manakshia_steel.api.fiscal_year_filter import FISCAL_YEAR_FILTER_DOCTYPES, _get_fy_date_range
        date_field = FISCAL_YEAR_FILTER_DOCTYPES.get(doctype)
        if date_field:
            date_range = _get_fy_date_range()
            if date_range:
                start, end = date_range
                doc_date = str(doc.get(date_field) or "")
                if doc_date and (doc_date < start or doc_date > end):
                    return False
                    
    return True

def hp_stock_entry(doc, ptype="read", user=None):          return _check_hp(doc, "Stock Entry", user)
def hp_purchase_receipt(doc, ptype="read", user=None):     return _check_hp(doc, "Purchase Receipt", user)
def hp_delivery_note(doc, ptype="read", user=None):        return _check_hp(doc, "Delivery Note", user)
def hp_purchase_order(doc, ptype="read", user=None):       return _check_hp(doc, "Purchase Order", user)
def hp_material_request(doc, ptype="read", user=None):     return _check_hp(doc, "Material Request", user)
def hp_supplier_quotation(doc, ptype="read", user=None):   return _check_hp(doc, "Supplier Quotation", user)
def hp_request_for_quotation(doc, ptype="read", user=None):return _check_hp(doc, "Request for Quotation", user)
def hp_purchase_invoice(doc, ptype="read", user=None):     return _check_hp(doc, "Purchase Invoice", user)
def hp_adjustment(doc, ptype="read", user=None):           return _check_hp(doc, "Adjustment", user)
def hp_production_order(doc, ptype="read", user=None):     return _check_hp(doc, "Production Order", user)
def hp_purchase_receipt_return(doc, ptype="read", user=None): return _check_hp(doc, "Purchase Receipt Return", user)
def hp_waybill(doc, ptype="read", user=None):              return _check_hp(doc, "Waybill", user)
def hp_waybill_return(doc, ptype="read", user=None):       return _check_hp(doc, "Waybill Return", user)
