"""
Lead doc_event hooks.

BRD references:
  FR-CRM-12  Duplicate lead handling: prevent duplicates by email.
  FR-CRM-66  Restrict lead deletion to System Manager / CRM Admin.
"""

import frappe
from frappe import _

_DELETE_ROLES = {"System Manager", "CRM Admin"}


def validate_duplicate_email(doc, method=None) -> None:
	"""FR-CRM-12 — block insert of a Lead whose email is already in use."""
	email = (doc.get("email_id") or "").strip().lower()
	if not email:
		return

	existing = frappe.db.sql(
		"""
		SELECT name FROM `tabLead`
		WHERE LOWER(email_id) = %s AND name != %s
		LIMIT 1
		""",
		(email, doc.name or ""),
	)
	if existing:
		frappe.throw(
			_("A Lead with email {0} already exists ({1}) — FR-CRM-12.").format(
				doc.email_id, existing[0][0]
			),
			title=_("Duplicate Lead Email"),
		)


def restrict_delete(doc, method=None) -> None:
	"""FR-CRM-66 — only System Manager / CRM Admin can delete a Lead."""
	if _DELETE_ROLES.isdisjoint(set(frappe.get_roles())):
		frappe.throw(
			_("Only System Manager or CRM Admin can delete a Lead "
			  "(FR-CRM-66)."),
			title=_("Lead Deletion Restricted"),
		)
