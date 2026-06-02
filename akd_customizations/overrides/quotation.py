"""
Quotation doc_event hooks.

BRD references:
  FR-SELL-21  Track lost quotations with reasons: Yes.
  FR-SELL-23  Quotation approval before sending: Yes.
"""

import frappe
from frappe import _


def validate_lost_reason(doc, method=None) -> None:
	"""FR-SELL-21 — lost Quotation must carry a lost reason."""
	if doc.get("status") == "Lost" and not doc.get("akd_lost_reason"):
		frappe.throw(
			_("Lost Reason is mandatory when Quotation status is Lost "
			  "(FR-SELL-21)."),
			title=_("Lost Reason Required"),
		)


def require_approval_before_submit(doc, method=None) -> None:
	"""FR-SELL-23 — Quotation must reach `Approved` workflow state to submit.

	Workflow fixtures position Sales Quotations at "Pending Approval". A
	programmatic `submit()` bypasses workflow buttons, so we gate it here.
	"""
	if doc.docstatus != 1:
		return
	if (doc.get("workflow_state") or "") != "Approved":
		frappe.throw(
			_("Quotation must be Approved before submission (FR-SELL-23). "
			  "Current state: {0}.").format(doc.get("workflow_state") or "—"),
			title=_("Approval Required"),
		)
