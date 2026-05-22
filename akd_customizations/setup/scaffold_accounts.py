"""
Scaffold accounts the BRD names explicitly, so the tax-template and exchange
helpers in accounting/bootstrap.py can find them on the Standard CoA.

BRD references:
  FR-ACC-22  — separate Exchange Gain/Loss account
  FR-ACC-26  — VAT output account named "VAT Output"
  FR-ACC-27  — VAT input account named "VAT Input"

Notes:
  • These accounts must survive the Odoo CoA import, OR the Odoo mapping
    (utils/coa_mapper.py) must rename equivalents to the same names. If
    Odoo CoA replaces them by name, accounting/bootstrap.py templates will
    point at orphan accounts — re-run after import to refresh.
"""

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

VAT_OUTPUT = "VAT Output"
VAT_INPUT = "VAT Input"
FX_GAIN_LOSS = "Exchange Gain/Loss"


def add() -> dict:
	return {
		"vat_output": _ensure_account(
			VAT_OUTPUT, "Tax", parent_candidates=["Duties and Taxes", "Tax Assets"],
		),
		"vat_input": _ensure_account(
			VAT_INPUT, "Tax", parent_candidates=["Duties and Taxes", "Tax Assets"],
		),
		"fx_gain_loss": _ensure_account(
			FX_GAIN_LOSS, "Expense Account",
			parent_candidates=[
				"Indirect Expenses", "Direct Expenses", "Expenses",
			],
		),
	}


def _ensure_account(account_name: str, account_type: str, parent_candidates: list[str]) -> str:
	full_name = f"{account_name} - {ABBR}"
	if frappe.db.exists("Account", full_name):
		return f"existing:{full_name}"

	parent = None
	for needle in parent_candidates:
		parent = frappe.db.get_value("Account", {
			"company": COMPANY,
			"is_group": 1,
			"account_name": needle,
		}, "name")
		if parent:
			break

	if not parent:
		frappe.throw(
			f"No parent group account found for {account_name} "
			f"among {parent_candidates}. The Standard CoA should provide one — "
			"verify Company creation produced default accounts."
		)

	doc = frappe.get_doc({
		"doctype": "Account",
		"account_name": account_name,
		"parent_account": parent,
		"company": COMPANY,
		"account_type": account_type,
		"is_group": 0,
	})
	doc.insert(ignore_permissions=True)
	return f"created:{doc.name}"
