// ============================================================
// Inventory Control - Workspace Sidebar Override
// Frappe v16 / ERPNext
// ============================================================
// PURPOSE:
//   1. Intercept sidebar URL link clicks and open forms/lists
//      in the same tab without switching workspace.
//   2. Permanently lock the sidebar to "Inventory Control"
//      workspace when navigating to any locked DocType —
//      even after save, submit, or amend.
// ============================================================


// ── DocTypes that should always stay in Inventory Control ────
var LOCK_DOCTYPES = [
    'Stock Entry',
    'Purchase Receipt',
    'Purchase Receipt Return',
    'Waybill',
    'Waybill Return',
    'Production Order',
    'Adjustment',
];


// ── Sidebar link definitions ──────────────────────────────────
// Each entry maps a URL pattern to an action:
//   action: 'new'  → opens a new form (with optional defaults)
//   action: 'list' → opens a filtered list view
var INVENTORY_LINKS = [

    // ── Purchase Receipt ──────────────────────────────────────
    { match: 'purchase-receipt/new-return', action: 'new', doctype: 'Purchase Receipt Return', defaults: {} },
    { match: 'purchase-receipt/new', action: 'new', doctype: 'Purchase Receipt', defaults: {} },

    // ── Waybill ───────────────────────────────────────────────
    { match: 'waybill-return/new', action: 'new', doctype: 'Waybill Return', defaults: {} },
    { match: 'waybill/new', action: 'new', doctype: 'Waybill', defaults: {} },

    // ── Production & Adjustment ───────────────────────────────
    { match: 'production-order/new', action: 'new', doctype: 'Production Order', defaults: {} },
    { match: 'adjustment/new', action: 'new', doctype: 'Adjustment', defaults: {} },

    // ── Stock Entry - New Forms ───────────────────────────────
    { match: 'stock-entry/new-transfer-in', action: 'new', doctype: 'Stock Entry', defaults: { stock_entry_type: 'Stock Transfer In' } },
    { match: 'stock-entry/new-transfer-out', action: 'new', doctype: 'Stock Entry', defaults: { stock_entry_type: 'Stock Transfer Out' } },
    { match: 'stock-entry/new-issue', action: 'new', doctype: 'Stock Entry', defaults: { stock_entry_type: 'Material Issue' } },
    { match: 'stock-entry/new-receipt', action: 'new', doctype: 'Stock Entry', defaults: { stock_entry_type: 'Material Receipt' } },

    // ── Stock Entry - Filtered List Views ─────────────────────
    { match: 'stock-entry/list-transfer-in', action: 'list', doctype: 'Stock Entry', filters: { stock_entry_type: 'Stock Transfer In' } },
    { match: 'stock-entry/list-transfer-out', action: 'list', doctype: 'Stock Entry', filters: { stock_entry_type: 'Stock Transfer Out' } },
    { match: 'stock-entry/list-issue', action: 'list', doctype: 'Stock Entry', filters: { stock_entry_type: 'Material Issue' } },
    { match: 'stock-entry/list-receipt', action: 'list', doctype: 'Stock Entry', filters: { stock_entry_type: 'Material Receipt' } },
];


// ── Permanently patch sidebar prototype ───────────────────────
// Frappe v16 calls set_workspace_sidebar() on every route change
// (open, save, submit, amend). By patching the prototype we block
// the workspace switch for all LOCK_DOCTYPES at every point.
//
// WHY prototype and not instance?
//   frappe.workspace.sidebar does not exist when this script first
//   loads. Patching the prototype ensures the override is in place
//   before the sidebar instance is created by Frappe.
//
// HOW it works:
//   - setInterval polls every 500ms until the sidebar is ready
//   - Once found, wraps set_workspace_sidebar on the prototype
//   - Sets __inventory_patched flag so it only runs once
//   - On every sidebar switch attempt, checks frappe.get_route()
//   - If current DocType is in LOCK_DOCTYPES → blocks the switch
//   - Otherwise → allows normal workspace switching
function patch_sidebar_prototype() {
    var sidebar = frappe.workspace && frappe.workspace.sidebar;
    if (!sidebar) return false; // Sidebar not ready yet, try again

    var proto = Object.getPrototypeOf(sidebar);
    if (proto.__inventory_patched) return true; // Already patched

    // Store original method to call for non-locked DocTypes
    var orig = proto.set_workspace_sidebar;

    proto.set_workspace_sidebar = function () {
        var route = frappe.get_route();
        // route[0] = view type ('Form' / 'List')
        // route[1] = DocType name
        if (route && route[1] && LOCK_DOCTYPES.includes(route[1])) {
            // Block workspace switch — stay on Inventory Control
            console.log('Inventory Control: blocked workspace switch for', route[1]);
            return;
        }
        // Allow normal workspace switching for all other DocTypes
        return orig.apply(this, arguments);
    };

    proto.__inventory_patched = true;
    console.log('Inventory Control: sidebar prototype patched successfully');
    return true;
}

// Poll every 500ms until sidebar is available and patch is applied
var patch_interval = setInterval(function () {
    if (patch_sidebar_prototype()) {
        clearInterval(patch_interval); // Stop polling once patched
    }
}, 500);


// ── Open form or filtered list ────────────────────────────────
// Handles both 'new' and 'list' actions from INVENTORY_LINKS.
// For 'list': sets route_options (filters) before navigating
//             so Frappe applies them automatically on list load.
// For 'new':  opens a blank new form with optional default values
//             (e.g. stock_entry_type pre-filled).
function block_and_open(cfg) {
    if (cfg.action === 'list') {
        // Set filters before routing so list view picks them up
        frappe.route_options = cfg.filters;
        frappe.set_route('List', cfg.doctype);
    } else {
        // Open new form with pre-filled default field values
        frappe.new_doc(cfg.doctype, cfg.defaults);
    }
}


// ── Intercept sidebar link clicks ─────────────────────────────
// Frappe v16 hardcodes target="_blank" on URL-type sidebar links.
// We intercept clicks at the capture phase (3rd arg = true) before
// Frappe handles them, prevent default browser navigation, and
// use our own routing instead to keep everything in the same tab.
document.addEventListener('click', function (e) {
    var link = e.target.closest('a');
    if (!link || !link.href) return;

    // Check if clicked link matches any of our inventory links
    for (var i = 0; i < INVENTORY_LINKS.length; i++) {
        var cfg = INVENTORY_LINKS[i];
        if (link.href.includes(cfg.match)) {
            e.preventDefault();  // Stop browser from opening new tab
            e.stopPropagation(); // Stop Frappe from handling the click
            block_and_open(cfg); // Handle navigation ourselves
            return;
        }
    }
}, true); // true = capture phase, runs before Frappe's handlers