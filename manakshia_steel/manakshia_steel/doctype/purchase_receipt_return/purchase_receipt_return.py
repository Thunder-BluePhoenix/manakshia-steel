# Copyright (c) 2026, Blue Phoenix and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.stock_ledger import make_sl_entries
import erpnext.stock.serial_batch_bundle as sbb

if not getattr(sbb.SerialBatchBundle, "_is_manakshia_patched", False):
	_original_child_doctype = sbb.SerialBatchBundle.child_doctype

	@property
	def _custom_child_doctype(self):
		if self.sle.voucher_type == "Purchase Receipt Return":
			return "Purchase Receipt Item"
		if self.sle.voucher_type == "Waybill Return":
			return "Waybill Item"
		if self.sle.voucher_type == "Production Order":
			return "Production Order Item"
		if self.sle.voucher_type == "Adjustment":
			return "Adjustment Item"
		return _original_child_doctype.fget(self)

	sbb.SerialBatchBundle.child_doctype = _custom_child_doctype
	sbb.SerialBatchBundle._is_manakshia_patched = True


class PurchaseReceiptReturn(StockController):
	def set_incoming_rate(self):
		pass

	def is_internal_transfer(self):
		return False

	def set_total_in_words(self):
		pass

	def validate(self):
		self.set_company()
		self.set_child_stock_fields()
		super().validate()
		self.set_exchange_rate()
		self.validate_warehouses()

	def set_child_stock_fields(self):
		for item in self.get("items"):
			if not item.stock_uom:
				item.stock_uom = item.uom or frappe.db.get_value("Item", item.item_code, "stock_uom")
			if not item.conversion_factor:
				item.conversion_factor = 1.0
			if not item.stock_qty:
				item.stock_qty = flt(item.qty) * flt(item.conversion_factor)

	def set_exchange_rate(self):
		if not getattr(self, "currency", None):
			self.currency = frappe.get_cached_value('Company', self.company, 'default_currency')
		if not getattr(self, "conversion_rate", None) or self.conversion_rate == 0:
			self.conversion_rate = 1.0

	def set_company(self):
		if not self.get("company"):
			self.company = frappe.db.get_default("company") or frappe.defaults.get_user_default("Company")
			if not self.company:
				companies = frappe.get_all("Company", limit=1)
				if companies:
					self.company = companies[0].name
			
	def validate_warehouses(self):
		"""Ensure at least one item has a source warehouse set."""
		items_without_warehouse = []
		for item in self.get("items"):
			if not item.item_code:
				continue
			warehouse = (
				item.warehouse
				or getattr(item, "rejected_warehouse", None)
				or getattr(self, "set_warehouse", None)
				or getattr(self, "rejected_warehouse", None)
			)
			if not warehouse:
				items_without_warehouse.append(item.item_code)

		if items_without_warehouse and len(items_without_warehouse) == len(
			[i for i in self.get("items") if i.item_code]
		):
			frappe.throw(
				_(
					"Please set a Warehouse for at least one item before submitting. "
					"Items missing warehouse: {0}"
				).format(", ".join(items_without_warehouse))
			)

	def on_submit(self):
		self.set_company()
		self.update_stock_ledger()
		self.make_gl_entries()

	def on_cancel(self):
		self.set_company()
		self.ignore_linked_doctypes = ('Stock Ledger Entry', 'GL Entry')
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()

	def update_stock_ledger(self):
		sl_entries = self.get_sl_entries()
		if sl_entries:
			make_sl_entries(sl_entries)

	def get_sl_entries(self):
		sl_entries = []
		for item in self.get("items"):
			if not item.item_code:
				continue

			source_warehouse = (
				item.warehouse
				or getattr(item, "rejected_warehouse", None)
				or getattr(self, "set_warehouse", None)
				or getattr(self, "rejected_warehouse", None)
			)

			if not source_warehouse:
				continue
			
			qty = -1 * abs(item.qty)
			
			sl_entries.append(
				frappe._dict({
					"item_code": item.item_code,
					"warehouse": source_warehouse,
					"qty": qty,
					"actual_qty": qty,
					"company": self.company,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"voucher_detail_no": item.name,
					"posting_date": self.get("posting_date") or self.get("date") or frappe.utils.today(),
					"posting_time": self.get("posting_time") or frappe.utils.nowtime(),
					"is_cancelled": 1 if self.docstatus == 2 else 0,
					"serial_and_batch_bundle": getattr(item, "serial_and_batch_bundle", None),
					"dependant_sle_voucher_detail_no": item.name
				})
			)
			
			# Re-link Serial and Batch bundles natively to this doc if not cancelled
			if getattr(item, "serial_and_batch_bundle", None) and self.docstatus == 1:
				frappe.db.set_value(
					"Serial and Batch Bundle",
					item.serial_and_batch_bundle,
					{"voucher_type": self.doctype, "voucher_no": self.name, "voucher_detail_no": item.name}
				)

		return sl_entries

	def make_gl_entries(self):
		import erpnext
		if not frappe.utils.cint(erpnext.is_perpetual_inventory_enabled(self.company)):
			return

		gl_entries = self.get_custom_gl_entries()
		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries
			make_gl_entries(gl_entries)

	def make_gl_entries_on_cancel(self):
		import erpnext
		if not frappe.utils.cint(erpnext.is_perpetual_inventory_enabled(self.company)):
			return

		from erpnext.accounts.general_ledger import make_reverse_gl_entries
		make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

	def get_custom_gl_entries(self):
		gl_entries = []
		
		# For a return, we credit the warehouse and debit the expense/clearing account
		difference_account = frappe.get_cached_value('Company', self.company, 'default_expense_account')
		if not difference_account:
			frappe.throw(_("Please define a Default Expense Account in the Company master to process accounting entries for Purchase Receipt Return."))

		inventory_account_map = self.get_inventory_account_map()
		
		for item in self.get("items"):
			if not item.item_code:
				continue
				
			source_warehouse = (
				item.warehouse
				or getattr(item, "rejected_warehouse", None)
				or getattr(self, "set_warehouse", None)
				or getattr(self, "rejected_warehouse", None)
			)

			if not source_warehouse:
				continue
				
			warehouse_account = self.get_inventory_account_dict(
				frappe._dict({"item_code": item.item_code, "warehouse": source_warehouse}), 
				inventory_account_map, 
				warehouse_field="warehouse"
			).get("account")
			
			if not warehouse_account:
				frappe.throw(_("Inventory account not found for warehouse {0}").format(source_warehouse))
			
			amount = flt(abs(item.qty)) * flt(item.get("rate") or frappe.db.get_value("Item", item.item_code, "valuation_rate") or 0.0)
			
			if amount:
				# Debit the difference/expense account
				gl_entries.append(
					self.get_gl_dict({
						"account": difference_account,
						"against": warehouse_account,
						"cost_center": getattr(item, "cost_center", None) or getattr(self, "cost_center", None) or frappe.get_cached_value('Company', self.company, 'cost_center'),
						"remarks": getattr(self, "remarks", None) or _("Accounting Entry for Purchase Receipt Return"),
						"debit": amount,
						"debit_in_account_currency": amount
					}, item=item)
				)

				# Credit the source warehouse account
				gl_entries.append(
					self.get_gl_dict({
						"account": warehouse_account,
						"against": difference_account,
						"cost_center": getattr(item, "cost_center", None) or getattr(self, "cost_center", None) or frappe.get_cached_value('Company', self.company, 'cost_center'),
						"remarks": getattr(self, "remarks", None) or _("Accounting Entry for Purchase Receipt Return"),
						"credit": amount,
						"credit_in_account_currency": amount
					}, item=item)
				)

		return gl_entries
