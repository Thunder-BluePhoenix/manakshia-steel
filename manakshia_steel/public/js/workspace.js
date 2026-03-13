var INVENTORY_LINKS = [
    // Purchase Receipt
    { match: 'purchase-receipt/new-return', doctype: 'Purchase Receipt Return', defaults: {} },
    { match: 'purchase-receipt/new', doctype: 'Purchase Receipt', defaults: {} },

    // Waybill
    { match: 'waybill-return/new', doctype: 'Waybill Return', defaults: {} },
    { match: 'waybill/new', doctype: 'Waybill', defaults: {} },

    // Production & Adjustment
    { match: 'production-order/new', doctype: 'Production Order', defaults: {} },
    { match: 'adjustment/new', doctype: 'Adjustment', defaults: {} },

    // Stock Entry
    { match: 'stock-entry/new-transfer-in', doctype: 'Stock Entry', defaults: { stock_entry_type: 'Stock Transfer In' } },
    { match: 'stock-entry/new-transfer-out', doctype: 'Stock Entry', defaults: { stock_entry_type: 'Stock Transfer Out' } },
    { match: 'stock-entry/new-issue', doctype: 'Stock Entry', defaults: { stock_entry_type: 'Material Issue' } },
    { match: 'stock-entry/new-receipt', doctype: 'Stock Entry', defaults: { stock_entry_type: 'Material Receipt' } },
];

function block_and_open(doctype, defaults) {
    var sidebar = frappe.workspace.sidebar;
    var orig = sidebar.set_workspace_sidebar.bind(sidebar);
    var block = true;

    sidebar.set_workspace_sidebar = function () {
        if (block) return;
        return orig.apply(this, arguments);
    };

    frappe.new_doc(doctype, defaults);

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
            block_and_open(cfg.doctype, cfg.defaults);
            return;
        }
    }
}, true);