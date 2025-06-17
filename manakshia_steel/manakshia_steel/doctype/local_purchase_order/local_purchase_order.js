// local_purchase_order.js - Enhanced version with item fetching
// Client-side script for Local Purchase Order

frappe.ui.form.on('Local Purchase Order', {
    refresh: function(frm) {
        // Calculate totals on form load
        calculate_totals(frm);
        
        // Set today's date if not set
        if (!frm.doc.date) {
            frm.set_value('date', frappe.datetime.get_today());
        }
    },
    
    discount_percentage: function(frm) {
        calculate_totals(frm);
    },
    
    shipping: function(frm) {
        calculate_totals(frm);
    },
    
    // Add custom button to recalculate
    setup: function(frm) {
        frm.add_custom_button(__('Recalculate'), function() {
            calculate_totals(frm);
            frappe.show_alert({
                message: __('Totals recalculated'),
                indicator: 'green'
            });
        });
    }
});

frappe.ui.form.on('Items', {
    unit: function(frm, cdt, cdn) {
        // Fetch item details when item is selected
        let row = locals[cdt][cdn];
        if (row.unit) {
            frappe.call({
                method: 'manakshia_steel.manakshia_steel.doctype.local_purchase_order.local_purchase_order.get_item_details',
                args: {
                    item_code: row.unit
                },
                callback: function(r) {
                    if (r.message) {
                        // frappe.model.set_value(cdt, cdn, 'description', r.message.description);
                        frappe.model.set_value(cdt, cdn, 'unit_cost', r.message.unit_cost);
                        
                        // Recalculate after setting unit cost
                        setTimeout(() => {
                            calculate_item_total(frm, cdt, cdn);
                        }, 100);
                    }
                }
            });
        }
    },
    
    qty: function(frm, cdt, cdn) {
        calculate_item_total(frm, cdt, cdn);
    },
    
    unit_cost: function(frm, cdt, cdn) {
        calculate_item_total(frm, cdt, cdn);
    },
    
    items_add: function(frm, cdt, cdn) {
        // Set default values when new row is added
        let row = locals[cdt][cdn];
        if (!row.qty) {
            frappe.model.set_value(cdt, cdn, 'qty', 1);
        }
    },
    
    items_remove: function(frm) {
        calculate_totals(frm);
    }
});

function calculate_item_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    // Convert to numbers, default to 0 if empty or invalid
    let qty = flt(row.qty) || 0;
    let unit_cost = flt(row.unit_cost) || 0;
    
    // Calculate total cost for this item
    let total_cost = qty * unit_cost;
    
    // Update the total_cost field
    frappe.model.set_value(cdt, cdn, 'total_cost', total_cost);
    
    // Recalculate document totals after a short delay
    setTimeout(() => {
        calculate_totals(frm);
    }, 100);
}

function calculate_totals(frm) {
    let net_total = 0;
    
    // Calculate net total from all items
    if (frm.doc.items && frm.doc.items.length > 0) {
        frm.doc.items.forEach(function(item) {
            let total_cost = flt(item.total_cost) || 0;
            net_total += total_cost;
        });
    }
    
    // Set net total
    frm.set_value('net_total', net_total);
    
    // Calculate discount amount
    let discount_percentage = flt(frm.doc.discount_percentage) || 0;
    let discount_amount = (net_total * discount_percentage) / 100;
    
    // Calculate total after discount
    let total_after_discount = net_total - discount_amount;
    
    // Add shipping/handling charges
    let shipping = flt(frm.doc.shipping) || 0;
    
    // Calculate grand total
    let grand_total = total_after_discount + shipping;
    
    // Set grand total
    frm.set_value('grand_total', grand_total);
    
    // Format the display values
    frm.set_df_property('net_total', 'description', format_currency(net_total));
    frm.set_df_property('grand_total', 'description', format_currency(grand_total));
}

// Utility function to format currency
function format_currency(amount) {
    return frappe.format(amount, {fieldtype: 'Currency'});
}

// Keyboard shortcuts
frappe.ui.keys.on('ctrl+shift+c', function() {
    if (cur_frm && cur_frm.doctype === 'Local Purchase Order') {
        calculate_totals(cur_frm);
        frappe.show_alert('Totals recalculated');
    }
});