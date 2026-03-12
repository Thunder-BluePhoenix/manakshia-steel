frappe.ui.form.on("Production Order", {
	refresh(frm) {
		// Logic handles material transfer automatically on submit
	},
	taxes_and_charges(frm) {
		if (frm.doc.taxes_and_charges) {
			frappe.db.get_doc("Purchase Taxes and Charges Template", frm.doc.taxes_and_charges).then(template => {
				frm.clear_table("taxes");
				$.each(template.taxes || [], function(i, d) {
					var row = frm.add_child("taxes");
					row.charge_type = d.charge_type;
					row.account_head = d.account_head;
					row.description = d.description;
					row.rate = d.rate;
					row.tax_amount = d.tax_amount;
				});
				frm.refresh_field("taxes");
				calculate_totals(frm);
			});
		}
	},
	vat_rate(frm) {
		calculate_totals(frm);
	},
	amount_to_be_deposited(frm) {
		calculate_totals(frm);
	},
	items_remove(frm) {
		calculate_totals(frm);
	}
});

frappe.ui.form.on("Production Order Item", {
	item_code: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.item_code) {
			frappe.db.get_value("Item", row.item_code, ["item_name", "stock_uom", "valuation_rate"], function(r) {
				if (r) {
					frappe.model.set_value(cdt, cdn, "item_name", r.item_name);
					frappe.model.set_value(cdt, cdn, "uom", r.stock_uom);
					frappe.model.set_value(cdt, cdn, "stock_uom", r.stock_uom);
					frappe.model.set_value(cdt, cdn, "conversion_factor", 1.0);
					frappe.model.set_value(cdt, cdn, "rate", r.valuation_rate || 0);
				}
			});
		}
	},
	qty: function(frm, cdt, cdn) {
		calculate_row_amount(frm, cdt, cdn);
	},
	rate: function(frm, cdt, cdn) {
		calculate_row_amount(frm, cdt, cdn);
	}
});

frappe.ui.form.on("Production Order Tax", {
	rate: function(frm, cdt, cdn) {
		calculate_totals(frm);
	},
	tax_amount: function(frm, cdt, cdn) {
		calculate_totals(frm);
	},
	taxes_remove: function(frm) {
		calculate_totals(frm);
	}
});

var calculate_row_amount = function(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	var amount = flt(row.qty) * flt(row.rate);
	var stock_qty = flt(row.qty) * flt(row.conversion_factor || 1.0);
	frappe.model.set_value(cdt, cdn, "amount", amount);
	frappe.model.set_value(cdt, cdn, "stock_qty", stock_qty);
	calculate_totals(frm);
};

var calculate_totals = function(frm) {
	var net_total = 0;
	var total_qty = 0;
	$.each(frm.doc.items || [], function(i, d) {
		net_total += flt(d.amount);
		total_qty += flt(d.qty);
	});
	
	// Calculate Taxes
	var total_taxes_and_charges = 0;
	var running_total = net_total;
	
	$.each(frm.doc.taxes || [], function(i, d) {
		var tax_amount = 0;
		if (d.charge_type == "Actual") {
			tax_amount = flt(d.tax_amount);
		} else if (d.charge_type == "On Net Total") {
			tax_amount = net_total * flt(d.rate) / 100;
		} else if (d.charge_type == "On Previous Row Amount") {
			var prev_row = frm.doc.taxes[i-1];
			if (prev_row) tax_amount = flt(prev_row.tax_amount) * flt(d.rate) / 100;
		} else if (d.charge_type == "On Previous Row Total") {
			var prev_total = (i == 0) ? net_total : flt(frm.doc.taxes[i-1].total);
			tax_amount = prev_total * flt(d.rate) / 100;
		}
		
		d.tax_amount = tax_amount;
		running_total += tax_amount;
		d.total = running_total;
		total_taxes_and_charges += tax_amount;
	});
	
	frm.refresh_field("taxes");

	// Simple VAT fallback logic (deprecated by user requirement but kept for safety if template is empty)
	if (flt(frm.doc.vat_rate) > 0 && total_taxes_and_charges === 0) {
		total_taxes_and_charges = net_total * flt(frm.doc.vat_rate) / 100;
	}

	var grand_total = net_total + total_taxes_and_charges;
	var amount_due = grand_total - flt(frm.doc.amount_to_be_deposited);
	
	frm.set_value("net_total", net_total);
	frm.set_value("total_qty", total_qty);
	frm.set_value("total_taxes_and_charges", total_taxes_and_charges);
	frm.set_value("grand_total", grand_total);
	frm.set_value("amount_due", amount_due);

	// Hidden sync field (not required in UI anymore as per user)
	// frm.set_value("vat_amount", total_taxes_and_charges);
};
