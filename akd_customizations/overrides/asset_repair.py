"""
Asset Repair doc_event hooks.

BRD references:
  FR-FA-43  Capitalise repair costs: Never.
  FR-FA-44  Repairs do not extend useful life.
"""

import frappe
from frappe import _


def block_capitalisation(doc, method=None) -> None:
	if doc.get("capitalize_repair_cost"):
		frappe.throw(
			_("Repair costs may not be capitalised (FR-FA-43)."),
			title=_("Capitalisation Not Allowed"),
		)
	if doc.get("increase_in_asset_life"):
		frappe.throw(
			_("Repairs do not extend asset useful life (FR-FA-44)."),
			title=_("Useful-Life Extension Not Allowed"),
		)
