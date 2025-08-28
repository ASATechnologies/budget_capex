import frappe
from frappe import _

from erpnext.accounts.doctype.budget.budget import Budget, DuplicateBudgetError


class CapexBudget(Budget):

    def validate_accounts(self):
        account_list = []
        for d in self.get("accounts"):
            if d.account:
                account_details = frappe.get_cached_value(
                    "Account",
                    d.account,
                    ["is_group", "company", "report_type", "account_type"],
                    as_dict=1,
                )
                if account_details.is_group:
                    frappe.throw(
                        _("Budget cannot be assigned against Group Account {0}").format(
                            d.account
                        )
                    )
                elif account_details.company != self.company:
                    frappe.throw(
                        _("Account {0} does not belongs to company {1}").format(
                            d.account, self.company
                        )
                    )
                elif not (
                    account_details.account_type == "Fixed Asset"
                    or account_details.report_type == "Profit and Loss"
                ):
                    frappe.throw(
                        _(
                            "Budget cannot be assigned against {0}, as it's not an Income or Expense account"
                        ).format(d.account)
                    )

                if d.account in account_list:
                    frappe.throw(
                        _("Account {0} has been entered multiple times").format(
                            d.account
                        )
                    )
                else:
                    account_list.append(d.account)

    def validate_duplicate(self):
        budget_against_field = frappe.scrub(self.budget_against)
        budget_against = self.get(budget_against_field)
        accounts = [d.account for d in self.accounts] or []

        # Get existing budgets for the same criteria
        existing_budgets = frappe.db.sql(
            """
			select
				b.name, ba.account 
			from `tabBudget` b, `tabBudget Account` ba
			where
				ba.parent = b.name and b.docstatus < 2 and b.company = %s and {}=%s and
				b.fiscal_year=%s and b.name != %s and ba.account in ({})
			""".format(
                budget_against_field, ",".join(["%s"] * len(accounts))
            ),
            (
                self.company,
                budget_against,
                self.fiscal_year,
                self.name,
                *tuple(accounts),
            ),
            as_dict=1,
        )

        if not existing_budgets:
            return

        # Get current budget's monthly distribution
        current_monthly_distribution = self.get_monthly_distribution()

        # Check each existing budget for overlapping monthly distributions
        for existing_budget in existing_budgets:
            # Get the monthly distribution for the existing budget
            existing_monthly_distribution = frappe.get_doc(
                "Budget", existing_budget.name
            ).get_monthly_distribution()

            # Check if there's any overlap in monthly distributions
            if self.has_overlapping_months(
                current_monthly_distribution,
                existing_monthly_distribution,
                existing_budget.account,
            ):
                frappe.throw(
                    _(
                        "Another Budget record '{0}' already exists against {1} '{2}' and account '{3}' for fiscal year {4} with overlapping monthly distribution"
                    ).format(
                        existing_budget.name,
                        self.budget_against,
                        budget_against,
                        existing_budget.account,
                        self.fiscal_year,
                    ),
                    DuplicateBudgetError,
                )

    def get_monthly_distribution(self):
        """Get the monthly distribution for this budget"""
        monthly_distribution = {}

        if hasattr(self, "monthly_distribution") and self.monthly_distribution:
            # If monthly distribution is specified, get the percentages for each month
            distribution_doc = frappe.get_doc(
                "Monthly Distribution", self.monthly_distribution
            )
            for row in distribution_doc.percentages:
                if row.percentage_allocation > 0:
                    monthly_distribution[row.month] = row.percentage_allocation
        else:
            # If no monthly distribution specified, assume it applies to all months
            months = [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ]
            for month in months:
                monthly_distribution[month] = 8.333  # roughly 100/12

        return monthly_distribution

    def has_overlapping_months(
        self, current_distribution, existing_distribution, account
    ):
        """Check if two monthly distributions have overlapping months for the same account"""
        # Only check for the specific account that matches
        current_account_exists = any(d.account == account for d in self.accounts)
        if not current_account_exists:
            return False

        # Get months where both distributions have allocations > 0
        current_months = set(
            month
            for month, percentage in current_distribution.items()
            if percentage > 0
        )
        existing_months = set(
            month
            for month, percentage in existing_distribution.items()
            if percentage > 0
        )

        # Check for intersection (overlapping months)
        overlapping_months = current_months.intersection(existing_months)

        return len(overlapping_months) > 0


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def account_link_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Link field query that enforces:
      company = <company> AND is_group = 0 AND (report_type = 'Profit and Loss' OR account_type = 'Fixed Asset')
    Also supports user typing via `txt` (matches name or account_name).
    Returns rows as (value, description).
    """
    company = (filters or {}).get("company")

    params = {
        "txt": f"%{txt or ''}%",
        "start": int(start) if start else 0,
        "page_len": int(page_len) if page_len else 20,
    }

    where_parts = ["is_group = 0"]

    if company:
        where_parts.append("company = %(company)s")
        params["company"] = company

    # Your OR group:
    where_parts.append(
        "(report_type = 'Profit and Loss' OR account_type = 'Fixed Asset')"
    )

    # Let users search by what they type
    search_cond = " AND (name LIKE %(txt)s OR account_name LIKE %(txt)s)"

    query = f"""
		SELECT name, account_name
		FROM `tabAccount`
		WHERE {" AND ".join(where_parts)} {search_cond}
		ORDER BY
			CASE WHEN name LIKE %(txt)s THEN 0 ELSE 1 END,
			name
		LIMIT %(start)s, %(page_len)s
	"""

    return frappe.db.sql(query, params)
