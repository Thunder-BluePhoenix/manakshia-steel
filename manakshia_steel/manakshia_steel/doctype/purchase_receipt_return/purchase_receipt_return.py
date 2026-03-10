# Copyright (c) 2026, Blue Phoenix and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PurchaseReceiptReturn(Document):
	def on_submit(self):
		self.make_material_issue()

	def on_cancel(self):
		self.cancel_material_issue()

	def make_material_issue(self):
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Issue"
		se.purpose = "Material Issue"
		se.company = self.company
		se.posting_date = self.posting_date
		se.posting_time = self.posting_time
		
		# For Material Issue, Stock Entry requires Source Warehouse (s_warehouse)
		for item in self.get("items"):
			if not item.item_code:
				continue
			se.append("items", {
				"item_code": item.item_code,
				"qty": item.qty,
				"uom": item.uom,
				"stock_uom": item.stock_uom,
				"conversion_factor": item.conversion_factor,
				"s_warehouse": item.warehouse or getattr(item, 'rejected_warehouse', None) or getattr(self, 'set_warehouse', None) or getattr(self, 'rejected_warehouse', None),
				"cost_center": getattr(item, 'cost_center', getattr(self, 'cost_center', None)),
			})
			
		if se.get("items"):
			se.set_stock_entry_type()
			se.insert()
			se.submit()
			self.db_set("return_stock_entry", se.name)

	def cancel_material_issue(self):
		if self.return_stock_entry:
			se = frappe.get_doc("Stock Entry", self.return_stock_entry)
			if se.docstatus == 1:
				se.cancel()
