# Copyright (c) 2026, Blue Phoenix and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SteelManufacturingSettings(Document):
    pass


def get_warehouse(warehouse_field: str, fallback: str) -> str:
    """Helper used by controller.py to fetch configured warehouse with fallback."""
    try:
        value = frappe.db.get_single_value(
            "Steel Manufacturing Settings", warehouse_field
        )
        return value or fallback
    except Exception:
        return fallback
