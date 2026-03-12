import frappe
from frappe import _
from frappe.utils import flt
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.stock_ledger import make_sl_entries
import erpnext.stock.serial_batch_bundle as sbb
import erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry as sle_module

# ─────────────────────────────────────────────────────────────────────────────
#  Monkey-patch 1 – StockLedgerEntry.on_submit
#
#  ERPNext's default on_submit tries to auto-create / validate Serial and Batch
#  Bundles for every SLE.  For our custom voucher types we create bundles
#  explicitly (before SLEs are written), so we skip that step and only update
#  the running stock balance.
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
            update_entries_after({
                "item_code": self.item_code,
                "warehouse": self.warehouse,
                "posting_date": self.posting_date,
                "posting_time": self.posting_time,
                "creation": self.creation,
                "via_landed_cost_voucher": False,
            })
            return
        _original_sle_on_submit(self)

    sle_module.StockLedgerEntry.on_submit = _patched_sle_on_submit
    sle_module.StockLedgerEntry._is_manakshia_patched = True


# ─────────────────────────────────────────────────────────────────────────────
#  Monkey-patch 2 – SerialBatchBundle.child_doctype
#
#  Tells ERPNext which child table to inspect when it needs to read serial/batch
#  lines from a voucher (e.g. during reconciliation).
# ─────────────────────────────────────────────────────────────────────────────

if not getattr(sbb.SerialBatchBundle, "_is_manakshia_patched", False):
    _original_child_doctype = sbb.SerialBatchBundle.child_doctype

    @property
    def _custom_child_doctype(self):
        mapping = {
            "Waybill Return": "Waybill Item",
            "Purchase Receipt Return": "Purchase Receipt Item",
            "Production Order": "Production Order Item",
            "Adjustment": "Adjustment Item",
        }
        if self.sle.voucher_type in mapping:
            return mapping[self.sle.voucher_type]
        return _original_child_doctype.fget(self)

    sbb.SerialBatchBundle.child_doctype = _custom_child_doctype
    sbb.SerialBatchBundle._is_manakshia_patched = True


# ─────────────────────────────────────────────────────────────────────────────


class WaybillReturn(StockController):

    # ── ERPNext controller stubs ──────────────────────────────────────────────

    def set_incoming_rate(self):
        pass

    def is_internal_transfer(self):
        return False

    def set_total_in_words(self):
        pass

    def calculate_taxes_and_totals(self):
        pass

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def validate(self):
        self.set_company()
        self.set_child_stock_fields()
        self.set_exchange_rate()
        # Deliberately skip super().validate() — ERPNext's accounts_controller
        # calls validate_return() which requires a 'return_against' field that
        # does not exist on this custom doctype.

    def on_submit(self):
        self.set_company()
        # Outward bundles MUST be created before SLEs are written so that each
        # SLE row already carries the bundle name when it is inserted.
        self._create_outward_serial_batch_bundles()
        self.update_stock_ledger()

    def on_cancel(self):
        self.set_company()
        self.ignore_linked_doctypes = ("Stock Ledger Entry", "Serial and Batch Bundle")
        # Cancel bundles before reversing the ledger so availability is restored
        # in the correct order.
        self._cancel_serial_batch_bundles()
        self.update_stock_ledger()

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
            self.company = (
                frappe.db.get_default("company")
                or frappe.defaults.get_user_default("Company")
            )
            if not self.company:
                companies = frappe.get_all("Company", limit=1)
                if companies:
                    self.company = companies[0].name

    # ── Stock ledger ──────────────────────────────────────────────────────────

    def update_stock_ledger(self):
        sl_entries = self.get_sl_entries()
        if sl_entries:
            make_sl_entries(sl_entries)

    def get_sl_entries(self):
        """
        Waybill stocks IN to to_warehouse on receipt.
        Waybill Return reverses that → stock OUT from to_warehouse (negative qty).
        On cancel of the return the qty flips back to positive.
        """
        if not self.to_warehouse:
            frappe.throw(_("To Warehouse is required to process stock return."))

        is_cancelled = self.docstatus == 2
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
                    # Embed the outward bundle created in on_submit.
                    # On cancel the bundle is already cancelled; pass None so
                    # the reversal SLE does not re-reference it.
                    "serial_and_batch_bundle": (
                        item.get("serial_and_batch_bundle") if not is_cancelled else None
                    ),
                })
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
          1. Find the inward bundle stored on the linked Waybill's item row.
          2. Create a new Outward bundle (negated qtys) referencing this doc.
          3. Save the new bundle name back to the Waybill Item child row so the
             SLE can reference it.
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

            bundle_name = self._make_outward_bundle(item, source_bundle)
            if bundle_name:
                frappe.db.set_value(
                    "Waybill Item", item.name, "serial_and_batch_bundle", bundle_name
                )
                item.serial_and_batch_bundle = bundle_name

    def _find_source_bundle(self, item):
        """
        Locate the inward Serial and Batch Bundle from the original Waybill.
        Priority:
          1. Bundle already stored on the child row (carried over by JS fetch).
          2. Bundle from the matching item row in the linked Waybill.
        """
        # 1. Already on the row (set by waybill_return.js which now copies it)
        existing = item.get("serial_and_batch_bundle")
        if existing:
            return existing

        # 2. Look up the original Waybill
        waybill_name = self.get("waybill")
        if not waybill_name:
            return None

        rows = frappe.get_all(
            "Waybill Item",
            filters={"parent": waybill_name, "item_code": item.item_code},
            fields=["serial_and_batch_bundle"],
            order_by="idx asc",
            limit=1,
        )
        if rows and rows[0].get("serial_and_batch_bundle"):
            return rows[0]["serial_and_batch_bundle"]

        return None

    def _make_outward_bundle(self, item, source_bundle_name):
        """
        Clone the inward bundle as an Outward bundle with negated qtys.
        The new bundle is linked to this Waybill Return doc.
        """
        try:
            source = frappe.get_doc("Serial and Batch Bundle", source_bundle_name)
        except frappe.DoesNotExistError:
            frappe.log_error(
                f"[Waybill Return] Serial and Batch Bundle {source_bundle_name} "
                f"not found while processing {self.name}"
            )
            return None

        bundle = frappe.new_doc("Serial and Batch Bundle")
        bundle.voucher_type = self.doctype
        bundle.voucher_no = self.name
        bundle.voucher_detail_no = item.name
        bundle.item_code = item.item_code
        bundle.warehouse = self.to_warehouse
        bundle.type_of_transaction = "Outward"
        bundle.company = self.company

        for entry in source.entries:
            bundle.append("entries", {
                "serial_no": entry.serial_no,
                "batch_no": entry.batch_no,
                "qty": -abs(flt(entry.qty)),   # Outward → negative qty
                "warehouse": self.to_warehouse,
            })

        if not bundle.entries:
            return None

        bundle.insert(ignore_permissions=True)

        # Use db_set instead of bundle.submit() to bypass
        # SerialBatchBundle.validate_voucher_detail_no(), which checks that the
        # voucher_detail_no (child row name) already exists in the DB.  At this
        # point the parent Waybill Return is still mid-save so its child rows
        # are not yet committed — the check always fails.
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
                    f"[Waybill Return] Could not cancel Serial and Batch Bundle "
                    f"{bundle_name}: {exc}"
                )