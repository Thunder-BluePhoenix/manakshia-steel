# manakshia_steel/api/doc_naming.py
#
# Central document naming for all custom and ERPNext DocTypes.
#
# Series format:  PREFIX/{fy}/.#####  →  PREFIX/2025-2026/00001
# Stock Entry:    Issue/{letter}/{fy}/.#####  →  Issue/G/2025-2026/00001
#                 Receipt/{letter}/{fy}/.##### →  Receipt/G/2025-2026/00001
#
# The `.#####` part is Frappe's counter token (5-digit, zero-padded).
# The counter key in tabSeries is everything before `.#####`,
# so each unique PREFIX/fiscal-year combination gets its own counter.
#
# Year token is taken from the USER's active fiscal year (user default),
# which makes counters reset at fiscal year boundaries (April → new series).
# Falls back to calendar year from the doc date for background jobs /
# System Manager sessions that have no fiscal year default set.

import frappe
from frappe.model.naming import make_autoname
from frappe.utils import getdate, nowdate

# ── Warehouse → Unit Code mapping ─────────────────────────────────────────────

# Abbreviation is now fetched dynamically from the `custom_abbr` field on the Warehouse DocType.


# ── Internal helpers ──────────────────────────────────────────────────────────


def _year(doc, date_field):
    """Return 4-digit year from the document's date field."""
    val = doc.get(date_field)
    if not val:
        val = nowdate()
    try:
        return str(getdate(val).year)
    except Exception:
        return str(getdate(nowdate()).year)


def _unit_code(doc):
    """
    Return the unit abbreviation for the user's active warehouse from the 'custom_abbr' field.
    Returns an empty string if no warehouse or abbreviation is found.
    """
    wh = frappe.defaults.get_user_default("warehouse")
    if not wh:
        # Fallback to general default if user default not set
        wh = frappe.defaults.get_default("warehouse")

    if not wh:
        return ""

    # Fetch the custom abbreviation directly from the Warehouse doctype
    try:
        code = frappe.db.get_value("Warehouse", wh, "custom_abbr")
        if code:
            return code
    except Exception:
        pass

    return ""


def _inject_meta(doctype, series):
    """
    Append *series* to the in-memory naming_series field options so
    Frappe's validate_series() does not reject our dynamically-built string.
    """
    try:
        meta = frappe.get_meta(doctype)
        field = meta.get_field("naming_series")
        if not field:
            return
        opts = [s.strip() for s in (field.options or "").split("\n") if s.strip()]
        if series not in opts:
            field.options = "\n".join(opts + [series])
    except Exception:
        pass


def _assign(doc, unit, type_code, modifier, year):
    """
    Generate name in format: UNIT-TYPE-MODIFIER_COUNTER-YEAR
    e.g. OT-AJ-G0001-2026 or OT-SI-00001-2026

    To ensure counters reset per year while keeping the year at the end:
    1. We use a key that includes the year for tabSeries (e.g. MAB-AJ-G-2026).
    2. We extract the generated counter.
    3. We assemble the final name with the year at the end.
    """
    if unit:
        prefix = f"{unit}-{type_code}-{modifier}" if modifier else f"{unit}-{type_code}"
    else:
        prefix = f"{type_code}-{modifier}" if modifier else f"{type_code}"

    key = f"{prefix}-{year}"
    padding = 4 if modifier else 5
    hashes = "#" * padding

    # Get the name with counter from Frappe (increments tabSeries)
    name_with_counter = make_autoname(f"{key}.{hashes}", doc=doc)

    # Extract only the digits from the end
    counter_digits = name_with_counter[-padding:]

    # Re-assemble in the requested format
    if modifier:
        doc.name = f"{prefix}{counter_digits}-{year}"
    else:
        doc.name = f"{prefix}-{counter_digits}-{year}"

    # Ensure naming_series matches the key used so Frappe doesn't complain
    doc.naming_series = f"{key}.{hashes}"


# ── Process → letter mapping (matches Process DocType master names) ────────────

PROCESS_LETTER = {
    "GENERAL": "O",
    "CGL": "G",
    "CTL": "B",
    "CR CORRUGATION": "Z",
    "PROFILE (GC)": "F",
    "COATING MIXING": "M",
    "COLOUR COATING": "C",
    "EMBOSSING": "E",
    "POWER AND FUEL": "H",
    "ROPP": "P",
    "SPARE PARTS": "S",
    "PROFILE (ALUMINIUM)": "D",
    "JOB WORK": "J",
}


# ── Adjustment ────────────────────────────────────────────────────────────────

ADJUSTMENT_MODIFIER = {
    "GENERAL ADJUSTMENT": "G",
    "PHYSICAL STOCK ADJUSTMENT": "P",
    "YEARLY STOCK ADJUSTMENT": "Y",
}


