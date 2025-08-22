import frappe
from frappe import _
from frappe.auth import LoginManager

def get_context(context):
    context.no_cache = 1
    context.show_sidebar = False
    context.title = _("Login")

    if frappe.form_dict.get('usr') and frappe.form_dict.get('pwd'):
        try:
            login_manager = LoginManager()
            login_manager.login()  
            frappe.local.response["type"] = "redirect"
            frappe.local.response["location"] = "/app"
            raise frappe.Redirect

        except frappe.AuthenticationError:
            context.error = "Invalid username or password"

    return context
