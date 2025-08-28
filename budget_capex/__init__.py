import frappe

__version__ = "0.0.1"


def apply_patches():
    """
    Apply all your monkey patches for standalone functions
    """
    try:
        # Import and apply your patches
        from budget_capex.budget_capex.custom.patch import (
            patch_validate_expense_function,
        )

        patch_validate_expense_function()

        frappe.logger().info("CapEx patches applied successfully")

    except ImportError:
        frappe.logger().warning("Patch modules not found")
    except Exception as e:
        frappe.logger().error(f"Patching failed: {str(e)}")


apply_patches()
