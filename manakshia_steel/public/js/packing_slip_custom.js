// ===========================================================================
// Packing Slip Custom — auto-populate custom_packing_slip table
// ===========================================================================
//
// Flow:
//   1. User opens Purchase Receipt and adds serials via the Serial & Batch
//      Bundle dialog. ERPNext saves the doc after the dialog closes, which
//      causes a full form reload.
//   2. On reload the `refresh` event fires. We call sync_packing_slip() there
//      so that the packing slip table is populated from the saved bundle data.
//   3. If serials are set manually (serial_no text field), the child-table
//      trigger also calls sync_packing_slip() immediately.
//
// ===========================================================================

// ---------------------------------------------------------------------------
// Helper: fetch coil details (thickness / width) from Serial No → Item
// ---------------------------------------------------------------------------
var fetch_packing_details = function (frm, cdt, cdn, fallback_item_code) {
  let row = locals[cdt][cdn];
  if (!row.coil_number) return Promise.resolve();

  return frappe.db
    .get_value("Serial No", row.coil_number, ["item_code", "batch_no"])
    .then((res) => {
      let d = res.message || {};
      let item_code = d.item_code || fallback_item_code;
      let batch_no = d.batch_no;

      if (batch_no) frappe.model.set_value(cdt, cdn, "batch_no", batch_no);

      if (item_code) {
        return frappe.db
          .get_value("Item", item_code, [
            "custom_thickness_in_mm",
            "custom_width_in_mm",
          ])
          .then((r) => {
            if (r.message) {
              frappe.model.set_value(
                cdt,
                cdn,
                "thickness",
                r.message.custom_thickness_in_mm || ""
              );
              frappe.model.set_value(
                cdt,
                cdn,
                "width",
                r.message.custom_width_in_mm || ""
              );
            }
            return true;
          });
      }
      return true;
    })
    .catch((err) => {
      console.error("Error fetching details for " + row.coil_number, err);
      return true;
    });
};

// ---------------------------------------------------------------------------
// Packing Slip Child — manual coil_number entry
// ---------------------------------------------------------------------------
frappe.ui.form.on("Packing Slip Child", {
  coil_number: function (frm, cdt, cdn) {
    fetch_packing_details(frm, cdt, cdn);
  },
});

