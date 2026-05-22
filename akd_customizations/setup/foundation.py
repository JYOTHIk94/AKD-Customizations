"""
Foundation setup — ERPNext Setup Wizard + BRD-specific patches.

If the site has not been through the Setup Wizard yet (no Company, no UOMs,
no Warehouse Types), we drive `erpnext.setup.setup_wizard.setup_wizard.
setup_complete` programmatically with AKD's parameters. After that, we patch
Company attrs the wizard doesn't take (TRN, CR, perpetual=off per FR-ACC-79),
add the registered address, enable extra currencies, and create RAK Bank +
its two Bank Accounts.

BRD references:
  Section 3  — company profile (legal name, abbr, AED, UAE, TRN, CR, address)
  FR-ACC-16  — fiscal year 1 Jan to 31 Dec
  FR-ACC-19, FR-BUY-74 — transaction currencies AED, USD, EUR, GBP, NGN
  FR-ACC-49, FR-ACC-50 — 2 RAK Bank accounts (Current AED + Current USD)
  FR-ACC-79  — periodic inventory (perpetual disabled at Company level)

Run via the orchestrator. Each helper is idempotent and returns what it touched.
"""

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"
COUNTRY = "United Arab Emirates"
BASE_CURRENCY = "AED"
TAX_ID = "104661110700003"          # TRN — Accounts Q8/Q39
COMPANY_NUMBER = "1403338"          # CR / trade-licence number — Accounts Q9
ADDRESS_LINE_1 = "3302 Prism Tower"
ADDRESS_CITY = "Dubai"
ADDRESS_AREA = "Business Bay"

FISCAL_YEAR_START = "2026-01-01"
FISCAL_YEAR_END = "2026-12-31"
FISCAL_YEAR_NAME = "2026"

TRANSACTION_CURRENCIES = ["AED", "USD", "EUR", "GBP", "NGN"]

BANK_NAME = "RAK Bank"
BANK_ACCOUNTS = [
	# (account_name on Bank Account, currency)
	("RAK Bank - Current AED", "AED"),
	("RAK Bank - Current USD", "USD"),
]


def setup() -> dict:
	return {
		"setup_wizard": _run_setup_wizard_if_needed(),
		"company_patch": _patch_company_brd_attrs(),
		"address": _ensure_company_address(),
		"fiscal_year": _ensure_fiscal_year(),
		"currencies_enabled": _enable_currencies(),
		"bank": _ensure_bank(),
		"bank_gl_accounts": _ensure_bank_gl_accounts(),
		"bank_accounts": _ensure_bank_accounts(),
	}


def _run_setup_wizard_if_needed() -> str:
	if frappe.db.exists("Company", COMPANY):
		return f"skipped:{COMPANY} already exists"

	# Lazy import — ERPNext may not be on path if this app is mis-installed.
	from erpnext.setup.setup_wizard.setup_wizard import setup_complete

	args = frappe._dict({
		"language": "English",
		"country": COUNTRY,
		"timezone": "Asia/Dubai",
		"currency": BASE_CURRENCY,
		"company_name": COMPANY,
		"company_abbr": ABBR,
		"fy_start_date": FISCAL_YEAR_START,
		"fy_end_date": FISCAL_YEAR_END,
		"chart_of_accounts": "Standard",
		# Domain table only has Manufacturing/Retail on this site; BRD says
		# "Other" (Accounts Q5). Pick a placeholder that exists — Company.domain
		# is informational, not behavioural.
		"domain": "Manufacturing",
		"bank_account": BANK_NAME,
		"setup_demo": 0,
	})
	setup_complete(args)
	frappe.db.commit()
	return f"ran:setup_complete for {COMPANY}"


def _patch_company_brd_attrs() -> dict:
	"""Patch Company attrs the Setup Wizard doesn't take.

	v16 Company doctype stores the trade-licence / CR number under the free-form
	`registration_details` longtext rather than a dedicated column, so we
	prefix it with a stable label so downstream parsing / print formats can
	pick it back out.
	"""
	registration_details = f"CR / Trade Licence: {COMPANY_NUMBER}"

	patch = {
		"tax_id": TAX_ID,                       # FR-ACC TRN
		"registration_details": registration_details,
		"enable_perpetual_inventory": 0,        # FR-ACC-79
	}
	current = frappe.db.get_value(
		"Company", COMPANY,
		list(patch.keys()), as_dict=True,
	) or {}
	changes = {
		k: {"from": current.get(k), "to": v}
		for k, v in patch.items()
		if current.get(k) != v
	}
	if changes:
		frappe.db.set_value("Company", COMPANY, patch)
	return changes


