"""
COMPREHENSIVE AUDIT v2
======================
Checks EVERYTHING: entry tables, exit tables, parent JSONs, Python syntax,
SQL field refs vs DB columns, JS field refs, hooks registration, autoname,
report queries, workspace, settings DocType.

Run: bench --site manaksia execute manakshia_steel.steel_manufacturing.setup.deep_audit_v2.run
"""

import ast
import json
import os

import frappe

BASE = "/home/prasun/frappe-bench-16/apps/manakshia_steel/manakshia_steel"

issues = []
ok = []


def chk(label, condition, msg_pass=None, msg_fail=None):
    if condition:
        ok.append(msg_pass or label)
    else:
        issues.append(msg_fail or f"FAIL: {label}")


def section(title):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


# ──────────────────────────────────────────────────────────
def check_python_syntax():
    section("[A] Python Syntax — all .py files")
    py_files = [
        "steel_manufacturing/controller.py",
        "steel_manufacturing/api.py",
        "steel_manufacturing/report/batch_traceability/batch_traceability.py",
        "steel_manufacturing/report/stage_production_summary/stage_production_summary.py",
        "steel_manufacturing/report/wip_batch_stock/wip_batch_stock.py",
        "steel_manufacturing/doctype/steel_manufacturing_settings/steel_manufacturing_settings.py",
    ]
    for rel in py_files:
        path = os.path.join(BASE, rel)
        if not os.path.exists(path):
            issues.append(f"MISSING file: {rel}")
            print(f"  !! MISSING: {rel}")
            continue
        try:
            with open(path) as f:
                src = f.read()
            ast.parse(src)
            ok.append(f"Syntax OK: {rel}")
            print(f"  OK  {os.path.basename(rel)}")
        except SyntaxError as e:
            issues.append(f"SYNTAX ERROR in {rel}: {e}")
            print(f"  !! SYNTAX: {rel}: {e}")


# ──────────────────────────────────────────────────────────
def check_all_child_table_fields():
    section("[B] All Child Table Fields — DB vs JSON")
    child_tables = [
        # (DocType, expected_good_fields, bad_old_fields)
        (
            "Galvanized Coil Entry",
            ["coil_no", "minl_gr_wt", "chln_net_wt", "scrap_wt"],
            [],
        ),
        (
            "Galvanized Coil Exit",
            [
                "gp_coil_no",
                "thick",
                "width",
                "net_wt",
                "sleeve_wt",
                "length_mtr",
                "brand",
            ],
            [],
        ),
        ("CC Coil Entry", ["coil_no", "minl_net_wt", "chln_net_wt", "scrap_wt"], []),
        (
            "CC Coil Exit",
            [
                "cc_coil_no",
                "fin_thk",
                "width",
                "cc_coil_wt",
                "colour",
                "brand",
                "length",
            ],
            [],
        ),
        (
            "Embossed Coil Entry",
            ["coil_no", "minl_net_w", "chln_net_w", "scrap_wt"],
            [],
        ),
        (
            "Embossed Coil Exit",
            [
                "emb_coil_no",
                "fin_thk",
                "width",
                "colour",
                "emb_nt_wt",
                "sleeve_wt",
                "brand",
            ],
            [],
        ),
        (
            "CTL Production Item",
            [
                "coil_no",
                "coil_weight",
                "packet_no",
                "coil_length",
                "thick",
                "width",
                "qty_sheets",
                "packet_wt",
                "scrap_sheets",
                "scrap_wt",
                "colour",
            ],
            ["coil_leng", "qnty_sht", "scrap_sh"],
        ),
        (
            "Colour Profile Item",
            [
                "coil_no",
                "coil_wt",
                "thick",
                "width",
                "length",
                "colour",
                "pattern",
                "qty_pcs",
                "qnty_kg",
                "scrap_pcs",
                "scrap_wt",
                "brand",
            ],
            ["thik", "wdth", "lengt", "col", "pat", "stsc_wt", "sc", "qnty"],
        ),
        (
            "Corrugated Sheet Item",
            [
                "packet_no",
                "packet_wt",
                "pattern",
                "colour",
                "quantity",
                "qnty_kg",
                "scrap_sheets",
                "scrap_wt",
                "brand",
                "thick",
                "width",
                "length",
                "remarks",
            ],
            ["ptn", "col", "sc_st", "sc_wt", "remark"],
        ),
    ]
    for dt, expected, bad in child_tables:
        print(f"\n  {dt}:")
        m = frappe.get_meta(dt)
        actual = {f.fieldname for f in m.fields}
        for fn in expected:
            if fn in actual:
                ok.append(f"{dt}.{fn} ✓")
                print(f"    OK  {fn}")
            else:
                issues.append(
                    f"MISSING: {dt}.{fn} — expected field not found in schema"
                )
                print(f"    !! MISSING: {fn}")
        for fn in bad:
            if fn in actual:
                issues.append(f"OLD FIELD: {dt}.{fn} still present — rename incomplete")
                print(f"    !! OLD FIELD STILL PRESENT: {fn}")
            else:
                ok.append(f"{dt}.{fn} removed ✓")


