import frappe
from frappe import _
from frappe.auth import LoginManager
from frappe.utils import get_url

@frappe.whitelist(allow_guest=True)
def login(usr, pwd, warehouse=None, fiscal_year=None):
    try:
        login_manager = LoginManager()
        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()
    except frappe.AuthenticationError:
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success_key": 0,
            "message": "Authentication Failed. Please check your credentials."
        }
        return

    # If login successful, set the warehouse and fiscal year in session/defaults
    if warehouse:
        frappe.defaults.set_user_default("warehouse", warehouse)
        # Also set in session for immediate access if needed
        frappe.session.data["warehouse"] = warehouse

    if fiscal_year:
        frappe.defaults.set_user_default("fiscal_year", fiscal_year)
        frappe.session.data["fiscal_year"] = fiscal_year

    api_response = {
        "success_key": 1,
        "message": "Logged In",
        "sid": frappe.session.sid,
        "user": frappe.session.user,
        "full_name": frappe.utils.get_fullname(frappe.session.user)
    }

    frappe.local.response["message"] = api_response
    return api_response
