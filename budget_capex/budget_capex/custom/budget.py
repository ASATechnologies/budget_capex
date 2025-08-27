import frappe
from frappe import _

from erpnext.accounts.doctype.budget.budget import (
	Budget
)


class CapexBudget(Budget):
	
	def validate_accounts(self):
		account_list = []
		for d in self.get("accounts"):
			if d.account:
				account_details = frappe.get_cached_value(
					"Account", d.account, ["is_group", "company", "report_type", "account_type"], as_dict=1
				)
				if account_details.is_group:
					frappe.throw(_("Budget cannot be assigned against Group Account {0}").format(d.account))
				elif account_details.company != self.company:
					frappe.throw(
						_("Account {0} does not belongs to company {1}").format(d.account, self.company)
					)
				elif not (account_details.account_type == "Fixed Asset" or 
                     account_details.report_type == "Profit and Loss"):
					frappe.throw(
						_(
							"Budget cannot be assigned against {0}, as it's not an Income or Expense account"
						).format(d.account)
					)

				if d.account in account_list:
					frappe.throw(_("Account {0} has been entered multiple times").format(d.account))
				else:
					account_list.append(d.account)

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
    where_parts.append("(report_type = 'Profit and Loss' OR account_type = 'Fixed Asset')")

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