"""
Asset doc_event hooks.

BRD references:
  FR-FA-06/07  Unique asset numbers / tags per asset.
  FR-FA-26     Salvage value expressed as a fixed amount.
"""

import frappe
from frappe import _
from frappe.utils import flt


def validate_unique_asset_tag(doc, method=None) -> None:
	"""FR-FA-06/07 — `akd_asset_tag` is mandatory and unique."""
	tag = (doc.get("akd_asset_tag") or "").strip()
	if not tag:
		frappe.throw(
			_("Asset Tag is mandatory (FR-FA-06)."),
			title=_("Asset Tag Required"),
		)

	clash = frappe.db.sql(
		"""
		SELECT name FROM `tabAsset`
		WHERE akd_asset_tag = %s AND name != %s
		LIMIT 1
		""",
		(tag, doc.name or ""),
	)
	if clash:
		frappe.throw(
			_("Asset Tag {0} is already used by {1} (FR-FA-07).").format(
				tag, clash[0][0]
			),
			title=_("Duplicate Asset Tag"),
		)


def validate_salvage_value(doc, method=None) -> None:
	"""FR-FA-26 — salvage value must be a positive fixed amount, < gross cost."""
	salvage = flt(doc.get("expected_value_after_useful_life"))
	gross = flt(doc.get("gross_purchase_amount"))
	if gross <= 0:
		return
	if salvage < 0 or salvage >= gross:
		frappe.throw(
			_("Expected Value After Useful Life must be between 0 and the "
			  "gross purchase amount ({0}) — FR-FA-26.").format(
				f"{gross:,.2f}"
			),
			title=_("Invalid Salvage Value"),
		)
