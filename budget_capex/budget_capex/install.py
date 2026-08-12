import json

import frappe
from frappe import _
from frappe.utils import getdate, nowdate


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
		accounting_dimension = frappe.get_doc(
			{
				"doctype": "Accounting Dimension",
				"document_type": "Capital Expenditure",
				"label": "Capital Expenditure",
				"fieldname": "capital_expenditure",
				"disabled": 0,
				"mandatory_for_bs": 0,  # Not mandatory for Balance Sheet
				"mandatory_for_pl": 0,  # Mandatory for Profit & Loss (expenses)
			}
		)

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
			"Custom Field", filters={"fieldname": "capital_expenditure"}, fields=["name", "dt"]
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


def after_insert_fiscal_year(doc, method):
	"""Runs after a Fiscal Year is created"""
	fiscal_year = doc.name  # usually same as doc.fiscal_year
	start_year = getdate(doc.year_start_date).year

	# Example: check if fiscal year == current calendar year
	current_year = getdate().year
	if start_year == current_year:
		frappe.logger().info(f"Fiscal Year {fiscal_year} is current year. Running fixture logic...")

		# Call your fixture loader here
		create_monthly_distributions_with_fiscal_year(fiscal_year)


def create_distribution_fixtures():
	today = nowdate()
	today_date_object = frappe.utils.getdate(today)
	current_year = today_date_object.year

	if frappe.db.exists("Fiscal Year", current_year):
		create_monthly_distributions_with_fiscal_year(current_year)


def create_monthly_distributions_with_fiscal_year(fiscal_year):

	# Path to your fixture file
	fixture_path = frappe.get_app_path(
		"budget_capex", "budget_capex", "custom", "data", "monthly_distribution.json"
	)

	with open(fixture_path, "r") as f:
		data = json.load(f)

	for record in data:
		doctype = record.get("doctype")
		name = record.get("name")
		new_name = f"{record['name']} - {fiscal_year}"
		record["name"] = new_name
		record["distribution_id"] = new_name
		record["fiscal_year"] = fiscal_year
		if not frappe.db.exists(doctype, new_name):
			doc = frappe.get_doc(record)
			doc.insert()

	frappe.db.commit()


# Hook functions for installation
def after_install():
	"""
	Called after app installation
	"""
	setup_capex_accounting_dimension()
	create_distribution_fixtures()


def before_uninstall():
	"""
	Called before app uninstallation
	"""
	remove_capex_accounting_dimension()
