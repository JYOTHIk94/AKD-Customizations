"""
Row-level CRM visibility — reps see only their own Leads / Opportunities.

BRD: FR-CRM-64 — sales reps see only their own leads / deals.
     FR-CRM-65 — managers see all team data.

Wired via `permission_query_conditions` in hooks.py. Managers / admins are
unrestricted; everyone else is scoped to records they own or are assigned.
"""

import frappe

# Roles that see everything (FR-CRM-65).
PRIVILEGED = {
	"System Manager", "CRM Admin", "Sales Manager",
	"Marketing User", "Read-only Viewer",
}


def _unrestricted(user: str) -> bool:
	if user in ("Administrator", None):
		return True
	return bool(PRIVILEGED.intersection(frappe.get_roles(user)))


def lead_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	if _unrestricted(user):
		return ""
	u = frappe.db.escape(user)
	return f"(`tabLead`.lead_owner = {u} OR `tabLead`.owner = {u})"


def opportunity_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	if _unrestricted(user):
		return ""
	u = frappe.db.escape(user)
	return f"(`tabOpportunity`.opportunity_owner = {u} OR `tabOpportunity`.owner = {u})"
