"""
seed_item_masters.py
=====================
Creates all Item Masters required for the Steel Manufacturing module.

Run:
    bench --site manaksia execute \
        manakshia_steel.steel_manufacturing.setup.seed_item_masters.run

The script is IDEMPOTENT — safe to re-run. It skips items that already exist
and prints a summary at the end.

Item Groups used (all under 'All Item Groups'):
  - Raw Material         → RM Coils (CR, ALU, ALU ROPP)
  - Semi Finished        → WIP Coils + WIP Sheets
  - Products             → FG Corrugated + FG Profiled

UOM: Kg for all (weight-based costing throughout all stages)
"""

import frappe

# ── Item definitions ──────────────────────────────────────────────────────────
# Format: (item_code, item_name, item_group, is_purchase, is_sales, description)

ITEMS = [
    # ── Raw Materials (RM warehouse) ──────────────────────────────────────────
    (
        "CR Coil",
        "CR Coil",
        "Raw Material",
        1,
        0,
        "Cold Rolled Steel Coil. Base raw material for the Galvanising line.",
    ),
    (
        "ALU Coil",
        "ALU Coil",
        "Raw Material",
        1,
        0,
        "Aluminium Coil. Can enter at Colour Coating, Embossing, CTL, or Profile directly.",
    ),
    (
        "ALU ROPP Coil",
        "ALU ROPP Coil",
        "Raw Material",
        1,
        0,
        "Aluminium ROPP Coil. Goes to Colour Coating only; bypasses Embossing and Profile.",
    ),
    # ── WIP Coils (WIP warehouse) ─────────────────────────────────────────────
    (
        "GP Coil",
        "GP Coil",
        "Semi Finished",
        0,
        0,
        "Galvanised Plain Coil. Output of Galvanising stage. Zinc-coated steel.",
    ),
    (
        "CC Coil",
        "CC Coil",
        "Semi Finished",
        0,
        0,
        "Colour Coated Coil (from GP input). Output of Colour Coating.",
    ),
    (
        "CC ROPP",
        "CC ROPP",
        "Semi Finished",
        0,
        0,
        "Colour Coated ROPP Coil (from ALU ROPP input). Goes to CTL only — no Embossing or Profile.",
    ),
    (
        "CC ALU",
        "CC ALU",
        "Semi Finished",
        0,
        0,
        "Colour Coated Aluminium Coil (from ALU input). Goes to CTL only via bypass B3.",
    ),
    (
        "EMB Coil",
        "EMB Coil",
        "Semi Finished",
        0,
        0,
        "Embossed Coil. Output of Embossing stage. Has textured surface pattern.",
    ),
    # ── WIP Sheets (WIP warehouse) ────────────────────────────────────────────
    (
        "GP Sheet",
        "GP Sheet",
        "Semi Finished",
        0,
        0,
        "Galvanised Plain Flat Sheet. Output of CTL from GP Coil (bypass B1).",
    ),
    (
        "CC Sheet",
        "CC Sheet",
        "Semi Finished",
        0,
        0,
        "Colour Coated Flat Sheet. Output of CTL from CC Coil.",
    ),
    (
        "CC ROPP Sheet",
        "CC ROPP Sheet",
        "Semi Finished",
        0,
        0,
        "CC ROPP Flat Sheet. Output of CTL from CC ROPP coil (bypass B3).",
    ),
    (
        "CC ALU Sheet",
        "CC ALU Sheet",
        "Semi Finished",
        0,
        0,
        "CC ALU Flat Sheet. Output of CTL from CC ALU coil (bypass B3).",
    ),
    (
        "ALU Sheet",
        "ALU Sheet",
        "Semi Finished",
        0,
        0,
        "Aluminium Flat Sheet. Output of CTL from ALU Coil directly (bypass B4).",
    ),
    (
        "EMB Sheet",
        "EMB Sheet",
        "Semi Finished",
        0,
        0,
        "Embossed Flat Sheet. Output of CTL from EMB Coil.",
    ),
    # ── Finished Goods — Corrugated (FG warehouse) ───────────────────────────
    (
        "Corrugated GP Sheet",
        "Corrugated GP Sheet",
        "Products",
        0,
        1,
        "Corrugated Galvanised Plain Sheet. Output of Corrugation from GP Sheet.",
    ),
    (
        "Corrugated CC Sheet",
        "Corrugated CC Sheet",
        "Products",
        0,
        1,
        "Corrugated Colour Coated Sheet. Output of Corrugation from CC Sheet.",
    ),
    (
        "Corrugated CC ROPP Sheet",
        "Corrugated CC ROPP Sheet",
        "Products",
        0,
        1,
        "Corrugated CC ROPP Sheet. Output of Corrugation from CC ROPP Sheet.",
    ),
    (
        "Corrugated CC ALU Sheet",
        "Corrugated CC ALU Sheet",
        "Products",
        0,
        1,
        "Corrugated CC ALU Sheet. Output of Corrugation from CC ALU Sheet.",
    ),
    (
        "Corrugated ALU Sheet",
        "Corrugated ALU Sheet",
        "Products",
        0,
        1,
        "Corrugated Aluminium Sheet. Output of Corrugation from ALU Sheet.",
    ),
    (
        "Corrugated EMB Sheet",
        "Corrugated EMB Sheet",
        "Products",
        0,
        1,
        "Corrugated Embossed Sheet. Output of Corrugation from EMB Sheet.",
    ),
    # ── Finished Goods — Profiled (FG warehouse) ─────────────────────────────
    (
        "Profiled GP Sheet",
        "Profiled GP Sheet",
        "Products",
        0,
        1,
        "Profiled GP Sheet. Roll-formed from GP Coil directly (no CTL required).",
    ),
    (
        "Profiled CC Sheet",
        "Profiled CC Sheet",
        "Products",
        0,
        1,
        "Profiled CC Sheet. Roll-formed from CC Coil directly (no CTL required).",
    ),
    (
        "Profiled ALU Sheet",
        "Profiled ALU Sheet",
        "Products",
        0,
        1,
        "Profiled Aluminium Sheet. Roll-formed from ALU Coil directly.",
    ),
    (
        "Profiled EMB Sheet",
        "Profiled EMB Sheet",
        "Products",
        0,
        1,
        "Profiled Embossed Sheet. Roll-formed from EMB Coil directly.",
    ),
]


# ── Runner ────────────────────────────────────────────────────────────────────


def run():
    frappe.set_user("Administrator")

    created = []
    skipped = []
    errors = []

    default_uom = "Kg"
    _ensure_uom(default_uom)

    for item_code, item_name, item_group, is_purchase, is_sales, desc in ITEMS:
        try:
            if frappe.db.exists("Item", item_code):
                skipped.append(item_code)
                print(f"  SKIP  {item_code}")
                continue

            doc = frappe.new_doc("Item")
            doc.item_code = item_code
            doc.item_name = item_name
            doc.item_group = item_group
            doc.stock_uom = default_uom
            doc.is_stock_item = 1
            doc.include_item_in_manufacturing = 1
            doc.is_purchase_item = is_purchase
            doc.is_sales_item = is_sales
            doc.description = desc
            doc.valuation_method = "Moving Average"
            doc.allow_negative_stock = 0

            doc.insert(ignore_permissions=True)
            # Fix tracking flags after insert — CR Coil uses Serial No, not Batch
            if item_code == "CR Coil":
                frappe.db.set_value(
                    "Item",
                    item_code,
                    {"has_serial_no": 1, "has_batch_no": 0, "create_new_batch": 0},
                )
            elif item_code == "Steel Scrap":
                frappe.db.set_value(
                    "Item",
                    item_code,
                    {"has_serial_no": 0, "has_batch_no": 0, "create_new_batch": 0},
                )
            created.append(item_code)
            print(f"  CREATED  {item_code}  [{item_group}]")

        except Exception as e:
            errors.append((item_code, str(e)))
            print(f"  ERROR   {item_code}: {e}")

    frappe.db.commit()

    print(f"\n{'=' * 55}")
    print(f"  Created : {len(created)}")
    print(f"  Skipped : {len(skipped)} (already exist)")
    print(f"  Errors  : {len(errors)}")
    if errors:
        print("  Error details:")
        for code, err in errors:
            print(f"    {code}: {err}")
    print(f"{'=' * 55}")
    print(
        "✅ Done. Run seed_manufacturing_stages.run() next to configure Process stages."
    )


def _ensure_uom(uom_name):
    """Create UOM if it doesn't exist."""
    if not frappe.db.exists("UOM", uom_name):
        doc = frappe.new_doc("UOM")
        doc.uom_name = uom_name
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Created UOM: {uom_name}")
