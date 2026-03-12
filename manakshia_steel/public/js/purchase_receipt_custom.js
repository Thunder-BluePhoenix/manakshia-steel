// ── Naming Series ─────────────────────────────────────────────────────────────

const PR_TYPE_TO_SERIES = {
    "RAW MATERIAL": "GRN/R.#####",
    "CAPITAL GOODS": "GRN/C.#####",
    "POWER AND FUELS": "GRN/F.#####",
    "GENERAL GOODS": "GRN/G.#####",
    "JOB WORK": "GRN/J.#####",
};

const PR_DEFAULT_SERIES = "MAT-PRE-.YYYY.-";

function pr_inject_series(frm) {
    // Inject custom series into the field's option list in-memory so the
    // dropdown shows them. Server-side validation is handled by the
    // purchase_receipt_hooks.py monkey-patch, so no DB change is needed.
    const field = frm.get_field("naming_series");
    if (!field) return;

    const existing = (field.df.options || "").split("\n").map(s => s.trim()).filter(Boolean);
    const toAdd = Object.values(PR_TYPE_TO_SERIES).filter(s => !existing.includes(s));

    if (toAdd.length) {
        field.df.options = [...existing, ...toAdd].join("\n");
        field.refresh();
    }
}

function pr_apply_series(frm) {
    if (!frm.doc.__islocal) return;
    const series = PR_TYPE_TO_SERIES[frm.doc.custom_purchase_receipt_type] || PR_DEFAULT_SERIES;
    if (frm.doc.naming_series !== series) {
        frm.set_value("naming_series", series);
    }
}

// ── Purchase Receipt Item ─────────────────────────────────────────────────────

frappe.ui.form.on("Purchase Receipt Item", {
    warehouse(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.warehouse && row.rejected_warehouse && row.warehouse === row.rejected_warehouse) {
            frappe.model.set_value(cdt, cdn, "rejected_warehouse", "");
        }
    },
    rejected_warehouse(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.warehouse && row.rejected_warehouse && row.warehouse === row.rejected_warehouse) {
            frappe.msgprint(__("Accepted and Rejected Warehouse cannot be the same."));
            frappe.model.set_value(cdt, cdn, "rejected_warehouse", "");
        }
    },
});

// ── Purchase Receipt ──────────────────────────────────────────────────────────

frappe.ui.form.on("Purchase Receipt", {
    onload(frm) {
        pr_inject_series(frm);
        pr_apply_series(frm);
    },

    refresh(frm) {
        pr_inject_series(frm);

        if (frm.doc.__islocal) {
            pr_apply_series(frm);
        }

        // Clear rejected_warehouse if it matches warehouse
        (frm.doc.items || []).forEach(row => {
            if (row.warehouse && row.rejected_warehouse && row.warehouse === row.rejected_warehouse) {
                frappe.model.set_value(row.doctype, row.name, "rejected_warehouse", "");
            }
        });
    },

    custom_purchase_receipt_type(frm) {
        pr_inject_series(frm);
        const series = PR_TYPE_TO_SERIES[frm.doc.custom_purchase_receipt_type] || PR_DEFAULT_SERIES;
        frm.set_value("naming_series", series);
        frappe.show_alert({ message: __("Naming series set to: {0}", [series]), indicator: "blue" });
    },
});