"""
Row-level project visibility — users see only projects they're assigned to.

BRD: FR-PROJ-62 — users see only projects they are assigned to.
     (Managers/admins see everything; FR-PROJ-29/65-equivalent.)

Wired via `permission_query_conditions` in hooks.py.
"""

import frappe

PRIVILEGED = {"System Manager", "Projects Manager", "Read-only Viewer"}


def _unrestricted(user: str) -> bool:
	if user in ("Administrator", None):
		return True
	return bool(PRIVILEGED.intersection(frappe.get_roles(user)))


def project_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	if _unrestricted(user):
		return ""
	u = frappe.db.escape(user)
	# Owner, or a member in the Project Users child table.
	return (
		f"(`tabProject`.owner = {u} OR `tabProject`.name IN "
		f"(SELECT parent FROM `tabProject User` WHERE user = {u}))"
	)


def task_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	if _unrestricted(user):
		return ""
	u = frappe.db.escape(user)
	# Tasks of visible projects, or directly assigned via _assign.
	return (
		f"(`tabTask`.owner = {u} "
		f"OR `tabTask`._assign LIKE CONCAT('%', {u}, '%') "
		f"OR `tabTask`.project IN "
		f"(SELECT parent FROM `tabProject User` WHERE user = {u}))"
	)