def autoname_adjustment(doc, method=None):
    """
    autoname hook for Adjustment.
    OT-AJ-G0001-2026
    """
    unit = _unit_code(doc)
    year = _year(doc, "posting_date")
    mod = ADJUSTMENT_MODIFIER.get(doc.get("adjustment_type"), "G")
    _assign(doc, unit, "AJ", mod, year)


# ── Stock Entry ───────────────────────────────────────────────────────────────


def autoname_stock_entry(doc, method=None):
    """
    autoname hook for Stock Entry.

    Material Issue   → OT-IS-G0001-2026
    Material Receipt → OT-FG-G0001-2026
    Stock Transfer In  → OT-SI-00001-2026
    Stock Transfer Out → OT-SO-00001-2026
    """
    unit = _unit_code(doc)
    year = _year(doc, "posting_date")
    etype = doc.stock_entry_type

    if etype == "Stock Transfer In":
        _assign(doc, unit, "SI", None, year)
        return

    if etype == "Stock Transfer Out":
        _assign(doc, unit, "SO", None, year)
        return

    if etype not in ("Material Issue", "Material Receipt"):
        return  # Manufacture, Repack, etc. — Frappe handles naming

    process = doc.get("custom_process") or ""
    mod = PROCESS_LETTER.get(process, "O")
    type_code = "IS" if etype == "Material Issue" else "FG"
    _assign(doc, unit, type_code, mod, year)


# ── Purchase Receipt (GRN) ────────────────────────────────────────────────────

PR_MODIFIER = {
    "RAW MATERIAL": "R",
    "CAPITAL GOODS": "C",
    "POWER AND FUELS": "F",
    "GENERAL GOODS": "G",
    "JOB WORK": "J",
}


def autoname_purchase_receipt(doc, method=None):
    """
    autoname hook for Purchase Receipt (GRN).
    OT-GN-R0001-2026
    """
    unit = _unit_code(doc)
    year = _year(doc, "posting_date")
    mod = PR_MODIFIER.get(doc.get("custom_purchase_receipt_type"))
    if not mod:
        return  # not a custom GRN type — Frappe handles naming
    _assign(doc, unit, "GN", mod, year)


# ── Purchase Receipt Return (GRN Return) ──────────────────────────────────────


def autoname_grn_return(doc, method=None):
    """OT-GR-00001-2026"""
    unit = _unit_code(doc)
    year = _year(doc, "posting_date")
    _assign(doc, unit, "GR", None, year)


# ── Waybill ───────────────────────────────────────────────────────────────────

WAYBILL_MODIFIER = {
    "General": None,
    "Job work": "J",
    "Export": "E",
}


def autoname_waybill(doc, method=None):
    """
    autoname hook for Waybill.
    OT-SL-00001-2026
    OT-SL-J0001-2026
    """
    unit = _unit_code(doc)
    year = _year(doc, "date")
    mod = WAYBILL_MODIFIER.get(doc.get("waybill_type"))
    _assign(doc, unit, "SL", mod, year)


# ── Waybill Return ────────────────────────────────────────────────────────────


def autoname_waybill_return(doc, method=None):
    """OT-SR-00001-2026"""
    unit = _unit_code(doc)
    year = _year(doc, "date")
    _assign(doc, unit, "SR", None, year)


# ── ERPNext built-in DocTypes ─────────────────────────────────────────────────


def autoname_material_request(doc, method=None):
    """OT-MR-00001-2026"""
    unit = _unit_code(doc)
    year = _year(doc, "transaction_date")
    _assign(doc, unit, "MR", None, year)


def autoname_supplier_quotation(doc, method=None):
    """OT-SQ-00001-2026"""
    unit = _unit_code(doc)
    year = _year(doc, "transaction_date")
    _assign(doc, unit, "SQ", None, year)


def autoname_rfq(doc, method=None):
    """OT-RFQ-00001-2026"""
    unit = _unit_code(doc)
    year = _year(doc, "transaction_date")
    _assign(doc, unit, "RFQ", None, year)


def autoname_purchase_order(doc, method=None):
    """OT-PO-00001-2026"""
    unit = _unit_code(doc)
    year = _year(doc, "transaction_date")
    _assign(doc, unit, "PO", None, year)


def autoname_production_order(doc, method=None):
    """OT-PRO-00001-2026"""
    unit = _unit_code(doc)
    year = _year(doc, "order_date")
    _assign(doc, unit, "PRO", None, year)


MFG_PREFIX = {
    "Galvanized Coil Production": "GC",
    "CC Coil Production": "CC",
    "Embossed Coil Production": "EM",
    "CTL Production": "CTL",
    "Colour Profile Production": "CPRO",
    "Corrugated Sheet Production": "CS",
}


def autoname_manufacturing(doc, method=None):
    """OT-GC-00001-2026"""
    unit = _unit_code(doc)
    year = _year(doc, "date")
    prefix = MFG_PREFIX.get(doc.doctype, "MFG")
    _assign(doc, unit, prefix, None, year)
