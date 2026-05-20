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

var LOCK_DOCTYPES = [
  "Stock Entry",
  "Purchase Receipt",
  "Purchase Receipt Return",
  "Waybill",
  "Waybill Return",
  "Production Order",
  "Adjustment",
  "Item",
  "Supplier",
  "Customer",
];

// ── Sidebar link definitions ──────────────────────────────────
// Each entry maps a URL pattern to an action:
//   action: 'new'  → opens a new form (with optional defaults)
//   action: 'list' → opens a filtered list view
var INVENTORY_LINKS = [
  // ── Purchase Receipt ──────────────────────────────────────
  {
    match: "purchase-receipt/new-return",
    action: "new",
    doctype: "Purchase Receipt Return",
    defaults: {},
  },
  {
    match: "purchase-receipt/new",
    action: "new",
    doctype: "Purchase Receipt",
    defaults: {},
  },

  // ── Waybill ───────────────────────────────────────────────
  {
    match: "waybill-return/new",
    action: "new",
    doctype: "Waybill Return",
    defaults: {},
  },
  { match: "waybill/new", action: "new", doctype: "Waybill", defaults: {} },

  // ── Production & Adjustment ───────────────────────────────
  {
    match: "production-order/new",
    action: "new",
    doctype: "Production Order",
    defaults: {},
  },
  {
    match: "adjustment/new",
    action: "new",
    doctype: "Adjustment",
    defaults: {},
  },

  // ── Stock Entry - New Forms ───────────────────────────────
  {
    match: "stock-entry/new-transfer-in",
    action: "new",
    doctype: "Stock Entry",
    defaults: { stock_entry_type: "Stock Transfer In" },
  },
  {
    match: "stock-entry/new-transfer-out",
    action: "new",
    doctype: "Stock Entry",
    defaults: { stock_entry_type: "Stock Transfer Out" },
  },
  {
    match: "stock-entry/new-issue",
    action: "new",
    doctype: "Stock Entry",
    defaults: { stock_entry_type: "Material Issue" },
  },
  {
    match: "stock-entry/new-receipt",
    action: "new",
    doctype: "Stock Entry",
    defaults: { stock_entry_type: "Material Receipt" },
  },

  // ── Stock Entry - Filtered List Views ─────────────────────
  {
    match: "stock-entry/list-transfer-in",
    action: "list",
    doctype: "Stock Entry",
    filters: { stock_entry_type: "Stock Transfer In" },
  },
  {
    match: "stock-entry/list-transfer-out",
    action: "list",
    doctype: "Stock Entry",
    filters: { stock_entry_type: "Stock Transfer Out" },
  },
  {
    match: "stock-entry/list-issue",
    action: "list",
    doctype: "Stock Entry",
    filters: { stock_entry_type: "Material Issue" },
  },
  {
    match: "stock-entry/list-receipt",
    action: "list",
    doctype: "Stock Entry",
    filters: { stock_entry_type: "Material Receipt" },
  },
];

