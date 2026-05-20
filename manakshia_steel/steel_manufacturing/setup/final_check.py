"""Check all parent DocType selector fields used by controller + JS field refs"""

import os

import frappe

BASE = "/home/prasun/frappe-bench-16/apps/manakshia_steel/manakshia_steel"
issues = []


def run():
    frappe.set_user("Administrator")

    # ── 1. Parent DocType fields used by controller ──────────────────────────
    print("\n[1] Parent DocType selector fields (used by controller)")
    checks = {
        "Galvanized Coil Production": [
            "date",
            "shift",
            "operator_name",
            "entry_items",
            "exit_items",
            "stock_entry_ref",
            "total_input_wt",
            "total_output_wt",
            "day",
        ],
        "CC Coil Production": [
            "date",
            "process_type",
            "entry_items",
            "exit_items",
            "stock_entry_ref",
            "total_input_wt",
            "total_output_wt",
            "day",
        ],
        "Embossed Coil Production": [
            "date",
            "coil_type",
            "entry_items",
            "exit_items",
            "stock_entry_ref",
            "total_input_wt",
            "total_output_wt",
            "day",
        ],
        "CTL Production": [
            "date",
            "material",
            "select_type",
            "items",
            "stock_entry_ref",
            "total_input_wt",
            "total_output_wt",
            "day",
        ],
        "Colour Profile Production": [
            "date",
            "select_coil",
            "material",
            "items",
            "stock_entry_ref",
            "total_input_wt",
            "total_output_wt",
            "day",
        ],
        "Corrugated Sheet Production": [
            "date",
            "material",
            "items",
            "stock_entry_ref",
            "total_input_wt",
            "total_output_wt",
            "day",
        ],
    }
    for dt, required in checks.items():
        m = frappe.get_meta(dt)
        actual = {f.fieldname for f in m.fields}
        for fn in required:
            if fn in actual:
                print(f"  OK  {dt}.{fn}")
            else:
                issues.append(
                    f"CRITICAL: {dt} missing field '{fn}' — controller/JS will fail"
                )
                print(f"  !! MISSING: {dt}.{fn}")

    # ── 2. JS field refs vs JSON child table fields ─────────────────────────
    print("\n[2] JS auto-fill field refs vs child table JSON fields")
    js_checks = [
        # (js_file, target_child_table, fieldnames_that_must_exist_in_json)
        (
            "doctype/galvanized_coil_production/galvanized_coil_production.js",
            "Galvanized Coil Entry",
            ["coil_no", "thick", "width", "supplier", "minl_gr_wt"],
        ),
        (
            "doctype/cc_coil_production/cc_coil_production.js",
            "CC Coil Entry",
            ["coil_no", "thick", "width", "brand", "length", "minl_net_wt"],
        ),
        (
            "doctype/embossed_coil_production/embossed_coil_production.js",
            "Embossed Coil Entry",
            ["coil_no", "thick", "width", "brand", "colour", "length", "minl_net_w"],
        ),
        (
            "doctype/ctl_production/ctl_production.js",
            "CTL Production Item",
            [
                "coil_no",
                "thick",
                "width",
                "brand",
                "colour",
                "coil_length",
                "coil_weight",
            ],
        ),
        (
            "doctype/colour_profile_production/colour_profile_production.js",
            "Colour Profile Item",
            [
                "coil_no",
                "thick",
                "width",
                "brand",
                "colour",
                "pattern",
                "length",
                "coil_wt",
                "qnty_kg",
            ],
        ),
        (
            "doctype/corrugated_sheet_production/corrugated_sheet_production.js",
            "Corrugated Sheet Item",
            [
                "packet_no",
                "thick",
                "width",
                "brand",
                "colour",
                "length",
                "packet_wt",
                "qnty_kg",
            ],
        ),
    ]
    for js_rel, dt, expected_fields in js_checks:
        m = frappe.get_meta(dt)
        actual = {f.fieldname for f in m.fields}
        for fn in expected_fields:
            if fn in actual:
                print(f"  OK  {dt}.{fn}")
            else:
                issues.append(
                    f"JS-SCHEMA MISMATCH: {dt}.{fn} used in {js_rel} but not in schema"
                )
                print(
                    f"  !! MISMATCH: {dt}.{fn} not in schema (referenced in {js_rel})"
                )
        # Also verify JS doesn't use any old field names
        js_path = os.path.join(BASE, js_rel)
        if os.path.exists(js_path):
            js_src = open(js_path).read()
            for bad_fn in [
                "updates.colr",
                "updates.thik",
                "updates.wdth",
                "updates.lengt",
                "updates.col ",
                "updates.pat ",
                "updates.stsc",
            ]:
                if bad_fn in js_src:
                    issues.append(f"OLD JS FIELD: '{bad_fn}' in {js_rel}")
                    print(f"  !! OLD FIELD in JS: '{bad_fn}'")

    # ── 3. Stock Entry type validation ──────────────────────────────────────
    print("\n[3] Stock Entry type 'Manufacture' exists")
    exists = frappe.db.exists("Stock Entry Type", "Manufacture")
    if exists:
        print("  OK  Stock Entry Type 'Manufacture' exists")
    else:
        issues.append(
            "CRITICAL: Stock Entry Type 'Manufacture' not found — SE submissions will fail"
        )
        print("  !! MISSING: Stock Entry Type 'Manufacture'")

    # ── 4. Entry table child link fields in parent JSONs ───────────────────
    print("\n[4] Parent child table link fields point to correct child DocTypes")
    links = {
        "Galvanized Coil Production": [
            ("entry_items", "Galvanized Coil Entry"),
            ("exit_items", "Galvanized Coil Exit"),
        ],
        "CC Coil Production": [
            ("entry_items", "CC Coil Entry"),
            ("exit_items", "CC Coil Exit"),
        ],
        "Embossed Coil Production": [
            ("entry_items", "Embossed Coil Entry"),
            ("exit_items", "Embossed Coil Exit"),
        ],
        "CTL Production": [("items", "CTL Production Item")],
        "Colour Profile Production": [("items", "Colour Profile Item")],
        "Corrugated Sheet Production": [("items", "Corrugated Sheet Item")],
    }
    for dt, pairs in links.items():
        m = frappe.get_meta(dt)
        for fieldname, expected_child in pairs:
            f = m.get_field(fieldname)
            if f and f.options == expected_child:
                print(f"  OK  {dt}.{fieldname} → {expected_child}")
            elif f:
                issues.append(
                    f"WRONG CHILD TABLE: {dt}.{fieldname} → {f.options} (expected {expected_child})"
                )
                print(
                    f"  !! WRONG: {dt}.{fieldname} → {f.options} (want {expected_child})"
                )
            else:
                issues.append(f"MISSING CHILD LINK: {dt}.{fieldname}")
                print(f"  !! MISSING: {dt}.{fieldname}")

    # ── SUMMARY ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print(f"ISSUES: {len(issues)}")
    for i in issues:
        print(f"  ✗ {i}")
    if not issues:
        print("  ✅  ALL CHECKS PASSED — FULLY PRODUCTION-READY")
    print("=" * 55)
