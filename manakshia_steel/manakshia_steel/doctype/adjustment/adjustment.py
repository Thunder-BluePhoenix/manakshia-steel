# Copyright (c) 2026, Blue Phoenix and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, nowdate, nowtime
from frappe.model.naming import make_autoname

from erpnext.controllers.stock_controller import StockController
from erpnext.stock.stock_ledger import make_sl_entries
import erpnext.stock.serial_batch_bundle as sbb
import erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry as sle_module

_SKIP_SERIAL_BATCH_VOUCHERS = {"Production Order", "Waybill Return", "Waybill", "Adjustment"}

if not getattr(sle_module.StockLedgerEntry, "_is_manakshia_patched", False):
	_original_on_submit = sle_module.StockLedgerEntry.on_submit

	def _patched_on_submit(self):
		if self.voucher_type in _SKIP_SERIAL_BATCH_VOUCHERS:
			from erpnext.stock.stock_ledger import update_entries_after
			update_entries_after({
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"creation": self.creation,
				"via_landed_cost_voucher": False,
			})
			return
		_original_on_submit(self)

	sle_module.StockLedgerEntry.on_submit = _patched_on_submit
	sle_module.StockLedgerEntry._is_manakshia_patched = True

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


class Adjustment(StockController):
	def autoname(self):
		if not self.adjustment_type:
			frappe.throw(_("Adjustment Type is required"))

		if self.adjustment_type == "GENERAL ADJUSTMENT":
			self.adjustment_type_code = "GN"
		elif self.adjustment_type == "PHYSICAL STOCK ADJUSTMENT":
			self.adjustment_type_code = "PH"
		elif self.adjustment_type == "YEARLY STOCK ADJUSTMENT":
			self.adjustment_type_code = "YR"
		else:
			frappe.throw(_("Invalid Adjustment Type: {0}").format(self.adjustment_type))
		
		# Now that adjustment_type_code is set, the Expression autoname 'format:{adjustment_type_code}.####' will work if defined in Doctypes.
		# However, if it's evaluated differently, we can just set it ourselves.
		self.name = make_autoname(f"{self.adjustment_type_code}.####")

	def validate(self):
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company")
		
		if not self.posting_date:
			self.posting_date = nowdate()

		self.validate_items()

	def validate_items(self):
		for item in self.get("items"):
			if not item.item_code:
				frappe.throw(_("Item Code is mandatory in row {0}").format(item.idx))
			if not item.warehouse:
				frappe.throw(_("Warehouse is mandatory for Item {0} in row {1}").format(item.item_code, item.idx))
			if not item.type:
				frappe.throw(_("Type (Receive/Issue) is mandatory for Item {0} in row {1}").format(item.item_code, item.idx))
			
			if flt(item.qty) <= 0:
				frappe.throw(_("Quantity must be greater than zero for Item {0} in row {1}").format(item.item_code, item.idx))
				
			# Calculate Amount
			item.amount = flt(item.qty) * flt(item.rate)

	def on_submit(self):
		self.update_stock_ledger()

	def on_cancel(self):
		self.ignore_linked_doctypes = ('Stock Ledger Entry', 'GL Entry')
		self.update_stock_ledger()

	def update_stock_ledger(self):
		sl_entries = self.get_sl_entries()
		if sl_entries:
			make_sl_entries(sl_entries)

	def get_sl_entries(self):
		sl_entries = []
		for item in self.get("items"):
			if not item.item_code or not item.warehouse:
				continue
			
			# Determine positive or negative qty
			if item.type == 'Receive':
				qty = abs(flt(item.qty))
			else:
				qty = -1 * abs(flt(item.qty))

			sl_entries.append(
				frappe._dict({
					"item_code": item.item_code,
					"warehouse": item.warehouse,
					"qty": qty,
					"actual_qty": qty,
					"company": self.company,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"voucher_detail_no": item.name,
					"posting_date": self.posting_date or nowdate(),
					"posting_time": self.get("posting_time") or nowtime(),
					"is_cancelled": 1 if self.docstatus == 2 else 0,
					"has_serial_no": 0,
					"has_batch_no": 0
				})
			)
		
		return sl_entries
