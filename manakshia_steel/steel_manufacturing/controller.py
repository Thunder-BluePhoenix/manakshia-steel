# Copyright (c) 2026, Blue Phoenix and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from manakshia_steel.steel_manufacturing.doctype.steel_manufacturing_settings.steel_manufacturing_settings import (
    get_warehouse,
)


class ManaksiaManufacturingController(Document):
    def validate(self):
        # Auto-derive day name from date field
        if self.get("date"):
            import datetime

            dt = self.get("date")
            if isinstance(dt, str):
                dt = datetime.datetime.strptime(dt, "%Y-%m-%d").date()
            self.day = dt.strftime("%A")

        # P3: Block CC ROPP from being used in Profile Production (per MINL routing rules)
        if self.doctype == "Colour Profile Production":
            if self.get("select_coil") == "Colour":
                for row in self.get("items", []):
                    coil = row.get("coil_no") or ""
                    if "ROPP" in coil.upper():
                        frappe.throw(
                            f"Row {row.idx}: CC ROPP coil ({coil}) cannot be used in Profile Production. "
                            f"CC ROPP must go to CTL then Corrugation. (MINL Bypass B3 rule)"
                        )

    def on_submit(self):
        self.create_stock_entry()

    def on_cancel(self):
        self.cancel_stock_entry()

    def get_company(self):
        return frappe.db.get_default("company") or frappe.get_all("Company")[0].name

    def create_stock_entry(self):
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Manufacture"
        se.posting_date = self.get("date") or nowdate()
        se.company = self.get_company()

        # Fetch warehouses from Steel Manufacturing Settings (with safe fallback)
        rm_wh = get_warehouse("rm_warehouse", "Stores - ML")
        wip_wh = get_warehouse("wip_warehouse", "Work In Progress - ML")
        fg_wh = get_warehouse("fg_warehouse", "Finished Goods - ML")
        scrap_wh = get_warehouse("scrap_warehouse", "Scrap Warehouse - ML")

        doctype = self.doctype

        inputs = []
        outputs = []
        scraps = []

        if doctype == "Galvanized Coil Production":
            for row in self.get("entry_items"):
                qty = flt(row.minl_gr_wt)
                if qty <= 0:
                    continue
                self._ensure_item(
                    "CR Coil", "Raw Material", serial_tracked=True, batch_tracked=False
                )
                se.append(
                    "items",
                    {
                        "item_code": "CR Coil",
                        "s_warehouse": rm_wh,
                        "qty": qty,
                        "uom": "Kg",
                        "stock_uom": "Kg",
                        "serial_no": row.coil_no,  # Serial No — not batch
                        "allow_zero_valuation_rate": 1,
                    },
                )
                if flt(row.scrap_wt) > 0:
                    scraps.append((flt(row.scrap_wt), scrap_wh))
            for row in self.get("exit_items"):
                outputs.append(("GP Coil", row.gp_coil_no, flt(row.net_wt), wip_wh))

        elif doctype == "CC Coil Production":
            in_item, out_item = "GP Coil", "CC Coil"
            if self.process_type == "PRIM/V-SZ":
                in_item, out_item = "ALU ROPP Coil", "CC ROPP"
            elif self.process_type == "PRIM V-SIZ COL":
                in_item, out_item = "ALU Coil", "CC ALU"

            for row in self.get("entry_items"):
                inputs.append((in_item, row.coil_no, flt(row.minl_net_wt), wip_wh))
                if flt(row.scrap_wt) > 0:
                    scraps.append((flt(row.scrap_wt), scrap_wh))
            for row in self.get("exit_items"):
                outputs.append((out_item, row.cc_coil_no, flt(row.cc_coil_wt), wip_wh))

        elif doctype == "Embossed Coil Production":
            # B5 bypass: ALU Coil can enter Embossing directly (skip Galvanising + CC)
            in_item = "GP Coil"
            if self.coil_type == "Colour GP":
                in_item = "CC Coil"
            elif self.coil_type == "Colour Alu":
                in_item = "CC ALU"
            elif self.coil_type == "ALU":
                in_item = "ALU Coil"  # Bypass B5: ALU Coil direct to Embossing
            out_item = "EMB Coil"

            for row in self.get("entry_items"):
                inputs.append((in_item, row.coil_no, flt(row.minl_net_w), wip_wh))
                if flt(row.scrap_wt) > 0:
                    scraps.append((flt(row.scrap_wt), scrap_wh))
            for row in self.get("exit_items"):
                outputs.append((out_item, row.emb_coil_no, flt(row.emb_nt_wt), wip_wh))

        elif doctype == "CTL Production":
            for row in self.get("items"):
                if self.material == "GP COIL" and self.select_type == "GP":
                    in_item, out_item = "GP Coil", "GP Sheet"
                elif self.material == "GP COIL" and self.select_type == "Colour":
                    in_item, out_item = "CC Coil", "CC Sheet"
                elif self.material == "GP COIL" and self.select_type == "Embossed Coil":
                    in_item, out_item = "EMB Coil", "EMB Sheet"
                # Bypass B3: CC ROPP / CC ALU bypass Embossing and go directly to CTL
                elif self.select_type == "CC ROPP":
                    in_item, out_item = "CC ROPP", "CC ROPP Sheet"
                elif self.select_type == "CC ALU":
                    in_item, out_item = "CC ALU", "CC ALU Sheet"
                # Bypass B4: ALU Coil enters CTL directly
                elif self.material == "ALUMINIUM COIL":
                    in_item, out_item = "ALU Coil", "ALU Sheet"
                else:
                    in_item, out_item = "GP Coil", "GP Sheet"

                inputs.append((in_item, row.coil_no, flt(row.coil_weight), wip_wh))
                outputs.append((out_item, row.packet_no, flt(row.packet_wt), wip_wh))
                if flt(row.scrap_wt) > 0:
                    scraps.append((flt(row.scrap_wt), scrap_wh))

        elif doctype == "Colour Profile Production":
            for row in self.get("items"):
                in_item, out_item = "GP Coil", "Profiled GP Sheet"
                if self.select_coil == "Colour":
                    in_item, out_item = "CC Coil", "Profiled CC Sheet"
                elif self.select_coil == "Embossed Coil":
                    in_item, out_item = "EMB Coil", "Profiled EMB Sheet"
                elif self.material == "ALUMINIUM COIL":
                    in_item, out_item = "ALU Coil", "Profiled ALU Sheet"

                batch_out = f"{self.name}-{row.idx}"
                inputs.append((in_item, row.coil_no, flt(row.coil_wt), wip_wh))
                outputs.append((out_item, batch_out, flt(row.qnty_kg), fg_wh))
                if flt(row.scrap_wt) > 0:
                    scraps.append((flt(row.scrap_wt), scrap_wh))

        elif doctype == "Corrugated Sheet Production":
            for row in self.get("items"):
                # Map each skid/sheet type to input item code and output corrugated item
                MATERIAL_MAP = {
                    "GP SKID": ("GP Sheet", "Corrugated GP Sheet"),
                    "ALUMINIUM SKID": ("ALU Sheet", "Corrugated ALU Sheet"),
                    "CC SKID": ("CC Sheet", "Corrugated CC Sheet"),
                    "CC ALU SKID": ("CC ALU Sheet", "Corrugated CC ALU Sheet"),
                    "CC ROPP SKID": ("CC ROPP Sheet", "Corrugated CC ROPP Sheet"),
                    "EMB SKID": ("EMB Sheet", "Corrugated EMB Sheet"),
                }
                in_item, out_item = MATERIAL_MAP.get(
                    self.material, ("GP Sheet", "Corrugated GP Sheet")
                )

                batch_out = f"{self.name}-{row.idx}"
                inputs.append((in_item, row.packet_no, flt(row.packet_wt), wip_wh))
                outputs.append((out_item, batch_out, flt(row.qnty_kg), fg_wh))
                if flt(row.scrap_wt) > 0:
                    scraps.append((flt(row.scrap_wt), scrap_wh))

        # Add to Stock Entry
        for item_code, batch_no, qty, wh in inputs:
            if qty <= 0:
                continue
            self._ensure_item(item_code, "Semi Finished")
            se.append(
                "items",
                {
                    "item_code": item_code,
                    "s_warehouse": wh,
                    "qty": qty,
                    "uom": "Kg",
                    "stock_uom": "Kg",
                    "batch_no": self._ensure_batch(item_code, batch_no),
                    "allow_zero_valuation_rate": 1,
                },
            )

        for item_code, batch_no, qty, wh in outputs:
            if qty <= 0:
                continue
            self._ensure_item(item_code, "Semi Finished")
            se.append(
                "items",
                {
                    "item_code": item_code,
                    "t_warehouse": wh,
                    "qty": qty,
                    "uom": "Kg",
                    "stock_uom": "Kg",
                    "batch_no": self._ensure_batch(item_code, batch_no),
                    "is_finished_item": 1,
                    "allow_zero_valuation_rate": 1,
                },
            )

        for qty, wh in scraps:
            if qty <= 0:
                continue
            self._ensure_item(
                "Steel Scrap", "Raw Material", serial_tracked=False, batch_tracked=False
            )
            se.append(
                "items",
                {
                    "item_code": "Steel Scrap",
                    "t_warehouse": wh,
                    "qty": qty,
                    "uom": "Kg",
                    "stock_uom": "Kg",
                    "allow_zero_valuation_rate": 1,
                },
            )

        if not se.get("items"):
            frappe.throw("No items to process")

        se.insert(ignore_permissions=True)
        se.submit()
        frappe.db.set_value(self.doctype, self.name, "stock_entry_ref", se.name)

    def cancel_stock_entry(self):
        se_name = frappe.db.get_value(self.doctype, self.name, "stock_entry_ref")
        if se_name:
            se = frappe.get_doc("Stock Entry", se_name)
            se.cancel()

    def _ensure_item(self, item_code, group, serial_tracked=False, batch_tracked=True):
        if not frappe.db.exists("Item", item_code):
            # Ensure item group exists first
            if not frappe.db.exists("Item Group", group):
                ig = frappe.new_doc("Item Group")
                ig.item_group_name = group
                ig.parent_item_group = "All Item Groups"
                ig.insert(ignore_permissions=True)
            doc = frappe.new_doc("Item")
            doc.item_code = item_code
            doc.item_name = item_code
            doc.item_group = group
            doc.is_stock_item = 1
            doc.stock_uom = "Kg"
            doc.has_serial_no = 1 if serial_tracked else 0
            doc.has_batch_no = 1 if batch_tracked else 0
            doc.create_new_batch = 1 if batch_tracked else 0
            doc.insert(ignore_permissions=True)

    def _ensure_batch(self, item_code, batch_no):
        if not batch_no:
            return None
        if not frappe.db.exists("Batch", batch_no):
            doc = frappe.new_doc("Batch")
            doc.batch_id = batch_no
            doc.item = item_code
            doc.insert(ignore_permissions=True)
        return batch_no