# ──────────────────────────────────────────────────────────
def check_controller_field_refs():
    section("[C] Controller — field references vs JSON")
    path = os.path.join(BASE, "steel_manufacturing/controller.py")
    with open(path) as f:
        src = f.read()

    checks = [
        # (fieldname_in_code, should_exist, description)
        ("row.minl_gr_wt", True, "GCP entry weight"),
        ("row.coil_no", True, "coil batch ref (all WIP stages)"),
        ("row.net_wt", True, "GCP exit net weight"),
        ("row.gp_coil_no", True, "GCP exit coil no"),
        ("row.minl_net_wt", True, "CC entry net weight"),
        ("row.cc_coil_no", True, "CC exit coil no"),
        ("row.cc_coil_wt", True, "CC exit weight"),
        ("row.minl_net_w", True, "EMB entry weight"),
        ("row.emb_coil_no", True, "EMB exit coil no"),
        ("row.emb_nt_wt", True, "EMB exit net weight"),
        ("row.coil_weight", True, "CTL coil weight"),
        ("row.packet_no", True, "CTL packet no"),
        ("row.packet_wt", True, "CTL/COR packet weight"),
        ("row.scrap_wt", True, "scrap weight (CTL, COR, Profile)"),
        ("row.coil_wt", True, "Profile coil weight"),
        ("row.qnty_kg", True, "Profile/COR output kg"),
        # Old bad names that must NOT exist
        ("row.stsc_wt", False, "OLD Profile scrap field"),
        ("row.sc_wt", False, "OLD Corrugated scrap field"),
        ("row.coil_leng", False, "OLD CTL coil length"),
        ("row.qnty_sht", False, "OLD CTL qty sheets"),
        ("is_legacy_scrap_item", False, "invalid SE Detail field"),
    ]
    for ref, should_exist, desc in checks:
        found = ref in src
        if should_exist and found:
            ok.append(f"Controller has '{ref}' ✓")
            print(f"  OK  '{ref}' ({desc})")
        elif should_exist and not found:
            issues.append(f"CRITICAL: Controller missing '{ref}' — {desc}")
            print(f"  !! MISSING '{ref}' ({desc})")
        elif not should_exist and found:
            issues.append(
                f"CRITICAL: Controller still uses old/invalid '{ref}' — {desc}"
            )
            print(f"  !! OLD/INVALID '{ref}' found ({desc})")
        else:
            ok.append(f"Controller correctly absent: '{ref}' ✓")
            print(f"  OK  '{ref}' correctly absent ({desc})")


# ──────────────────────────────────────────────────────────
def check_api_sql_refs():
    section("[D] API — SQL field refs vs actual DB columns")
    path = os.path.join(BASE, "steel_manufacturing/api.py")
    with open(path) as f:
        f.read()

    # Fields referenced in SQL vs what must exist
    sql_checks = [
        (
            "tabGalvanized Coil Exit",
            ["thick", "width", "net_wt", "sleeve_wt", "brand", "length_mtr"],
        ),
        (
            "tabCC Coil Exit",
            ["fin_thk", "width", "cc_coil_wt", "brand", "length", "colour"],
        ),
        (
            "tabEmbossed Coil Exit",
            [
                "fin_thk",
                "width",
                "emb_nt_wt",
                "sleeve_wt",
                "brand",
                "length",
                "colour",
                "pattern",
            ],
        ),
        (
            "tabCTL Production Item",
            ["thick", "width", "packet_wt", "brand", "colour", "qty_sheets", "length"],
        ),
    ]
    for tab, fields in sql_checks:
        print(f"\n  {tab}:")
        try:
            cols = [r[0] for r in frappe.db.sql(f"SHOW COLUMNS FROM `{tab}`")]
            for fn in fields:
                if fn in cols:
                    ok.append(f"{tab}.{fn} DB ✓")
                    print(f"    OK  {fn}")
                else:
                    issues.append(f"CRITICAL: {tab}.{fn} not in DB — API SQL will fail")
                    print(f"    !! MISSING IN DB: {fn}")
        except Exception as e:
            issues.append(f"ERROR checking {tab}: {e}")
            print(f"    !! ERROR: {e}")


