import frappe


def get_context(context):
    context.warehouses = frappe.get_all(
        "Warehouse", fields=["name", "company"], filters={"is_group": 0}
    )
    context.fiscal_years = frappe.get_all(
        "Fiscal Year",
        fields=["name", "year_start_date", "year_end_date"],
        order_by="year_start_date desc",
    )
