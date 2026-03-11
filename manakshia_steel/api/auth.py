import frappe
from frappe.auth import LoginManager


@frappe.whitelist(allow_guest=True)
def login(usr, pwd, warehouse=None, fiscal_year=None):
    try:
        frappe.local.form_dict["cmd"] = "login"
        login_manager = LoginManager()
        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()
    except frappe.AuthenticationError:
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success_key": 0,
            "message": "Authentication Failed. Please check your credentials.",
        }
        return
    except Exception as e:
        msg = str(e)
        if hasattr(frappe.local, "message_log") and frappe.local.message_log:
            import json
            try:
                msgs = [json.loads(m).get("message", "") for m in frappe.local.message_log if m]
                if msgs:
                    msg = "\n".join(msgs)
            except Exception:
                pass
        
        frappe.local.response["message"] = {
            "success_key": 0,
            "message": msg or "An error occurred during login.",
        }
        return

    # If login successful, set the warehouse and fiscal year in session/defaults
    try:
        if warehouse:
            frappe.defaults.set_user_default("warehouse", warehouse)
            # Also set in session for immediate access if needed
            frappe.session.data["warehouse"] = warehouse

        if fiscal_year:
            frappe.defaults.set_user_default("fiscal_year", fiscal_year)
            frappe.session.data["fiscal_year"] = fiscal_year
    except Exception as e:
        frappe.log_error(title="Login Defaults Error", message=f"Failed to set defaults for {usr}: {str(e)}")

    api_response = {
        "success_key": 1,
        "message": "Logged In",
        "sid": frappe.session.sid,
        "user": frappe.session.user,
        "full_name": frappe.utils.get_fullname(frappe.session.user),
    }

    frappe.local.response["message"] = api_response
    return api_response


@frappe.whitelist()
def get_fiscal_year_dates(fiscal_year):
    """Return start and end dates for the given Fiscal Year name."""
    fy = frappe.get_doc("Fiscal Year", fiscal_year)
    return {
        "year_start_date": str(fy.year_start_date),
        "year_end_date": str(fy.year_end_date),
    }
