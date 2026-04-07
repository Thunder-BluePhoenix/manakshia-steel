import frappe
from frappe.model.document import Document
from frappe.utils import flt

class Waybill(Document):
    def validate(self):
        if not self.items:
            frappe.throw("At least one Item must be added in the Items table.")

        for item in self.items:
            if not item.item_code:
                frappe.throw("Item Code is mandatory for all rows in the Items table.")
            if flt(item.qty) <= 0:
                frappe.throw(f"Quantity must be greater than zero for Item {item.item_code}")
            
            # Auto-calculate amount server-side for consistency
            item.amount = flt(item.qty) * flt(item.rate)
            
        # Calculate Total Quantity
        self.total_quantity = sum([flt(d.qty) for d in self.items])
        
        # Calculate Weighbridge weights if provided
        if self.w_bridge_loaded_wt or self.w_bridge_empty_wt:
            self.w_bridge_wt = flt(self.w_bridge_loaded_wt) - flt(self.w_bridge_empty_wt)
