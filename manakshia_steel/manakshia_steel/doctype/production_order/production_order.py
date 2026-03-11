# Copyright (c) 2026, Blue Phoenix and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class ProductionOrder(Document):
	def on_submit(self):
		self.create_material_transfer()

	def create_material_transfer(self):
		"""Automatically create a Stock Entry for Material Transfer for Manufacture."""
		se = make_stock_entry(self.name)
		se.flags.ignore_permissions = True
		
		# Validate that there's at least one item to transfer
		if not se.get("items"):
			frappe.throw("Cannot create Material Transfer because the Production Order has no items.")
			
		# Insert the Stock Entry (Draft mode so users can verify warehouse logic if needed, 
		# or submit it directly if preferred, but usually Draft is safer for manual Warehouse entry)
		se.insert()
		
		frappe.msgprint(
			f"Material Transfer <b><a href='/app/stock-entry/{se.name}'>{se.name}</a></b> "
			"has been automatically created.", 
			alert=True, 
			indicator="green"
		)


@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.stock_entry_type = "Production Order"
		target.purpose = "Material Transfer for Manufacture"
		target.custom_production_order_no = source.name
		target.custom_production_order_date = source.date
		target.custom_process = source.custom_process
		
		# Set company if available from user defaults or first company
		company = frappe.defaults.get_user_default("Company")
		if not company:
			companies = frappe.get_all("Company", limit=1)
			if companies:
				company = companies[0].name
		target.company = company

	def update_item(source, target, source_parent):
		target.qty = source.quantity
		target.conversion_factor = 1
		if source_parent:
			target.s_warehouse = source_parent.source_warehouse
			target.t_warehouse = source_parent.target_warehouse

	doclist = get_mapped_doc(
		"Production Order",
		source_name,
		{
			"Production Order": {
				"doctype": "Stock Entry",
			},
			"Production Order Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"item_code": "item_code",
					"uom": "uom",
					"quantity": "qty",
				},
				"postprocess": update_item,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist
