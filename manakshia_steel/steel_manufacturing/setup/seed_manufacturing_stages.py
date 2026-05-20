"""
seed_manufacturing_stages.py
============================
Frappe console script to seed the 6 Steel Manufacturing Stage records
in the Process DocType, including the full Input → Output item mapping.

Run from the bench root:
    bench --site <sitename> execute manakshia_steel.steel_manufacturing.setup.seed_manufacturing_stages.run

BEFORE RUNNING:
  1. Make sure all Item masters exist with the names below (or update the
     ITEM_NAMES dict to match your actual item names in the system).
  2. Set SOURCE_WH and TARGET_WH to the correct warehouse names for your site.
  3. The script is idempotent — it will update existing Process records
     and create missing ones. Safe to re-run.
"""

import frappe

# ── Configure these to match your actual warehouse names ─────────────────────

RM_WH = "Stores - ML"  # Main warehouse / RM store
WIP_WH = "Work In Progress - ML"  # Work-In-Progress warehouse
FG_WH = "Finished Goods - ML"  # Finished Goods warehouse


# ── Item names — update if your actual item master names differ ───────────────

ITEM_NAMES = {
    # Raw Materials
    "CR Coil": "CR Coil",
    "ALU Coil": "ALU Coil",
    "ALU ROPP Coil": "ALU ROPP Coil",
    # WIP Coils
    "GP Coil": "GP Coil",
    "CC Coil": "CC Coil",
    "CC ROPP": "CC ROPP",
    "CC ALU": "CC ALU",
    "EMB Coil": "EMB Coil",
    # WIP Sheets
    "GP Sheet": "GP Sheet",
    "CC Sheet": "CC Sheet",
    "CC ROPP Sheet": "CC ROPP Sheet",
    "CC ALU Sheet": "CC ALU Sheet",
    "ALU Sheet": "ALU Sheet",
    "EMB Sheet": "EMB Sheet",
    # FG Corrugated
    "Corrugated GP": "Corrugated GP Sheet",
    "Corrugated CC": "Corrugated CC Sheet",
    "Corrugated CCROPP": "Corrugated CC ROPP Sheet",
    "Corrugated CCALU": "Corrugated CC ALU Sheet",
    "Corrugated ALU": "Corrugated ALU Sheet",
    "Corrugated EMB": "Corrugated EMB Sheet",
    # FG Profiled
    "Profiled GP": "Profiled GP Sheet",
    "Profiled CC": "Profiled CC Sheet",
    "Profiled ALU": "Profiled ALU Sheet",
    "Profiled EMB": "Profiled EMB Sheet",
}

ITM = ITEM_NAMES  # shorthand


# ── Stage definitions ─────────────────────────────────────────────────────────
# Each entry: (process_name, stage_code, source_wh, target_wh, mappings)
# mappings: list of (input_item_key, output_item_key, bypass_ref)

STAGES = [
    {
        "process_name": "Galvanising",
        "stage_code": "Galvanising",
        "source_wh": RM_WH,
        "target_wh": WIP_WH,
        "mappings": [
            (ITM["CR Coil"], ITM["GP Coil"], ""),
        ],
    },
    {
        "process_name": "Colour Coating",
        "stage_code": "Colour Coating",
        "source_wh": WIP_WH,
        "target_wh": WIP_WH,
        "mappings": [
            (ITM["GP Coil"], ITM["CC Coil"], ""),
            (ITM["ALU Coil"], ITM["CC ALU"], "B2"),
            (ITM["ALU ROPP Coil"], ITM["CC ROPP"], "B2"),
        ],
    },
    {
        "process_name": "Embossing",
        "stage_code": "Embossing",
        "source_wh": WIP_WH,
        "target_wh": WIP_WH,
        "mappings": [
            (ITM["CC Coil"], ITM["EMB Coil"], ""),
            (ITM["ALU Coil"], ITM["EMB Coil"], "B5"),
        ],
    },
    {
        "process_name": "CTL",
        "stage_code": "CTL",
        "source_wh": WIP_WH,
        "target_wh": WIP_WH,
        "mappings": [
            (ITM["GP Coil"], ITM["GP Sheet"], "B1"),
            (ITM["CC Coil"], ITM["CC Sheet"], ""),
            (ITM["CC ROPP"], ITM["CC ROPP Sheet"], "B3"),
            (ITM["CC ALU"], ITM["CC ALU Sheet"], "B3"),
            (ITM["ALU Coil"], ITM["ALU Sheet"], "B4"),
            (ITM["EMB Coil"], ITM["EMB Sheet"], ""),
        ],
    },
    {
        "process_name": "Corrugation",
        "stage_code": "Corrugation",
        "source_wh": WIP_WH,
        "target_wh": FG_WH,
        "mappings": [
            (ITM["GP Sheet"], ITM["Corrugated GP"], ""),
            (ITM["CC Sheet"], ITM["Corrugated CC"], ""),
            (ITM["CC ROPP Sheet"], ITM["Corrugated CCROPP"], ""),
            (ITM["CC ALU Sheet"], ITM["Corrugated CCALU"], ""),
            (ITM["ALU Sheet"], ITM["Corrugated ALU"], ""),
            (ITM["EMB Sheet"], ITM["Corrugated EMB"], ""),
        ],
    },
    {
        "process_name": "Profile",
        "stage_code": "Profile",
        "source_wh": WIP_WH,
        "target_wh": FG_WH,
        "mappings": [
            (ITM["GP Coil"], ITM["Profiled GP"], ""),
            (ITM["CC Coil"], ITM["Profiled CC"], ""),
            (ITM["ALU Coil"], ITM["Profiled ALU"], ""),
            (ITM["EMB Coil"], ITM["Profiled EMB"], ""),
        ],
    },
]


# ── Runner ────────────────────────────────────────────────────────────────────


def run():
    frappe.set_user("Administrator")
    created, updated = 0, 0

    for stage in STAGES:
        name = stage["process_name"]
        exists = frappe.db.exists("Process", {"process_name": name})

        if exists:
            doc = frappe.get_doc("Process", exists)
            action = "Updated"
        else:
            doc = frappe.new_doc("Process")
            doc.process_name = name
            action = "Created"

        doc.stage_code = stage["stage_code"]
        doc.source_warehouse = stage["source_wh"]
        doc.target_warehouse = stage["target_wh"]
        doc.is_active = 1
        doc.description = f"Manufacturing stage: {name}"

        # Rebuild stage_mappings child table
        doc.set("stage_mappings", [])
        for input_item, output_item, bypass_ref in stage["mappings"]:
            # Check items exist before adding mapping
            if not frappe.db.exists("Item", input_item):
                print(f"  ⚠  Item not found: '{input_item}' — skipping mapping row")
                continue
            if not frappe.db.exists("Item", output_item):
                print(f"  ⚠  Item not found: '{output_item}' — skipping mapping row")
                continue
            doc.append(
                "stage_mappings",
                {
                    "input_item": input_item,
                    "output_item": output_item,
                    "bypass_ref": bypass_ref,
                },
            )

        doc.save(ignore_permissions=True)

        if action == "Created":
            created += 1
        else:
            updated += 1
        print(f"  {action}: {name} ({len(doc.stage_mappings)} mapping rows)")

    frappe.db.commit()
    print(f"\n✅ Done — {created} created, {updated} updated.")
    print(
        "⚠  If items were skipped, create the Item masters first and re-run this script."
    )
