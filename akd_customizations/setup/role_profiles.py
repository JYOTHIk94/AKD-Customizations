"""
AKD Role Profiles per FR-ACC-84.

BRD names:                            ERPNext base roles to bundle:
  AKD Accounts User    →  Accounts User
  AKD Purchasing       →  Purchase User, Stock User
  AKD Admin Lead       →  Accounts Manager, Purchase Manager, Sales Manager,
                          Stock Manager

No data-level / role-level invoice or JE restrictions are required
(FR-ACC-85, 86, 87, 88 all "No") so these profiles are deliberately broad.

User records are NOT created here — AKD's email addresses for Raymond, Adeeb,
Puneet, and Theresa are still pending. Once supplied, attach this profile via
User.role_profile_name.
"""

import frappe

ROLE_PROFILES = {
	"AKD Accounts User": [
		"Accounts User",
	],
	"AKD Purchasing": [
		"Purchase User",
		"Stock User",
	],
	"AKD Admin Lead": [
		"Accounts Manager",
		"Purchase Manager",
		"Sales Manager",
		"Stock Manager",
	],
	# FR-QA-55..58 — Quality team. Roles created by setup/quality.py, which
	# orchestrator.run() invokes before this step.
	"AKD Quality": [
		"Quality Manager",
		"Quality Inspector",
		"Quality Auditor",
	],
	# FR-CRM-63 — CRM team. Roles created by setup/crm.py, which
	# orchestrator.run() invokes before this step.
	"AKD CRM": [
		"Sales Manager",
		"Sales User",
		"Marketing User",
		"CRM Admin",
	],
	# FR-PROJ-60 — Projects team. Timesheet User created by setup/projects.py,
	# which orchestrator.run() invokes before this step.
	"AKD Projects": [
		"Projects Manager",
		"Projects User",
		"Timesheet User",
	],
}


def ensure() -> dict:
	created = []
	updated = []

	for profile_name, roles in ROLE_PROFILES.items():
		_assert_roles_exist(roles)

		if frappe.db.exists("Role Profile", profile_name):
			doc = frappe.get_doc("Role Profile", profile_name)
			current = {r.role for r in (doc.roles or [])}
			target = set(roles)
			if current != target:
				doc.roles = []
				for r in roles:
					doc.append("roles", {"role": r})
				doc.save(ignore_permissions=True)
				updated.append(profile_name)
			continue

		doc = frappe.get_doc({
			"doctype": "Role Profile",
			"role_profile": profile_name,
			"roles": [{"role": r} for r in roles],
		})
		doc.insert(ignore_permissions=True)
		created.append(profile_name)

	return {"created": created, "updated": updated}


def _assert_roles_exist(roles: list[str]) -> None:
	missing = [r for r in roles if not frappe.db.exists("Role", r)]
	if missing:
		frappe.throw(f"Required Roles missing on this site: {missing}")
