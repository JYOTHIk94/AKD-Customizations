"""
Sales Partner scaffolding.

BRD: FR-SELL-56  External sales partners (agents, dealers, resellers) — Yes.
     FR-SELL-57  Commission calculation — Fixed %.
     FR-SELL-58  Multiple salespeople share commission on one order — Yes.
     FR-SELL-60  AKD has OEM partners, no distributors.

What this creates (idempotent):
  • Sales Partner Type `OEM` (if not in seeded list)
  • 2 placeholder OEM partners — `AKD OEM Partner Placeholder A/B`
    with commission_rate = 0 so accidental SOs don't accrue commission.
    AKD edits at sign-off to add real partners with real rates.

Usage:
  bench --site akd.com execute akd_customizations.setup.sales_partner.setup
"""

import frappe

PARTNER_TYPE = "OEM"

PLACEHOLDERS = [
	{
		"partner_name": "AKD OEM Partner Placeholder A",
		"commission_rate": 0,
		"territory": "Middle East",
	},
	{
		"partner_name": "AKD OEM Partner Placeholder B",
		"commission_rate": 0,
		"territory": "Africa",
	},
]


def setup() -> dict:
	return {
		"partner_type": _ensure_partner_type(),
		"partners": _ensure_partners(),
	}


def _ensure_partner_type() -> str:
	if frappe.db.exists("Sales Partner Type", PARTNER_TYPE):
		return f"existing:{PARTNER_TYPE}"
	frappe.get_doc({
		"doctype": "Sales Partner Type",
		"sales_partner_type": PARTNER_TYPE,
	}).insert(ignore_permissions=True)
	return f"created:{PARTNER_TYPE}"


def _ensure_partners() -> list[str]:
	results = []
	for p in PLACEHOLDERS:
		if frappe.db.exists("Sales Partner", p["partner_name"]):
			results.append(f"existing:{p['partner_name']}")
			continue
		territory = p.get("territory")
		if territory and not frappe.db.exists("Territory", territory):
			territory = None
		doc = frappe.get_doc({
			"doctype": "Sales Partner",
			"partner_name": p["partner_name"],
			"partner_type": PARTNER_TYPE,
			"commission_rate": p["commission_rate"],
			"territory": territory,
		})
		doc.insert(ignore_permissions=True)
		results.append(f"created:{doc.name}")
	frappe.db.commit()
	return results
