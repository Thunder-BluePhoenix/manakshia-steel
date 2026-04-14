"""
manakshia_steel/api/clear_transactions.py

⚠️  DANGER — GO-LIVE RESET SCRIPT ⚠️
Deletes ALL transaction data and resets document number counters to 0.
Master data (Items, Suppliers, Customers, Warehouses, etc.) is preserved.

Run:
    bench --site manakshia execute manakshia_steel.api.clear_transactions.run

After running:
    • All transaction records are gone (Stock Entry, GRN, PO, MR, Waybills, etc.)
    • GL Entry, Payment Ledger Entry cleared
    • Stock Ledger Entry, Bin balances zeroed
    • Serial and Batch Bundles removed
    • Serial No records cleared
    • Batch transaction history cleared (batch masters kept)
    • tabSeries counters for custom series reset to 0 (next doc → 00001)
"""

import frappe


# ── 1. Transaction parent DocTypes to delete ──────────────────────────────────
# Order matters: child tables are auto-discovered and deleted first.
TRANSACTION_DOCTYPES = [
    # ── Custom ──────────────────────────────────────────────────────────────
    "Adjustment",
    "Waybill",
    "Waybill Return",
    "Production Order",
    "Purchase Receipt Return",

    # ── ERPNext Buying ───────────────────────────────────────────────────────
    "Purchase Receipt",
    "Purchase Order",
    "Purchase Invoice",
    "Supplier Quotation",
    "Request for Quotation",
    "Material Request",

    # ── ERPNext Selling ──────────────────────────────────────────────────────
    "Delivery Note",
    "Sales Invoice",
    "Sales Order",
    "Quotation",

    # ── ERPNext Stock ────────────────────────────────────────────────────────
    "Stock Entry",
    "Stock Reconciliation",

    # ── ERPNext Accounts ─────────────────────────────────────────────────────
    "Payment Entry",
    "Journal Entry",
    "Purchase Invoice",   # already listed above but harmless duplicate
]

# ── 2. Standalone ledger / supporting tables (not DocType parents) ────────────
STANDALONE_TABLES = [
    ("GL Entry",                  "General Ledger"),
    ("Payment Ledger Entry",      "Payment Ledger"),
    ("Stock Ledger Entry",        "Stock Ledger"),
    ("Serial and Batch Bundle",   "Serial & Batch Bundles"),   # parent
    ("Serial and Batch Entry",    "Serial & Batch Entries"),   # its child table
    ("Bin",                       "Stock Bin balances"),
    ("Serial No",                 "Serial Nos"),
]

# ── 3. Series prefixes to reset (exact prefixes used in tabSeries) ────────────
# tabSeries stores keys like "Issue/G/2026-2027/" → current counter
SERIES_PATTERNS = [
    # Adjustment
    "GN/", "PH/", "YR/",
    # Stock Entry Issue (all process letters)
    "Issue/0/", "Issue/G/", "Issue/B/", "Issue/Z/", "Issue/F/",
    "Issue/M/", "Issue/C/", "Issue/E/", "Issue/H/", "Issue/P/",
    "Issue/S/", "Issue/D/", "Issue/J/",
    # Stock Entry Receipt
    "Receipt/0/", "Receipt/G/", "Receipt/B/", "Receipt/Z/", "Receipt/F/",
    "Receipt/M/", "Receipt/C/", "Receipt/E/", "Receipt/H/", "Receipt/P/",
    "Receipt/S/", "Receipt/D/", "Receipt/J/",
    # Stock Transfer
    "STI/", "STO/",
    # GRN
    "GRN/R/", "GRN/C/", "GRN/F/", "GRN/G/", "GRN/J/",
    # GRN Return / Waybill / Waybill Return
    "GRT/", "SAL/", "SAL/J/", "SAL/E/", "WRT/",
    # ERPNext DocTypes
    "MR/", "SQ/", "RFQ/", "PO/", "PRO/",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _truncate(table_name, label):
    """DELETE all rows from a Frappe DocType table. Skips if table doesn't exist."""
    tbl = f"tab{table_name}"
    try:
        count = frappe.db.sql(f"SELECT COUNT(*) FROM `{tbl}`")[0][0]
        frappe.db.sql(f"DELETE FROM `{tbl}`")
        print(f"  🗑  {label:<45s}  ({count} rows deleted)")
    except Exception as e:
        if "doesn't exist" in str(e) or "1146" in str(e):
            print(f"  –   {label:<45s}  (table not found, skipped)")
        else:
            print(f"  ⚠   {label:<45s}  ERROR: {e}")


def _delete_doctype(doctype):
    """Delete all records of a DocType and its child tables."""
    # Discover child tables via meta
    try:
        meta = frappe.get_meta(doctype)
    except Exception:
        print(f"  –   {doctype:<45s}  (meta not found, skipped)")
        return

    # Delete children first
    for field in meta.fields:
        if field.fieldtype == "Table" and field.options:
            _truncate(field.options, f"  └─ {field.options} (child of {doctype})")

    # Delete parent
    _truncate(doctype, doctype)


def _reset_series():
    """Reset custom series counters in tabSeries to 0."""
    print("\n── Resetting series counters ────────────────────────────────────────")
    total = 0
    for prefix in SERIES_PATTERNS:
        # tabSeries key format: "SERIESPREFIX/" + fiscal-year + "/"
        # We match anything that STARTS WITH this prefix
        rows = frappe.db.sql(
            "SELECT name, current FROM tabSeries WHERE name LIKE %s",
            (prefix + "%",), as_dict=True
        )
        for row in rows:
            frappe.db.sql("UPDATE tabSeries SET current = 0 WHERE name = %s", (row.name,))
            print(f"  ✓  Reset  {row.name:<50s}  {row.current} → 0")
            total += 1

    if total == 0:
        print("  (no matching series found — counters were already 0 or not yet created)")
    else:
        print(f"\n  Total series reset: {total}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    frappe.set_user("Administrator")

    print(f"\n{'='*68}")
    print(f"  ⚠  GO-LIVE TRANSACTION RESET")
    print(f"  Site     : {frappe.local.site}")
    print(f"  Clearing : all transactions, GL, SLE, Bin, Serial/Batch, Series")
    print(f"{'='*68}\n")

    # ── Step 1: Delete transactions (children auto-discovered) ──────────────
    seen = set()
    print("── Deleting transaction records ────────────────────────────────────")
    for dt in TRANSACTION_DOCTYPES:
        if dt in seen:
            continue
        seen.add(dt)
        _delete_doctype(dt)

    # ── Step 2: Standalone ledger / stock tables ─────────────────────────────
    print("\n── Clearing ledger and stock tables ─────────────────────────────────")
    for table_name, label in STANDALONE_TABLES:
        _truncate(table_name, label)

    # ── Step 3: Reset series counters ────────────────────────────────────────
    _reset_series()

    # ── Commit everything ────────────────────────────────────────────────────
    frappe.db.commit()

    print(f"\n{'='*68}")
    print(f"  ✅  DONE — database is now transaction-free.")
    print(f"  Master data (Items, Suppliers, Customers, Warehouses) preserved.")
    print(f"  Next document of each type will start from 00001.")
    print(f"{'='*68}\n")
