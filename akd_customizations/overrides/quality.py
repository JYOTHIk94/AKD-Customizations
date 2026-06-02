"""
Quality module doc_event hooks (Quality Inspection, Non Conformance,
Quality Action, Quality Review).

BRD references:
  FR-QA-12   Acceptance criteria Pass / Fail — Rejected QI must trigger NC.
  FR-QA-28   Quality Reviews must link to a Quality Goal.
  FR-QA-32   NC triggers: Customer complaint / Process deviation / Audit finding.
  FR-QA-34   CAPA — Quality Action must carry a future completion date.
"""

import frappe
from frappe import _
from frappe.utils import getdate, today


def require_nc_on_rejection(doc, method=None) -> None:
	"""FR-QA-12 — a Quality Inspection with `Rejected` status needs a NC."""
	if doc.get("status") != "Rejected":
		return
	nc = frappe.db.exists(
		"Non Conformance",
		{"quality_inspection": doc.name},
	)
	if not nc:
		frappe.throw(
			_("Create a Non Conformance for Quality Inspection {0} before "
			  "submitting (FR-QA-12).").format(doc.name),
			title=_("Non Conformance Required"),
		)


def validate_nc_trigger(doc, method=None) -> None:
	"""FR-QA-32 — NC trigger source is mandatory."""
	if not (doc.get("akd_nc_trigger") or "").strip():
		frappe.throw(
			_("NC Trigger is mandatory — pick Customer complaint, Process "
			  "deviation, or Audit finding (FR-QA-32)."),
			title=_("NC Trigger Required"),
		)


def validate_action_deadline(doc, method=None) -> None:
	"""FR-QA-34 — CAPA Quality Action must carry a future completion date."""
	completion = doc.get("completion_by_date")
	if not completion:
		frappe.throw(
			_("Completion By Date is mandatory for a Quality Action "
			  "(FR-QA-34)."),
			title=_("Completion Date Required"),
		)
	if doc.docstatus == 0 and getdate(completion) < getdate(today()):
		frappe.throw(
			_("Completion By Date must be today or later (FR-QA-34)."),
			title=_("Invalid Completion Date"),
		)


def validate_review_goal(doc, method=None) -> None:
	"""FR-QA-28 — Quality Review must reference a Quality Goal."""
	if not doc.get("goal"):
		frappe.throw(
			_("Quality Review must reference a Quality Goal (FR-QA-28)."),
			title=_("Quality Goal Required"),
		)
