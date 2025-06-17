// your_custom_app_name/public/js/material_request_custom.js

frappe.ui.form.on('Material Request', {
    refresh: function(frm) {
        // Add custom button only if document is submitted and material request type is Purchase
        if (frm.doc.docstatus === 1 && frm.doc.material_request_type === 'Purchase') {
            frm.add_custom_button(__('Request for Quotation'), function() {
                create_request_for_quotation(frm);
            }, __('Create'));
        }
    }
});

function create_request_for_quotation(frm) {
    // Check if there are items in the material request
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frappe.msgprint(__('No items found in Material Request'));
        return;
    }
    
    // Create new Request for Quotation
    frappe.model.with_doctype('Request for Quotation', function() {
        let rfq = frappe.model.get_new_doc('Request for Quotation');
        
        // Set basic details
        rfq.transaction_date = frappe.datetime.get_today();
        rfq.schedule_date = frm.doc.schedule_date || frappe.datetime.add_days(frappe.datetime.get_today(), 7);
        rfq.company = frm.doc.company;
        rfq.message_for_supplier = 'Please provide your best quotation for the following items:';
        
        // Counter for async operations
        let items_processed = 0;
        let total_items = frm.doc.items.length;
        
        // Add items from Material Request with proper UOM handling
        frm.doc.items.forEach(function(item, index) {
            let rfq_item = frappe.model.add_child(rfq, 'items');
            rfq_item.item_code = item.item_code;
            rfq_item.item_name = item.item_name;
            rfq_item.description = item.description;
            rfq_item.qty = item.qty;
            rfq_item.stock_uom = item.stock_uom;
            rfq_item.uom = item.uom || item.stock_uom;
            rfq_item.schedule_date = item.schedule_date || rfq.schedule_date;
            rfq_item.material_request = frm.doc.name;
            rfq_item.material_request_item = item.name;
            rfq_item.project = item.project;
            rfq_item.warehouse = item.warehouse;
            
            // Set UOM conversion factor
            if (item.conversion_factor) {
                rfq_item.conversion_factor = item.conversion_factor;
                items_processed++;
                
                // Check if all items are processed
                if (items_processed === total_items) {
                    open_rfq_form(rfq);
                }
            } else {
                // Fetch UOM conversion factor from server
                frappe.call({
                    method: 'erpnext.stock.get_item_details.get_conversion_factor',
                    args: {
                        item_code: item.item_code,
                        uom: item.uom || item.stock_uom
                    },
                    callback: function(r) {
                        if (r.message) {
                            rfq_item.conversion_factor = r.message.conversion_factor || 1;
                        } else {
                            rfq_item.conversion_factor = 1;
                        }
                        
                        items_processed++;
                        
                        // Check if all items are processed
                        if (items_processed === total_items) {
                            open_rfq_form(rfq);
                        }
                    }
                });
            }
        });
        
        // If no items need UOM fetching, open form directly
        if (total_items === 0) {
            open_rfq_form(rfq);
        }
    });
}

function open_rfq_form(rfq) {
    // Open the new RFQ form
    frappe.set_route('Form', 'Request for Quotation', rfq.name);
    
    // Show success message
    frappe.show_alert({
        message: __('Request for Quotation {0} created successfully', [rfq.name]),
        indicator: 'green'
    });
}