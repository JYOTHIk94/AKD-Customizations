"""
Asset disposal approval — FR-FA-55 ("asset disposals require approval: Yes").

ERPNext has no native disposal approval. Both disposal paths are hard-stopped:
  • Sale  → Sales Invoice line with a fixed asset (`item.asset`)
  • Scrap → Journal Entry whose account rows carry reference_type = "Asset"

Each referenced Asset must have `akd_disposal_approved` ticked first. FR-FA-74
("restrict disposal to certain roles: No") → the approval is a recorded gate,
not a role lock; `akd_disposal_approved_by` stamps who approved (audit).
"""

import frappe


def _block_unapproved(asset_names: set[str], context: str) -> None:
	unapproved = [
		a for a in asset_names
		if a and not frappe.db.get_value("Asset", a, "akd_disposal_approved")
	]
	if unapproved:
		frappe.throw(
			"Disposal not approved for Asset(s): "
			+ ", ".join(sorted(unapproved))
			+ f". Tick <b>Disposal Approved</b> on the Asset before {context} "
			"(FR-FA-55).",
			title="Asset Disposal Approval Required",
		)


def require_for_sales_invoice(doc, method=None) -> None:
	if doc.get("is_return"):
		return
	assets = {
		row.asset for row in (doc.items or [])
		if row.get("is_fixed_asset") and row.get("asset")
	}
	_block_unapproved(assets, "selling the asset")


def require_for_journal_entry(doc, method=None) -> None:
	assets = {
		row.reference_name for row in (doc.accounts or [])
		if row.get("reference_type") == "Asset" and row.get("reference_name")
	}
	_block_unapproved(assets, "scrapping the asset")


def stamp_approver(doc, method=None) -> None:
	"""Record who approved (and clear stamp if approval is withdrawn)."""
	if doc.get("akd_disposal_approved"):
		if not doc.get("akd_disposal_approved_by"):
			doc.akd_disposal_approved_by = frappe.session.user
	else:
		doc.akd_disposal_approved_by = None
