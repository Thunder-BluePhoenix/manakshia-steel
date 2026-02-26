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
        if (
            row.warehouse
            and row.rejected_warehouse
            and row.warehouse == row.rejected_warehouse
        ):
            row.rejected_warehouse = None
            frappe.msgprint(
                f"Row {row.idx}: Cleared 'Rejected Warehouse' as it matched 'Accepted Warehouse'.",
                alert=True,
            )


def clean_stock_entry(doc):
    """
    Fix row-level warehouse conflicts caused by user defaults auto-populating both
    s_warehouse and t_warehouse from the same default warehouse.

    - Material Issue:  source = user warehouse, target = transit.
                       If s_warehouse == t_warehouse → clear t_warehouse.
    - Material Receipt: source = transit, target = user warehouse.
                       If s_warehouse == t_warehouse → clear s_warehouse.
    - All others:      If from_warehouse == to_warehouse (header) → clear to_warehouse.
                       If s_warehouse == t_warehouse (row) → clear t_warehouse.
    """
    purpose = doc.purpose

    if purpose == "Material Issue":
        for row in doc.get("items", []):
            if (
                row.s_warehouse
                and row.t_warehouse
                and row.s_warehouse == row.t_warehouse
            ):
                row.t_warehouse = None

    elif purpose == "Material Receipt":
        for row in doc.get("items", []):
            if (
                row.s_warehouse
                and row.t_warehouse
                and row.s_warehouse == row.t_warehouse
            ):
                row.s_warehouse = None

    else:
        # Header level
        if (
            doc.from_warehouse
            and doc.to_warehouse
            and doc.from_warehouse == doc.to_warehouse
        ):
            doc.to_warehouse = None
            frappe.msgprint(
                "Cleared 'Target Warehouse' as it matched 'Source Warehouse'.",
                alert=True,
            )

        # Row level
        for row in doc.get("items", []):
            if (
                row.s_warehouse
                and row.t_warehouse
                and row.s_warehouse == row.t_warehouse
            ):
                row.t_warehouse = None


def clean_subcontracting_receipt(doc):
    """Clear Rejected Warehouse (Header) if matches Item Warehouse (Accepted)."""
    header_rejected = doc.rejected_warehouse

    if not header_rejected:
        return

    conflict_found = False
    for row in doc.get("items", []):
        if row.warehouse and row.warehouse == header_rejected:
            conflict_found = True
            break

    if conflict_found:
        doc.rejected_warehouse = None
        frappe.msgprint(
            "Cleared 'Rejected Warehouse' header as it matched accepted items.",
            alert=True,
        )
