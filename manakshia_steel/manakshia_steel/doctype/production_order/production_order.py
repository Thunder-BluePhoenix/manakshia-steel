# Copyright (c) 2026, Blue Phoenix and contributors
# For license information, please see license.txt

import erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry as sle_module
import erpnext.stock.serial_batch_bundle as sbb
import frappe
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.stock_ledger import make_sl_entries
from frappe import _
from frappe.utils import flt

_SKIP_SERIAL_BATCH_VOUCHERS = {
    "Production Order",
    "Waybill Return",
    "Waybill",
    "Adjustment",
}

if not getattr(sle_module.StockLedgerEntry, "_is_manakshia_patched", False):
    _original_on_submit = sle_module.StockLedgerEntry.on_submit

    def _patched_on_submit(self):
        if self.voucher_type in _SKIP_SERIAL_BATCH_VOUCHERS:
            # Skip serial/batch bundle processing for custom voucher types.
            # These doctypes track materials via packing slip, not ERPNext serial nos.
            from erpnext.stock.stock_ledger import update_entries_after

            update_entries_after(
                {
                    "item_code": self.item_code,
                    "warehouse": self.warehouse,
                    "posting_date": self.posting_date,
                    "posting_time": self.posting_time,
                    "creation": self.creation,
                    "via_landed_cost_voucher": False,
                }
            )
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


class ProductionOrder(StockController):
    def set_incoming_rate(self):
        pass

    def is_internal_transfer(self):
        return True

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
                item.stock_uom = item.uom or frappe.db.get_value(
                    "Item", item.item_code, "stock_uom"
                )
            if not item.conversion_factor:
                item.conversion_factor = 1.0
            if not item.stock_qty:
                item.stock_qty = flt(item.qty) * flt(item.conversion_factor)

    def set_exchange_rate(self):
        if not getattr(self, "currency", None):
            self.currency = frappe.get_cached_value(
                "Company", self.company, "default_currency"
            )
        if not getattr(self, "conversion_rate", None) or self.conversion_rate == 0:
            self.conversion_rate = 1.0

    def set_company(self):
        if not self.get("company"):
            self.company = frappe.db.get_default(
                "company"
            ) or frappe.defaults.get_user_default("Company")
            if not self.company:
                companies = frappe.get_all("Company", limit=1)
                if companies:
                    self.company = companies[0].name

    def on_submit(self):
        self.set_company()
        self.update_stock_ledger()
        self.make_gl_entries()

    def on_cancel(self):
        self.set_company()
        self.ignore_linked_doctypes = ("Stock Ledger Entry", "GL Entry")
        self.update_stock_ledger()
        self.make_gl_entries_on_cancel()

    def update_stock_ledger(self):
        sl_entries = self.get_sl_entries()
        if sl_entries:
            make_sl_entries(sl_entries)

    def get_sl_entries(self):
        if not self.source_warehouse or not self.target_warehouse:
            frappe.throw(
                _(
                    "Source and Target Warehouse are both required to process material transfer."
                )
            )

        is_cancelled = self.docstatus == 2

        sl_entries = []
        for item in self.get("items"):
            if not item.item_code:
                continue

            # 1. Outward from Source Warehouse
            sl_entries.append(
                frappe._dict(
                    {
                        "item_code": item.item_code,
                        "warehouse": self.source_warehouse,
                        "qty": -1 * flt(item.qty),
                        "actual_qty": -1 * flt(item.qty),
                        "incoming_rate": 0.0,
                        "company": self.company,
                        "voucher_type": self.doctype,
                        "voucher_no": self.name,
                        "voucher_detail_no": item.name,
                        "posting_date": self.get("date") or frappe.utils.today(),
                        "posting_time": frappe.utils.nowtime(),
                        "is_cancelled": 1 if is_cancelled else 0,
                        "allow_negative_stock": 1,
                        # Skip serial/batch bundle processing — items are tracked
                        # by coil/packing slip in this app, not ERPNext serial nos.
                        "has_serial_no": 0,
                        "has_batch_no": 0,
                    }
                )
            )

            # 2. Inward to Target Warehouse
            sl_entries.append(
                frappe._dict(
                    {
                        "item_code": item.item_code,
                        "warehouse": self.target_warehouse,
                        "qty": flt(item.qty),
                        "actual_qty": flt(item.qty),
                        "incoming_rate": flt(item.get("rate") or 0.0),
                        "company": self.company,
                        "voucher_type": self.doctype,
                        "voucher_no": self.name,
                        "voucher_detail_no": item.name,
                        "posting_date": self.get("date") or frappe.utils.today(),
                        "posting_time": frappe.utils.nowtime(),
                        "is_cancelled": 1 if is_cancelled else 0,
                        "allow_negative_stock": 1,
                        # Skip serial/batch bundle processing
                        "has_serial_no": 0,
                        "has_batch_no": 0,
                    }
                )
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

        inventory_account_map = self.get_inventory_account_map()

        for item in self.get("items"):
            if not item.item_code:
                continue

            source_account = self.get_inventory_account_dict(
                frappe._dict(
                    {"item_code": item.item_code, "warehouse": self.source_warehouse}
                ),
                inventory_account_map,
                warehouse_field="warehouse",
            ).get("account")

            target_account = self.get_inventory_account_dict(
                frappe._dict(
                    {"item_code": item.item_code, "warehouse": self.target_warehouse}
                ),
                inventory_account_map,
                warehouse_field="warehouse",
            ).get("account")

            if not source_account:
                frappe.throw(
                    _("Inventory account not found for source warehouse {0}").format(
                        self.source_warehouse
                    )
                )
            if not target_account:
                frappe.throw(
                    _("Inventory account not found for target warehouse {0}").format(
                        self.target_warehouse
                    )
                )

            amount = flt(item.qty) * flt(
                item.get("rate")
                or frappe.db.get_value("Item", item.item_code, "valuation_rate")
                or 0.0
            )

            if amount and source_account != target_account:
                # Debit target account
                gl_entries.append(
                    self.get_gl_dict(
                        {
                            "account": target_account,
                            "against": source_account,
                            "cost_center": frappe.get_cached_value(
                                "Company", self.company, "cost_center"
                            ),
                            "remarks": self.get("remarks")
                            or _("Accounting Entry for Production Order Transfer"),
                            "debit": amount,
                            "debit_in_account_currency": amount,
                        },
                        item=item,
                    )
                )

                # Credit source account
                gl_entries.append(
                    self.get_gl_dict(
                        {
                            "account": source_account,
                            "against": target_account,
                            "cost_center": frappe.get_cached_value(
                                "Company", self.company, "cost_center"
                            ),
                            "remarks": self.get("remarks")
                            or _("Accounting Entry for Production Order Transfer"),
                            "credit": amount,
                            "credit_in_account_currency": amount,
                        },
                        item=item,
                    )
                )

        return gl_entries
