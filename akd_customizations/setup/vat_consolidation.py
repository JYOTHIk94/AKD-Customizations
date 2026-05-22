"""
Reconcile ERPNext UAE-regional VAT accounts with the BRD-mandated names.

Problem (observed after Setup Wizard with country=UAE on akd.com):
  Under "Duties and Taxes - AKD" (Liability) we now have FIVE child accounts:
    • VAT 5%        — UAE regional, ERPNext-provided
    • VAT Zero      — UAE regional
    • VAT Exempted  — UAE regional
    • VAT Output    — created by scaffold_accounts.py per FR-ACC-26
    • VAT Input     — created by scaffold_accounts.py per FR-ACC-27

The BRD spec (FR-ACC-23..27) is a single-account-per-direction model:
  • All 5 sales tax templates post to "VAT Output".
  • All 5 purchase tax templates post to "VAT Input".

ERPNext-UAE's per-rate-account model is a valid alternative but does not
match the BRD-signed-off names. Until AKD chooses, no decision is made.

This module provides two reversible options:

  freeze_regional() — preferred, soft.
    Sets the 3 UAE-regional accounts to disabled + frozen so no transaction
    can post to them, while leaving the rows in place for audit.

  rename_regional(suffix=" (deprecated)") — harder, irreversible by
    re-running because it changes the account_name.

Run only after AKD signs off — neither mode is invoked by the orchestrator.
"""

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

UAE_REGIONAL_VAT_ACCOUNTS = ["VAT 5%", "VAT Zero", "VAT Exempted"]


def freeze_regional() -> dict:
	"""Soft-disable the 3 UAE-regional VAT accounts. Reversible."""
	result = {}
	for name in UAE_REGIONAL_VAT_ACCOUNTS:
		full_name = f"{name} - {ABBR}"
		if not frappe.db.exists("Account", full_name):
			result[name] = "absent"
			continue
		current = frappe.db.get_value(
			"Account", full_name, ["disabled", "freeze_account"], as_dict=True,
		)
		if current and current.get("disabled") and current.get("freeze_account") == "Yes":
			result[name] = "already-frozen"
			continue
		frappe.db.set_value("Account", full_name, {
			"disabled": 1,
			"freeze_account": "Yes",
		})
		result[name] = "frozen"
	return result


def rename_regional(suffix: str = " (deprecated)") -> dict:
	"""Rename UAE-regional accounts so they can't be confused with BRD ones."""
	result = {}
	for name in UAE_REGIONAL_VAT_ACCOUNTS:
		full_name = f"{name} - {ABBR}"
		if not frappe.db.exists("Account", full_name):
			result[name] = "absent"
			continue
		new_account_name = f"{name}{suffix}"
		new_full = f"{new_account_name} - {ABBR}"
		if frappe.db.exists("Account", new_full):
			result[name] = "already-renamed"
			continue
		frappe.rename_doc("Account", full_name, new_full, force=True)
		frappe.db.set_value("Account", new_full, "account_name", new_account_name)
		result[name] = f"renamed-to:{new_full}"
	return result


def status() -> dict:
	"""Inspector — no writes. Returns the current VAT-account landscape."""
	accounts = frappe.db.get_list(
		"Account",
		filters={"company": COMPANY, "account_name": ["like", "%VAT%"]},
		fields=["name", "account_name", "disabled", "freeze_account", "is_group"],
	)
	return {"vat_accounts": accounts}
