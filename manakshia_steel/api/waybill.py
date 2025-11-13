import frappe

@frappe.whitelist()
def create_from_source(doctype, docname):
    doc = frappe.get_doc(doctype, docname)

    # Prevent duplicate
    if doc.get("custom_waybill"):
        frappe.throw(f"Waybill already exists: {doc.custom_waybill}")

    # Route to correct creation function
    if doctype == "Purchase Receipt":
        waybill_name = create_from_purchase_receipt(doc)

    elif doctype == "Stock Entry":
        waybill_name = create_from_stock_entry(doc)

    elif doctype == "Delivery Note":
        waybill_name = create_from_delivery_note(doc)

    else:
        frappe.throw("Waybill creation not supported for: " + doctype)

    return waybill_name



def create_from_purchase_receipt(doc):
    waybill = frappe.new_doc("Waybill")

    waybill.customer_name = doc.supplier
    waybill.customer_address = doc.supplier_address
    waybill.buyers_order_no = doc.purchase_order
    waybill.sales_order_no = doc.purchase_order
    waybill.date = doc.posting_date

    if doc.items:
        waybill.to_warehouse = doc.items[0].warehouse

    waybill.delivery_order_no = doc.name
    waybill.authorized_by = doc.owner

    for it in doc.items:
        waybill.append("items", {
            "item_code": it.item_code,
            "qty": it.qty,
            "uom": it.uom,
            "rate": it.rate,
            "amount": it.amount
        })

    waybill.insert(ignore_permissions=True)
    waybill.submit()

    return waybill.name



def create_from_stock_entry(doc):

    if not doc.from_warehouse or not doc.to_warehouse:
        frappe.throw("Waybill can be created only for Stock Entry with both From and To Warehouse.")

    waybill = frappe.new_doc("Waybill")

    waybill.date = doc.posting_date
    waybill.from_warehouse = doc.from_warehouse
    waybill.to_warehouse = doc.to_warehouse
    waybill.delivery_order_no = doc.name
    waybill.authorized_by = doc.owner

    for it in doc.items:
        waybill.append("items", {
            "item_code": it.item_code,
            "qty": it.qty,
            "uom": it.uom,
            "rate": it.basic_rate or 0,
            "amount": it.amount or 0
        })

    waybill.insert(ignore_permissions=True)
    waybill.submit()

    return waybill.name
