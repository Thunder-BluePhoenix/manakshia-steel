var INVENTORY_LINKS = [
    // Purchase Receipt
    { match: 'purchase-receipt/new-return', action: 'new', doctype: 'Purchase Receipt Return', defaults: {} },
    { match: 'purchase-receipt/new', action: 'new', doctype: 'Purchase Receipt', defaults: {} },

    // Waybill
    { match: 'waybill-return/new', action: 'new', doctype: 'Waybill Return', defaults: {} },
    { match: 'waybill/new', action: 'new', doctype: 'Waybill', defaults: {} },

    // Production & Adjustment
    { match: 'production-order/new', action: 'new', doctype: 'Production Order', defaults: {} },
    { match: 'adjustment/new', action: 'new', doctype: 'Adjustment', defaults: {} },

    // Stock Entry - New Forms
    { match: 'stock-entry/new-transfer-in', action: 'new', doctype: 'Stock Entry', defaults: { stock_entry_type: 'Stock Transfer In' } },
    { match: 'stock-entry/new-transfer-out', action: 'new', doctype: 'Stock Entry', defaults: { stock_entry_type: 'Stock Transfer Out' } },
    { match: 'stock-entry/new-issue', action: 'new', doctype: 'Stock Entry', defaults: { stock_entry_type: 'Material Issue' } },
    { match: 'stock-entry/new-receipt', action: 'new', doctype: 'Stock Entry', defaults: { stock_entry_type: 'Material Receipt' } },

    // Stock Entry - Filtered Lists
    { match: 'stock-entry/list-transfer-in', action: 'list', doctype: 'Stock Entry', filters: { stock_entry_type: 'Stock Transfer In' } },
    { match: 'stock-entry/list-transfer-out', action: 'list', doctype: 'Stock Entry', filters: { stock_entry_type: 'Stock Transfer Out' } },
    { match: 'stock-entry/list-issue', action: 'list', doctype: 'Stock Entry', filters: { stock_entry_type: 'Material Issue' } },
    { match: 'stock-entry/list-receipt', action: 'list', doctype: 'Stock Entry', filters: { stock_entry_type: 'Material Receipt' } },
];

function block_and_open(cfg) {
    var sidebar = frappe.workspace.sidebar;
    var orig = sidebar.set_workspace_sidebar.bind(sidebar);
    var block = true;

    sidebar.set_workspace_sidebar = function () {
        if (block) return;
        return orig.apply(this, arguments);
    };

    if (cfg.action === 'list') {
        frappe.route_options = cfg.filters;
        frappe.set_route('List', cfg.doctype);
    } else {
        frappe.new_doc(cfg.doctype, cfg.defaults);
    }

    setTimeout(function () {
        block = false;
        sidebar.set_workspace_sidebar = orig;
    }, 3000);
}

document.addEventListener('click', function (e) {
    var link = e.target.closest('a');
    if (!link || !link.href) return;

    for (var i = 0; i < INVENTORY_LINKS.length; i++) {
        var cfg = INVENTORY_LINKS[i];
        if (link.href.includes(cfg.match)) {
            e.preventDefault();
            e.stopPropagation();
            block_and_open(cfg);
            return;
        }
    }
}, true);