"""
fix_item_flags.py
===================
Fixes CR Coil and Steel Scrap item tracking flags so Stock Entry submission works correctly.

CR Coil:    needs has_serial_no=1, has_batch_no=0 (it is tracked by serial number)
Steel Scrap: needs has_batch_no=0, has_serial_no=0 (no tracking required for scrap)

Run: bench --site manaksia execute manakshia_steel.steel_manufacturing.setup.fix_item_flags.run
"""

import frappe


def run():
    frappe.set_user("Administrator")

    # Fix CR Coil — Serial No tracked, NOT batch tracked
    if frappe.db.exists("Item", "CR Coil"):
        frappe.db.set_value(
            "Item",
            "CR Coil",
            {
                "has_serial_no": 1,
                "has_batch_no": 0,
                "create_new_batch": 0,
            },
        )
        print("  FIXED: CR Coil → has_serial_no=1, has_batch_no=0")
    else:
        print("  CR Coil not found — run seed_item_masters first")

    # Fix Steel Scrap — no tracking needed (weight-only scrap)
    if frappe.db.exists("Item", "Steel Scrap"):
        frappe.db.set_value(
            "Item",
            "Steel Scrap",
            {
                "has_serial_no": 0,
                "has_batch_no": 0,
                "create_new_batch": 0,
            },
        )
        print("  FIXED: Steel Scrap → has_serial_no=0, has_batch_no=0")
    else:
        print("  Steel Scrap not found — will be created correctly on first submit")

    frappe.db.commit()
    print("\n  Verify:")
    for ic in ["CR Coil", "Steel Scrap"]:
        if frappe.db.exists("Item", ic):
            r = frappe.db.get_value(
                "Item", ic, ["has_serial_no", "has_batch_no"], as_dict=True
            )
            print(
                f"    {ic}: has_serial_no={r.has_serial_no}, has_batch_no={r.has_batch_no}"
            )
    print(
        "\nDone. Also run fix_controller.py to remove is_legacy_scrap_item from controller.py"
    )
