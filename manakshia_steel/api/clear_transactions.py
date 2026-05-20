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
    "Purchase Invoice",  # already listed above but harmless duplicate
]

# ── 2. Standalone ledger / supporting tables (not DocType parents) ────────────
STANDALONE_TABLES = [
    ("GL Entry", "General Ledger"),
    ("Payment Ledger Entry", "Payment Ledger"),
    ("Stock Ledger Entry", "Stock Ledger"),
    ("Serial and Batch Bundle", "Serial & Batch Bundles"),  # parent
    ("Serial and Batch Entry", "Serial & Batch Entries"),  # its child table
    ("Bin", "Stock Bin balances"),
    ("Serial No", "Serial Nos"),
]

# ── 3. Series prefixes to reset ─────────────────────────────────────────────────
# Since doc_naming.py now dynamically injects the Unit abbreviation, the series
# in tabSeries will look like "OT-AJ-G-2026" or "MAB-IS-O-2026".
# We use LIKE patterns to match the specific type codes in the middle or start.
SERIES_PATTERNS = [
    "%-AJ-%",
    "AJ-%",  # Adjustment
    "%-IS-%",
    "IS-%",  # Material Issue
    "%-FG-%",
    "FG-%",  # Material Receipt
    "%-SI-%",
    "SI-%",  # Stock Transfer In
    "%-SO-%",
    "SO-%",  # Stock Transfer Out
    "%-GN-%",
    "GN-%",  # Purchase Receipt (GRN)
    "%-GR-%",
    "GR-%",  # Purchase Receipt Return
    "%-SL-%",
    "SL-%",  # Waybill
    "%-SR-%",
    "SR-%",  # Waybill Return
    "%-MR-%",
    "MR-%",  # Material Request
    "%-SQ-%",
    "SQ-%",  # Supplier Quotation
    "%-RFQ-%",
    "RFQ-%",  # Request for Quotation
    "%-PO-%",
    "PO-%",  # Purchase Order
    "%-PRO-%",
    "PRO-%",  # Production Order
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
    for pattern in SERIES_PATTERNS:
        rows = frappe.db.sql(
            "SELECT name, current FROM tabSeries WHERE name LIKE %s",
            (pattern,),
            as_dict=True,
        )
        for row in rows:
            frappe.db.sql(
                "UPDATE tabSeries SET current = 0 WHERE name = %s", (row.name,)
            )
            print(f"  ✓  Reset  {row.name:<50s}  {row.current} → 0")
            total += 1

    if total == 0:
        print(
            "  (no matching series found — counters were already 0 or not yet created)"
        )
    else:
        print(f"\n  Total series reset: {total}")


# ── Main ──────────────────────────────────────────────────────────────────────


def run():
    frappe.set_user("Administrator")

    print(f"\n{'=' * 68}")
    print("  ⚠  GO-LIVE TRANSACTION RESET")
    print(f"  Site     : {frappe.local.site}")
    print("  Clearing : all transactions, GL, SLE, Bin, Serial/Batch, Series")
    print(f"{'=' * 68}\n")

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

    print(f"\n{'=' * 68}")
    print("  ✅  DONE — database is now transaction-free.")
    print("  Master data (Items, Suppliers, Customers, Warehouses) preserved.")
    print("  Next document of each type will start from 00001.")
    print(f"{'=' * 68}\n")
