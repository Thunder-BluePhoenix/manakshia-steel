frappe.ui.form.on("Stock Entry", {

    onload: function (frm) {
        // Hide stock_entry_type if opened from custom sidebar
        var hide_types = [
            'Material Issue',
            'Material Receipt',
            'Stock Transfer In',
            'Stock Transfer Out'
        ];
        if (frm.is_new() && hide_types.includes(frm.doc.stock_entry_type)) {
            frm.set_df_property('stock_entry_type', 'hidden', 1);
            frm.set_df_property('stock_entry_type', 'read_only', 1);
        }
    },

    refresh: function (frm) {
        update_stock_entry_header(frm);
        toggle_custom_fields(frm);
        set_issue_filter(frm);

        // Add Create Material Receipt button on submitted Material Issues
        if (frm.doc.docstatus === 1 && frm.doc.purpose === "Material Issue") {
            frm.add_custom_button(
                "Create Receipt",
                function () {
                    frappe.new_doc("Stock Entry", {
                        stock_entry_type: "Material Receipt",
                        custom_material_issue: frm.doc.name,
                        custom_process: frm.doc.custom_process
                    });
                }
            ).addClass("btn-primary");
        }
    },

    purpose: function (frm) {
        frm.doc.__purpose_changed = true;
        update_stock_entry_header(frm);
        toggle_custom_fields(frm);
        set_issue_filter(frm);
    },

    stock_entry_type: function (frm) {
        if (frm.doc.stock_entry_type === "Stock Transfer In") {
            frm.set_value("naming_series", "STI/.#####");
        } else if (frm.doc.stock_entry_type === "Stock Transfer Out") {
            frm.set_value("naming_series", "STO/.#####");
        }
        update_stock_entry_header(frm);
        toggle_custom_fields(frm);
    },

    custom_process: function (frm) {
        if (!frm.doc.custom_process) return;

        frappe.db.get_value(
            "Process",
            frm.doc.custom_process,
            "naming_series",
            function (r) {
                if (r && r.naming_series) {
                    frm.set_value("naming_series", r.naming_series);
                }
            }
        );
    },

    validate: function (frm) {
        // Allow zero valuation rate for all items
        if (frm.doc.items) {
            frm.doc.items.forEach(row => {
                frappe.model.set_value(row.doctype, row.name, "allow_zero_valuation_rate", 1);
            });
        }
    },

    custom_material_issue: function (frm) {
        if (frm.doc.purpose !== "Material Receipt") return;
        if (!frm.doc.custom_material_issue) return;

        frm.clear_table("items");

        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Stock Entry",
                name: frm.doc.custom_material_issue
            },
            callback: function (r) {
                if (!r.message) return;

                let issue = r.message;

                // Copy process from Issue
                frm.set_value("custom_process", issue.custom_process);

                // Calculate total issued qty
                let issued_qty = {};
                issue.items.forEach(row => {
                    let key = row.item_code + "::" + (row.batch_no || "");
                    issued_qty[key] = (issued_qty[key] || 0) + row.qty;
                });

                // Get already received qty from submitted receipts
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Stock Entry",
                        filters: {
                            custom_material_issue: frm.doc.custom_material_issue,
                            purpose: "Material Receipt",
                            docstatus: 1
                        },
                        fields: ["name"]
                    },
                    callback: function (res) {
                        let received_qty = {};
                        let promises = [];

                        (res.message || []).forEach(d => {
                            promises.push(
                                frappe.client.get({
                                    doctype: "Stock Entry",
                                    name: d.name
                                }).then(doc => {
                                    doc.items.forEach(row => {
                                        let key = row.item_code + "::" + (row.batch_no || "");
                                        received_qty[key] = (received_qty[key] || 0) + row.qty;
                                    });
                                })
                            );
                        });

                        Promise.all(promises).then(() => {
                            issue.items.forEach(row => {
                                let key = row.item_code + "::" + (row.batch_no || "");
                                let remaining = (issued_qty[key] || 0) - (received_qty[key] || 0);

                                if (remaining > 0) {
                                    let r = frm.add_child("items");
                                    r.item_code = row.item_code;
                                    r.qty = remaining;
                                    r.batch_no = row.batch_no;
                                    r.uom = row.uom || row.stock_uom;
                                    r.stock_uom = row.stock_uom || row.uom;
                                    r.conversion_factor = 1;
                                    r.transfer_qty = r.qty * r.conversion_factor;
                                    r.allow_zero_valuation_rate = 1;
                                }
                            });

                            frm.refresh_field("items");
                        });
                    }
                });
            }
        });
    }
});

