# Copyright (c) 2026, Blue Phoenix and contributors
# For license information, please see license.txt

import erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry as sle_module
import erpnext.stock.serial_batch_bundle as sbb
import frappe
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.stock_ledger import make_sl_entries
from frappe import _
from frappe.utils import flt

# ─────────────────────────────────────────────────────────────────────────────
#  Monkey-patch 1 – StockLedgerEntry.on_submit
#
#  ERPNext's default on_submit calls SerialBatchBundle() which validates that
#  the bundle is already submitted (docstatus=1).  For our custom voucher types
#  we set docstatus directly via db_set to avoid a timing issue, so we skip
#  ERPNext's bundle re-validation and only update the running stock balance.
# ─────────────────────────────────────────────────────────────────────────────

_SKIP_SERIAL_BATCH_VOUCHERS = {
    "Purchase Receipt Return",
    "Waybill Return",
    "Waybill",
    "Production Order",
    "Adjustment",
}

if not getattr(sle_module.StockLedgerEntry, "_is_manakshia_patched", False):
    _original_sle_on_submit = sle_module.StockLedgerEntry.on_submit

    def _patched_sle_on_submit(self):
        if self.voucher_type in _SKIP_SERIAL_BATCH_VOUCHERS:
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
        _original_sle_on_submit(self)

    sle_module.StockLedgerEntry.on_submit = _patched_sle_on_submit
    sle_module.StockLedgerEntry._is_manakshia_patched = True


# ─────────────────────────────────────────────────────────────────────────────
#  Monkey-patch 2 – SerialBatchBundle.child_doctype
#
#  Maps custom voucher types to the child table ERPNext should read when it
#  needs to inspect serial/batch lines for a given SLE.
# ─────────────────────────────────────────────────────────────────────────────

if not getattr(sbb.SerialBatchBundle, "_is_manakshia_patched", False):
    _original_child_doctype = sbb.SerialBatchBundle.child_doctype

    @property
    def _custom_child_doctype(self):
        mapping = {
            "Purchase Receipt Return": "Purchase Receipt Item",
            "Waybill Return": "Waybill Item",
            "Production Order": "Production Order Item",
            "Adjustment": "Adjustment Item",
        }
        if self.sle.voucher_type in mapping:
            return mapping[self.sle.voucher_type]
        return _original_child_doctype.fget(self)

    sbb.SerialBatchBundle.child_doctype = _custom_child_doctype
    sbb.SerialBatchBundle._is_manakshia_patched = True


# ─────────────────────────────────────────────────────────────────────────────