// ── Intercept history.pushState to capture URL BEFORE Frappe rewrites it ──
// Workspace shortcuts (type=URL) call frappe.set_route() directly, so the
// document click listener never fires. By wrapping history.pushState we see
// the original URL (e.g. /stock-entry/new-issue) before it becomes
// /new-stock-entry-xxxx, and we stash the intended stock_entry_type so the
// onload handler in stock_entry_custom.js can read it from sessionStorage.
(function () {
  var URL_TYPE_MAP = {
    "stock-entry/new-issue": "Material Issue",
    "stock-entry/new-receipt": "Material Receipt",
    "stock-entry/new-transfer-in": "Stock Transfer In",
    "stock-entry/new-transfer-out": "Stock Transfer Out",
  };

  var _orig_push = window.history.pushState.bind(window.history);
  var _orig_replace = window.history.replaceState.bind(window.history);

  function check_url(url) {
    if (!url) return;
    var s = String(url);
    for (var key in URL_TYPE_MAP) {
      if (s.indexOf(key) !== -1) {
        sessionStorage.setItem("__pending_se_type", URL_TYPE_MAP[key]);
        return;
      }
    }
  }

  window.history.pushState = function (state, title, url) {
    check_url(url);
    return _orig_push(state, title, url);
  };
  window.history.replaceState = function (state, title, url) {
    check_url(url);
    return _orig_replace(state, title, url);
  };

  // Also check the CURRENT URL at script load time.
  // When a workspace shortcut (type=URL) is clicked, Frappe opens a NEW TAB
  // via window.open(). In that new tab, this script loads with the original
  // URL (e.g. /desk/stock-entry/new-issue) BEFORE Frappe rewrites it.
  // history.pushState is never called with the intermediate URL in that flow,
  // so we must capture it here at load time.
  check_url(window.location.href);
})();

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
  // Access the class prototype directly instead of waiting for an instance to mount
  if (!frappe.ui || !frappe.ui.Sidebar) return false;

  var proto = frappe.ui.Sidebar.prototype;
  if (proto.__inventory_patched) return true; // Already patched

  // Store original method to call for non-locked DocTypes
  var orig = proto.set_workspace_sidebar;

  proto.set_workspace_sidebar = function () {
    var route = frappe.get_route();
    // route[0] = view type ('Form' / 'List')
    // route[1] = DocType name
    if (route && route[1] && LOCK_DOCTYPES.includes(route[1])) {
      // Block workspace switch — stay on or force Inventory Control
      if (this.sidebar_title !== "Inventory Control") {
        console.log(
          "Inventory Control: forcing workspace switch for",
          route[1]
        );
        this.setup("Inventory Control");
      } else {
        console.log(
          "Inventory Control: blocked workspace switch for",
          route[1]
        );
      }
      return;
    }
    // Allow normal workspace switching for all other DocTypes
    return orig.apply(this, arguments);
  };

  proto.__inventory_patched = true;
  console.log("Inventory Control: sidebar prototype patched successfully");

  // If we patched late and Frappe already loaded the wrong sidebar on a hard refresh, correct it immediately
  setTimeout(function () {
    var route = frappe.get_route();
    if (route && route[1] && LOCK_DOCTYPES.includes(route[1])) {
      if (
        frappe.app &&
        frappe.app.sidebar &&
        frappe.app.sidebar.sidebar_title !== "Inventory Control"
      ) {
        frappe.app.sidebar.setup("Inventory Control");
      }
    }
  }, 200);

  return true;
}

// Poll every 50ms until frappe.ui.Sidebar class is available and patch is applied
var patch_interval = setInterval(function () {
  if (patch_sidebar_prototype()) {
    clearInterval(patch_interval); // Stop polling once patched
  }
}, 50);

// ── Open form or filtered list ────────────────────────────────
// Handles both 'new' and 'list' actions from INVENTORY_LINKS.
// For 'list': sets route_options (filters) before navigating
//             so Frappe applies them automatically on list load.
// For 'new':  opens a blank new form with optional default values
//             (e.g. stock_entry_type pre-filled).
function block_and_open(cfg) {
  if (cfg.action === "list") {
    // Set filters before routing so list view picks them up
    frappe.route_options = cfg.filters;
    frappe.set_route("List", cfg.doctype);
  } else {
    // Store stock_entry_type in sessionStorage so onload can read it
    // (URL has already changed by the time onload fires)
    if (
      cfg.doctype === "Stock Entry" &&
      cfg.defaults &&
      cfg.defaults.stock_entry_type
    ) {
      sessionStorage.setItem(
        "__pending_se_type",
        cfg.defaults.stock_entry_type
      );
    }
    frappe.route_options = cfg.defaults || {};
    frappe.new_doc(cfg.doctype);
  }
}

// ── Intercept sidebar link clicks ─────────────────────────────
// Frappe v16 hardcodes target="_blank" on URL-type sidebar links.
// We intercept clicks at the capture phase (3rd arg = true) before
// Frappe handles them, prevent default browser navigation, and
// use our own routing instead to keep everything in the same tab.
document.addEventListener(
  "click",
  function (e) {
    var link = e.target.closest("a");
    if (!link || !link.href) return;

    // Use raw attribute to avoid matching resolved URLs (like href="#")
    // on pages where the URL inherently contains the match string.
    var raw_href = link.getAttribute("href") || "";

    // Check if clicked link matches any of our inventory links
    for (var i = 0; i < INVENTORY_LINKS.length; i++) {
      var cfg = INVENTORY_LINKS[i];
      if (raw_href.includes(cfg.match)) {
        e.preventDefault(); // Stop browser from opening new tab
        e.stopPropagation(); // Stop Frappe from handling the click
        block_and_open(cfg); // Handle navigation ourselves
        return;
      }
    }
  },
  true
); // true = capture phase, runs before Frappe's handlers
