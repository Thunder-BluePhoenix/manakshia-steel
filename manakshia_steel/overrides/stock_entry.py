from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry


class CustomStockEntry(StockEntry):
    """
    Override Stock Entry to completely detach ERPNext v16's Serial/Batch Bundle
    auto-creation and validation from all Stock Entry operations.

    ERPNext v16 creates bundles at FIVE separate points:
      1. StockEntry.on_submit()  → make_bundle_using_old_serial_batch_fields()
      2. StockEntry.on_submit()  → make_serial_and_batch_bundle_for_outward()
         (triggered when "Auto Create Serial and Batch Bundle" is ON in Stock Settings)
      3. StockEntry.on_update()  → set_serial_and_batch_bundle()  (saves serial-batch
         values from any existing bundle links back to the items table)
      4. StockLedgerEntry.on_submit() → SerialBatchBundle(sle=self, ...)
         → make_serial_batch_no_bundle() — creates a Draft bundle per SLE
      5. StockController.set_use_serial_batch_fields() — re-enables legacy fields
         from Stock Settings during validate(), which can re-trigger 1-4.

    All five are suppressed for Stock Entry by this class.
    """

    # ── 1 & 5. Block legacy-field re-enable + auto-bundle from old fields ──────
    def set_use_serial_batch_fields(self):
        """No-op: prevent Stock Settings from re-enabling serial/batch on rows."""
        return

    def make_bundle_using_old_serial_batch_fields(
        self, table_name=None, via_landed_cost_voucher=False
    ):
        """No-op: prevent auto-creation of bundle from old serial_no/batch_no fields."""
        return

    # ── 2. Block outward bundle auto-creation ──────────────────────────────────
    def make_serial_and_batch_bundle_for_outward(self):
        """No-op: prevent auto-creation of outward bundle during submit."""
        return

    # ── 3. Block bundle sync on save ───────────────────────────────────────────
    def on_update(self):
        """Skip set_serial_and_batch_bundle; call the rest of parent on_update."""
        # StockController.on_update() only calls set_serial_and_batch_bundle()
        # Skip it entirely – there is nothing else in the parent on_update chain
        # that we need for Material Issue / Material Receipt.
        return

    # ── 4. After parent validate, wipe any serial/batch refs ERPNext set ───────
    def validate(self):
        super().validate()
        self._clear_serial_batch_fields()

    def _clear_serial_batch_fields(self):
        """Wipe all serial/batch references from every item row."""
        for row in self.get("items", []):
            row.serial_and_batch_bundle = None
            row.serial_no = None
            row.batch_no = None
            row.use_serial_batch_fields = 0

    # ── 5. On submit: patch SLE.on_submit to skip SerialBatchBundle creation ───
    def update_stock_ledger(self):
        from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import (
            StockLedgerEntry,
        )

        # ROOT CAUSE: StockLedgerEntry.on_submit() instantiates SerialBatchBundle(sle=self)
        # which inside __init__ calls make_serial_batch_no_bundle() — creating a Draft bundle.
        # Fix: patch SLE.on_submit to skip ALL serial/batch logic for Stock Entry SLEs.

        _orig_sle_on_submit = StockLedgerEntry.on_submit

        def _skip_serial_batch_for_stock_entry(sle_self):
            if sle_self.voucher_type == "Stock Entry":
                # Only run the stock-freeze date check; skip bundle creation entirely.
                sle_self.check_stock_frozen_date()
                return
            _orig_sle_on_submit(sle_self)

        StockLedgerEntry.on_submit = _skip_serial_batch_for_stock_entry

        try:
            super().update_stock_ledger()
        finally:
            StockLedgerEntry.on_submit = _orig_sle_on_submit
