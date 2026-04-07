frappe.ui.form.on("Waybill Return", {
	waybill(frm) {
		if (frm.doc.waybill) {
			frappe.db.get_doc("Waybill", frm.doc.waybill).then((waybill) => {
				frm.set_value("customer_name", waybill.customer_name);
				frm.set_value("customer_address", waybill.customer_address);
				frm.set_value("buyers_order_no", waybill.buyers_order_no);
				frm.set_value("sales_order_no", waybill.sales_order_no);
				frm.set_value("from_warehouse", waybill.from_warehouse);
				frm.set_value("to_warehouse", waybill.to_warehouse);
				frm.set_value("vehicle_no", waybill.vehicle_no);
				frm.set_value("delivery_order_no", waybill.delivery_order_no);
				frm.set_value("authorized_by", waybill.authorized_by);
				frm.set_value("start_time", waybill.start_time);
				frm.set_value("end_time", waybill.end_time);
				frm.set_value("remarks", waybill.remarks);
				frm.set_value("grand_total", waybill.grand_total);
				
				// Map Custom Waybill Type + Weighbridge fields
				frm.set_value("waybill_type", waybill.waybill_type);
				frm.set_value("w_bridge_slip_no", waybill.w_bridge_slip_no);
				frm.set_value("w_bridge_empty_wt", waybill.w_bridge_empty_wt);
				frm.set_value("w_bridge_loaded_wt", waybill.w_bridge_loaded_wt);
				frm.set_value("w_bridge_wt", waybill.w_bridge_wt);
				frm.set_value("total_quantity", waybill.total_quantity);
				frm.set_value("calculated_weight", waybill.calculated_weight);
				frm.set_value("physical_weight", waybill.physical_weight);

				// Carry financial constraints down from Waybill
				frm.set_value("ignore_pricing_rule", waybill.ignore_pricing_rule);
				frm.set_value("currency", waybill.currency);
				frm.set_value("conversion_rate", waybill.conversion_rate);
				frm.set_value("total_taxes_and_charges", waybill.total_taxes_and_charges);
				frm.set_value("discount_amount", waybill.discount_amount);

				frm.clear_table("items");
				waybill.items.forEach((item) => {
					let row = frm.add_child("items");
					row.item_code = item.item_code;
					row.description = item.description;
					row.qty = item.qty;
					row.uom = item.uom;
					row.pkgn_qnty = item.pkgn_qnty;
					row.physical_wt = item.physical_wt;
					row.stock_uom = item.stock_uom;
					row.conversion_factor = item.conversion_factor || 1;
					row.rate = item.rate;
					row.amount = item.amount;
					// Carry the inward Serial/Batch Bundle so Python can find
					// it in _find_source_bundle() without an extra DB query.
					row.serial_and_batch_bundle = item.serial_and_batch_bundle || null;
				});

				frm.clear_table("packing_slip");
				waybill.packing_slip.forEach((ps) => {
					let row = frm.add_child("packing_slip");
					row.coil_number = ps.coil_number;
					row.grade_specification = ps.grade_specification;
					row.batch_no = ps.batch_no;
					row.thickness = ps.thickness;
					row.width = ps.width;
					row.weight = ps.weight;
					row.confirmed_weight = ps.confirmed_weight;
				});

				frm.refresh_fields();
			});
		}
	},
});