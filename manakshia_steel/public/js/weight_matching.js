frappe.ui.form.on('Purchase Receipt', {
    onload: function (frm) {
        if (frm.patched_weight_validation) return;

        // Monkey patch validation to run weight check ONLY on Save/Submit
        // and NOT on intermediate validations (like Add Serial Nos)
        let original_validate = frm.validate_form_action;
        frm.validate_form_action = function (action, callback, btn) {

            if (action === 'Save' || action === 'Submit') {
                // Skip validation if a modal is open (e.g. Serial No dialog auto-saving)
                if ($('.modal:visible').length > 0) {
                    return original_validate.call(this, action, callback, btn);
                }

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

            return original_validate.call(this, action, callback, btn);
        };

        frm.patched_weight_validation = true;
    }
});
