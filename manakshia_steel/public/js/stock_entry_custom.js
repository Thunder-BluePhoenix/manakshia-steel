// Auto-select Naming Series from Process in Stock Entry
frappe.ui.form.on("Stock Entry", {
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
    }
});

// Auto-fill Material Receipt items & remaining qty in Stock Entry
frappe.ui.form.on("Stock Entry", {
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

                // copy process from Issue
                frm.set_value("custom_process", issue.custom_process);

                // total issued qty
                let issued_qty = {};
                issue.items.forEach(row => {
                    let key = row.item_code + "::" + (row.batch_no || "");
                    issued_qty[key] = (issued_qty[key] || 0) + row.qty;
                });

                // already received qty
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
                                        received_qty[key] =
                                            (received_qty[key] || 0) + row.qty;
                                    });
                                })
                            );
                        });

                        Promise.all(promises).then(() => {

                            issue.items.forEach(row => {
                                let key = row.item_code + "::" + (row.batch_no || "");
                                let remaining =
                                    (issued_qty[key] || 0) -
                                    (received_qty[key] || 0);

                                if (remaining > 0) {
                                    let r = frm.add_child("items");
                                    r.item_code = row.item_code;
                                    r.qty = remaining;
                                    r.batch_no = row.batch_no;
                                    r.uom = row.uom || row.stock_uom;
                                    r.stock_uom = row.stock_uom || row.uom;
                                    r.conversion_factor = 1;
                                    r.transfer_qty = r.qty * r.conversion_factor;
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

// Create Material Receipt button
frappe.ui.form.on("Stock Entry", {
    refresh: function (frm) {

        if (
            frm.doc.docstatus === 1 &&
            frm.doc.purpose === "Material Issue"
        ) {

            frm.add_custom_button(
                "Create Material Receipt",
                function () {

                    frappe.new_doc("Stock Entry", {
                        stock_entry_type: "Material Receipt",
                        custom_material_issue: frm.doc.name,
                        custom_process: frm.doc.custom_process
                    });

                },
                __("Create")
            );
        }
    }
});

// Show/hide Material Issue field based on Purpose
frappe.ui.form.on("Stock Entry", {
    refresh: function (frm) {
        toggle_issue_field(frm);
        set_issue_filter(frm);
    },

    purpose: function (frm) {
        toggle_issue_field(frm);
        set_issue_filter(frm);
    }
});

function toggle_issue_field(frm) {
    let show = frm.doc.purpose === "Material Receipt";
    frm.toggle_display("custom_material_issue", show);
    frm.toggle_reqd("custom_material_issue", show);
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

frappe.ui.form.on("Stock Entry", {
    refresh(frm) {
        // Don't show on refresh, only when purpose is changed
        if (frm.doc.__islocal && !frm.doc.__purpose_changed) {
            // Remove any existing label on new form
            if (frm.page && frm.page.$title_area) {
                frm.page.$title_area.find(".custom-stock-entry-title").remove();
            }
        } else {
            update_stock_entry_header(frm);
        }
    },

    purpose(frm) {
        // Mark that purpose has been changed
        frm.doc.__purpose_changed = true;
        update_stock_entry_header(frm);
    }
});

function update_stock_entry_header(frm) {
    // Always remove old custom title first
    if (frm.page && frm.page.$title_area) {
        frm.page.$title_area.find(".custom-stock-entry-title").remove();
    }

    // Only proceed if purpose is explicitly set and is Material Issue or Material Receipt
    if (!frm.doc.purpose || (frm.doc.purpose !== "Material Issue" && frm.doc.purpose !== "Material Receipt")) {
        return;
    }

    if (!frm.page || !frm.page.$title_area) return;

    let label = "";
    let gradient_color = "";

    if (frm.doc.purpose === "Material Issue") {
        label = "Material Issue Entry";
        gradient_color = "linear-gradient(135deg, #1e3a8a 0%, #6b21a8 100%)";
    } else if (frm.doc.purpose === "Material Receipt") {
        label = "Material Receipt Entry";
        gradient_color = "linear-gradient(135deg, #be123c 0%, #9f1239 100%)";
    }

    if (label) {
        const title_html = `
            <div class="custom-stock-entry-title"
                style="
                    font-size: 20px;
                    font-weight: 800;
                    background: ${gradient_color};
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    text-transform: uppercase;
                    letter-spacing: 1.5px;
                    white-space: nowrap;
                    margin-left: 200px;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    animation: fadeIn 0.5s ease-in;
                ">
                ${label}
            </div>
            <style>
                @keyframes fadeIn {
                    from {
                        opacity: 0;
                        transform: translateY(-10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
            </style>
        `;

        frm.page.$title_area.append(title_html);
    }
}