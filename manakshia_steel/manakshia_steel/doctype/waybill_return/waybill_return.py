import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class WaybillReturn(Document):
	def on_submit(self):
		self.create_material_receipt()

	def create_material_receipt(self):
		"""Automatically create a Stock Entry for Material Receipt (Waybill Return)."""
		se = make_stock_entry(self.name)
		se.flags.ignore_permissions = True
		
		if not se.get("items"):
			frappe.throw("Cannot create Material Receipt because the Waybill Return has no items.")
			
		se.insert()
		
		frappe.msgprint(
			f"Material Receipt <b><a href='/app/stock-entry/{se.name}'>{se.name}</a></b> "
			"has been automatically created.", 
			alert=True, 
			indicator="green"
		)


@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.stock_entry_type = "Waybill Return"
		target.purpose = "Material Receipt"
		target.custom_waybill_return = source.name
		target.custom_process = source.custom_process
		
		# Set company if available
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
			target.t_warehouse = source_parent.to_warehouse

	doclist = get_mapped_doc(
		"Waybill Return",
		source_name,
		{
			"Waybill Return": {
				"doctype": "Stock Entry",
			},
			"Waybill Item": {
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

