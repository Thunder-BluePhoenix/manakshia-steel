import frappe


def suppress_serial_batch_on_stock_entry(doc, method):
    """
    ERPNext v16 mandates serial/batch fields when items have has_serial_no or has_batch_no.
    For Stock Entry, we manage serial/batch ONLY at Purchase Receipt level.
    This hook clears all serial/batch references on every row before validation fires.
    """
    for row in doc.get("items", []):
        row.serial_and_batch_bundle = None
        row.serial_no = None
        row.batch_no = None
        row.use_serial_batch_fields = 0


def validate_material_receipt(doc, method):
    if doc.purpose != "Material Receipt":
        return

    if not doc.custom_material_issue:
        return  # Allow standalone Material Receipts

    issue = frappe.get_doc("Stock Entry", doc.custom_material_issue)

    if issue.purpose != "Material Issue":
        frappe.throw("Linked document must be a Material Issue")

    if doc.custom_process != issue.custom_process:
        frappe.throw("Process must match between Issue and Receipt")

    # Total issued qty — keyed by item_code only (no batch tracking in Stock Entry)
    issued_qty = {}
    for row in issue.items:
        key = row.item_code
        issued_qty[key] = issued_qty.get(key, 0) + row.qty

    # Already received qty from previously submitted receipts
    received_qty = {}
    previous = frappe.get_all(
        "Stock Entry",
        filters={
            "custom_material_issue": doc.custom_material_issue,
            "purpose": "Material Receipt",
            "docstatus": 1,
        },
        pluck="name",
    )

    for name in previous:
        r = frappe.get_doc("Stock Entry", name)
        for row in r.items:
            key = row.item_code
            received_qty[key] = received_qty.get(key, 0) + row.qty

    # Validate current receipt quantities
    for row in doc.items:
        key = row.item_code
        issued = issued_qty.get(key, 0)
        already = received_qty.get(key, 0)

        if row.qty + already > issued:
            frappe.throw(
                f"Receipt qty exceeds issued qty for {row.item_code}. "
                f"Issued: {issued}, Already Received: {already}"
            )
