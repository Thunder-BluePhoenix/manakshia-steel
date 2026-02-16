// Logic to fetch details when Coil Number (Serial No) is set in Packing Slip
// Returns a Promise that resolves when details are set
var fetch_packing_details = function (frm, cdt, cdn, fallback_item_code) {
    let row = locals[cdt][cdn];
    if (row.coil_number) {
        return frappe.db.get_value("Serial No", row.coil_number, ["item_code", "batch_no"])
            .then(res => {
                let d = res.message || {};

                // Fallback: If Serial No invalid or not yet committed, use fallback item code
                let item_code = d.item_code || fallback_item_code;
                let batch_no = d.batch_no;

                if (batch_no) frappe.model.set_value(cdt, cdn, "batch_no", batch_no);

                if (item_code) {
                    return frappe.db.get_value("Item", item_code, ["custom_thickness_in_mm", "custom_width_in_mm"])
                        .then(r => {
                            if (r.message) {
                                frappe.model.set_value(cdt, cdn, "thickness", r.message.custom_thickness_in_mm || "");
                                frappe.model.set_value(cdt, cdn, "width", r.message.custom_width_in_mm || "");
                            }
                            // Always return true to signal completion
                            return true;
                        });
                }
                return true;
            })
            .catch(err => {
                console.error("Error fetching details for " + row.coil_number, err);
                return true; // Resolve anyway to not break Promise.all
            });
    }
    return Promise.resolve();
};

frappe.ui.form.on('Packing Slip Child', {
    coil_number: function (frm, cdt, cdn) {
        // We don't have easy access to fallback_item_code here without searching parent items
        // But usually manual entry means Serial No exists. 
        // We can try to find it in parent items if needed, but keeping it simple for now.
        fetch_packing_details(frm, cdt, cdn);
    }
});

// Logic to Auto-Populate Packing Slip from Items table Serial Nos
var sync_packing_slip = function (frm) {
    if (!frm.doc.items) return;

    let all_serials_map = {}; // Map serial -> { item_code: ..., batch_no: ... }
    let distinct_item_codes = new Set();
    let promises = [];

    // Gather all serials from Items table
    $.each(frm.doc.items, function (i, row) {
        if (row.item_code) distinct_item_codes.add(row.item_code);

        if (row.serial_no) {
            let serials = row.serial_no.split(/\r?\n/);
            serials.forEach(function (s) {
                if (s.trim()) {
                    all_serials_map[s.trim()] = { item_code: row.item_code, batch_no: row.batch_no };
                }
            });
        }
        else if (row.serial_and_batch_bundle) {
            let p = frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Serial and Batch Bundle",
                    name: row.serial_and_batch_bundle
                }
            }).then(r => {
                if (r.message && r.message.entries) {
                    r.message.entries.forEach(entry => {
                        if (entry.serial_no) {
                            all_serials_map[entry.serial_no] = {
                                item_code: row.item_code,
                                batch_no: entry.batch_no || row.batch_no
                            };
                        }
                    });
                }
            });
            promises.push(p);
        }
    });

    // Step 1: Resolve all serial sources (Serial Bundle fetch)
    Promise.all(promises).then(() => {
        // Step 1.5: Batch Fetch Item Details (Thickness/Width)
        let item_data_map = {};

        let item_details_promises = [];
        distinct_item_codes.forEach(item_code => {
            let p = frappe.db.get_value("Item", item_code, ["custom_thickness_in_mm", "custom_width_in_mm"])
                .then(r => {
                    if (r && r.message) {
                        item_data_map[item_code] = r.message;
                    }
                });
            item_details_promises.push(p);
        });

        Promise.all(item_details_promises).then(() => {
            // Now we have all serials mapped, AND all item details fetched.
            // We can add rows synchronously and they will appear instantly with data.

            let existing_coils = [];
            let has_empty_first_row = false;

            if (frm.doc.custom_packing_slip && frm.doc.custom_packing_slip.length > 0) {
                // Check if the first row is effectively empty (no coil number)
                // sometimes Frappe adds a blank row by default
                if (!frm.doc.custom_packing_slip[0].coil_number) {
                    has_empty_first_row = true;
                    // We don't include it in existing_coils so we don't block adding, 
                    // but we will reuse it.
                }
                existing_coils = frm.doc.custom_packing_slip.map(r => r.coil_number).filter(c => c);
            }

            let all_serials = Object.keys(all_serials_map);
            let to_add = all_serials.filter(s => !existing_coils.includes(s));

            if (to_add.length > 0) {
                to_add.forEach(function (sn, index) {
                    let child;

                    // Reuse first row if it's empty and this is the first item we are adding
                    if (index === 0 && has_empty_first_row) {
                        child = frm.doc.custom_packing_slip[0];
                    } else {
                        child = frm.add_child("custom_packing_slip");
                    }

                    child.coil_number = sn;

                    // Apply Details Immediately
                    let mapped_data = all_serials_map[sn];
                    if (mapped_data) {
                        child.batch_no = mapped_data.batch_no;
                        child.item_code = mapped_data.item_code; // If field exists

                        // Look up item details
                        let item_details = item_data_map[mapped_data.item_code];
                        if (item_details) {
                            child.thickness = item_details.custom_thickness_in_mm || "";
                            child.width = item_details.custom_width_in_mm || "";
                        }
                    }
                });

                // Refresh entire grid once
                frm.refresh_field("custom_packing_slip");

                frappe.show_alert({
                    message: __('Added ' + to_add.length + ' coils to Packing Slip.'),
                    indicator: 'green'
                });

            } else {
                // Up to date
            }
        });
    });
};


// Hook into Source DocTypes
var packing_slip_sources = ['Purchase Receipt', 'Delivery Note', 'Stock Entry'];

packing_slip_sources.forEach(function (doctype) {
    frappe.ui.form.on(doctype, {
        refresh: function (frm) {
            // Auto sync on refresh if needed, or just rely on triggers
        },
        validate: function (frm) {
            sync_packing_slip(frm);
        }
    });

    // Determine child table name
    let child_doctype = '';
    if (doctype === 'Purchase Receipt') child_doctype = 'Purchase Receipt Item';
    if (doctype === 'Delivery Note') child_doctype = 'Delivery Note Item';
    if (doctype === 'Stock Entry') child_doctype = 'Stock Entry Detail';

    if (child_doctype) {
        frappe.ui.form.on(child_doctype, {
            serial_no: function (frm, cdt, cdn) {
                sync_packing_slip(frm);
            },
            serial_and_batch_bundle: function (frm, cdt, cdn) {
                sync_packing_slip(frm);
            }
        });
    }
});