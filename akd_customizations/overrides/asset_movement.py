"""
Asset Movement doc_event hooks.

BRD references:
  FR-FA-47/48/49  Transfers between locations / custodians: No.

AKD's scope explicitly excludes asset movements. Block at validate time
rather than removing the DocType from the desk, so any rogue
programmatic creation (imports, scripted moves) is also caught.
"""

import frappe
from frappe import _


def block_movement(doc, method=None) -> None:
	frappe.throw(
		_("Asset Movement is out of scope for AKD (FR-FA-47/48/49)."),
		title=_("Asset Movement Not Allowed"),
	)
