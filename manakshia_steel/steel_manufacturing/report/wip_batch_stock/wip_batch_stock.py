# Copyright (c) 2026, Blue Phoenix and contributors
# WIP Coil Stock — Coils currently in WIP (produced but not yet consumed as input)
# Queries exit child tables of Pattern A doctypes (Galvanizing, Embossing, CC Coating).
# For Pattern B (CTL, Colour Profile, Corrugated), tracks via Stock Entry batch ledger.

import frappe
from frappe import _

# ── Pattern A: Separate entry/exit child tables ────────────────────────────────
# Each tuple: (parent_doctype, label, exit_table, exit_coil_field, exit_wt_field, exit_thick_field)
PATTERN_A = [
    (
        "Galvanized Coil Production",
        "Galvanizing",
        "Galvanized Coil Exit",
        "gp_coil_no",
        "net_wt",
        "thick",
    ),
    (
        "Embossed Coil Production",
        "Embossing",
        "Embossed Coil Exit",
        "emb_coil_no",
        "emb_nt_wt",
        "fin_thk",
    ),
    (
        "CC Coil Production",
        "CC Coating",
        "CC Coil Exit",
        "cc_coil_no",
        "cc_coil_wt",
        "fin_thk",
    ),
]

# ── All entry child tables: to determine if a coil has been consumed ───────────
ENTRY_TABLES = [
    ("Galvanized Coil Entry", "coil_no", "Galvanized Coil Production"),
    ("Embossed Coil Entry", "coil_no", "Embossed Coil Production"),
    ("CC Coil Entry", "coil_no", "CC Coil Production"),
    ("Colour Profile Item", "coil_no", "Colour Profile Production"),
    ("CTL Production Item", "coil_no", "CTL Production"),
    # Corrugated Sheet Item uses packet_no (not coil_no) — excluded from coil tracking
]


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 150},
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
            "label": _("Thickness"),
            "fieldname": "thick",
            "fieldtype": "Float",
            "width": 90,
        },
        {
            "label": _("Net Wt (Kg)"),
            "fieldname": "net_wt",
            "fieldtype": "Float",
            "width": 110,
        },
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
    ]


def get_data(filters):
    show_wip_only = filters.get("show_wip_only")
    stage_filter = filters.get("stage")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # 1. Get all consumed coil_nos (in any submitted entry across all entry child tables)
    consumed_coil_nos = set()
    for entry_table, coil_field, parent_doctype in ENTRY_TABLES:
        rows = frappe.db.sql(
            f"""
            SELECT DISTINCT e.`{coil_field}` AS coil_no
            FROM `tab{entry_table}` e
            JOIN `tab{parent_doctype}` p ON p.name = e.parent
            WHERE p.docstatus = 1
              AND e.`{coil_field}` IS NOT NULL
              AND e.`{coil_field}` != ''
        """,
            as_dict=True,
        )
        for r in rows:
            if r["coil_no"]:
                consumed_coil_nos.add(r["coil_no"])

    # 2. Collect all produced coils from Pattern A exit tables
    rows = []
    for parent_doctype, label, exit_table, exit_coil, exit_wt, exit_thick in PATTERN_A:
        if stage_filter and label != stage_filter:
            continue

        date_cond = "p.docstatus = 1"
        params = {}
        if from_date:
            date_cond += " AND p.date >= %(from_date)s"
            params["from_date"] = from_date
        if to_date:
            date_cond += " AND p.date <= %(to_date)s"
            params["to_date"] = to_date

        produced = frappe.db.sql(
            f"""
            SELECT
                p.name    AS production_no,
                p.date,
                e.`{exit_coil}` AS coil_no,
                e.`{exit_wt}`   AS net_wt,
                e.`{exit_thick}` AS thick
            FROM `tab{exit_table}` e
            JOIN `tab{parent_doctype}` p ON p.name = e.parent
            WHERE {date_cond}
              AND e.`{exit_coil}` IS NOT NULL
              AND e.`{exit_coil}` != ''
            ORDER BY p.date DESC, p.name DESC
        """,
            params,
            as_dict=True,
        )

        for r in produced:
            coil_no = r["coil_no"]
            status = "Consumed" if coil_no in consumed_coil_nos else "In WIP"
            if show_wip_only and status == "Consumed":
                continue
            rows.append(
                {
                    "stage": label,
                    "production_no": r["production_no"],
                    "date": r["date"],
                    "coil_no": coil_no,
                    "thick": r.get("thick") or 0,
                    "net_wt": r.get("net_wt") or 0,
                    "status": status,
                }
            )

    return rows
