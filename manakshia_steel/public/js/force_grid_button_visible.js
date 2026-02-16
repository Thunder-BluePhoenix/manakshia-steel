
// Inject CSS to force the "Add Serial/Batch No" button to be visible in the grid
frappe.ui.form.on('Purchase Receipt', {
    refresh: function (frm) {
        // We inject a style block to override the default grid behavior
        // The button usually has a class like .grid-row .btn-open-row or specific field class
        // Based on user feedback "add serial/batch no button", it's likely the specific column button.
        // We target the class causing it to hide.
        // Usually, these buttons are hidden via .grid-row:not(:hover) .grid-static-col .btn ...

        const css = `
            .grid-row .grid-static-col .btn {
                display: inline-block !important;
                visibility: visible !important;
                opacity: 1 !important;
            }
            /* Specifically targeting the 'Add Serial / Batch No' button if it has a unique class or attribute */
            /* If it's a specific field 'add_serial_batch_bundle' rendered as a button */
            [data-fieldname="add_serial_batch_bundle"] {
                 display: block !important;
                 visibility: visible !important;
            }
        `;

        $('<style>').prop('type', 'text/css').html(css).appendTo('head');
    }
});

// Also apply to other docs if needed
['Delivery Note', 'Stock Entry'].forEach(doctype => {
    frappe.ui.form.on(doctype, {
        refresh: function (frm) {
            const css = `
                .grid-row .grid-static-col .btn {
                    display: inline-block !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                }
                 [data-fieldname="add_serial_batch_bundle"] {
                     display: block !important;
                     visibility: visible !important;
                }
            `;
            $('<style>').prop('type', 'text/css').html(css).appendTo('head');
        }
    });
});
