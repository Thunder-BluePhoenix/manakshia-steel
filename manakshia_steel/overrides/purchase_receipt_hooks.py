# manakshia_steel/overrides/purchase_receipt_hooks.py
#
# Injects custom GRN/* naming series into Purchase Receipt's field meta
# BEFORE Frappe generates the document name, so the correct series is used.
#
# Wire up in hooks.py:
#
#   doc_events = {
#       "Purchase Receipt": {
#           "autoname":    "manakshia_steel.overrides.purchase_receipt_hooks.autoname",
#           "validate":    "manakshia_steel.overrides.purchase_receipt_hooks.validate",
#           "before_save": "manakshia_steel.overrides.purchase_receipt_hooks.before_save",
#       }
#   }

import frappe
from frappe.model.naming import make_autoname

CUSTOM_SERIES = [
    "GRN/R.#####",     # RAW MATERIAL
    "GRN/C.#####",     # CAPITAL GOODS
    "GRN/F.#####",     # POWER AND FUELS
    "GRN/G.#####",     # GENERAL GOODS
    "GRN/J.#####",     # JOB WORK
]

PR_TYPE_TO_SERIES = {
    "RAW MATERIAL":    "GRN/R.#####",
    "CAPITAL GOODS":   "GRN/C.#####",
    "POWER AND FUELS": "GRN/F.#####",
    "GENERAL GOODS":   "GRN/G.#####",
    "JOB WORK":        "GRN/J.#####",
}


def _inject_series_into_meta():
    """Append custom series into in-memory meta so validate_series() passes."""
    meta = frappe.get_meta("Purchase Receipt")
    field = meta.get_field("naming_series")
    if not field:
        return
    existing = [s.strip() for s in (field.options or "").split("\n") if s.strip()]
    to_add = [s for s in CUSTOM_SERIES if s not in existing]
    if to_add:
        field.options = "\n".join(existing + to_add)


def autoname(doc, method=None):
    """
    Fires before the document name is generated.
    If naming_series is one of our custom GRN/* series, inject it into
    meta and generate the name explicitly so Frappe doesn't fall back
    to the default series stored in the DocField.
    """
    series = PR_TYPE_TO_SERIES.get(doc.custom_purchase_receipt_type)
    if not series:
        return  # not a custom type — let Frappe handle naming normally

    # Ensure the chosen series matches the type (in case JS didn't set it)
    doc.naming_series = series

    # Inject into meta so validate_series() won't reject it
    _inject_series_into_meta()

    # Generate the name now — this sets doc.name and increments the counter
    doc.name = make_autoname(series, doc=doc)


def validate(doc, method=None):
    """Inject meta options so validate_series() passes on save/update."""
    if doc.naming_series in CUSTOM_SERIES:
        _inject_series_into_meta()


def before_save(doc, method=None):
    """Same injection needed on every subsequent save."""
    if doc.naming_series in CUSTOM_SERIES:
        _inject_series_into_meta()