"""
Wire AKD's Modes of Payment to company-specific bank accounts.

BRD references:
  FR-ACC-46  — Modes of Payment used: Bank Transfer, Cheque
  FR-ACC-49, 50 — RAK Bank Current AED is the company default bank

Bank Transfer and Cheque post against the RAK Bank AED current account.
Separate from accounting/bootstrap.py because it doesn't depend on cost centres
or VAT templates and can run before the Odoo CoA import.
"""

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

DEFAULT_BANK_GL_ACCOUNT = f"RAK Bank - Current AED - {ABBR}"
MODES_TO_WIRE = ["Bank Transfer", "Cheque"]


def wire() -> list[str]:
	if not frappe.db.exists("Account", DEFAULT_BANK_GL_ACCOUNT):
		frappe.throw(
			f"Bank GL account {DEFAULT_BANK_GL_ACCOUNT!r} missing — "
			"run foundation.setup() first."
		)

	updated = []
	for mop in MODES_TO_WIRE:
		if not frappe.db.exists("Mode of Payment", mop):
			continue
		doc = frappe.get_doc("Mode of Payment", mop)
		if any(r.company == COMPANY for r in (doc.accounts or [])):
			continue
		doc.append("accounts", {
			"company": COMPANY,
			"default_account": DEFAULT_BANK_GL_ACCOUNT,
		})
		doc.save(ignore_permissions=True)
		updated.append(mop)
	return updated
