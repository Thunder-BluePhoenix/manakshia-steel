frappe.ui.form.on("Waybill", {
    supplier_name: function (frm) {
        if (frm.doc.supplier_name) {
            frappe.db.get_value("Supplier", frm.doc.supplier_name, [
                "custom_address_line_1", 
                "custom_address_line_2", 
                "custom_citytown", 
                "custom_state__province", 
                "country", 
                "custom_postal_code",
                "custom_phone",
                "custom_email"
            ]).then(r => {
                if (r && r.message) {
                    let d = r.message;
                    let address_parts = [];
                    if (d.custom_address_line_1) address_parts.push(d.custom_address_line_1);
                    if (d.custom_address_line_2) address_parts.push(d.custom_address_line_2);
                    
                    let city_state = [];
                    if (d.custom_citytown) city_state.push(d.custom_citytown);
                    if (d.custom_state__province) city_state.push(d.custom_state__province);
                    if (city_state.length > 0) address_parts.push(city_state.join(", "));
                    
                    let curr_country = [];
                    if (d.country) curr_country.push(d.country);
                    if (d.custom_postal_code) curr_country.push(d.custom_postal_code);
                    if (curr_country.length > 0) address_parts.push(curr_country.join(" - "));

                    if (d.custom_phone) address_parts.push("Phone: " + d.custom_phone);
                    if (d.custom_email) address_parts.push("Email: " + d.custom_email);

                    frm.set_value("supplier_address", address_parts.join("\n"));
                }
            });
        } else {
            frm.set_value("supplier_address", "");
        }
    },
    w_bridge_loaded_wt: function (frm) {
        calculate_w_bridge_wt(frm);
    },
    w_bridge_empty_wt: function (frm) {
        calculate_w_bridge_wt(frm);
    }
});

function calculate_w_bridge_wt(frm) {
    if (frm.doc.w_bridge_loaded_wt || frm.doc.w_bridge_empty_wt) {
        let loaded = flt(frm.doc.w_bridge_loaded_wt);
        let empty = flt(frm.doc.w_bridge_empty_wt);
        let w_bridge_wt = loaded - empty;
        frm.set_value("w_bridge_wt", w_bridge_wt);
    }
}

frappe.ui.form.on("Waybill Item", {
    item_code: function (frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if (row.item_code) {
            frappe.db.get_value("Item", row.item_code, ["item_name", "description", "stock_uom", "valuation_rate", "standard_rate"])
                .then(r => {
                    if (r && r.message) {
                        let value = r.message;
                        frappe.model.set_value(cdt, cdn, {
                            description: value.description || value.item_name,
                            uom: value.stock_uom,
                            stock_uom: value.stock_uom,
                            rate: value.standard_rate || value.valuation_rate || 0,
                            conversion_factor: 1.0
                        });
                    }
                });
        }
    },
    qty: function (frm, cdt, cdn) {
        calculate_amount(frm, cdt, cdn);
        calculate_total_qty(frm);
    },
    rate: function (frm, cdt, cdn) {
        calculate_amount(frm, cdt, cdn);
    },
    items_remove: function (frm) {
        calculate_total_qty(frm);
    }
});

function calculate_amount(frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
}

function calculate_total_qty(frm) {
    let total = 0;
    if (frm.doc.items) {
        frm.doc.items.forEach(d => {
            total += flt(d.qty);
        });
    }
    frm.set_value('total_quantity', total);
}
