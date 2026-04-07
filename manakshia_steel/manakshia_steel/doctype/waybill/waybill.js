frappe.ui.form.on("Waybill", {
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
