# manakshia_steel/steel_manufacturing/api.py
#
# Whitelisted APIs for auto-populating coil/packet details
# across manufacturing stages.
#
# Stage flow:
#   GCP Entry:  coil_no = Serial No (CR Coil RM)
#   CC  Entry:  coil_no = Batch    (GP Coil / ALU / ROPP WIP)
#   EMB Entry:  coil_no = Batch    (CC Coil / ALU WIP)
#   CTL Item:   coil_no = Batch    (any WIP coil)
#   PRO Item:   coil_no = Batch    (any WIP coil)
#   COR Item:   packet_no = Batch  (sheet packet from CTL)

import frappe


@frappe.whitelist()
def get_serial_no_details(serial_no):
    """
    Called when operator selects a CR Coil Serial No in GCP Entry row.
    Returns: thickness, width, item_name, item_code, purchase_rate, supplier.
    """
    if not serial_no:
        return {}

    sn = frappe.db.get_value(
        "Serial No",
        serial_no,
        ["item_code", "item_name", "batch_no", "purchase_rate", "supplier"],
        as_dict=True,
    )
    if not sn:
        return {}

    # Fetch thickness and width from Item master custom fields
    item_data = (
        frappe.db.get_value(
            "Item",
            sn.item_code,
            ["custom_thickness_in_mm", "custom_width_in_mm", "item_name"],
            as_dict=True,
        )
        or {}
    )

    return {
        "item_code": sn.item_code,
        "item_name": sn.item_name,
        "batch_no": sn.batch_no,
        "purchase_rate": sn.purchase_rate,
        "supplier": sn.supplier,
        "thickness": item_data.get("custom_thickness_in_mm"),
        "width": item_data.get("custom_width_in_mm"),
    }


@frappe.whitelist()
def get_coil_details(coil_no):
    """
    Called when operator selects a WIP coil Batch number in CC / EMB / CTL / Profile Entry rows.
    Searches all previous stage Exit tables in sequence.
    Returns: thick, width, colour, brand, sleeve_wt, length, pattern, source stage.
    """
    if not coil_no:
        return {}

    # 1. Search GCP Exit (GP Coil)
    result = frappe.db.sql(
        """
		SELECT
			ei.thick, ei.width, ei.net_wt AS weight, ei.sleeve_wt,
			ei.brand, ei.length_mtr AS length, NULL AS colour, NULL AS pattern,
			'Galvanized Coil Production' AS source_stage, p.name AS source_doc
		FROM `tabGalvanized Coil Exit` ei
		INNER JOIN `tabGalvanized Coil Production` p ON ei.parent = p.name
		WHERE ei.gp_coil_no = %(coil_no)s AND p.docstatus = 1
		LIMIT 1
	""",
        {"coil_no": coil_no},
        as_dict=True,
    )
    if result:
        return result[0]

    # 2. Search CC Exit (CC Coil / CC ROPP / CC ALU)
    result = frappe.db.sql(
        """
		SELECT
			ei.fin_thk AS thick, ei.width, ei.cc_coil_wt AS weight,
			NULL AS sleeve_wt, ei.brand, ei.length, ei.colour, NULL AS pattern,
			'CC Coil Production' AS source_stage, p.name AS source_doc
		FROM `tabCC Coil Exit` ei
		INNER JOIN `tabCC Coil Production` p ON ei.parent = p.name
		WHERE ei.cc_coil_no = %(coil_no)s AND p.docstatus = 1
		LIMIT 1
	""",
        {"coil_no": coil_no},
        as_dict=True,
    )
    if result:
        return result[0]

    # 3. Search EMB Exit (EMB Coil)
    result = frappe.db.sql(
        """
		SELECT
			ei.fin_thk AS thick, ei.width, ei.emb_nt_wt AS weight,
			ei.sleeve_wt, ei.brand, ei.length, ei.colour, ei.pattern,
			'Embossed Coil Production' AS source_stage, p.name AS source_doc
		FROM `tabEmbossed Coil Exit` ei
		INNER JOIN `tabEmbossed Coil Production` p ON ei.parent = p.name
		WHERE ei.emb_coil_no = %(coil_no)s AND p.docstatus = 1
		LIMIT 1
	""",
        {"coil_no": coil_no},
        as_dict=True,
    )
    if result:
        return result[0]

    # 4. Check if it's an ALU Coil batch (from Purchase Receipt)
    #    For ALU/ROPP coils that enter CC or EMB directly (bypass B2/B5)
    batch = frappe.db.get_value("Batch", coil_no, ["item", "batch_id"], as_dict=True)
    if batch:
        item_data = (
            frappe.db.get_value(
                "Item",
                batch.item,
                ["custom_thickness_in_mm", "custom_width_in_mm"],
                as_dict=True,
            )
            or {}
        )
        return {
            "thick": item_data.get("custom_thickness_in_mm"),
            "width": item_data.get("custom_width_in_mm"),
            "source_stage": "Item Master (bypass route)",
        }

    return {}


@frappe.whitelist()
def get_packet_details(packet_no):
    """
    Called when operator selects a sheet packet Batch number in Corrugated Sheet Production rows.
    Searches CTL Production Item rows for the packet.
    Returns: thick, width, packet_wt, brand, colour, qnty_sht.
    """
    if not packet_no:
        return {}

    result = frappe.db.sql(
        """
		SELECT
			ci.thick, ci.width, ci.packet_wt, ci.brand, ci.colour,
			ci.qty_sheets, ci.length,
			'CTL Production' AS source_stage, p.name AS source_doc
		FROM `tabCTL Production Item` ci
		INNER JOIN `tabCTL Production` p ON ci.parent = p.name
		WHERE ci.packet_no = %(packet_no)s AND p.docstatus = 1
		LIMIT 1
	""",
        {"packet_no": packet_no},
        as_dict=True,
    )

    return result[0] if result else {}
