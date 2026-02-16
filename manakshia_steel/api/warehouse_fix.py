
import frappe

def validate_warehouse_conflict(doc, method):
    """
    Fixes "Same Warehouse" errors caused by User Defaults being applied to conflicting fields.
    Runs on: Purchase Receipt, Stock Entry, Subcontracting Receipt via hooks.
    """
    
    if doc.doctype == "Purchase Receipt":
        clean_purchase_receipt(doc)

    elif doc.doctype == "Stock Entry":
        clean_stock_entry(doc)

    elif doc.doctype == "Subcontracting Receipt":
        clean_subcontracting_receipt(doc)


def clean_purchase_receipt(doc):
    """Clear rejected_warehouse if same as warehouse (Accepted)."""
    for row in doc.get("items", []):
        if row.warehouse and row.rejected_warehouse and row.warehouse == row.rejected_warehouse:
            row.rejected_warehouse = None
            frappe.msgprint(f"Row {row.idx}: Cleared 'Rejected Warehouse' as it matched 'Accepted Warehouse'.", alert=True)


def clean_stock_entry(doc):
    """Clear To Warehouse if same as From Warehouse (Source)."""
    # 1. Header Level
    if doc.from_warehouse and doc.to_warehouse and doc.from_warehouse == doc.to_warehouse:
        doc.to_warehouse = None
        frappe.msgprint("Cleared 'Target Warehouse' as it matched 'Source Warehouse'.", alert=True)

    # 2. Row Level (s_warehouse vs t_warehouse)
    for row in doc.get("items", []):
        if row.s_warehouse and row.t_warehouse and row.s_warehouse == row.t_warehouse:
            row.t_warehouse = None
            # Only alert if it wasn't just cleared by header change logic propogation
            # frappe.msgprint(f"Row {row.idx}: Cleared 'Target Warehouse' as it matched 'Source Warehouse'.", alert=True)


def clean_subcontracting_receipt(doc):
    """Clear Rejected Warehouse (Header) if matches Item Warehouse (Accepted)."""
    header_rejected = doc.rejected_warehouse
    
    if not header_rejected:
        return

    # Subcontracting Receipt standard: Header Rejected vs Item Accepted
    conflict_found = False
    for row in doc.get("items", []):
        # row.warehouse is the Accepted Warehouse
        if row.warehouse and row.warehouse == header_rejected:
            conflict_found = True
            break
    
    if conflict_found:
        doc.rejected_warehouse = None
        frappe.msgprint("Cleared 'Rejected Warehouse' header as it matched accepted items.", alert=True)
