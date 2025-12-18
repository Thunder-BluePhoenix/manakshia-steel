frappe.ui.form.on('Purchase Receipt', {
    before_save: function(frm) {
        if (frm.doc.custom_packing_slip && frm.doc.items) {
            let total_net_weight = 0;

            // Sum all net weights from Packing Slip child table
            (frm.doc.custom_packing_slip || []).forEach(ps_row => {
                if (ps_row.weight) {
                    total_net_weight += flt(ps_row.weight);
                }
            });

            // Sum all weights from Items table
            let total_item_weight = 0;
            (frm.doc.items || []).forEach(it_row => {
                if (it_row.custom_weight) {
                    total_item_weight += flt(it_row.custom_weight);
                }
            });

            // Compare
            if (total_item_weight !== total_net_weight) {
                frappe.throw(
                    __('⚠️ Total Item Weights (' + total_item_weight + 
                    ') do not match with Net Weight (' + total_net_weight + ')')
                );
            }
        }
    }
});
