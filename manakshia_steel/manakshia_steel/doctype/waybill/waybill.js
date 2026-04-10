frappe.ui.form.on("Waybill", {
    customer_name: function(frm) {
        if (frm.doc.customer_name) {
            let party_type = frm.fields_dict.customer_name.df.options || "Customer";
            frappe.call({
                method: "erpnext.accounts.party.get_party_details",
                args: {
                    party: frm.doc.customer_name,
                    party_type: party_type
                },
                callback: function(r) {
                    if (r.message && r.message.address_display) {
                        frm.set_value("customer_address", r.message.address_display);
                    }
                }
            });
        }
    },
    w_bridge_loaded_wt: function(frm) {
        calculate_w_bridge_wt(frm);
    },
    w_bridge_empty_wt: function(frm) {
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
    item_code: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if (row.item_code) {
            frappe.db.get_value("Item", row.item_code, ["item_name", "description", "stock_uom", "valuation_rate", "standard_rate"], function(value) {
                if (value && value.message) {
                    frappe.model.set_value(cdt, cdn, {
                        description: value.message.description || value.message.item_name,
                        uom: value.message.stock_uom,
                        stock_uom: value.message.stock_uom,
                        rate: value.message.standard_rate || value.message.valuation_rate || 0,
                        conversion_factor: 1.0
                    });
                }
            });
        }
    },
    qty: function(frm, cdt, cdn) {
        calculate_amount(frm, cdt, cdn);
        calculate_total_qty(frm);
    },
    rate: function(frm, cdt, cdn) {
        calculate_amount(frm, cdt, cdn);
    },
    items_remove: function(frm) {
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
