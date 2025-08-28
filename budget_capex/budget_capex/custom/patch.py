import frappe
from frappe import _
from erpnext.accounts.doctype.budget.budget import (
    validate_budget_records,
    get_item_details,
)
from erpnext.accounts.utils import get_fiscal_year
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_accounting_dimensions,
)


def patch_validate_expense_function():
    """
    Template for patching your standalone function
    """
    try:
        # 1. Import the module containing your target function
        import erpnext.accounts.doctype.budget.budget as target_module

        # 2. Store reference to original function
        original_function = getattr(target_module, "validate_expense_against_budget")

        # 4. Apply the patch
        setattr(
            target_module,
            "validate_expense_against_budget",
            validate_expense_against_budget,
        )

        frappe.logger().info("Patched function successfully")

    except ImportError as e:
        frappe.logger().error(f"Could not import module: {e}")
    except AttributeError as e:
        frappe.logger().error(f"Function not found: {e}")


def validate_expense_against_budget(args, expense_amount=0):
    args = frappe._dict(args)
    if not frappe.get_all("Budget", limit=1):
        return

    if args.get("company") and not args.fiscal_year:
        args.fiscal_year = get_fiscal_year(
            args.get("posting_date"), company=args.get("company")
        )[0]
        frappe.flags.exception_approver_role = frappe.get_cached_value(
            "Company", args.get("company"), "exception_budget_approver_role"
        )

    if not frappe.get_cached_value(
        "Budget", {"fiscal_year": args.fiscal_year, "company": args.company}
    ):  # nosec
        return

    if not args.account:
        args.account = args.get("expense_account")

    if not (args.get("account") and args.get("cost_center")) and args.item_code:
        args.cost_center, args.account = get_item_details(args)

    if not args.account:
        return

    default_dimensions = [
        {
            "fieldname": "project",
            "document_type": "Project",
        },
        {
            "fieldname": "cost_center",
            "document_type": "Cost Center",
        },
    ]

    for dimension in default_dimensions + get_accounting_dimensions(as_list=False):
        budget_against = dimension.get("fieldname")

        if (
            args.get(budget_against)
            and args.account
            and (
                (
                    frappe.get_cached_value("Account", args.account, "root_type")
                    == "Expense"
                )
                or (
                    frappe.get_cached_value("Account", args.account, "account_type")
                    == "Fixed Asset"
                )
            )
        ):
            doctype = dimension.get("document_type")

            if frappe.get_cached_value("DocType", doctype, "is_tree"):
                lft, rgt = frappe.get_cached_value(
                    doctype, args.get(budget_against), ["lft", "rgt"]
                )
                condition = f"""and exists(select name from `tab{doctype}`
					where lft<={lft} and rgt>={rgt} and name=b.{budget_against})"""  # nosec
                args.is_tree = True
            else:
                condition = f"and b.{budget_against}={frappe.db.escape(args.get(budget_against))}"
                args.is_tree = False

            args.budget_against_field = budget_against
            args.budget_against_doctype = doctype

            budget_records = frappe.db.sql(
                f"""
				select
					b.{budget_against} as budget_against, ba.budget_amount, b.monthly_distribution,
					ifnull(b.applicable_on_material_request, 0) as for_material_request,
					ifnull(applicable_on_purchase_order, 0) as for_purchase_order,
					ifnull(applicable_on_booking_actual_expenses,0) as for_actual_expenses,
					b.action_if_annual_budget_exceeded, b.action_if_accumulated_monthly_budget_exceeded,
					b.action_if_annual_budget_exceeded_on_mr, b.action_if_accumulated_monthly_budget_exceeded_on_mr,
					b.action_if_annual_budget_exceeded_on_po, b.action_if_accumulated_monthly_budget_exceeded_on_po
				from
					`tabBudget` b, `tabBudget Account` ba
				where
					b.name=ba.parent and b.fiscal_year=%s
					and ba.account=%s and b.docstatus=1
					{condition}
			""",
                (args.fiscal_year, args.account),
                as_dict=True,
            )  # nosec

            if budget_records:
                validate_budget_records(args, budget_records, expense_amount)
