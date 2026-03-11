// Copyright (c) 2026, Blue Phoenix and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchase Receipt Return", {
    refresh(frm) {
        // Show the "Fetch Items" button only when the document is not yet submitted
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Fetch Items from Purchase Receipt"), function () {
                if (!frm.doc.original_purchase_receipt) {
                    frappe.msgprint({
                        title: __("Missing Original Purchase Receipt"),
                        message: __("Please select an <b>Original Purchase Receipt</b> before fetching items."),
                        indicator: "orange",
                    });
                    return;
                }

                frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "Purchase Receipt",
                        name: frm.doc.original_purchase_receipt,
                    },
                    callback: function (r) {
                        if (!r.message) {
                            frappe.msgprint(__("Could not load the selected Purchase Receipt."));
                            return;
                        }

                        const pr = r.message;
                        const conv = pr.conversion_rate || 1;

                        // Auto-fill header fields from the original PR
                        frm.set_value("supplier", pr.supplier);
                        frm.set_value("company", pr.company);
                        frm.set_value("currency", pr.currency);
                        frm.set_value("conversion_rate", conv);
                        frm.set_value("buying_price_list", pr.buying_price_list);
                        frm.set_value("price_list_currency", pr.price_list_currency);
                        frm.set_value("plc_conversion_rate", pr.plc_conversion_rate);

                        // Clear and populate the items table
                        frm.clear_table("items");

                        (pr.items || []).forEach(function (item) {
                            const row = frm.add_child("items");

                            // Core fields
                            row.item_code = item.item_code;
                            row.item_name = item.item_name;
                            row.description = item.description || item.item_name;

                            // Qty & UOM
                            row.qty = item.qty;
                            row.received_qty = item.received_qty || item.qty;
                            row.stock_qty = item.stock_qty || item.qty;
                            row.uom = item.uom;
                            row.stock_uom = item.stock_uom || item.uom;
                            row.conversion_factor = item.conversion_factor || 1;

                            // Pricing — both supplier currency and company base currency
                            row.rate = item.rate || 0;
                            row.amount = item.amount || 0;
                            row.net_rate = item.net_rate || item.rate || 0;
                            row.net_amount = item.net_amount || item.amount || 0;
                            row.base_rate = item.base_rate || ((item.rate || 0) * conv);
                            row.base_amount = item.base_amount || ((item.amount || 0) * conv);
                            row.base_net_rate = item.base_net_rate || ((item.net_rate || item.rate || 0) * conv);
                            row.base_net_amount = item.base_net_amount || ((item.net_amount || item.amount || 0) * conv);
                            row.price_list_rate = item.price_list_rate || item.rate || 0;
                            row.base_price_list_rate = item.base_price_list_rate || ((item.price_list_rate || item.rate || 0) * conv);

                            // Warehouse
                            row.warehouse = item.warehouse;
                            row.rejected_warehouse = item.rejected_warehouse;

                            // Accounting
                            row.cost_center = item.cost_center;
                            row.expense_account = item.expense_account;
                            row.project = item.project;
                        });

                        frm.refresh_field("items");
                        frappe.show_alert({
                            message: __("Items fetched from {0}", [frm.doc.original_purchase_receipt]),
                            indicator: "green",
                        });
                    },
                });
            }, __("Get Items"));
        }
    },

    original_purchase_receipt(frm) {
        // When the original PR is changed, clear the items table to avoid stale data
        if (frm.doc.items && frm.doc.items.length > 0) {
            frappe.confirm(
                __("Changing the Original Purchase Receipt will clear the current items. Continue?"),
                function () {
                    frm.clear_table("items");
                    frm.refresh_field("items");
                },
                function () {
                    // User said no — restore previous value (just refresh)
                    frm.refresh_field("original_purchase_receipt");
                }
            );
        }
    },
});
