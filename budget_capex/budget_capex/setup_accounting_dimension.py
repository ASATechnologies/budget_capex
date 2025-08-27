import frappe
from frappe import _

def setup_capex_accounting_dimension():
    """
    Setup CapEx as an accounting dimension in ERPNext
    This should be run after installing the app
    """
    
    # Check if CapEx dimension already exists
    if frappe.db.exists("Accounting Dimension", "Capital Expenditure"):
        frappe.logger().info("CapEx Accounting Dimension already exists")
        return
    
    try:
        # Create the Accounting Dimension record
        accounting_dimension = frappe.get_doc({
            "doctype": "Accounting Dimension",
            "document_type": "Capital Expenditure",
            "label": "Capital Expenditure",
            "fieldname": "capital_expenditure",
            "disabled": 0,
            "mandatory_for_bs": 0,  # Not mandatory for Balance Sheet
            "mandatory_for_pl": 0,  # Mandatory for Profit & Loss (expenses)
        })
        
        accounting_dimension.insert()
        frappe.db.commit()
        
        frappe.logger().info("Created CapEx Accounting Dimension successfully")
        
    except Exception as e:
        frappe.logger().error(f"Failed to create CapEx Accounting Dimension: {str(e)}")
        frappe.throw(_("Failed to setup CapEx Accounting Dimension: {0}").format(str(e)))


def remove_capex_accounting_dimension():
    """
    Remove CapEx accounting dimension (for cleanup/uninstall)
    """
    try:
        # Remove custom fields
        custom_fields = frappe.get_all(
            "Custom Field", 
            filters={"fieldname": "capital_expenditure"},
            fields=["name", "dt"]
        )
        
        for field in custom_fields:
            frappe.delete_doc("Custom Field", field.name)
            frappe.logger().info(f"Removed CapEx field from {field.dt}")
        
        # Remove accounting dimension
        if frappe.db.exists("Accounting Dimension", "Capital Expenditure"):
            frappe.delete_doc("Accounting Dimension", "Capital Expenditure")
            frappe.logger().info("Removed Capital Expenditure Accounting Dimension")
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.logger().error(f"Failed to remove Capital Expenditure Accounting Dimension: {str(e)}")



# Hook functions for installation
def after_install():
    """
    Called after app installation
    """
    setup_capex_accounting_dimension()

def before_uninstall():
    """
    Called before app uninstallation
    """
    remove_capex_accounting_dimension()