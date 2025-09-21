# Copyright (c) 2025, ASA Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CapitalExpenditure(Document):
	def autoname(self):
		company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
		self.name =  " - ".join([self.capex_name, company_abbr])

