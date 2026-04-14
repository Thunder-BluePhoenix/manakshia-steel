# manakshia_steel/overrides/purchase_receipt_hooks.py
#
# validate() and before_save() hooks for Purchase Receipt.
#
# autoname() has moved to manakshia_steel.api.doc_naming.autoname_purchase_receipt.
# These hooks ensure that the dynamically-built GRN series (with year embedded)
# passes Frappe's validate_series() check when a doc is saved or amended.

import frappe
from frappe.utils import getdate, nowdate
from manakshia_steel.api.doc_naming import PR_PREFIX, _inject_meta


def _inject_if_custom(doc):
    """If this PR has a custom GRN series, inject the year-embedded series into meta."""
    ptype = doc.get("custom_purchase_receipt_type")
    pfx = PR_PREFIX.get(ptype)
    if not pfx:
        return

    # Mirror doc_naming._year(): fiscal year default first, calendar year fallback
    fy = frappe.defaults.get_user_default("fiscal_year")
    if not fy:
        from frappe.utils import getdate, nowdate
        fy = str(getdate(doc.posting_date or nowdate()).year)

    series = f"{pfx}/{fy}/.#####"
    _inject_meta("Purchase Receipt", series)


def validate(doc, method=None):
    """Inject meta options so validate_series() passes on save/update."""
    _inject_if_custom(doc)


def before_save(doc, method=None):
    """Same injection needed on every subsequent save."""
    _inject_if_custom(doc)