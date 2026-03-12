import frappe
from frappe.utils import flt


@frappe.whitelist()
def create_from_source(doctype, docname):
    """Main router. Creates Waybill based on source document type."""
    doc = frappe.get_doc(doctype, docname)

    existing = frappe.db.exists("Waybill", {"delivery_order_no": doc.name})
    if existing:
        frappe.throw(f"Waybill already exists: {existing}")

    if doctype == "Purchase Receipt":
        waybill = create_from_purchase_receipt(doc)
    elif doctype == "Stock Entry":
        waybill = create_from_stock_entry(doc)
    elif doctype == "Delivery Note":
        waybill = create_from_delivery_note(doc)
    else:
        frappe.throw("Waybill creation not supported for: " + doctype)

    return waybill.name


# =====================================================================
#  PURCHASE RECEIPT → WAYBILL
# =====================================================================
def create_from_purchase_receipt(doc):
    waybill = frappe.new_doc("Waybill")
    waybill.customer_name = doc.supplier

    if doc.get("supplier_address"):
        waybill.customer_address = get_address_display(doc.supplier_address)

    waybill.buyers_order_no = doc.supplier_delivery_note
    waybill.date = doc.posting_date

    if doc.items:
        waybill.to_warehouse = doc.items[0].warehouse

    waybill.delivery_order_no = doc.name

    vehicle_no = get_vehicle_no(doc)
    if vehicle_no:
        waybill.vehicle_no = vehicle_no

    waybill.grand_total = doc.grand_total

    populate_items(waybill, doc.items)
    populate_packing_slip(waybill, doc)

    waybill.insert(ignore_permissions=True)
    set_waybill_link(doc, waybill.name)

    return waybill


def create_from_stock_entry(doc):
    if not doc.from_warehouse and not doc.to_warehouse:
        if doc.items:
            if not doc.from_warehouse:
                doc.from_warehouse = doc.items[0].s_warehouse
            if not doc.to_warehouse:
                doc.to_warehouse = doc.items[0].t_warehouse

    waybill = frappe.new_doc("Waybill")
    waybill.date = doc.posting_date
    waybill.from_warehouse = doc.from_warehouse
    waybill.to_warehouse = doc.to_warehouse
    waybill.delivery_order_no = doc.name

    if doc.get("custom_vehicle_no"):
        waybill.vehicle_no = doc.custom_vehicle_no

    waybill.grand_total = doc.get("total_outgoing_value") or doc.get("total_amount")

    populate_items(waybill, doc.items, is_stock_entry=True)
    populate_packing_slip(waybill, doc)

    waybill.insert(ignore_permissions=True)
    set_waybill_link(doc, waybill.name)

    return waybill


def create_from_delivery_note(doc):
    waybill = frappe.new_doc("Waybill")
    waybill.customer_name = doc.customer

    if doc.get("customer_address"):
        waybill.customer_address = get_address_display(doc.customer_address)

    waybill.buyers_order_no = doc.po_no

    if doc.items and doc.items[0].get("against_sales_order"):
        waybill.sales_order_no = doc.items[0].against_sales_order

    waybill.date = doc.posting_date

    if doc.items:
        waybill.from_warehouse = doc.items[0].warehouse

    waybill.delivery_order_no = doc.name

    vehicle_no = get_vehicle_no(doc)
    if vehicle_no:
        waybill.vehicle_no = vehicle_no

    waybill.grand_total = doc.grand_total

    populate_items(waybill, doc.items)
    populate_packing_slip(waybill, doc)

    waybill.insert(ignore_permissions=True)
    set_waybill_link(doc, waybill.name)

    return waybill


def set_waybill_link(source_doc, waybill_name):
    """Sets the custom_waybill field on source doc if it exists."""
    if source_doc.meta.has_field("custom_waybill"):
        frappe.db.set_value(
            source_doc.doctype, source_doc.name, "custom_waybill", waybill_name
        )


def get_vehicle_no(doc):
    """Try to fetch vehicle number from common fields."""
    return (
        doc.get("vehicle_no")
        or doc.get("custom_vehicle_no")
        or doc.get("vehicle_number")
    )


# =====================================================================
#  HELPERS
# =====================================================================


def get_address_display(address_name):
    """Get formatted address display as plain text."""
    if not address_name:
        return None

    from frappe.contacts.doctype.address.address import (
        get_address_display as frappe_get_address_display,
    )

    try:
        html_address = frappe_get_address_display(
            frappe.get_doc("Address", address_name).as_dict()
        )
        if html_address:
            plain_address = (
                html_address.replace("<br>", "\n")
                .replace("<br/>", "\n")
                .replace("<br />", "\n")
            )
            return plain_address
        return address_name
    except Exception:
        return address_name


def populate_items(waybill, items, is_stock_entry=False):
    """
    Append items from a source document onto the Waybill.

    On a Purchase Receipt, ERPNext stores accepted and rejected quantities as
    separate rows for the same item_code:
      - Accepted row:  has warehouse set,          accepted_qty > 0
      - Rejected row:  has rejected_warehouse set,  accepted_qty = 0, qty > 0

    We only want accepted rows on the Waybill.  The filter is:
      1. accepted_qty > 0  (PR-specific field; falls back to qty for other doctypes)
      2. AND the row must have a normal warehouse (not rejected_warehouse only)

    serial_and_batch_bundle is carried forward so Waybill Return can locate the
    inward bundle without an extra DB query.
    """
    seen_item_warehouse = set()  # extra dedup guard: (item_code, warehouse)

    for it in items:
        # ── Determine effective qty ───────────────────────────────────────────
        if is_stock_entry:
            qty = flt(it.get("qty") or it.get("transfer_qty") or 0)
        else:
            # For Purchase Receipt: prefer accepted_qty; it is 0 on rejected rows
            accepted_qty = flt(it.get("accepted_qty", 0))
            qty = accepted_qty if accepted_qty > 0 else flt(it.get("qty", 0))

        if qty <= 0:
            continue

        # ── Skip rejected-warehouse-only rows ─────────────────────────────────
        # On a PR, rejected rows have no `warehouse` (only `rejected_warehouse`).
        warehouse = it.get("warehouse") or it.get("t_warehouse")
        if not warehouse:
            continue

        # ── Dedup guard: same item + warehouse combo already added ────────────
        key = (it.item_code, warehouse)
        if key in seen_item_warehouse:
            continue
        seen_item_warehouse.add(key)

        conversion_factor = flt(it.get("conversion_factor") or 1.0)
        row = {
            "item_code": it.item_code,
            "description": it.description if it.get("description") else it.item_name,
            "qty": qty,
            "uom": it.uom,
            "stock_uom": it.get("stock_uom") or it.uom,
            "conversion_factor": conversion_factor,
            "stock_qty": qty * conversion_factor,
            "rate": it.get("rate", 0),
            "amount": it.get("amount", 0),
            # Carry inward bundle reference forward for Waybill Return
            "serial_and_batch_bundle": it.get("serial_and_batch_bundle") or None,
        }
        waybill.append("items", row)


def populate_packing_slip(waybill, source_doc):
    packing_table = getattr(source_doc, "custom_packing_slip", None)
    if not packing_table:
        return

    fields = [
        "coil_number",
        "grade_specification",
        "batch_no",
        "thickness",
        "width",
        "weight",
        "confirmed_weight",
    ]

    for row in packing_table:
        ps_row = {}
        has_data = False
        for field in fields:
            val = getattr(row, field, None)
            if val:
                ps_row[field] = val
                has_data = True
        if has_data:
            waybill.append("packing_slip", ps_row)