def _ensure_company_address() -> str:
	title = f"{COMPANY}-Billing"
	if frappe.db.exists("Address", {"address_title": COMPANY, "address_type": "Billing"}):
		return f"existing:{title}"

	doc = frappe.get_doc({
		"doctype": "Address",
		"address_title": COMPANY,
		"address_type": "Billing",
		"address_line1": ADDRESS_LINE_1,
		"address_line2": ADDRESS_AREA,
		"city": ADDRESS_CITY,
		"country": COUNTRY,
		"is_primary_address": 1,
		"is_shipping_address": 1,
		"links": [{
			"link_doctype": "Company",
			"link_name": COMPANY,
		}],
	})
	doc.insert(ignore_permissions=True)
	return f"created:{doc.name}"


def _ensure_fiscal_year() -> str:
	existing = frappe.db.exists("Fiscal Year", {
		"year_start_date": FISCAL_YEAR_START,
		"year_end_date": FISCAL_YEAR_END,
	})
	if existing:
		# Ensure company is linked
		doc = frappe.get_doc("Fiscal Year", existing)
		if not any(c.company == COMPANY for c in (doc.companies or [])):
			doc.append("companies", {"company": COMPANY})
			doc.save(ignore_permissions=True)
		return f"existing:{existing}"

	doc = frappe.get_doc({
		"doctype": "Fiscal Year",
		"year": FISCAL_YEAR_NAME,
		"year_start_date": FISCAL_YEAR_START,
		"year_end_date": FISCAL_YEAR_END,
		"companies": [{"company": COMPANY}],
	})
	doc.insert(ignore_permissions=True)
	return f"created:{doc.name}"


def _enable_currencies() -> list[str]:
	touched = []
	for code in TRANSACTION_CURRENCIES:
		if not frappe.db.exists("Currency", code):
			continue
		if not frappe.db.get_value("Currency", code, "enabled"):
			frappe.db.set_value("Currency", code, "enabled", 1)
			touched.append(code)
	return touched


def _ensure_bank() -> str:
	if frappe.db.exists("Bank", BANK_NAME):
		return f"existing:{BANK_NAME}"
	doc = frappe.get_doc({"doctype": "Bank", "bank_name": BANK_NAME})
	doc.insert(ignore_permissions=True)
	return f"created:{BANK_NAME}"


def _ensure_bank_gl_accounts() -> list[str]:
	"""Create the GL accounts that the Bank Account doctype rows point to."""
	parent = _find_parent_account(["Bank Accounts", "Bank Account"])
	if not parent:
		frappe.throw(
			"Could not find a parent group account 'Bank Accounts' under the "
			f"company {COMPANY}. The Standard CoA should provide it — "
			"verify Company creation actually produced default accounts."
		)

	created = []
	for account_name, currency in BANK_ACCOUNTS:
		# Frappe auto-suffixes "- AKD" to the saved name.
		full_name = f"{account_name} - {ABBR}"
		if frappe.db.exists("Account", full_name):
			continue
		doc = frappe.get_doc({
			"doctype": "Account",
			"account_name": account_name,
			"parent_account": parent,
			"company": COMPANY,
			"account_type": "Bank",
			"account_currency": currency,
			"is_group": 0,
		})
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created


def _ensure_bank_accounts() -> list[str]:
	created = []
	for account_name, currency in BANK_ACCOUNTS:
		# Bank Account autonames as "{account_name} - {bank}".
		bank_account_name = f"{account_name} - {BANK_NAME}"
		if frappe.db.exists("Bank Account", bank_account_name):
			continue
		gl_account = f"{account_name} - {ABBR}"
		if not frappe.db.exists("Account", gl_account):
			frappe.throw(
				f"GL account {gl_account!r} missing — "
				"_ensure_bank_gl_accounts should have created it."
			)
		doc = frappe.get_doc({
			"doctype": "Bank Account",
			"account_name": account_name,
			"bank": BANK_NAME,
			"account": gl_account,
			# Bank Account Type doctype is empty on this site and is optional;
			# leave blank rather than auto-create "Current"/"Savings" entries
			# that AKD did not request.
			"company": COMPANY,
			"is_company_account": 1,
		})
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created


def _find_parent_account(candidates: list[str]) -> str | None:
	for needle in candidates:
		acc = frappe.db.get_value("Account", {
			"company": COMPANY,
			"is_group": 1,
			"account_name": needle,
		}, "name")
		if acc:
			return acc
	return None