class PurchaseReceiptReturn(StockController):
    # ── ERPNext controller stubs ──────────────────────────────────────────────

    def set_incoming_rate(self):
        pass

    def is_internal_transfer(self):
        return False

    def set_total_in_words(self):
        pass

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def validate(self):
        self.set_company()
        self.set_child_stock_fields()
        self.set_exchange_rate()
        self.validate_warehouses()

        # ── Stash & clear inward bundle refs before ERPNext's duplicate check ──
        #
        # super().validate() → validate_duplicate_serial_and_batch_bundle()
        # checks every child row's serial_and_batch_bundle against existing SLEs.
        # The bundles we carry from the original PR are legitimately "already
        # used" there, so the check always raises a false-positive ValidationError.
        #
        # We temporarily blank the field, let ERPNext validate, then restore so
        # that on_submit → _find_source_bundle() can still read them from memory.
        bundle_stash = {}
        for item in self.get("items"):
            bundle_stash[item.name] = item.get("serial_and_batch_bundle")
            item.serial_and_batch_bundle = None

        try:
            super().validate()
        finally:
            # Always restore, even if super().validate() raises for another reason.
            for item in self.get("items"):
                item.serial_and_batch_bundle = bundle_stash.get(item.name)

    def on_submit(self):
        self.set_company()
        # Outward bundles MUST be created before SLEs are written so that each
        # SLE row already carries the bundle name when it is inserted.
        self._create_outward_serial_batch_bundles()
        self.update_stock_ledger()
        self.make_gl_entries()

    def on_cancel(self):
        self.set_company()
        self.ignore_linked_doctypes = (
            "Stock Ledger Entry",
            "GL Entry",
            "Serial and Batch Bundle",
        )
        # Cancel bundles before reversing the ledger so availability is restored
        # in the correct order.
        self._cancel_serial_batch_bundles()
        self.update_stock_ledger()
        self.make_gl_entries_on_cancel()

    # ── Field helpers ─────────────────────────────────────────────────────────

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

    def validate_warehouses(self):
        """Ensure at least one item has a source warehouse set."""
        all_items = [i for i in self.get("items") if i.item_code]
        items_without_warehouse = [
            item.item_code
            for item in all_items
            if not (
                item.warehouse
                or getattr(item, "rejected_warehouse", None)
                or getattr(self, "set_warehouse", None)
                or getattr(self, "rejected_warehouse", None)
            )
        ]
        if items_without_warehouse and len(items_without_warehouse) == len(all_items):
            frappe.throw(
                _(
                    "Please set a Warehouse for at least one item before submitting. "
                    "Items missing warehouse: {0}"
                ).format(", ".join(items_without_warehouse))
            )

    # ── Stock ledger ──────────────────────────────────────────────────────────

    def update_stock_ledger(self):
        sl_entries = self.get_sl_entries()
        if sl_entries:
            make_sl_entries(sl_entries)

    def get_sl_entries(self):
        """
        Purchase Receipt stocks IN to item.warehouse.
        Purchase Receipt Return reverses that → stock OUT (negative qty).
        """
        is_cancelled = self.docstatus == 2
        sl_entries = []

        for item in self.get("items"):
            if not item.item_code:
                continue

            # Skip zero/negative qty rows
            if flt(item.qty) <= 0:
                continue

            source_warehouse = (
                item.warehouse
                or getattr(item, "rejected_warehouse", None)
                or getattr(self, "set_warehouse", None)
                or getattr(self, "rejected_warehouse", None)
            )
            if not source_warehouse:
                continue

            qty = -1 * abs(flt(item.qty))

            sl_entries.append(
                frappe._dict(
                    {
                        "item_code": item.item_code,
                        "warehouse": source_warehouse,
                        "qty": qty,
                        "actual_qty": qty,
                        "company": self.company,
                        "voucher_type": self.doctype,
                        "voucher_no": self.name,
                        "voucher_detail_no": item.name,
                        "posting_date": (
                            self.get("posting_date")
                            or self.get("date")
                            or frappe.utils.today()
                        ),
                        "posting_time": (
                            self.get("posting_time") or frappe.utils.nowtime()
                        ),
                        "is_cancelled": 1 if is_cancelled else 0,
                        # Outward bundle created in on_submit.
                        # On cancel the bundle is already cancelled; pass None so
                        # the reversal SLE does not re-reference it.
                        "serial_and_batch_bundle": (
                            item.get("serial_and_batch_bundle")
                            if not is_cancelled
                            else None
                        ),
                        "dependant_sle_voucher_detail_no": item.name,
                    }
                )
            )
        return sl_entries

    # ── Serial / Batch Bundle – outward creation ──────────────────────────────

    def _item_tracks_serial_batch(self, item_code):
        """Return True when the Item master has serial nos or batch tracking."""
        item_doc = frappe.get_cached_doc("Item", item_code)
        return bool(item_doc.has_serial_no or item_doc.has_batch_no)

    def _create_outward_serial_batch_bundles(self):
        """
        For every item that tracks serial/batch numbers:
          1. Find the inward bundle from the Purchase Receipt.
          2. Create a new Outward bundle (negated qtys) referencing this doc.
          3. Save the new bundle name back to the Purchase Receipt Item child row
             so the SLE can reference it.
        """
        # Track source bundles already processed in this run so that duplicate
        # rows carrying the same inward bundle only produce one outward bundle.
        processed_source_bundles = set()

        for item in self.get("items"):
            if not item.item_code:
                continue

            # Skip zero/negative qty rows (rejected or ghost lines).
            if flt(item.qty) <= 0:
                continue

            if not self._item_tracks_serial_batch(item.item_code):
                continue

            source_warehouse = (
                item.warehouse
                or getattr(item, "rejected_warehouse", None)
                or getattr(self, "set_warehouse", None)
                or getattr(self, "rejected_warehouse", None)
            )
            if not source_warehouse:
                continue

            # Idempotency: skip if an outward bundle already exists for this row.
            existing_outward = frappe.db.get_value(
                "Serial and Batch Bundle",
                {
                    "voucher_type": self.doctype,
                    "voucher_no": self.name,
                    "voucher_detail_no": item.name,
                    "type_of_transaction": "Outward",
                    "docstatus": 1,
                },
                "name",
            )
            if existing_outward:
                item.serial_and_batch_bundle = existing_outward
                continue

            source_bundle = self._find_source_bundle(item)
            if not source_bundle:
                continue

            # Skip if same inward bundle already processed in this run.
            if source_bundle in processed_source_bundles:
                continue
            processed_source_bundles.add(source_bundle)

            bundle_name = self._make_outward_bundle(
                item, source_bundle, source_warehouse
            )
            if bundle_name:
                frappe.db.set_value(
                    "Purchase Receipt Item",
                    item.name,
                    "serial_and_batch_bundle",
                    bundle_name,
                )
                item.serial_and_batch_bundle = bundle_name

    def _find_source_bundle(self, item):
        """
        Locate the inward Serial and Batch Bundle from the PR.
        Priority:
          1. Bundle already on the child row (carried over by JS 'Fetch Items').
          2. Bundle from the matching item row in the Purchase Receipt.
        """
        # 1. Already on the row (set by purchase_receipt_return.js fetch button)
        existing = item.get("serial_and_batch_bundle")
        if existing:
            return existing

        # 2. Query the PR directly
        pr = self.get("purchase_receipt")
        if not pr:
            return None

        rows = frappe.get_all(
            "Purchase Receipt Item",
            filters={"parent": pr, "item_code": item.item_code},
            fields=["serial_and_batch_bundle"],
            order_by="idx asc",
            limit=1,
        )
        if rows and rows[0].get("serial_and_batch_bundle"):
            return rows[0]["serial_and_batch_bundle"]

        return None

    def _make_outward_bundle(self, item, source_bundle_name, warehouse):
        """
        Clone the inward bundle as an Outward bundle with negated qtys.
        The new bundle is linked to this Purchase Receipt Return doc.
        """
        try:
            source = frappe.get_doc("Serial and Batch Bundle", source_bundle_name)
        except frappe.DoesNotExistError:
            frappe.log_error(
                f"[Purchase Receipt Return] Serial and Batch Bundle "
                f"{source_bundle_name} not found while processing {self.name}"
            )
            return None

        bundle = frappe.new_doc("Serial and Batch Bundle")
        bundle.voucher_type = self.doctype
        bundle.voucher_no = self.name
        bundle.voucher_detail_no = item.name
        bundle.item_code = item.item_code
        bundle.warehouse = warehouse
        bundle.type_of_transaction = "Outward"
        bundle.company = self.company

        for entry in source.entries:
            bundle.append(
                "entries",
                {
                    "serial_no": entry.serial_no,
                    "batch_no": entry.batch_no,
                    "qty": -abs(flt(entry.qty)),  # Outward → negative qty
                    "warehouse": warehouse,
                },
            )

        if not bundle.entries:
            return None

        bundle.insert(ignore_permissions=True)

        # Use db_set instead of bundle.submit() to bypass
        # SerialBatchBundle.validate_voucher_detail_no(), which checks that the
        # voucher_detail_no (child row name) already exists in the DB.  At this
        # point the parent Purchase Receipt Return is still mid-save so its
        # child rows are not yet committed — the check always fails.
        # Setting docstatus directly is safe here because we built the bundle
        # ourselves with the correct voucher linkage.
        bundle.db_set("docstatus", 1)

        return bundle.name

    # ── Serial / Batch Bundle – cancel ────────────────────────────────────────

    def _cancel_serial_batch_bundles(self):
        """
        Cancel the Outward bundles that were created on submit so that
        serial/batch availability is fully restored.
        """
        for item in self.get("items"):
            bundle_name = item.get("serial_and_batch_bundle")
            if not bundle_name:
                continue
            try:
                bundle = frappe.get_doc("Serial and Batch Bundle", bundle_name)
                if bundle.docstatus == 1:
                    bundle.cancel()
            except Exception as exc:
                frappe.log_error(
                    f"[Purchase Receipt Return] Could not cancel Serial and Batch "
                    f"Bundle {bundle_name}: {exc}"
                )

    # ── GL Entries ────────────────────────────────────────────────────────────

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

        difference_account = frappe.get_cached_value(
            "Company", self.company, "default_expense_account"
        )
        if not difference_account:
            frappe.throw(
                _(
                    "Please define a Default Expense Account in the Company master to "
                    "process accounting entries for Purchase Receipt Return."
                )
            )

        inventory_account_map = self.get_inventory_account_map()
        doc_cost_center = getattr(self, "cost_center", None) or frappe.get_cached_value(
            "Company", self.company, "cost_center"
        )
        doc_remarks = getattr(self, "remarks", None) or _(
            "Accounting Entry for Purchase Receipt Return"
        )

        for item in self.get("items"):
            if not item.item_code:
                continue

            # Skip zero/negative qty rows
            if flt(item.qty) <= 0:
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
                frappe._dict(
                    {"item_code": item.item_code, "warehouse": source_warehouse}
                ),
                inventory_account_map,
                warehouse_field="warehouse",
            ).get("account")

            if not warehouse_account:
                frappe.throw(
                    _("Inventory account not found for warehouse {0}").format(
                        source_warehouse
                    )
                )

            amount = flt(abs(item.qty)) * flt(
                item.get("rate")
                or frappe.db.get_value("Item", item.item_code, "valuation_rate")
                or 0.0
            )
            if not amount:
                continue

            item_cost_center = getattr(item, "cost_center", None) or doc_cost_center

            # Debit the difference/expense account (stock is leaving the company)
            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": difference_account,
                        "against": warehouse_account,
                        "cost_center": item_cost_center,
                        "remarks": doc_remarks,
                        "debit": amount,
                        "debit_in_account_currency": amount,
                    },
                    item=item,
                )
            )
            # Credit the source warehouse account
            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": warehouse_account,
                        "against": difference_account,
                        "cost_center": item_cost_center,
                        "remarks": doc_remarks,
                        "credit": amount,
                        "credit_in_account_currency": amount,
                    },
                    item=item,
                )
            )

        return gl_entries
