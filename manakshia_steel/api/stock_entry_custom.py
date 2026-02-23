import frappe

def validate_material_receipt(doc, method):

    if doc.purpose != "Material Receipt":
        return

    if not doc.custom_material_issue:
        # -- Previous implementation --
        # frappe.throw("Material Receipt must be linked to a Material Issue")
        return  # Allow standalone Material Receipts

    issue = frappe.get_doc("Stock Entry", doc.custom_material_issue)

    if issue.purpose != "Material Issue":
        frappe.throw("Linked document must be a Material Issue")

    if doc.custom_process != issue.custom_process:
        frappe.throw("Process must match between Issue and Receipt")

    # total issued qty
    issued_qty = {}
    for row in issue.items:
        key = (row.item_code, row.batch_no)
        issued_qty[key] = issued_qty.get(key, 0) + row.qty

    # already received qty
    received_qty = {}
    previous = frappe.get_all(
        "Stock Entry",
        filters={
            "custom_material_issue": doc.custom_material_issue,
            "purpose": "Material Receipt",
            "docstatus": 1
        },
        pluck="name"
    )

    for name in previous:
        r = frappe.get_doc("Stock Entry", name)
        for row in r.items:
            key = (row.item_code, row.batch_no)
            received_qty[key] = received_qty.get(key, 0) + row.qty

    # validate current receipt
    for row in doc.items:
        key = (row.item_code, row.batch_no)
        issued = issued_qty.get(key, 0)
        already = received_qty.get(key, 0)

        if row.qty + already > issued:
            frappe.throw(
                f"Receipt qty exceeds issued qty for {row.item_code}. "
                f"Issued: {issued}, Already Received: {already}"
            )