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

				frm.clear_table("items");
				waybill.items.forEach((item) => {
					let row = frm.add_child("items");
					row.item_code = item.item_code;
					row.description = item.description;
					row.qty = item.qty;
					row.uom = item.uom;
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