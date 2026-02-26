
// ============================================================================
// FISCAL YEAR DATE DEFAULTS
// Runs on every desk page. When a user opens a NEW document in any of the
// listed doctypes, this sets posting_date / transaction_date to the correct
// date within their session fiscal year so naming series tokens (.YYYY.)
// and ERPNext's fiscal year validation both work correctly.
// ============================================================================

(function () {
    // Doctypes that use posting_date
    const POSTING_DATE_DOCTYPES = [
        "Stock Entry",
        "Purchase Receipt",
        "Delivery Note",
    ];

    // Doctypes that use transaction_date
    const TRANSACTION_DATE_DOCTYPES = [
        "Purchase Order",
        "Material Request",
        "Supplier Quotation",
    ];

    // Cache for fiscal year dates fetched from server
    let _fy_cache = null;  // { year_start_date, year_end_date, effective_date }

    function get_fy_defaults(callback) {
        if (_fy_cache) {
            callback(_fy_cache);
            return;
        }

        const fiscal_year = frappe.defaults.get_user_default("fiscal_year");
        if (!fiscal_year) {
            callback(null);
            return;
        }

        frappe.call({
            method: "manakshia_steel.api.auth.get_fiscal_year_dates",
            args: { fiscal_year },
            callback: function (r) {
                if (!r.message) { callback(null); return; }

                const today = frappe.datetime.get_today();  // "YYYY-MM-DD"
                const start = r.message.year_start_date;
                const end = r.message.year_end_date;

                // If today is within the fiscal year use today, else use the year_end_date
                let effective_date;
                if (today >= start && today <= end) {
                    effective_date = today;
                } else {
                    effective_date = end;  // Past fiscal year — pin to last day
                }

                _fy_cache = { year_start_date: start, year_end_date: end, effective_date };
                callback(_fy_cache);
            }
        });
    }

    function apply_date_silently(frm, field, effective_date) {
        if (!frm.is_new()) return;
        if (frm.doc[field] === effective_date) return;  // already correct

        const today = frappe.datetime.get_today();

        // If using a past fiscal year date, mark "Edit Posting Date and Time" = 1
        // so ERPNext does NOT try to reset the date back to today (which causes the popup)
        if (effective_date !== today && frm.doc.hasOwnProperty("set_posting_time")) {
            frm.doc.set_posting_time = 1;
            frm.refresh_field("set_posting_time");
        }

        frm.doc[field] = effective_date;
        frm.refresh_field(field);
    }

    function apply_posting_date(frm) {
        if (!frm.is_new()) return;
        get_fy_defaults(function (fy) {
            if (!fy) return;
            apply_date_silently(frm, "posting_date", fy.effective_date);
        });
    }

    function apply_transaction_date(frm) {
        if (!frm.is_new()) return;
        get_fy_defaults(function (fy) {
            if (!fy) return;
            apply_date_silently(frm, "transaction_date", fy.effective_date);
        });
    }

    // Hook posting_date doctypes — refresh only (after ERPNext defaults are set)
    POSTING_DATE_DOCTYPES.forEach(function (doctype) {
        frappe.ui.form.on(doctype, {
            refresh: function (frm) { apply_posting_date(frm); }
        });
    });

    // Hook transaction_date doctypes — refresh only
    TRANSACTION_DATE_DOCTYPES.forEach(function (doctype) {
        frappe.ui.form.on(doctype, {
            refresh: function (frm) { apply_transaction_date(frm); }
        });
    });

})();
