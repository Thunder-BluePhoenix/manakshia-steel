# Copyright (c) 2026, Blue Phoenix and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PurchaseReceiptReturn(Document):
	def validate(self):
		self.validate_warehouses()

	def validate_warehouses(self):
		"""Ensure at least one item has a source warehouse set."""
		items_without_warehouse = []
		for item in self.get("items"):
			if not item.item_code:
				continue
			warehouse = (
				item.warehouse
				or getattr(item, "rejected_warehouse", None)
				or self.set_warehouse
				or self.rejected_warehouse
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
		self.make_material_issue()

	def on_cancel(self):
		self.cancel_material_issue()

	def make_material_issue(self):
		"""Create a Stock Entry of type Material Issue to move stock out (back to supplier)."""
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Issue"
		se.purpose = "Material Issue"
		se.company = self.company
		se.posting_date = self.posting_date
		se.posting_time = self.posting_time

		# custom_process is mandatory on Stock Entry — pull from this doc's field,
		# or fall back to the first active Process record in the system.
		process = self.get("custom_process")
		if not process:
			process = frappe.db.get_value("Process", {"is_active": 1}, "name")
		if not process:
			frappe.throw(
				_(
					"Please set a Process on this Purchase Receipt Return before submitting, "
					"or ensure at least one active Process exists in the system."
				)
			)
		se.custom_process = process

		# Build a remarks string referencing this return document and the original PR
		remarks_parts = [f"Purchase Receipt Return: {self.name}"]
		if self.get("original_purchase_receipt"):
			remarks_parts.append(f"Original Purchase Receipt: {self.original_purchase_receipt}")
		if self.get("reason_for_return"):
			remarks_parts.append(f"Reason: {self.reason_for_return}")
		se.remarks = " | ".join(remarks_parts)

		for item in self.get("items"):
			if not item.item_code:
				continue

			source_warehouse = (
				item.warehouse
				or getattr(item, "rejected_warehouse", None)
				or self.set_warehouse
				or self.rejected_warehouse
			)

			if not source_warehouse:
				frappe.msgprint(
					_(
						"Skipping item {0} — no source warehouse found. "
						"Please set the warehouse and resubmit."
					).format(item.item_code),
					alert=True,
				)
				continue

			se.append(
				"items",
				{
					"item_code": item.item_code,
					"qty": abs(item.qty),
					"uom": item.uom,
					"stock_uom": item.stock_uom,
					"conversion_factor": item.conversion_factor or 1,
					"s_warehouse": source_warehouse,
					"serial_and_batch_bundle": getattr(item, "serial_and_batch_bundle", None),
					"use_serial_batch_fields": 1 if getattr(item, "serial_and_batch_bundle", None) else 0,
					"cost_center": getattr(item, "cost_center", None)
					or getattr(self, "cost_center", None),
					"allow_zero_valuation_rate": 1,
				},
			)

		if se.get("items"):
			se.set_stock_entry_type()

			# Re-link Serial and Batch bundles so Stock Entry can adopt them on insert
			for row in se.get("items"):
				if row.serial_and_batch_bundle:
					frappe.db.set_value(
						"Serial and Batch Bundle",
						row.serial_and_batch_bundle,
						{
							"voucher_type": "Stock Entry",
							"voucher_no": "",
							"voucher_detail_no": ""
						}
					)

			se.insert()
			se.submit()
			self.db_set("return_stock_entry", se.name)
			frappe.msgprint(
				_("Stock Entry {0} created and submitted for Material Issue.").format(
					frappe.bold(se.name)
				),
				alert=True,
			)
		else:
			frappe.throw(
				_(
					"No items with valid warehouse found. "
					"Stock Entry could not be created."
				)
			)

	def cancel_material_issue(self):
		"""Cancel the linked Stock Entry when this return is cancelled."""
		if self.return_stock_entry:
			try:
				se = frappe.get_doc("Stock Entry", self.return_stock_entry)
				if se.docstatus == 1:
					se.cancel()
					frappe.msgprint(
						_("Linked Stock Entry {0} has been cancelled.").format(
							frappe.bold(self.return_stock_entry)
						),
						alert=True,
					)
			except frappe.DoesNotExistError:
				frappe.msgprint(
					_("Linked Stock Entry {0} not found — may have already been deleted.").format(
						self.return_stock_entry
					),
					alert=True,
				)