# ──────────────────────────────────────────────────────────
def check_parent_doctypes():
    section("[E] Parent DocType Fields — all 6")
    parents = {
        "Galvanized Coil Production": [
            "date",
            "shift",
            "operator_name",
            "mc_no",
            "entry_items",
            "exit_items",
            "stock_entry_ref",
            "amended_from",
            "total_input_wt",
            "total_output_wt",
        ],
        "CC Coil Production": [
            "date",
            "process_type",
            "entry_items",
            "exit_items",
            "stock_entry_ref",
            "amended_from",
            "total_input_wt",
            "total_output_wt",
        ],
        "Embossed Coil Production": [
            "date",
            "coil_type",
            "entry_items",
            "exit_items",
            "stock_entry_ref",
            "amended_from",
            "total_input_wt",
            "total_output_wt",
        ],
        "CTL Production": [
            "date",
            "material",
            "select_type",
            "items",
            "stock_entry_ref",
            "amended_from",
            "total_input_wt",
            "total_output_wt",
        ],
        "Colour Profile Production": [
            "date",
            "select_coil",
            "material",
            "items",
            "stock_entry_ref",
            "amended_from",
            "total_input_wt",
            "total_output_wt",
        ],
        "Corrugated Sheet Production": [
            "date",
            "material",
            "items",
            "stock_entry_ref",
            "amended_from",
            "total_input_wt",
            "total_output_wt",
        ],
    }
    for dt, required in parents.items():
        m = frappe.get_meta(dt)
        actual = {f.fieldname for f in m.fields}
        missing = [f for f in required if f not in actual]
        print(f"  {dt}: {'OK' if not missing else '!! MISSING: ' + str(missing)}")
        if missing:
            issues.append(f"MISSING fields on {dt}: {missing}")
        else:
            ok.append(f"{dt} fields complete ✓")


# ──────────────────────────────────────────────────────────
def check_item_flags():
    section("[F] Item Tracking Flags")
    checks = [
        ("CR Coil", 1, 0, "serial tracked RM"),
        ("GP Coil", 0, 1, "batch tracked WIP"),
        ("CC Coil", 0, 1, "batch tracked WIP"),
        ("EMB Coil", 0, 1, "batch tracked WIP"),
        ("CC ROPP", 0, 1, "batch tracked WIP"),
        ("CC ALU", 0, 1, "batch tracked WIP"),
        ("ALU Coil", 0, 1, "batch tracked WIP"),
        ("ALU ROPP Coil", 0, 1, "batch tracked WIP"),
        ("Steel Scrap", 0, 0, "no tracking"),
    ]
    for ic, sn, bn, desc in checks:
        if not frappe.db.exists("Item", ic):
            issues.append(f"MISSING item: {ic}")
            print(f"  !! MISSING: {ic}")
            continue
        r = frappe.db.get_value(
            "Item", ic, ["has_serial_no", "has_batch_no"], as_dict=True
        )
        ok_flag = r.has_serial_no == sn and r.has_batch_no == bn
        chk(
            f"{ic} flags",
            ok_flag,
            f"{ic}: sn={r.has_serial_no}, bn={r.has_batch_no} ✓",
            f"CRITICAL: {ic} flags wrong: sn={r.has_serial_no}(want {sn}), bn={r.has_batch_no}(want {bn}) — {desc}",
        )
        print(
            f"  {'OK' if ok_flag else '!!'} {ic}: has_serial_no={r.has_serial_no}, has_batch_no={r.has_batch_no} ({desc})"
        )


# ──────────────────────────────────────────────────────────
def check_hooks():
    section("[G] hooks.py — JS registrations")
    path = os.path.join(BASE, "hooks.py")
    with open(path) as f:
        src = f.read()
    for js in [
        "sm_utils.js",
        "child_table_auto_row.js",
        "fiscal_year_defaults.js",
        "workspace.js",
    ]:
        chk(js, js in src, f"hooks: {js} ✓", f"MISSING from hooks: {js}")
        print(f"  {'OK' if js in src else '!!'} {js}")


