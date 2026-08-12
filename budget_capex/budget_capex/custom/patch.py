import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.budget.budget import (
	get_fiscal_year_date_range,
	get_item_details,
	validate_budget_records,
)
from erpnext.accounts.utils import get_fiscal_year
from frappe import _
from frappe.utils import add_months, flt, fmt_money, get_last_day, getdate, month_diff


def patch_validate_expense_function():
	"""
	Template for patching your standalone function
	"""
	try:
		# 1. Import the module containing your target function
		import erpnext.accounts.doctype.budget.budget as target_module

		# 2. Store reference to original function
		getattr(target_module, "validate_expense_against_budget")

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


def validate_expense_against_budget(params, expense_amount=0):
	params = frappe._dict(params)
	if not frappe.db.count("Budget", cache=True):
		return

	if not params.fiscal_year:
		params.fiscal_year = get_fiscal_year(params.get("posting_date"), company=params.get("company"))[0]

	posting_date = getdate(params.get("posting_date"))
	posting_fiscal_year = get_fiscal_year(posting_date, company=params.get("company"))[0]
	year_start_date, year_end_date = get_fiscal_year_date_range(posting_fiscal_year, posting_fiscal_year)

	budget_exists = frappe.db.sql(
		"""
		select name
		from `tabBudget`
		where company = %s
		and docstatus = 1
		and (SELECT year_start_date FROM `tabFiscal Year` WHERE name = from_fiscal_year) <= %s
		and (SELECT year_end_date FROM `tabFiscal Year` WHERE name = to_fiscal_year) >= %s
		limit 1
		""",
		(params.company, year_end_date, year_start_date),
	)

	if not budget_exists:
		return

	if params.get("company"):
		frappe.flags.exception_approver_role = frappe.get_cached_value(
			"Company", params.get("company"), "exception_budget_approver_role"
		)

	if not params.account:
		params.account = params.get("expense_account")

	if not params.get("expense_account") and params.get("account"):
		params.expense_account = params.account

	if not (params.get("account") and params.get("cost_center")) and params.item_code:
		params.cost_center, params.account = get_item_details(params)

	if not params.account:
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
			params.get(budget_against)
			and params.account
			and (
				(frappe.get_cached_value("Account", params.account, "root_type") == "Expense")
				or (frappe.get_cached_value("Account", params.account, "account_type") == "Fixed Asset")
			)
		):
			doctype = dimension.get("document_type")

			if frappe.get_cached_value("DocType", doctype, "is_tree"):
				lft, rgt = frappe.get_cached_value(doctype, params.get(budget_against), ["lft", "rgt"])
				condition = f"""and exists(select name from `tab{doctype}`
					where lft<={lft} and rgt>={rgt} and name=b.{budget_against})"""  # nosec
				params.is_tree = True
			else:
				condition = f"and b.{budget_against}={frappe.db.escape(params.get(budget_against))}"
				params.is_tree = False

			params.budget_against_field = budget_against
			params.budget_against_doctype = doctype

			budget_records = frappe.db.sql(
				f"""
				SELECT
					b.name,
					b.{budget_against} AS budget_against,
					b.budget_amount,
					b.from_fiscal_year,
					b.to_fiscal_year,
					b.budget_start_date,
					b.budget_end_date,
					IFNULL(b.applicable_on_material_request, 0) AS for_material_request,
					IFNULL(b.applicable_on_purchase_order, 0) AS for_purchase_order,
					IFNULL(b.applicable_on_booking_actual_expenses, 0) AS for_actual_expenses,
					b.action_if_annual_budget_exceeded,
					b.action_if_accumulated_monthly_budget_exceeded,
					b.action_if_annual_budget_exceeded_on_mr,
					b.action_if_accumulated_monthly_budget_exceeded_on_mr,
					b.action_if_annual_budget_exceeded_on_po,
					b.action_if_accumulated_monthly_budget_exceeded_on_po
				FROM
					`tabBudget` b
				WHERE
					b.company = %s
					AND b.docstatus = 1
					AND %s BETWEEN b.budget_start_date AND b.budget_end_date
					AND b.account = %s
					{condition}
				""",
				(params.company, params.posting_date, params.account),
				as_dict=True,
			)  # nosec

			if budget_records:
				validate_budget_records(params, budget_records, expense_amount)