// ---------------------------------------------------------------------------
// Core sync function
// Collects all serial nos from Items (both serial_no text field AND
// Serial & Batch Bundle) and adds missing ones to custom_packing_slip.
// ---------------------------------------------------------------------------
var sync_packing_slip = function (frm) {
  if (!frm.doc.items) return;

  let all_serials_map = {}; // { serial_no → { item_code, batch_no } }
  let distinct_item_codes = new Set();
  let promises = [];

  // -- Gather from serial_no text field (legacy / manual entry) --
  $.each(frm.doc.items, function (i, row) {
    if (row.item_code) distinct_item_codes.add(row.item_code);

    if (row.serial_no) {
      row.serial_no.split(/\r?\n/).forEach((s) => {
        if (s.trim()) {
          all_serials_map[s.trim()] = {
            item_code: row.item_code,
            batch_no: row.batch_no,
          };
        }
      });
    }

    // -- Gather from Serial and Batch Bundle --
    if (row.serial_and_batch_bundle) {
      let p = frappe
        .call({
          method: "frappe.client.get",
          args: {
            doctype: "Serial and Batch Bundle",
            name: row.serial_and_batch_bundle,
          },
        })
        .then((r) => {
          if (r.message && r.message.entries) {
            r.message.entries.forEach((entry) => {
              if (entry.serial_no) {
                all_serials_map[entry.serial_no] = {
                  item_code: row.item_code,
                  batch_no: entry.batch_no || row.batch_no,
                };
              }
            });
          }
        })
        .catch((err) => {
          console.error("Error fetching Serial Bundle:", err);
        });
      promises.push(p);
    }
  });

  // Wait for all bundle fetches to complete before updating the table
  Promise.all(promises).then(() => {
    if (!Object.keys(all_serials_map).length) return; // nothing to do

    // Batch-fetch item details (thickness / width)
    let item_data_map = {};
    let item_promises = [];

    distinct_item_codes.forEach((item_code) => {
      let p = frappe.db
        .get_value("Item", item_code, [
          "custom_thickness_in_mm",
          "custom_width_in_mm",
        ])
        .then((r) => {
          if (r && r.message) item_data_map[item_code] = r.message;
        });
      item_promises.push(p);
    });

    Promise.all(item_promises).then(() => {
      // Determine which serials are already in the packing slip table
      let existing_coils = (frm.doc.custom_packing_slip || [])
        .map((r) => r.coil_number)
        .filter((c) => c);

      let has_empty_first_row =
        frm.doc.custom_packing_slip &&
        frm.doc.custom_packing_slip.length === 1 &&
        !frm.doc.custom_packing_slip[0].coil_number;

      let all_serials = Object.keys(all_serials_map);
      let to_add = all_serials.filter((s) => !existing_coils.includes(s));

      if (!to_add.length) return; // already up-to-date

      to_add.forEach((sn, index) => {
        let child;

        // Reuse the blank first row if present
        if (index === 0 && has_empty_first_row) {
          child = frm.doc.custom_packing_slip[0];
        } else {
          child = frm.add_child("custom_packing_slip");
        }

        child.coil_number = sn;

        let mapped = all_serials_map[sn];
        if (mapped) {
          child.batch_no = mapped.batch_no;

          let details = item_data_map[mapped.item_code];
          if (details) {
            child.thickness = details.custom_thickness_in_mm || "";
            child.width = details.custom_width_in_mm || "";
          }
        }
      });

      frm.refresh_field("custom_packing_slip");

      frappe.show_alert({
        message: __("Added " + to_add.length + " coils to Packing Slip."),
        indicator: "green",
      });
    });
  });
};

// ---------------------------------------------------------------------------
// Hook into parent DocTypes
// ---------------------------------------------------------------------------
var packing_slip_sources = ["Purchase Receipt", "Delivery Note", "Stock Entry"];

packing_slip_sources.forEach(function (doctype) {
  frappe.ui.form.on(doctype, {
    // *** KEY FIX ***
    // After the Serial & Batch Bundle dialog saves serials it calls
    // frm.save(), which reloads the form. The `refresh` event fires
    // AFTER the reload, at which point serial_and_batch_bundle is set
    // on the item row. That is the correct moment to sync.
    refresh: function (frm) {
      // Only sync if the doc has items with serial bundles or serial_no
      // and the packing slip table appears to be missing rows.
      if (!frm.doc.items) return;

      let has_serials = frm.doc.items.some(
        (r) => r.serial_and_batch_bundle || (r.serial_no && r.serial_no.trim())
      );

      if (!has_serials) return;

      // Sync — will add only missing rows (idempotent)
      sync_packing_slip(frm);
    },

    // NOTE: Do NOT call sync_packing_slip in the `validate` event.
    // That event is sync but sync_packing_slip is async (uses Promises),
    // so Frappe cannot await it and rows appear missing at validation time.
  });

  // Determine child table name
  let child_doctype = "";
  if (doctype === "Purchase Receipt") child_doctype = "Purchase Receipt Item";
  if (doctype === "Delivery Note") child_doctype = "Delivery Note Item";
  if (doctype === "Stock Entry") child_doctype = "Stock Entry Detail";

  if (child_doctype) {
    frappe.ui.form.on(child_doctype, {
      // When serial_no text field is filled manually
      serial_no: function (frm, cdt, cdn) {
        sync_packing_slip(frm);
      },
      // When Serial & Batch Bundle field is set (e.g. existing doc load,
      // or certain programmatic flows — supplement to the refresh hook)
      serial_and_batch_bundle: function (frm, cdt, cdn) {
        sync_packing_slip(frm);
      },
    });
  }
});
