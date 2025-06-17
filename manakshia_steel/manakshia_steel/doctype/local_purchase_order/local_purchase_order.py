# local_purchase_order.py
# Server-side Python code for Local Purchase Order

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint

class LocalPurchaseOrder(Document):
    def validate(self):
        """Validate the document before saving"""
        self.calculate_totals()
        self.validate_items()
    
    def before_save(self):
        """Execute before saving the document"""
        self.calculate_totals()
    
    def calculate_totals(self):
        """Calculate all totals for the purchase order"""
        # Calculate item totals first
        self.calculate_item_totals()
        
        # Calculate net total
        self.calculate_net_total()
        
        # Calculate grand total
        self.calculate_grand_total()
    
    def calculate_item_totals(self):
        """Calculate total cost for each item"""
        for item in self.items:
            qty = flt(item.qty)
            unit_cost = flt(item.unit_cost)
            item.total_cost = qty * unit_cost
    
    def calculate_net_total(self):
        """Calculate net total from all items"""
        net_total = 0
        for item in self.items:
            net_total += flt(item.total_cost)
        
        self.net_total = net_total
    
    def calculate_grand_total(self):
        """Calculate grand total including discount and shipping"""
        net_total = flt(self.net_total)
        discount_percentage = flt(self.discount_percentage)
        shipping = flt(self.shipping)
        
        # Calculate discount amount
        discount_amount = (net_total * discount_percentage) / 100
        
        # Calculate total after discount
        total_after_discount = net_total - discount_amount
        
        # Add shipping to get grand total
        self.grand_total = total_after_discount + shipping
    
    def validate_items(self):
        """Validate items in the purchase order"""
        if not self.items:
            frappe.throw(_("Please add at least one item"))
        
        for item in self.items:
            if not item.unit:
                frappe.throw(_("Row {0}: Item is required").format(item.idx))
            
            if flt(item.qty) <= 0:
                frappe.throw(_("Row {0}: Quantity must be greater than 0").format(item.idx))
            
            if flt(item.unit_cost) < 0:
                frappe.throw(_("Row {0}: Unit Cost cannot be negative").format(item.idx))

# Hooks for the Items child table
@frappe.whitelist()
def get_item_details(item_code):
    """Get item details when item is selected"""
    if not item_code:
        return {}
    
    item = frappe.get_doc("Item", item_code)
    
    return {
        "description": item.description or "",
        "unit_cost": item.standard_rate or 0
    }

# Custom method to recalculate totals (can be called from client)
@frappe.whitelist()
def calculate_purchase_order_totals(doc_name):
    """Calculate totals for a purchase order"""
    doc = frappe.get_doc("Local Purchase Order", doc_name)
    doc.calculate_totals()
    doc.save()
    return doc

# Workflow methods (if you want to add approval workflow)
def on_submit(doc, method):
    """Execute when document is submitted"""
    # Add any submission logic here
    pass

def on_cancel(doc, method):
    """Execute when document is cancelled"""
    # Add any cancellation logic here
    pass
