import frappe
from frappe import _

@frappe.whitelist()
def create_from_source(doctype, docname):
    """Main router. Creates Waybill based on source document type."""
    doc = frappe.get_doc(doctype, docname)

    # Prevent duplicate
    # Check if a Waybill already claims this document as its source
    # We check if there's an existing Waybill with this delivery_order_no (linked field)
    existing = frappe.db.exists("Waybill", {"delivery_order_no": doc.name})
    if existing:
        frappe.throw(f"Waybill already exists: {existing}")

    # Route creation based on doctype
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
    
    # Header fields
    # "customer_name" field options is "Supplier" in the new Waybill DocType
    waybill.customer_name = doc.supplier
    
    # Try to fetch address
    if doc.get("supplier_address"):
         waybill.customer_address = get_address_display(doc.supplier_address)

    waybill.buyers_order_no = doc.supplier_delivery_note # or purchase_order?
    
    # Sales Order No - Not applicable for PR usually, but check Items
    # waybill.sales_order_no = ...
    
    waybill.date = doc.posting_date

    # Warehouse
    # PR items usually go TO a warehouse
    if doc.items:
        waybill.to_warehouse = doc.items[0].warehouse

    waybill.delivery_order_no = doc.name
    # waybill.authorized_by = doc.owner # Owner is email, field might be data. Keep it for now.

    vehicle_no = get_vehicle_no(doc)
    if vehicle_no:
        waybill.vehicle_no = vehicle_no
    
    waybill.grand_total = doc.grand_total

    # Items
    populate_items(waybill, doc.items)
    
    # Packing Slip
    populate_packing_slip(waybill, doc)

    waybill.insert(ignore_permissions=True)
    
    # Link back to source
    set_waybill_link(doc, waybill.name)
    
    return waybill

def create_from_stock_entry(doc):
    # ... (existing logic) ...
    if not doc.from_warehouse and not doc.to_warehouse:
         if doc.items:
             if not doc.from_warehouse: doc.from_warehouse = doc.items[0].s_warehouse
             if not doc.to_warehouse: doc.to_warehouse = doc.items[0].t_warehouse

    waybill = frappe.new_doc("Waybill")
    waybill.date = doc.posting_date
    waybill.from_warehouse = doc.from_warehouse
    waybill.to_warehouse = doc.to_warehouse
    waybill.delivery_order_no = doc.name
    
    if doc.get("custom_vehicle_no"):
        waybill.vehicle_no = doc.custom_vehicle_no
    
    # Stock Entry total value
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
        frappe.db.set_value(source_doc.doctype, source_doc.name, "custom_waybill", waybill_name)

# ... (existing helpers) ...


def get_vehicle_no(doc):
    """Try to fetch vehicle number from common fields."""
    return doc.get("vehicle_no") or doc.get("custom_vehicle_no") or doc.get("vehicle_number")

# =====================================================================
#  HELPERS
# =====================================================================

def get_address_display(address_name):
    """Get formatted address display as plain text."""
    if not address_name:
        return None
    
    # Use Frappe's built-in address formatting
    from frappe.contacts.doctype.address.address import get_address_display as frappe_get_address_display
    
    try:
        # Get HTML formatted address
        html_address = frappe_get_address_display(frappe.get_doc("Address", address_name).as_dict())
        
        # Convert HTML <br> tags to newlines for plain text display
        if html_address:
            plain_address = html_address.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
            return plain_address
        
        return address_name
    except Exception:
        # Fallback to just the address name if formatting fails
        return address_name

def populate_items(waybill, items, is_stock_entry=False):
    for it in items:
        # Stock Entry items don't have 'rate' sometimes, generic logic
        row = {
            "item_code": it.item_code,
            "description": it.description if it.get("description") else it.item_name,
            "quantity": it.qty,
            "uom": it.uom,
            "rate": it.get("rate", 0),
            "amount": it.get("amount", 0)
        }
        waybill.append("items", row)

def populate_packing_slip(waybill, source_doc):
    # Check if source has a table named 'custom_packing_slip' or similar
    # Using 'custom_packing_slip' as per likely custom field
    
    packing_table = getattr(source_doc, "custom_packing_slip", None)
    
    if not packing_table:
        # Try finding standard Packing Slip docs linked to this?
        # Standard Frappe "Packing Slip" is a separate DocType linked to DN.
        # But User has "Packing Slip Child" table.
        # Maybe they have a custom table on the source doc correctly named.
        # We will assume "custom_packing_slip" for now.
        return

    for row in packing_table:
        # Map fields 1:1 if they match
        ps_row = {}
        fields = ["coil_number", "grade_specification", "batch_no", 
                  "thickness", "width", "weight", "confirmed_weight"]
        
        has_data = False
        for field in fields:
            val = getattr(row, field, None)
            if val:
                ps_row[field] = val
                has_data = True
        
        if has_data:
            waybill.append("packing_slip", ps_row)
