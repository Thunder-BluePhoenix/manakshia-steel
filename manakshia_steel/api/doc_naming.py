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


# ── Internal helpers ──────────────────────────────────────────────────────────

def _year(doc, date_field):
    """
    Return the year token for the naming series.

    Priority:
    1. User's active fiscal year (frappe user default) — e.g. "2025-2026"
       This ensures counters reset at fiscal year boundaries regardless of
       the document's calendar date.
    2. Calendar year from the document's date field — fallback for background
       jobs, System Manager sessions, or users without a fiscal year set.
    """
    # 1. Try fiscal year from user defaults (set during unit/FY login)
    try:
        fy = frappe.defaults.get_user_default("fiscal_year")
        if fy:
            return fy                  # e.g. "2025-2026"
    except Exception:
        pass

    # 2. Fall back to calendar year from the document's date field
    from frappe.utils import getdate, nowdate
    val = doc.get(date_field)
    if not val:
        val = nowdate()
    try:
        return str(getdate(val).year)  # e.g. "2026"
    except Exception:
        return str(getdate(nowdate()).year)


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


def _assign(doc, series):
    """
    Inject series into meta, generate a new name, assign both
    doc.naming_series and doc.name.  Setting doc.name prevents
    Frappe's built-in autoname from overwriting our value.
    """
    _inject_meta(doc.doctype, series)
    doc.naming_series = series
    doc.name = make_autoname(series, doc=doc)


# ── Process → letter mapping (matches Process DocType master names) ────────────

PROCESS_LETTER = {
    "GENERAL":             "0",
    "CGL":                 "G",
    "CTL":                 "B",
    "CR CORRUGATION":      "Z",
    "PROFILE (GC)":        "F",
    "COATING MIXING":      "M",
    "COLOUR COATING":      "C",
    "EMBOSSING":           "E",
    "POWER AND FUEL":      "H",
    "ROPP":                "P",
    "SPARE PARTS":         "S",
    "PROFILE (ALUMINIUM)": "D",
    "JOB WORK":            "J",
}


# ── Adjustment ────────────────────────────────────────────────────────────────

ADJUSTMENT_PREFIX = {
    "GENERAL ADJUSTMENT":        "GN",
    "PHYSICAL STOCK ADJUSTMENT": "PH",
    "YEARLY STOCK ADJUSTMENT":   "YR",
}


def autoname_adjustment(doc, method=None):
    """
    autoname hook for Adjustment.
    Maps adjustment_type → prefix, generates GN/2026/00001 style name.
    """
    year = _year(doc, "posting_date")
    prefix = ADJUSTMENT_PREFIX.get(doc.get("adjustment_type"), "GN")
    _assign(doc, f"{prefix}/{year}/.#####")


# ── Stock Entry ───────────────────────────────────────────────────────────────

def autoname_stock_entry(doc, method=None):
    """
    autoname hook for Stock Entry.

    Material Issue   → Issue/{letter}/{year}/.#####   e.g. Issue/G/2026/00001
    Material Receipt → Receipt/{letter}/{year}/.##### e.g. Receipt/G/2026/00001
    Stock Transfer In  → STI/{year}/.#####
    Stock Transfer Out → STO/{year}/.#####
    Other types (Manufacture, etc.) → return, let Frappe use its default series.
    """
    year = _year(doc, "posting_date")
    etype = doc.stock_entry_type

    if etype == "Stock Transfer In":
        _assign(doc, f"STI/{year}/.#####")
        return

    if etype == "Stock Transfer Out":
        _assign(doc, f"STO/{year}/.#####")
        return

    if etype not in ("Material Issue", "Material Receipt"):
        return  # Manufacture, Repack, etc. — Frappe handles naming

    process = doc.get("custom_process") or ""
    letter = PROCESS_LETTER.get(process, "0")
    type_pfx = "Issue" if etype == "Material Issue" else "Receipt"
    _assign(doc, f"{type_pfx}/{letter}/{year}/.#####")


# ── Purchase Receipt (GRN) ────────────────────────────────────────────────────

PR_PREFIX = {
    "RAW MATERIAL":    "GRN/R",
    "CAPITAL GOODS":   "GRN/C",
    "POWER AND FUELS": "GRN/F",
    "GENERAL GOODS":   "GRN/G",
    "JOB WORK":        "GRN/J",
}


def autoname_purchase_receipt(doc, method=None):
    """
    autoname hook for Purchase Receipt (GRN).
    Maps custom_purchase_receipt_type → GRN/R/2026/00001 etc.
    Falls through for types without a mapping (let Frappe use default series).
    """
    year = _year(doc, "posting_date")
    pfx = PR_PREFIX.get(doc.get("custom_purchase_receipt_type"))
    if not pfx:
        return  # not a custom GRN type — Frappe handles naming
    _assign(doc, f"{pfx}/{year}/.#####")


# ── Purchase Receipt Return (GRN Return) ──────────────────────────────────────

def autoname_grn_return(doc, method=None):
    """autoname hook for Purchase Receipt Return → GRT/2026/00001"""
    year = _year(doc, "posting_date")
    _assign(doc, f"GRT/{year}/.#####")


# ── Waybill ───────────────────────────────────────────────────────────────────

WAYBILL_PREFIX = {
    "General":  "SAL",
    "Job work": "SAL/J",
    "Export":   "SAL/E",
}


def autoname_waybill(doc, method=None):
    """
    autoname hook for Waybill.
    General → SAL/2026/00001
    Job work → SAL/J/2026/00001
    Export   → SAL/E/2026/00001
    """
    year = _year(doc, "date")
    pfx = WAYBILL_PREFIX.get(doc.get("waybill_type"), "SAL")
    _assign(doc, f"{pfx}/{year}/.#####")


# ── Waybill Return ────────────────────────────────────────────────────────────

def autoname_waybill_return(doc, method=None):
    """autoname hook for Waybill Return → WRT/2026/00001"""
    year = _year(doc, "date")
    _assign(doc, f"WRT/{year}/.#####")


# ── ERPNext built-in DocTypes ─────────────────────────────────────────────────

def autoname_material_request(doc, method=None):
    """autoname hook for Material Request → MR/2026/00001"""
    year = _year(doc, "transaction_date")
    _assign(doc, f"MR/{year}/.#####")


def autoname_supplier_quotation(doc, method=None):
    """autoname hook for Supplier Quotation → SQ/2026/00001"""
    year = _year(doc, "transaction_date")
    _assign(doc, f"SQ/{year}/.#####")


def autoname_rfq(doc, method=None):
    """autoname hook for Request for Quotation → RFQ/2026/00001"""
    year = _year(doc, "transaction_date")
    _assign(doc, f"RFQ/{year}/.#####")


def autoname_purchase_order(doc, method=None):
    """autoname hook for Purchase Order → PO/2026/00001"""
    year = _year(doc, "transaction_date")
    _assign(doc, f"PO/{year}/.#####")


def autoname_production_order(doc, method=None):
    """autoname hook for Production Order → PRO/2026/00001"""
    year = _year(doc, "order_date")
    _assign(doc, f"PRO/{year}/.#####")
