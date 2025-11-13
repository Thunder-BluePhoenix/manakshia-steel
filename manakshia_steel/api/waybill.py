import frappe

@frappe.whitelist()
def create_from_source(doctype, docname):
    """Main router. Creates Waybill based on source document type."""
    doc = frappe.get_doc(doctype, docname)

    # Prevent duplicate
    if doc.get("custom_waybill"):
        frappe.throw(f"Waybill already exists: {doc.custom_waybill}")

    # Route creation based on doctype
    if doctype == "Purchase Receipt":
        waybill_name = create_from_purchase_receipt(doc)

    elif doctype == "Stock Entry":
        waybill_name = create_from_stock_entry(doc)

    elif doctype == "Delivery Note":
        waybill_name = create_from_delivery_note(doc)

    else:
        frappe.throw("Waybill creation not supported for: " + doctype)

    return waybill_name



# =====================================================================
#  PURCHASE RECEIPT → WAYBILL
# =====================================================================
def create_from_purchase_receipt(doc):
    waybill = frappe.new_doc("Waybill")

    # Header fields
    waybill.customer_name = doc.supplier
    waybill.customer_address = doc.supplier_address
    waybill.buyers_order_no = doc.purchase_order
    waybill.sales_order_no = doc.purchase_order
    waybill.date = doc.posting_date

    # Warehouse
    if doc.items:
        waybill.to_warehouse = doc.items[0].warehouse

    waybill.delivery_order_no = doc.name
    waybill.authorized_by = doc.owner

    # Items
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



# =====================================================================
#  STOCK ENTRY → WAYBILL
# =====================================================================
def create_from_stock_entry(doc):

    # Must be warehouse movement
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



# =====================================================================
#  DELIVERY NOTE → WAYBILL
# =====================================================================
def create_from_delivery_note(doc):
    waybill = frappe.new_doc("Waybill")

    waybill.customer_name = doc.customer
    waybill.customer_address = doc.customer_address
    waybill.buyers_order_no = doc.po_no
    waybill.sales_order_no = doc.sales_order
    waybill.date = doc.posting_date

    if doc.items:
        waybill.from_warehouse = doc.items[0].warehouse

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
