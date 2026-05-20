# Copyright (c) 2026, Blue Phoenix and contributors
# Coil Traceability — Given a coil_no, trace its full journey across all production stages.

import frappe
from frappe import _

# ── All entry child tables where a coil is consumed ───────────────────────────
ENTRY_SOURCES = [
    ("Galvanized Coil Production", "Galvanized Coil Entry", "coil_no", "chln_net_wt"),
    ("Embossed Coil Production", "Embossed Coil Entry", "coil_no", "chln_net_w"),
    ("CC Coil Production", "CC Coil Entry", "coil_no", "chln_net_wt"),
    ("Colour Profile Production", "Colour Profile Item", "coil_no", "coil_wt"),
    ("CTL Production", "CTL Production Item", "coil_no", "coil_weight"),
    (
        "Corrugated Sheet Production",
        "Corrugated Sheet Item",
        "packet_no",
        "packet_wt",
    ),  # #12 fix
]

# ── All exit child tables where a coil is produced ────────────────────────────
EXIT_SOURCES = [
    ("Galvanized Coil Production", "Galvanized Coil Exit", "gp_coil_no", "net_wt"),
    ("Embossed Coil Production", "Embossed Coil Exit", "emb_coil_no", "emb_nt_wt"),
    ("CC Coil Production", "CC Coil Exit", "cc_coil_no", "cc_coil_wt"),
]

STAGE_LABELS = {
    "Galvanized Coil Production": "Galvanizing",
    "Embossed Coil Production": "Embossing",
    "CC Coil Production": "CC Coating",
    "Colour Profile Production": "Colour Profiling",
    "CTL Production": "Cut to Length",
    "Corrugated Sheet Production": "Corrugation",
}


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Direction"),
            "fieldname": "direction",
            "fieldtype": "Data",
            "width": 110,
        },
        {"label": _("Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 160},
        {
            "label": _("Production No."),
            "fieldname": "production_no",
            "fieldtype": "Data",
            "width": 200,
        },
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
        {
            "label": _("Coil No."),
            "fieldname": "coil_no",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Weight (Kg)"),
            "fieldname": "weight",
            "fieldtype": "Float",
            "width": 110,
        },
        {"label": _("Role"), "fieldname": "role", "fieldtype": "Data", "width": 130},
    ]


def get_data(filters):
    coil_no = (filters.get("coil_no") or "").strip()
    serial_no = (filters.get("serial_no") or "").strip()

    # Allow search by Serial No (CR Coil RM) — look it up in GCP Entry
    if serial_no and not coil_no:
        rows = []
        params = {"sn": serial_no}
        found = frappe.db.sql(
            """
            SELECT p.name AS production_no, p.date, e.coil_no AS coil_no, e.chln_net_wt AS weight
            FROM `tabGalvanized Coil Entry` e
            JOIN `tabGalvanized Coil Production` p ON p.name = e.parent
            WHERE e.coil_no = %(sn)s AND p.docstatus = 1
            ORDER BY p.date
        """,
            params,
            as_dict=True,
        )
        for r in found:
            rows.append(
                {
                    "direction": "⬆ Consumed as Input",
                    "stage": "Galvanizing (Serial No)",
                    "production_no": r["production_no"],
                    "date": r["date"],
                    "coil_no": r["coil_no"],
                    "weight": r.get("weight") or 0,
                    "role": "CR Coil (RM)",
                }
            )
        return rows

    if not coil_no:
        return []

    rows = []
    params = {"coil_no": coil_no}

    # 1. Find all stages where this coil was CONSUMED as input
    for parent_dt, entry_tbl, coil_fld, wt_fld in ENTRY_SOURCES:
        found = frappe.db.sql(
            f"""
            SELECT
                p.name  AS production_no,
                p.date,
                e.`{coil_fld}` AS coil_no,
                e.`{wt_fld}`   AS weight
            FROM `tab{entry_tbl}` e
            JOIN `tab{parent_dt}` p ON p.name = e.parent
            WHERE e.`{coil_fld}` = %(coil_no)s
              AND p.docstatus = 1
            ORDER BY p.date
        """,
            params,
            as_dict=True,
        )

        for r in found:
            rows.append(
                {
                    "direction": "⬆ Consumed as Input",
                    "stage": STAGE_LABELS.get(parent_dt, parent_dt),
                    "production_no": r["production_no"],
                    "date": r["date"],
                    "coil_no": r["coil_no"],
                    "weight": r.get("weight") or 0,
                    "role": "Input Coil",
                }
            )

    # 2. Find all stages where this coil was PRODUCED as output
    for parent_dt, exit_tbl, coil_fld, wt_fld in EXIT_SOURCES:
        found = frappe.db.sql(
            f"""
            SELECT
                p.name  AS production_no,
                p.date,
                e.`{coil_fld}` AS coil_no,
                e.`{wt_fld}`   AS weight
            FROM `tab{exit_tbl}` e
            JOIN `tab{parent_dt}` p ON p.name = e.parent
            WHERE e.`{coil_fld}` = %(coil_no)s
              AND p.docstatus = 1
            ORDER BY p.date
        """,
            params,
            as_dict=True,
        )

        for r in found:
            rows.append(
                {
                    "direction": "✅ Produced as Output",
                    "stage": STAGE_LABELS.get(parent_dt, parent_dt),
                    "production_no": r["production_no"],
                    "date": r["date"],
                    "coil_no": r["coil_no"],
                    "weight": r.get("weight") or 0,
                    "role": "Produced Coil",
                }
            )

    # Sort by date then direction so the timeline flows correctly
    rows.sort(key=lambda x: (str(x.get("date") or ""), x["direction"]))
    return rows
