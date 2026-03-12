// Copyright (c) 2026, Blue Phoenix and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchase Receipt Return", {
    refresh(frm) {
        // Show the "Fetch Items" button only when the document is not yet submitted
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Fetch Items from Purchase Receipt"), function () {
                if (!frm.doc.purchase_receipt) {
                    frappe.msgprint({
                        title: __("Missing Purchase Receipt"),
                        message: __("Please select a <b>Purchase Receipt</b> before fetching items."),
                        indicator: "orange",
                    });
                    return;
                }

                frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "Purchase Receipt",
                        name: frm.doc.purchase_receipt,
                    },
                    callback: function (r) {
                        if (!r.message) {
                            frappe.msgprint(__("Could not load the selected Purchase Receipt."));
                            return;
                        }

                        const pr = r.message;
                        const conv = pr.conversion_rate || 1;

                        // ── Standard header fields ────────────────────────────────
                        frm.set_value("supplier", pr.supplier);
                        frm.set_value("company", pr.company);
                        frm.set_value("currency", pr.currency);
                        frm.set_value("conversion_rate", conv);
                        frm.set_value("buying_price_list", pr.buying_price_list);
                        frm.set_value("price_list_currency", pr.price_list_currency);
                        frm.set_value("plc_conversion_rate", pr.plc_conversion_rate);

                        // ── Custom header fields ──────────────────────────────────
                        frm.set_value("custom_purchase_receipt_type", pr.custom_purchase_receipt_type);
                        frm.set_value("custom_supplier_invoice_no", pr.custom_supplier_invoice_no);
                        frm.set_value("custom_supplier_invoice_date", pr.custom_supplier_invoice_date);
                        frm.set_value("custom_shipped_on_board_date", pr.custom_shipped_on_board_date);
                        frm.set_value("custom_b_l_issue_date", pr.custom_b_l_issue_date);
                        frm.set_value("custom_form_m_number", pr.custom_form_m_number);
                        frm.set_value("custom_pre_carriage_by", pr.custom_pre_carriage_by);
                        frm.set_value("custom_mode_of_transport", pr.custom_mode_of_transport);
                        frm.set_value("custom_port_of_discharge", pr.custom_port_of_discharge);
                        frm.set_value("custom_port_of_loading", pr.custom_port_of_loading);
                        frm.set_value("custom_final_destination", pr.custom_final_destination);

                        // NOTE: custom_waybill is read-only / auto-set — intentionally not copied.

                        // ── Items table ───────────────────────────────────────────
                        frm.clear_table("items");

                        (pr.items || []).forEach(function (item) {
                            const row = frm.add_child("items");

                            row.item_code = item.item_code;
                            row.item_name = item.item_name;
                            row.description = item.description || item.item_name;

                            row.qty = item.qty;
                            row.received_qty = item.received_qty || item.qty;
                            row.stock_qty = item.stock_qty || item.qty;
                            row.uom = item.uom;
                            row.stock_uom = item.stock_uom || item.uom;
                            row.conversion_factor = item.conversion_factor || 1;

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

                            row.warehouse = item.warehouse;
                            row.rejected_warehouse = item.rejected_warehouse;

                            row.cost_center = item.cost_center;
                            row.expense_account = item.expense_account;
                            row.project = item.project;

                            row.custom_lpo_no = item.custom_lpo_no || null;
                            row.custom_date = item.custom_date || null;
                            row.custom_country_of_origin_of_goods = item.custom_country_of_origin_of_goods || null;
                            row.custom_country_of_final_destination = item.custom_country_of_final_destination || null;
                            row.custom_weight = item.custom_weight || null;

                            row.serial_and_batch_bundle = item.serial_and_batch_bundle || null;
                        });

                        frm.refresh_field("items");

                        // ── Packing Slip table ────────────────────────────────────
                        frm.clear_table("custom_packing_slip");

                        (pr.custom_packing_slip || []).forEach(function (ps) {
                            const row = frm.add_child("custom_packing_slip");
                            row.coil_number = ps.coil_number;
                            row.grade_specification = ps.grade_specification;
                            row.batch_no = ps.batch_no;
                            row.thickness = ps.thickness;
                            row.width = ps.width;
                            row.weight = ps.weight;
                            row.confirmed_weight = ps.confirmed_weight;
                        });

                        frm.refresh_field("custom_packing_slip");

                        frappe.show_alert({
                            message: __("Items fetched from {0}", [frm.doc.purchase_receipt]),
                            indicator: "green",
                        });
                    },
                });
            }, __("Get Items"));
        }
    },

    purchase_receipt(frm) {
        // Clear dependent tables immediately when PR is changed, no confirmation needed
        frm.clear_table("items");
        frm.refresh_field("items");
        frm.clear_table("custom_packing_slip");
        frm.refresh_field("custom_packing_slip");
    },
});