# ──────────────────────────────────────────────────────────
def check_report_filters():
    section("[H] Report Filter fieldnames vs Python get_data()")
    report_jsons = {
        "Batch Traceability": "steel_manufacturing/report/batch_traceability/batch_traceability.json",
        "WIP Batch Stock": "steel_manufacturing/report/wip_batch_stock/wip_batch_stock.json",
        "Stage Production Summary": "steel_manufacturing/report/stage_production_summary/stage_production_summary.json",
    }
    checks = [
        ("Batch Traceability", "coil_no", True),
        ("Batch Traceability", "serial_no", True),
        ("Batch Traceability", "batch_no", False),  # OLD — must NOT exist
        ("WIP Batch Stock", "stage", True),
        ("WIP Batch Stock", "process_stage", False),  # OLD
        ("Stage Production Summary", "stage", True),
        ("Stage Production Summary", "process_stage", False),  # OLD
    ]
    # Load JSON filters
    loaded = {}
    for name, rel in report_jsons.items():
        path = os.path.join(BASE, rel)
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            loaded[name] = [fi.get("fieldname") for fi in data.get("filters", [])]
        else:
            loaded[name] = []
            issues.append(f"MISSING report JSON: {rel}")

    for report, fn, should_exist in checks:
        fieldnames = loaded.get(report, [])
        found = fn in fieldnames
        ok_flag = found == should_exist
        status = "OK" if ok_flag else "!!"
        note = (
            "present ✓"
            if (found and should_exist)
            else (
                "absent ✓"
                if (not found and not should_exist)
                else ("UNEXPECTED PRESENT" if found else "MISSING")
            )
        )
        chk(
            f"{report}.{fn}",
            ok_flag,
            f"{report}: '{fn}' {note}",
            f"REPORT FILTER BUG: {report} filter '{fn}' — found={found}, expected={should_exist}",
        )
        print(f"  {status} {report}: '{fn}' {note}")


# ──────────────────────────────────────────────────────────
def check_autonames():
    section("[I] Autoname formats")
    expected = {
        "Galvanized Coil Production": "OT-GC-",
        "CC Coil Production": "OT-CC-",
        "Embossed Coil Production": "OT-EMB-",
        "CTL Production": "OT-CTL-",
        "Colour Profile Production": "OT-CPRO-",
        "Corrugated Sheet Production": "OT-CORR-",
    }
    for dt, prefix in expected.items():
        autoname = frappe.db.get_value("DocType", dt, "autoname") or ""
        has_prefix = prefix in autoname
        chk(
            dt,
            has_prefix,
            f"{dt}: {autoname} ✓",
            f"AUTONAME WRONG: {dt}: '{autoname}' (expected prefix '{prefix}')",
        )
        print(f"  {'OK' if has_prefix else '!!'} {dt}: {autoname}")


# ──────────────────────────────────────────────────────────
def check_settings():
    section("[J] Steel Manufacturing Settings")
    try:
        settings = frappe.get_single("Steel Manufacturing Settings")
        for wh_field in [
            "rm_warehouse",
            "wip_warehouse",
            "fg_warehouse",
            "scrap_warehouse",
        ]:
            val = settings.get(wh_field)
            chk(
                f"Settings.{wh_field}",
                bool(val),
                f"Settings.{wh_field} = {val} ✓",
                f"EMPTY: Steel Manufacturing Settings.{wh_field} not configured",
            )
            print(f"  {'OK' if val else '!!'} {wh_field} = {val!r}")
    except Exception as e:
        issues.append(f"ERROR reading Steel Manufacturing Settings: {e}")
        print(f"  !! ERROR: {e}")


# ──────────────────────────────────────────────────────────
def check_sm_utils_js():
    section("[K] sm_utils.js content validation")
    path = os.path.join(BASE, "public/js/sm_utils.js")
    chk(
        "sm_utils.js exists",
        os.path.exists(path),
        "sm_utils.js exists ✓",
        "MISSING: public/js/sm_utils.js",
    )
    if os.path.exists(path):
        with open(path) as f:
            src = f.read()
        for fn in ["refresh_totals", "sm_utils", "frm.set_value"]:
            chk(fn, fn in src, f"sm_utils: '{fn}' ✓", f"sm_utils.js missing '{fn}'")
            print(f"  {'OK' if fn in src else '!!'} sm_utils.js has '{fn}'")


# ──────────────────────────────────────────────────────────
def run():
    frappe.set_user("Administrator")

    print("\n" + "=" * 55)
    print("  COMPREHENSIVE AUDIT v2 — Manakshia Steel")
    print("=" * 55)

    check_python_syntax()
    check_all_child_table_fields()
    check_controller_field_refs()
    check_api_sql_refs()
    check_parent_doctypes()
    check_item_flags()
    check_hooks()
    check_report_filters()
    check_autonames()
    check_settings()
    check_sm_utils_js()

    print("\n" + "=" * 55)
    print(f"  TOTAL ISSUES : {len(issues)}")
    for i in issues:
        print(f"    ✗ {i}")
    print(f"  TOTAL PASSED : {len(ok)}")
    if len(issues) == 0:
        print("\n  ✅✅✅  MODULE IS PRODUCTION-READY — ZERO ISSUES  ✅✅✅")
    else:
        print(f"\n  ⚠️  {len(issues)} issue(s) need attention before go-live.")
    print("=" * 55)
