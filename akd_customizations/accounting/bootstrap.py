"""
Company-aware Accounting setup for AKD Consulting LLC.

Run after:
  1. Company doctype is created with abbreviation "AKD"
  2. Chart of Accounts has been imported from Odoo
  3. VAT Input / VAT Output / Cash / Bank accounts exist in CoA

Usage:
  bench --site akd.com execute \\
    akd_customizations.accounting.bootstrap.setup_akd_company \\
    --kwargs "{'company': 'AKD Consulting LLC'}"

BRD references: FR-ACC-12, 23, 24, 26, 27, 46, 50.
"""

import frappe


COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

COST_CENTRES = ["Sales", "Admin", "Finance", "HR"]

# (template_name_suffix, rate, account_lookup_root)
# account_lookup_root: GL account name pattern under which we expect VAT Input/Output to live.
UAE_VAT_TEMPLATES = [
	("UAE VAT 5%", 5.0),
	("UAE VAT 0%", 0.0),
	("UAE VAT Exempt", 0.0),
	("UAE VAT RCM", 5.0),
	("UAE VAT Out of Scope", 0.0),
]


def setup_akd_company(company: str = COMPANY) -> dict:
	abbr = frappe.db.get_value("Company", company, "abbr")
	if not abbr:
		frappe.throw(f"Company {company!r} not found. Create it first.")

	results = {
		"cost_centres": _create_cost_centres(company, abbr),
		"sales_tax_templates": _create_tax_templates(company, abbr, "Sales"),
		"purchase_tax_templates": _create_tax_templates(company, abbr, "Purchase"),
		"mode_of_payment_accounts": _wire_mode_of_payment_accounts(company, abbr),
	}
	frappe.db.commit()
	return results


def _create_cost_centres(company: str, abbr: str) -> list[str]:
	parent = f"{company} - {abbr}"
	if not frappe.db.exists("Cost Center", parent):
		frappe.throw(f"Parent cost center {parent!r} missing. Create company first.")

	created = []
	for cc in COST_CENTRES:
		name = f"{cc} - {abbr}"
		if frappe.db.exists("Cost Center", name):
			continue
		doc = frappe.get_doc({
			"doctype": "Cost Center",
			"cost_center_name": cc,
			"parent_cost_center": parent,
			"company": company,
			"is_group": 0,
		})
		doc.insert(ignore_permissions=True)
		created.append(name)
	return created


def _create_tax_templates(company: str, abbr: str, direction: str) -> list[str]:
	"""direction is 'Sales' or 'Purchase'."""
	dt = f"{direction} Taxes and Charges Template"
	child_dt = f"{direction} Taxes and Charges"
	# Standard ERPNext naming: tax-rate account lives under "Duties and Taxes".
	output_account = _find_account(company, ["VAT Output", "Output VAT"])
	input_account = _find_account(company, ["VAT Input", "Input VAT"])

	created = []
	for label, rate in UAE_VAT_TEMPLATES:
		name = f"AKD {label} - {abbr}"
		if frappe.db.exists(dt, name):
			continue

		account_head = output_account if direction == "Sales" else input_account
		if rate == 0:
			# Zero-rated / Exempt / Out-of-scope templates still need an account_head
			# but compute zero. Point at the same account; rate filter does the rest.
			pass

		doc = frappe.get_doc({
			"doctype": dt,
			"title": f"AKD {label}",
			"company": company,
			"taxes": [{
				"doctype": child_dt,
				"charge_type": "On Net Total",
				"account_head": account_head,
				"description": label,
				"rate": rate,
				"included_in_print_rate": 0,
			}],
		})
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created


def _wire_mode_of_payment_accounts(company: str, abbr: str) -> list[str]:
	"""Attach company-specific default accounts to each Mode of Payment."""
	bank_aed = _find_account(company, ["RAK Bank - Current AED", "Bank Account"])
	updated = []
	for mop in ["Bank Transfer", "Cheque"]:
		if not frappe.db.exists("Mode of Payment", mop):
			continue
		doc = frappe.get_doc("Mode of Payment", mop)
		# Skip if already wired for this company
		if any(row.company == company for row in (doc.accounts or [])):
			continue
		doc.append("accounts", {
			"doctype": "Mode of Payment Account",
			"company": company,
			"default_account": bank_aed,
		})
		doc.save(ignore_permissions=True)
		updated.append(mop)
	return updated


def _find_account(company: str, candidates: list[str]) -> str:
	"""Find first matching account head in the company's CoA."""
	for needle in candidates:
		acc = frappe.db.sql(
			"""
			SELECT name FROM `tabAccount`
			WHERE company = %s AND is_group = 0
			  AND (account_name = %s OR name LIKE %s)
			LIMIT 1
			""",
			(company, needle, f"{needle}%"),
		)
		if acc:
			return acc[0][0]
	frappe.throw(
		f"None of these accounts found in CoA for {company}: {candidates}. "
		"Verify the CoA import or rename accounts to match."
	)