// ── Block serial/batch selector dialog from auto-opening on Stock Entry ───────
// erpnext scripts are fully loaded before doctype JS runs, so override directly.

// Guard 1: Override the global show_serial_batch_selector function
const _orig_show_selector = erpnext.show_serial_batch_selector;
erpnext.show_serial_batch_selector = function (frm, item_row, callback, on_close, show_dialog) {
    if (frm && frm.doctype === 'Stock Entry') {
        return;  // Block entirely for Stock Entry
    }
    return _orig_show_selector.apply(this, arguments);
};

// Guard 2: Override SerialBatchPackageSelector constructor
if (erpnext.SerialBatchPackageSelector) {
    const _OrigSelector = erpnext.SerialBatchPackageSelector;
    erpnext.SerialBatchPackageSelector = function (frm, item, callback) {
        if (frm && frm.doctype === 'Stock Entry') {
            return;  // No-op for Stock Entry
        }
        return new _OrigSelector(frm, item, callback);
    };
}

// ── Stock Entry Detail: clear serial/batch fields on item selection ───────────
frappe.ui.form.on('Stock Entry Detail', {
    item_code: function (frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, 'use_serial_batch_fields', 0);
        frappe.model.set_value(cdt, cdn, 'serial_and_batch_bundle', null);
        frappe.model.set_value(cdt, cdn, 'serial_no', null);
        frappe.model.set_value(cdt, cdn, 'batch_no', null);
    },
    form_render: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row && row.use_serial_batch_fields) {
            frappe.model.set_value(cdt, cdn, 'use_serial_batch_fields', 0);
        }
    }
});


function toggle_custom_fields(frm) {
    let is_transfer = ["Stock Transfer In", "Stock Transfer Out"].includes(frm.doc.stock_entry_type);

    // Hide process field if it's a transfer
    frm.toggle_display("custom_process", !is_transfer);

    // Hide issue field if it's a transfer, otherwise only show for Material Receipt
    let show_issue = !is_transfer && frm.doc.purpose === "Material Receipt";
    frm.toggle_display("custom_material_issue", show_issue);
    frm.toggle_reqd("custom_material_issue", false);
}

function set_issue_filter(frm) {
    frm.set_query("custom_material_issue", function () {
        return {
            filters: {
                purpose: "Material Issue",
                custom_process: frm.doc.custom_process || undefined,
                docstatus: 1
            }
        };
    });
}

function update_stock_entry_header(frm) {
    if (frm.page && frm.page.$title_area) {
        frm.page.$title_area.find(".custom-stock-entry-title").remove();
    }

    if (frm.doc.__islocal && !frm.doc.__purpose_changed) return;

    const transferTypes = ["Stock Transfer In", "Stock Transfer Out"];
    const isProcessEntry =
        frm.doc.purpose === "Material Issue" ||
        frm.doc.purpose === "Material Receipt";
    const isTransferEntry =
        frm.doc.stock_entry_type && transferTypes.includes(frm.doc.stock_entry_type);

    if (!isProcessEntry && !isTransferEntry) return;

    if (!frm.page || !frm.page.$title_area) return;

    let label = "";
    let gradient_color = "";

    if (frm.doc.stock_entry_type === "Stock Transfer In") {
        label = "Stock Transfer In";
        gradient_color = "linear-gradient(135deg, #0369a1 0%, #06b6d4 100%)";
    } else if (frm.doc.stock_entry_type === "Stock Transfer Out") {
        label = "Stock Transfer Out";
        gradient_color = "linear-gradient(135deg, #b91c1c 0%, #f97316 100%)";
    } else if (frm.doc.purpose === "Material Issue") {
        label = "Material Issue";
        gradient_color = "linear-gradient(135deg, #1e3a8a 0%, #6b21a8 100%)";
    } else if (frm.doc.purpose === "Material Receipt") {
        label = "Material Receipt";
        gradient_color = "linear-gradient(135deg, #129f41ff 0%, #12be5aff 100%)";
    }

    if (label) {
        const title_html = `
            <div class="custom-stock-entry-title"
                style="
                    font-size: 16px;
                    font-weight: 800;
                    background: ${gradient_color};
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    text-transform: uppercase;
                    letter-spacing: 1.5px;
                    white-space: nowrap;
                    margin-left: 10px;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    animation: fadeIn 0.5s ease-in;
                ">
                ${label}
            </div>
            <style>
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to   { opacity: 1; transform: translateY(0); }
                }
            </style>
        `;

        frm.page.$title_area.append(title_html);
    }
}