import frappe
from frappe import _
from frappe.utils import flt
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.stock_ledger import make_sl_entries
import erpnext.stock.serial_batch_bundle as sbb
import erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry as sle_module

_SKIP_SERIAL_BATCH_VOUCHERS = {"Production Order", "Waybill Return", "Waybill", "Adjustment"}

if not getattr(sle_module.StockLedgerEntry, "_is_manakshia_patched", False):
	_original_on_submit = sle_module.StockLedgerEntry.on_submit

	def _patched_on_submit(self):
		if self.voucher_type in _SKIP_SERIAL_BATCH_VOUCHERS:
			# Skip serial/batch bundle processing for custom voucher types.
			# These doctypes track materials via packing slip, not ERPNext serial nos.
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
		if self.sle.voucher_type == "Waybill Return":
			return "Waybill Item"
		if self.sle.voucher_type == "Adjustment":
			return "Adjustment Item"
		return _original_child_doctype.fget(self)

	sbb.SerialBatchBundle.child_doctype = _custom_child_doctype
	sbb.SerialBatchBundle._is_manakshia_patched = True


class WaybillReturn(StockController):
	def set_incoming_rate(self):
		pass

	def is_internal_transfer(self):
		return False

	def set_total_in_words(self):
		pass

	def calculate_taxes_and_totals(self):
		pass

	def validate(self):
		self.set_company()
		self.set_child_stock_fields()
		self.set_exchange_rate()
		# Deliberately skip super().validate() — ERPNext's accounts_controller
		# calls validate_return() which requires a 'return_against' field
		# that does not exist on this custom doctype.

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
			self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
		if not getattr(self, "conversion_rate", None) or self.conversion_rate == 0:
			self.conversion_rate = 1.0

	def set_company(self):
		if not self.get("company"):
			self.company = frappe.db.get_default("company") or frappe.defaults.get_user_default("Company")
			if not self.company:
				companies = frappe.get_all("Company", limit=1)
				if companies:
					self.company = companies[0].name

	def on_submit(self):
		self.set_company()
		self.update_stock_ledger()

	def on_cancel(self):
		self.set_company()
		self.ignore_linked_doctypes = ("Stock Ledger Entry",)
		self.update_stock_ledger()

	def update_stock_ledger(self):
		sl_entries = self.get_sl_entries()
		if sl_entries:
			make_sl_entries(sl_entries)

	def get_sl_entries(self):
		# Waybill (like Purchase Receipt) stocks IN to to_warehouse.
		# Waybill Return reverses that: stock OUT from to_warehouse (negative qty).
		if not self.to_warehouse:
			frappe.throw(_("To Warehouse is required to process stock return."))

		is_cancelled = self.docstatus == 2
		# Waybill Return = negative qty (stock going OUT)
		# Cancel of Waybill Return = positive qty (reverting the return)
		qty_multiplier = 1 if is_cancelled else -1

		sl_entries = []
		for item in self.get("items"):
			if not item.item_code:
				continue

			actual_qty = flt(item.qty) * qty_multiplier

			sl_entries.append(
				frappe._dict({
					"item_code": item.item_code,
					"warehouse": self.to_warehouse,
					"qty": actual_qty,
					"actual_qty": actual_qty,
					"incoming_rate": flt(item.get("rate")),
					"company": self.company,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"voucher_detail_no": item.name,
					"posting_date": self.get("date") or frappe.utils.today(),
					"posting_time": frappe.utils.nowtime(),
					"is_cancelled": 1 if is_cancelled else 0,
					"allow_negative_stock": 1,
				})
			)
		return sl_entries