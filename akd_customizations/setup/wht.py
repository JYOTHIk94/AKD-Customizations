"""
Withholding Tax (TDS) scaffolding.

BRD: FR-BUY-68 — TDS / WHT required for AKD purchases.
     FR-SELL-54 — also required on sales side (same accounts apply).

Final WHT rates are an Open Item pending AKD input (BRD §12 — Nigeria rates,
UAE applicability). This module creates two placeholder categories so the
mechanism is in place and the BRD requirement is testable end-to-end. Rates
can be edited via the Tax Withholding Category UI once AKD confirms.

What this creates (idempotent):
  • Account `Tax Deducted at Source - AKD` (Liability, under Duties and Taxes)
  • Tax Withholding Category `AKD WHT 5%`   — single-threshold 0
  • Tax Withholding Category `AKD WHT 10%`  — single-threshold 0

Usage:
  bench --site akd.com execute akd_customizations.setup.wht.setup
"""

from datetime import date

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

TDS_ACCOUNT_NAME = "Tax Deducted at Source"
TDS_PARENT_GROUP_CANDIDATES = ["Duties and Taxes", "Current Liabilities"]

CATEGORIES = [
	("AKD WHT 5%", 5.0),
	("AKD WHT 10%", 10.0),
]


def setup() -> dict:
	report = {
		"account": _ensure_tds_account(),
		"categories": _ensure_categories(),
	}
	frappe.db.commit()
	return report


def _ensure_tds_account() -> str:
	full_name = f"{TDS_ACCOUNT_NAME} - {ABBR}"
	if frappe.db.exists("Account", full_name):
		return f"existing:{full_name}"

	parent = None
	for candidate in TDS_PARENT_GROUP_CANDIDATES:
		candidate_full = f"{candidate} - {ABBR}"
		if frappe.db.exists("Account", candidate_full):
			parent = candidate_full
			break
	if not parent:
		frappe.throw(
			f"None of these parent groups found in CoA: {TDS_PARENT_GROUP_CANDIDATES}. "
			"Cannot create TDS account."
		)

	doc = frappe.get_doc({
		"doctype": "Account",
		"account_name": TDS_ACCOUNT_NAME,
		"parent_account": parent,
		"company": COMPANY,
		"root_type": "Liability",
		"account_type": "Tax",
		"is_group": 0,
	})
	doc.insert(ignore_permissions=True)
	return f"created:{doc.name}"


def _ensure_categories() -> list[str]:
	tds_account = f"{TDS_ACCOUNT_NAME} - {ABBR}"
	# Effective from fiscal year start; AKD edits later when rates are agreed.
	fy_start = date(date.today().year, 1, 1)
	fy_end = date(date.today().year, 12, 31)

	results = []
	for name, rate in CATEGORIES:
		if frappe.db.exists("Tax Withholding Category", name):
			results.append(f"existing:{name}")
			continue
		doc = frappe.get_doc({
			"doctype": "Tax Withholding Category",
			"name": name,
			"category_name": name,
			"tax_deduction_basis": "Net Total",
			"rates": [{
				"tax_withholding_rate": rate,
				"single_threshold": 0,
				"cumulative_threshold": 0,
				"from_date": fy_start,
				"to_date": fy_end,
			}],
			"accounts": [{
				"company": COMPANY,
				"account": tds_account,
			}],
		})
		doc.insert(ignore_permissions=True)
		results.append(f"created:{doc.name}")
	return results
