
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
        "Request for Quotation"
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

    function validate_fy_date(frm, field) {
        get_fy_defaults(function (fy) {
            if (!fy) return;
            const date_val = frm.doc[field];
            if (!date_val) return;

            if (date_val < fy.year_start_date || date_val > fy.year_end_date) {
                let field_label = frappe.meta.get_label(frm.doctype, field) || field;
                frappe.msgprint({
                    title: __('Fiscal Year Validation'),
                    indicator: 'red',
                    message: __('The <b>{0}</b> ({1}) does not belong to your currently active Fiscal Year ({2} to {3}).', 
                        [
                            field_label, 
                            frappe.datetime.str_to_user(date_val),
                            frappe.datetime.str_to_user(fy.year_start_date),
                            frappe.datetime.str_to_user(fy.year_end_date)
                        ]
                    )
                });
                frappe.validated = false;
            }
        });
    }

    function validate_warehouse(frm, field) {
        const warehouse = frappe.defaults.get_user_default("warehouse");
        if (!warehouse) return;

        const wh_val = frm.doc[field];
        if (!wh_val) return;

        if (frm.doctype === "Stock Entry" || frm.doctype === "Waybill" || frm.doctype === "Waybill Return") {
            const from_wh = frm.doc.from_warehouse;
            const to_wh = frm.doc.to_warehouse;
            
            if (from_wh && from_wh !== warehouse) {
                frappe.msgprint({
                    title: __('Unit Validation'),
                    indicator: 'red',
                    message: __('The <b>Source Warehouse</b> ({0}) must be your active Unit ({1}).', [from_wh, warehouse])
                });
                frappe.validated = false;
            } else if (!from_wh && to_wh && to_wh !== warehouse) {
                frappe.msgprint({
                    title: __('Unit Validation'),
                    indicator: 'red',
                    message: __('For incoming stock, the <b>Target Warehouse</b> ({0}) must be your active Unit ({1}).', [to_wh, warehouse])
                });
                frappe.validated = false;
            }
        } else if (frm.doctype === "Production Order") {
            const source_wh = frm.doc.source_warehouse;
            if (source_wh && source_wh !== warehouse) {
                frappe.msgprint({
                    title: __('Unit Validation'),
                    indicator: 'red',
                    message: __('The <b>Source Warehouse</b> ({0}) must be your active Unit ({1}).', [source_wh, warehouse])
                });
                frappe.validated = false;
            }
        } else {
            // Other doctypes
            if (wh_val !== warehouse) {
                let field_label = frappe.meta.get_label(frm.doctype, field) || field;
                frappe.msgprint({
                    title: __('Unit Validation'),
                    indicator: 'red',
                    message: __('The <b>{0}</b> ({1}) does not match your currently active Unit ({2}). Please change it or switch units.', 
                        [field_label, wh_val, warehouse]
                    )
                });
                frappe.validated = false;
            }
        }
    }

    // Hook posting_date doctypes
    POSTING_DATE_DOCTYPES.forEach(function (doctype) {
        let events = {
            refresh: function (frm) { apply_posting_date(frm); },
            posting_date: function (frm) { validate_fy_date(frm, "posting_date"); },
            validate: function (frm) { 
                validate_fy_date(frm, "posting_date"); 
                if (frm.doctype === "Stock Entry") {
                    validate_warehouse(frm, "from_warehouse");
                    validate_warehouse(frm, "to_warehouse");
                } else if (frm.doctype === "Production Order") {
                    validate_warehouse(frm, "source_warehouse");
                    validate_warehouse(frm, "target_warehouse");
                } else {
                    validate_warehouse(frm, "set_warehouse");
                }
            }
        };

        if (doctype === "Stock Entry") {
            events.from_warehouse = function(frm) { validate_warehouse(frm, "from_warehouse"); };
            events.to_warehouse = function(frm) { validate_warehouse(frm, "to_warehouse"); };
        } else {
            events.set_warehouse = function(frm) { validate_warehouse(frm, "set_warehouse"); };
        }

        frappe.ui.form.on(doctype, events);
    });

    // Hook transaction_date doctypes
    TRANSACTION_DATE_DOCTYPES.forEach(function (doctype) {
        frappe.ui.form.on(doctype, {
            refresh: function (frm) { apply_transaction_date(frm); },
            transaction_date: function (frm) { validate_fy_date(frm, "transaction_date"); },
            set_warehouse: function(frm) { validate_warehouse(frm, "set_warehouse"); },
            validate: function (frm) { 
                validate_fy_date(frm, "transaction_date");
                validate_warehouse(frm, "set_warehouse");
            }
        });
    });

    const DATE_DOCTYPES = [
        "Waybill",
        "Waybill Return"
    ];

    DATE_DOCTYPES.forEach(function (doctype) {
        let events = {
            refresh: function (frm) { apply_posting_date(frm, "date"); },
            date: function (frm) { validate_fy_date(frm, "date"); },
            validate: function (frm) { 
                validate_fy_date(frm, "date"); 
                validate_warehouse(frm, "from_warehouse");
                validate_warehouse(frm, "to_warehouse");
            }
        };

        frappe.ui.form.on(doctype, events);
    });

})();

// ============================================================================
// GLOBAL UNIT UI DISPLAY
// Continually checks and injects a Unit badge into Frappe's top navbar.
// ============================================================================
$(document).ready(function() {
    setInterval(function() {
        if (!window.frappe || !frappe.defaults) return;
        
        const unit = frappe.defaults.get_user_default("warehouse") || frappe.defaults.get_default("warehouse");
        const fy = frappe.defaults.get_user_default("fiscal_year") || frappe.defaults.get_default("fiscal_year");
        
        if (!unit) return;

        let displayText = unit;
        if (fy) {
            displayText = unit + " - " + fy;
        }

        if (document.querySelector("#custom-unit-scope-badge")) {
            let badgeText = document.querySelector("#custom-unit-scope-badge .unit-text");
            if (badgeText && badgeText.innerText !== displayText) {
                badgeText.innerText = displayText;
            }
            return;
        }

        const badge = document.createElement("div");
        badge.id = "custom-unit-scope-badge";
        badge.innerHTML = `
            <i class="fa fa-industry" style="margin-right:8px;"></i>
            <span class="unit-text">${displayText}</span>
        `;
        Object.assign(badge.style, {
            position: "fixed",
            bottom: "16px",
            right: "16px",
            background: "linear-gradient(135deg, #D41F26 0%, #2E3D92 100%)",
            color: "#fff",
            padding: "5px 12px",
            borderRadius: "18px",
            fontSize: "11px",
            fontWeight: "700",
            fontFamily: "Inter, sans-serif",
            boxShadow: "0 4px 12px rgba(46, 61, 146, 0.35)",
            zIndex: "9999",
            display: "flex",
            alignItems: "center",
            letterSpacing: "0.4px",
            cursor: "default",
            userSelect: "none",
            textTransform: "uppercase",
            border: "1px solid rgba(255,255,255,0.15)",
            animation: "fadeInUp 0.5s ease-out"
        });

        // Add subtle animation
        const style = document.createElement('style');
        style.innerHTML = `
            @keyframes fadeInUp {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            #custom-unit-scope-badge:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(46, 61, 146, 0.6);
                transition: all 0.3s ease;
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(badge);
    }, 1000);
});
