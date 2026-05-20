import frappe


def run():
    frappe.set_user("Administrator")
    company = (
        frappe.db.get_single_value("Global Defaults", "default_company")
        or frappe.get_all("Company")[0].name
    )
    company_abbr = frappe.db.get_value("Company", company, "abbr") or "ML"

    scrap_wh_name = f"Scrap Warehouse - {company_abbr}"

    # 1. Create Scrap Warehouse if missing
    if not frappe.db.exists("Warehouse", scrap_wh_name):
        # Find parent warehouse
        parent = frappe.db.get_value(
            "Warehouse",
            {"company": company, "is_group": 1, "parent_warehouse": ""},
            "name",
        )
        if not parent:
            parent = frappe.db.sql(
                "SELECT name FROM `tabWarehouse` WHERE is_group=1 AND (parent_warehouse IS NULL OR parent_warehouse='') LIMIT 1",
                as_dict=True,
            )
            parent = parent[0].name if parent else None

        wh = frappe.new_doc("Warehouse")
        wh.warehouse_name = "Scrap Warehouse"
        wh.company = company
        wh.parent_warehouse = parent
        wh.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Created: {scrap_wh_name} under {parent}")
    else:
        print(f"  Already exists: {scrap_wh_name}")

    # 2. Update Settings to confirm scrap warehouse
    frappe.db.set_value(
        "Steel Manufacturing Settings", None, "scrap_warehouse", scrap_wh_name
    )
    frappe.db.commit()

    # 3. Final confirmation
    for field in ["rm_warehouse", "wip_warehouse", "fg_warehouse", "scrap_warehouse"]:
        val = frappe.db.get_single_value("Steel Manufacturing Settings", field)
        wh_exists = frappe.db.exists("Warehouse", val) if val else False
        print(f"  {field}: {val!r}  -> {'OK' if wh_exists else 'MISSING'}")

    print("\nAll done — Steel Manufacturing Settings is fully configured.")
