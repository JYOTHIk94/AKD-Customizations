"""
Landed Cost charge-type accounts.

BRD: FR-BUY-70 — Allocate Freight / Customs / Insurance / Handling / Inspection
                  to purchase cost (landed cost) required.
     FR-BUY-71 — Five types listed by AKD.
     FR-BUY-72 — Distribute by Amount (operational at LCV time, not config).
     FR-BUY-73 — Auto-set landed cost from PI rate: No.

What this creates (idempotent):
  Five leaf expense accounts under `Stock Expenses - AKD` so a Landed Cost
  Voucher can charge each cost type to its own account for analytics.

Usage:
  bench --site akd.com execute akd_customizations.setup.landed_cost.setup
"""

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

PARENT_CANDIDATES = ["Stock Expenses", "Direct Expenses", "Indirect Expenses"]

ACCOUNTS = [
	"Freight and Shipping Charges",
	"Customs Duty",
	"Insurance — Inward",
	"Handling Charges",
	"Inspection Fees",
]


def setup() -> dict:
	parent = _resolve_parent()
	created = []
	for acc_name in ACCOUNTS:
		full = f"{acc_name} - {ABBR}"
		if frappe.db.exists("Account", full):
			created.append(f"existing:{full}")
			continue
		doc = frappe.get_doc({
			"doctype": "Account",
			"account_name": acc_name,
			"parent_account": parent,
			"company": COMPANY,
			"root_type": "Expense",
			"account_type": "Expense Account",
			"is_group": 0,
		})
		doc.insert(ignore_permissions=True)
		created.append(f"created:{doc.name}")
	frappe.db.commit()
	return {"parent": parent, "accounts": created}


def _resolve_parent() -> str:
	for candidate in PARENT_CANDIDATES:
		full = f"{candidate} - {ABBR}"
		if frappe.db.exists("Account", full):
			return full
	frappe.throw(
		f"None of these expense parents found in CoA: {PARENT_CANDIDATES}. "
		"Cannot scaffold landed-cost accounts."
	)
