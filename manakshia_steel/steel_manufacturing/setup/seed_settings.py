import frappe


def run():
    frappe.set_user("Administrator")

    # 1. Seed Steel Manufacturing Settings (Single DocType — stored in tabSingles)
    settings_exists = frappe.db.get_singles_dict("Steel Manufacturing Settings")
    if not settings_exists.get("rm_warehouse"):
        frappe.db.set_value(
            "Steel Manufacturing Settings",
            None,
            {
                "rm_warehouse": "Stores - ML",
                "wip_warehouse": "Work In Progress - ML",
                "fg_warehouse": "Finished Goods - ML",
                "scrap_warehouse": "Scrap Warehouse - ML",
            },
        )
        frappe.db.commit()
        print("  Settings seeded.")
    else:
        print(
            f"  Settings already set: RM={settings_exists.get('rm_warehouse')}, WIP={settings_exists.get('wip_warehouse')}, FG={settings_exists.get('fg_warehouse')}"
        )

    # 2. Confirm warehouses exist in DB
    for wh in ["Stores - ML", "Work In Progress - ML", "Finished Goods - ML"]:
        exists = frappe.db.exists("Warehouse", wh)
        print(f"  Warehouse {'EXISTS' if exists else 'MISSING'}: {wh}")

    # Check if Scrap Warehouse - ML exists
    scrap_exists = frappe.db.exists("Warehouse", "Scrap Warehouse - ML")
    print(
        f"  Scrap Warehouse {'EXISTS' if scrap_exists else 'MISSING'}: Scrap Warehouse - ML"
    )

    # 3. Read back settings to confirm
    rm = frappe.db.get_single_value("Steel Manufacturing Settings", "rm_warehouse")
    wip = frappe.db.get_single_value("Steel Manufacturing Settings", "wip_warehouse")
    fg = frappe.db.get_single_value("Steel Manufacturing Settings", "fg_warehouse")
    scrap = frappe.db.get_single_value(
        "Steel Manufacturing Settings", "scrap_warehouse"
    )
    print("\n  CONFIRMED Settings:")
    print(f"    rm_warehouse    = {rm!r}")
    print(f"    wip_warehouse   = {wip!r}")
    print(f"    fg_warehouse    = {fg!r}")
    print(f"    scrap_warehouse = {scrap!r}")

    # 4. List all warehouses so we can pick the correct scrap WH name
    all_wh = frappe.db.sql(
        "SELECT name FROM `tabWarehouse` WHERE is_group=0 ORDER BY name", as_dict=True
    )
    print("\n  All Warehouses in system:")
    for w in all_wh:
        print(f"    - {w.name}")
