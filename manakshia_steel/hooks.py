app_name = "manakshia_steel"
app_title = "Manakshia Steel"
app_publisher = "Blue Phoenix"
app_description = "Manakshia Steel manufacture"
app_email = "bluephoenix00995@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "manakshia_steel",
# 		"logo": "/assets/manakshia_steel/logo.png",
# 		"title": "Manakshia Steel",
# 		"route": "/manakshia_steel",
# 		"has_permission": "manakshia_steel.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/manakshia_steel/css/manakshia_steel.css"
app_include_js = [
    "/assets/manakshia_steel/js/child_table_auto_row.js",
    "/assets/manakshia_steel/js/fiscal_year_defaults.js",
]

doctype_js = {
    "Supplier": "public/js/supplier_address.js",
    "Customer": "public/js/customer_address.js",
    "Material Request": "public/js/material_request.js",
    "Purchase Receipt": [
        "public/js/weight_matching.js",
        "public/js/packing_slip_custom.js",
        "public/js/waybill_buttons.js",
        "public/js/warehouse_conflict_fix.js",
        "public/js/serial_batch_bundle_fix.js",
    ],
    "Stock Entry": [
        "public/js/stock_entry_custom.js",
        "public/js/waybill_buttons.js",
        "public/js/warehouse_conflict_fix.js",
        "public/js/packing_slip_custom.js",
    ],
    "Delivery Note": [
        "public/js/waybill_buttons.js",
        "public/js/serial_batch_bundle_fix.js",
    ],
    "Subcontracting Receipt": "public/js/warehouse_conflict_fix.js",
}

_fix_naming_year = "manakshia_steel.api.fiscal_year_hooks.fix_naming_year"

# NOTE: Only ONE doc_events dict is allowed in hooks.py.
# A second dict silently overwrites the first (Python dict re-assignment).
# All events are merged here.
doc_events = {
    "Stock Entry": {
        "before_naming": _fix_naming_year,
        "before_validate": [
            "manakshia_steel.api.stock_entry_custom.suppress_serial_batch_on_stock_entry",
            "manakshia_steel.api.warehouse_fix.validate_warehouse_conflict",
        ],
        "before_submit": "manakshia_steel.api.stock_entry_custom.validate_material_receipt",
    },
    "Purchase Receipt": {
        "before_naming": _fix_naming_year,
        "before_validate": "manakshia_steel.api.warehouse_fix.validate_warehouse_conflict",
    },
    "Delivery Note": {
        "before_naming": _fix_naming_year,
    },
    "Purchase Order": {
        "before_naming": _fix_naming_year,
    },
    "Material Request": {
        "before_naming": _fix_naming_year,
    },
    "Supplier Quotation": {
        "before_naming": _fix_naming_year,
    },
    "Subcontracting Receipt": {
        "before_validate": "manakshia_steel.api.warehouse_fix.validate_warehouse_conflict",
    },
}

# include js, css files in header of web template
# web_include_css = "/assets/manakshia_steel/css/manakshia_steel.css"
# web_include_js = "/assets/manakshia_steel/js/manakshia_steel.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "manakshia_steel/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "manakshia_steel/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

fixtures = [
    {
        "dt": "Property Setter",
        "filters": [
            ["name", "in", ["Purchase Receipt-custom_packing_slip-allow_bulk_edit"]]
        ],
    },
    {"dt": "Custom HTML Block"},
]

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "manakshia_steel.utils.jinja_methods",
# 	"filters": "manakshia_steel.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "manakshia_steel.install.before_install"
# after_install = "manakshia_steel.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "manakshia_steel.uninstall.before_uninstall"
# after_uninstall = "manakshia_steel.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "manakshia_steel.utils.before_app_install"
# after_app_install = "manakshia_steel.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "manakshia_steel.utils.before_app_uninstall"
# after_app_uninstall = "manakshia_steel.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "manakshia_steel.notifications.get_notification_config"

# Permissions
# -----------
# Restricts list views and reports to the user's logged-in fiscal year.
# System Manager / Administrator are exempt and see all years.

_pqc = "manakshia_steel.api.fiscal_year_filter"

permission_query_conditions = {
    "Stock Entry": f"{_pqc}.pqc_stock_entry",
    "Purchase Receipt": f"{_pqc}.pqc_purchase_receipt",
    "Delivery Note": f"{_pqc}.pqc_delivery_note",
    "Purchase Order": f"{_pqc}.pqc_purchase_order",
    "Material Request": f"{_pqc}.pqc_material_request",
    "Supplier Quotation": f"{_pqc}.pqc_supplier_quotation",
    "Purchase Invoice": f"{_pqc}.pqc_purchase_invoice",
    "Stock Ledger Entry": f"{_pqc}.pqc_stock_ledger_entry",
}

# DocType Class
# ---------------
# Override standard doctype classes
override_doctype_class = {
    "Stock Entry": "manakshia_steel.overrides.stock_entry.CustomStockEntry"
}

# Document Events
# ---------------
# Hook on document methods and events

# _fix_naming_year is defined above, near doc_events where it is first used.
# (All doc_events hooks are in the single dict above.)


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"manakshia_steel.tasks.all"
# 	],
# 	"daily": [
# 		"manakshia_steel.tasks.daily"
# 	],
# 	"hourly": [
# 		"manakshia_steel.tasks.hourly"
# 	],
# 	"weekly": [
# 		"manakshia_steel.tasks.weekly"
# 	],
# 	"monthly": [
# 		"manakshia_steel.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "manakshia_steel.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "manakshia_steel.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "manakshia_steel.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["manakshia_steel.utils.before_request"]
# after_request = ["manakshia_steel.utils.after_request"]

# Job Events
# ----------
# before_job = ["manakshia_steel.utils.before_job"]
# after_job = ["manakshia_steel.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"manakshia_steel.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
