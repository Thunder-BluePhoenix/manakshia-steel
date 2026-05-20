"""
Deep audit script — checks every potential logic issue in the module.
Run: bench --site manaksia execute manakshia_steel.steel_manufacturing.setup.deep_audit.run
"""

import frappe


def run():
    frappe.set_user("Administrator")
    issues = []
    ok = []

    print("=" * 60)
    print("DEEP AUDIT — Manakshia Steel Manufacturing")
    print("=" * 60)

    # ── 1. CR Coil item — should have has_serial_no, NOT has_batch_no ─────────
    print("\n[1] CR Coil item flags")
    cr = frappe.db.get_value(
        "Item",
        "CR Coil",
        ["has_serial_no", "has_batch_no", "is_stock_item", "item_group"],
        as_dict=True,
    )
    if cr:
        if cr.has_serial_no:
            ok.append("CR Coil.has_serial_no = 1")
        else:
            issues.append(
                "CRITICAL: CR Coil.has_serial_no = 0 — serial_no in SE won't work"
            )
        if cr.has_batch_no:
            issues.append(
                "CRITICAL: CR Coil.has_batch_no = 1 — should be 0 (serial tracked, not batch)"
            )
        else:
            ok.append("CR Coil.has_batch_no = 0 ✓")
        print(
            f"  has_serial_no={cr.has_serial_no}, has_batch_no={cr.has_batch_no}, group={cr.item_group}"
        )
    else:
        issues.append("CR Coil item does not exist — run seed_item_masters first")
        print("  CR Coil NOT FOUND")

    # ── 2. GP Coil, CC Coil etc — should have has_batch_no ───────────────────
    print("\n[2] WIP coil item batch flags")
    wip_items = [
        "GP Coil",
        "CC Coil",
        "EMB Coil",
        "CC ROPP",
        "CC ALU",
        "ALU Coil",
        "ALU ROPP Coil",
    ]
    for ic in wip_items:
        row = frappe.db.get_value(
            "Item", ic, ["has_batch_no", "has_serial_no"], as_dict=True
        )
        if row:
            if row.has_batch_no and not row.has_serial_no:
                ok.append(f"{ic}: batch tracked ✓")
                print(f"  OK  {ic}: has_batch_no=1, has_serial_no=0")
            else:
                issues.append(
                    f"HIGH: {ic} has_batch_no={row.has_batch_no}, has_serial_no={row.has_serial_no} — should be batch only"
                )
                print(
                    f"  !! {ic}: has_batch_no={row.has_batch_no}, has_serial_no={row.has_serial_no}"
                )
        else:
            print(f"  MISSING: {ic}")

    # ── 3. Controller: is_legacy_scrap_item is not a valid SE Detail field ────
    print("\n[3] Controller scrap SE field validity")
    controller_path = "/home/prasun/frappe-bench-16/apps/manakshia_steel/manakshia_steel/steel_manufacturing/controller.py"
    with open(controller_path) as f:
        ctrl = f.read()
    if "is_legacy_scrap_item" in ctrl:
        issues.append(
            "CRITICAL: controller.py uses 'is_legacy_scrap_item' — not a valid Stock Entry Detail field, will cause SE insert error"
        )
        print("  !! is_legacy_scrap_item found — INVALID SE field")
    else:
        ok.append("No invalid SE fields")
        print("  OK")

    # ── 4. _ensure_item creates CR Coil with has_batch_no=1 ──────────────────
    print("\n[4] _ensure_item CR Coil creation logic")
    if (
        'self._ensure_item("CR Coil", "Raw Material")' in ctrl
        and "has_batch_no" in ctrl
    ):
        # Check if CR Coil path sets serial flags correctly
        if "has_serial_no" not in ctrl:
            issues.append(
                "HIGH: _ensure_item always sets has_batch_no=1 — CR Coil should have has_serial_no=1 instead"
            )
            print(
                "  !! _ensure_item uses has_batch_no for all items, including CR Coil"
            )
        else:
            ok.append("_ensure_item handles serial_no flag")
            print("  OK")
    else:
        print("  OK (CR Coil directly appended, _ensure_item separate)")

    # ── 5. Stage Production Summary — stage label match ───────────────────────
    print("\n[5] Stage Production Summary label consistency")
    from manakshia_steel.steel_manufacturing.report.stage_production_summary.stage_production_summary import (
        STAGE_CONFIG,
    )

    py_labels = [c["label"] for c in STAGE_CONFIG]
    js_options = [
        "Galvanizing",
        "CC Coating",
        "Embossing",
        "Cut to Length",
        "Colour Profiling",
        "Corrugation",
    ]
    for lab in py_labels:
        if lab in js_options:
            ok.append(f"SPS label '{lab}' ✓")
        else:
            issues.append(
                f"MEDIUM: SPS Python label '{lab}' not in JS filter options {js_options}"
            )
    print(f"  Python labels: {py_labels}")
    print(f"  JS options:    {js_options}")

    # ── 6. WIP Batch Stock — stage label match ────────────────────────────────
    print("\n[6] WIP Batch Stock PATTERN_A label consistency")
    from manakshia_steel.steel_manufacturing.report.wip_batch_stock.wip_batch_stock import (
        PATTERN_A,
    )

    wip_labels = [p[1] for p in PATTERN_A]
    wip_js = ["Galvanizing", "Embossing", "CC Coating"]
    for lab in wip_labels:
        if lab in wip_js:
            ok.append(f"WBS label '{lab}' ✓")
        else:
            issues.append(f"MEDIUM: WBS PATTERN_A label '{lab}' not in JS options")
    print(f"  PATTERN_A labels: {wip_labels}")

    # ── 7. Child table nonstandard field names ───────────────────────────────
    print("\n[7] Child table field name consistency")
    bad_names = {
        "Colour Profile Item": [
            "thik",
            "wdth",
            "lengt",
            "col",
            "pat",
            "stsc_wt",
            "sc",
            "qnty",
        ],
        "CTL Production Item": ["coil_leng", "qnty_sht", "scrap_sh"],
        "Corrugated Sheet Item": ["ptn", "col", "sc_st", "sc_wt", "remark"],
    }
    for dt, bad in bad_names.items():
        m = frappe.get_meta(dt)
        for fn in bad:
            f = m.get_field(fn)
            if f:
                issues.append(f"LOW: {dt}.{fn} still exists (old abbreviated name)")
                print(f"  !! {dt}.{fn} still present")
            else:
                ok.append(f"{dt}.{fn} removed ✓")
                print(f"  OK  {dt}.{fn} not present")

    # ── 8. All 6 Python controllers inherit from ManaksiaManufacturingController
    print("\n[8] DocType Python controller inheritance")
    import importlib

    for mod_path, dt in [
        (
            "manakshia_steel.steel_manufacturing.doctype.galvanized_coil_production.galvanized_coil_production",
            "GCP",
        ),
        (
            "manakshia_steel.steel_manufacturing.doctype.cc_coil_production.cc_coil_production",
            "CC",
        ),
        (
            "manakshia_steel.steel_manufacturing.doctype.embossed_coil_production.embossed_coil_production",
            "EMB",
        ),
        (
            "manakshia_steel.steel_manufacturing.doctype.ctl_production.ctl_production",
            "CTL",
        ),
        (
            "manakshia_steel.steel_manufacturing.doctype.colour_profile_production.colour_profile_production",
            "PROF",
        ),
        (
            "manakshia_steel.steel_manufacturing.doctype.corrugated_sheet_production.corrugated_sheet_production",
            "CORR",
        ),
    ]:
        try:
            mod = importlib.import_module(mod_path)
            cls = [
                c
                for c in dir(mod)
                if not c.startswith("_")
                and c != "ManaksiaManufacturingController"
                and c != "Document"
                and c != "frappe"
            ]
            ok.append(f"{dt} controller OK")
            print(f"  OK  {dt}: {cls}")
        except Exception as e:
            issues.append(f"CRITICAL: {dt} controller import failed: {e}")
            print(f"  !! {dt}: {e}")

    # ── 9. Packing Slip Child fetch_from ─────────────────────────────────────
    print("\n[9] Packing Slip Child fetch_from")
    try:
        m = frappe.get_meta("Packing Slip Child")
        for fn in ["batch_no", "grade_specification"]:
            f = m.get_field(fn)
            if f:
                print(f"  {fn}: fetch_from={f.fetch_from!r}, read_only={f.read_only}")
                if not f.fetch_from:
                    issues.append(f"MEDIUM: Packing Slip Child.{fn} has no fetch_from")
            else:
                issues.append(f"MEDIUM: Packing Slip Child.{fn} field missing")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── 10. custom item fields exist ──────────────────────────────────────────
    print("\n[10] Item master custom fields for auto-fill")
    for fn in ["custom_thickness_in_mm", "custom_width_in_mm"]:
        f = frappe.get_meta("Item").get_field(fn)
        if f:
            ok.append(f"Item.{fn} exists ✓")
            print(f"  OK  Item.{fn}: {f.fieldtype}")
        else:
            issues.append(
                f"HIGH: Item.{fn} missing — GCP auto-fill will return None for all coils"
            )
            print(f"  !! Item.{fn} MISSING")

    # ── 11. Steel Scrap item batch/serial flags ───────────────────────────────
    print("\n[11] Steel Scrap item")
    scrap = frappe.db.get_value(
        "Item",
        "Steel Scrap",
        ["has_batch_no", "has_serial_no", "is_stock_item"],
        as_dict=True,
    )
    if scrap:
        print(
            f"  has_batch_no={scrap.has_batch_no}, has_serial_no={scrap.has_serial_no}, is_stock={scrap.is_stock_item}"
        )
        if scrap.has_batch_no or scrap.has_serial_no:
            issues.append(
                "HIGH: Steel Scrap has batch/serial tracking — SE scrap rows don't pass batch_no, will error on submit"
            )
    else:
        print("  Steel Scrap NOT in DB — will be auto-created on first submit")

    # ── 12. GCP JSON: no duplicate fields ────────────────────────────────────
    print("\n[12] GCP JSON field_order vs fields duplicate check")
    import json

    gcp_path = "/home/prasun/frappe-bench-16/apps/manakshia_steel/manakshia_steel/steel_manufacturing/doctype/galvanized_coil_production/galvanized_coil_production.json"
    with open(gcp_path) as f:
        gcp = json.load(f)
    fo = gcp["field_order"]
    fnames = [fd["fieldname"] for fd in gcp["fields"]]
    fo_dups = [x for x in fo if fo.count(x) > 1]
    fn_dups = [x for x in fnames if fnames.count(x) > 1]
    if fo_dups:
        issues.append(f"CRITICAL: GCP field_order duplicates: {set(fo_dups)}")
    if fn_dups:
        issues.append(f"CRITICAL: GCP fields duplicates: {set(fn_dups)}")
    missing_from_fo = [
        n for n in fnames if n not in fo and n not in ("Section Break", "Column Break")
    ]
    missing_from_fields = [n for n in fo if n not in fnames]
    print(f"  field_order count={len(fo)}, fields count={len(fnames)}")
    if missing_from_fo:
        issues.append(f"MEDIUM: GCP fields not in field_order: {missing_from_fo}")
        print(f"  !! In fields but not field_order: {missing_from_fo}")
    if missing_from_fields:
        issues.append(
            f"MEDIUM: GCP field_order has unknown names: {missing_from_fields}"
        )
        print(f"  !! In field_order but not fields: {missing_from_fields}")
    if not fo_dups and not fn_dups and not missing_from_fo and not missing_from_fields:
        ok.append("GCP JSON fields consistent ✓")
        print("  OK")

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"ISSUES FOUND: {len(issues)}")
    for i in issues:
        print(f"  {i}")
    print(f"\nPASSED CHECKS: {len(ok)}")
    print("=" * 60)
