# Copyright (c) 2026, Blue Phoenix and contributors
# Stage Production Summary — Production per stage per date range
# Covers all 6 steel manufacturing production doctypes.

import frappe
from frappe import _

# ── Map of each production stage to its child table metadata ──────────────────
# (parent_doctype, child_entry_table, entry_coil_field, entry_weight_field,
#   child_exit_table, exit_coil_field, exit_weight_field)
# For Pattern B doctypes (single items table): exit fields = None
STAGE_CONFIG = [
    {
        "stage": "Galvanized Coil Production",
        "label": "Galvanizing",
        "entry_table": "Galvanized Coil Entry",
        "entry_coil": "coil_no",
        "entry_wt": "chln_net_wt",
        "exit_table": "Galvanized Coil Exit",
        "exit_coil": "gp_coil_no",
        "exit_wt": "net_wt",
    },
    {
        "stage": "Embossed Coil Production",
        "label": "Embossing",
        "entry_table": "Embossed Coil Entry",
        "entry_coil": "coil_no",
        "entry_wt": "chln_net_w",
        "exit_table": "Embossed Coil Exit",
        "exit_coil": "emb_coil_no",
        "exit_wt": "emb_nt_wt",
    },
    {
        "stage": "CC Coil Production",
        "label": "CC Coating",
        "entry_table": "CC Coil Entry",
        "entry_coil": "coil_no",
        "entry_wt": "chln_net_wt",
        "exit_table": "CC Coil Exit",
        "exit_coil": "cc_coil_no",
        "exit_wt": "cc_coil_wt",
    },
    {
        "stage": "Colour Profile Production",
        "label": "Colour Profiling",
        "entry_table": "Colour Profile Item",
        "entry_coil": "coil_no",
        "entry_wt": "coil_wt",
        "exit_table": None,  # Single items table (no separate exit)
        "exit_coil": None,
        "exit_wt": "qnty_kg",  # Output qty is in same table
    },
    {
        "stage": "Corrugated Sheet Production",
        "label": "Corrugation",
        "entry_table": "Corrugated Sheet Item",
        "entry_coil": "packet_no",
        "entry_wt": "packet_wt",
        "exit_table": None,
        "exit_coil": None,
        "exit_wt": "qnty_kg",
    },
    {
        "stage": "CTL Production",
        "label": "Cut to Length",
        "entry_table": "CTL Production Item",
        "entry_coil": "coil_no",
        "entry_wt": "coil_weight",
        "exit_table": None,
        "exit_coil": None,
        "exit_wt": "packet_wt",
    },
]


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 180},
        {
            "label": _("Production No."),
            "fieldname": "production_no",
            "fieldtype": "Data",
            "width": 180,
        },
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": _("Shift"), "fieldname": "shift", "fieldtype": "Data", "width": 70},
        {
            "label": _("Operator"),
            "fieldname": "operator_name",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Input Coils"),
            "fieldname": "input_count",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("Input Wt (Kg)"),
            "fieldname": "input_wt",
            "fieldtype": "Float",
            "width": 120,
        },
        {
            "label": _("Output Coils/Pcs"),
            "fieldname": "output_count",
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "label": _("Output Wt (Kg)"),
            "fieldname": "output_wt",
            "fieldtype": "Float",
            "width": 120,
        },
        {
            "label": _("Variance Wt (Kg)"),
            "fieldname": "variance_wt",
            "fieldtype": "Float",
            "width": 130,
        },
    ]


def get_data(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    stage_filter = filters.get("stage")

    rows = []

    for cfg in STAGE_CONFIG:
        if stage_filter and cfg["stage"] != stage_filter:
            continue

        parent = cfg["stage"]
        e_tbl = cfg["entry_table"]
        e_wt = cfg["entry_wt"]
        x_tbl = cfg["exit_table"]
        x_wt = cfg["exit_wt"]

        # Build WHERE for parent date
        conds = ["docstatus = 1"]
        params = {}
        if from_date:
            conds.append("`date` >= %(from_date)s")
            params["from_date"] = from_date
        if to_date:
            conds.append("`date` <= %(to_date)s")
            params["to_date"] = to_date
        where = " AND ".join(conds)

        # Parent documents
        parents = frappe.db.sql(
            f"""
            SELECT name, `date`, shift, operator_name
            FROM `tab{parent}`
            WHERE {where}
            ORDER BY `date` DESC, name DESC
        """,
            params,
            as_dict=True,
        )

        for par in parents:
            pname = par["name"]
            params2 = {"pname": pname}

            # Input (entry_items or items)
            entry_count = frappe.db.sql(
                f"""
                SELECT COUNT(*) AS cnt, COALESCE(SUM(`{e_wt}`), 0) AS tot
                FROM `tab{e_tbl}` WHERE parent = %(pname)s
            """,
                params2,
                as_dict=True,
            )[0]

            if x_tbl:
                # Pattern A: separate exit table
                exit_count = frappe.db.sql(
                    f"""
                    SELECT COUNT(*) AS cnt, COALESCE(SUM(`{x_wt}`), 0) AS tot
                    FROM `tab{x_tbl}` WHERE parent = %(pname)s
                """,
                    params2,
                    as_dict=True,
                )[0]
            else:
                # Pattern B: output qty is in same items table
                exit_count = frappe.db.sql(
                    f"""
                    SELECT COUNT(*) AS cnt, COALESCE(SUM(`{x_wt}`), 0) AS tot
                    FROM `tab{e_tbl}` WHERE parent = %(pname)s
                """,
                    params2,
                    as_dict=True,
                )[0]

            in_wt = entry_count["tot"] or 0
            out_wt = exit_count["tot"] or 0

            rows.append(
                {
                    "stage": cfg["label"],
                    "production_no": pname,
                    "date": par["date"],
                    "shift": par.get("shift") or "",
                    "operator_name": par.get("operator_name") or "",
                    "input_count": entry_count["cnt"] or 0,
                    "input_wt": in_wt,
                    "output_count": exit_count["cnt"] or 0,
                    "output_wt": out_wt,
                    "variance_wt": in_wt - out_wt,
                }
            )

    return rows
