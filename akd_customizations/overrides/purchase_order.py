"""
Purchase Order doc_event hooks.

BRD references:
  FR-BUY-42  Place POs on hold: required.
"""

import frappe
from frappe import _


def validate_hold_state(doc, method=None) -> None:
	"""FR-BUY-42 — held POs cannot be submitted; hold reason mandatory."""
	if not doc.get("akd_on_hold"):
		return

	if not (doc.get("akd_hold_reason") or "").strip():
		frappe.throw(
			_("Hold Reason is mandatory when Purchase Order is on hold."),
			title=_("Hold Reason Required"),
		)

	if doc.docstatus == 1:
		frappe.throw(
			_("Purchase Order {0} is on hold — release the hold before "
			  "submitting (FR-BUY-42).").format(doc.name or ""),
			title=_("Purchase Order On Hold"),
		)
