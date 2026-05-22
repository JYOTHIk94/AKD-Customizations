"""
Buying / Procurement setup — Buying Settings + Rejected warehouse.

BRD references (Section 5):
  FR-BUY-35   PO mandatory before receiving goods
  FR-BUY-36   PO mandatory before PI  (Section 11 C-01 resolved Yes)
  FR-BUY-40   Rate consistency from quotation through to invoice — Warn only
  FR-BUY-42   POs can be placed on hold (custom field elsewhere)
  FR-BUY-43   Purchase Receipt mandatory before PI
  FR-BUY-44   3-way matching (PO → Receipt → Invoice) — falls out of 36+43
  FR-BUY-48   Over-delivery above PO qty NOT accepted (strict)
  FR-BUY-49   Rejected-goods warehouse required
  FR-BUY-50   Rejected qty NOT billed
  FR-BUY-64   Track last purchase rate per item (do NOT disable)
  FR-BUY-75   Exchange rates based on transaction date

Resolved conflicts assumed (pending AKD sign-off):
  C-01 → po_required = Yes
  C-09 → Quality incoming inspection ON (configured in Quality module)
  C-10 → Purchase Taxes & Charges Templates exist (UAE regional already created)
"""

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

REJECTED_WAREHOUSE = "Rejected"


def setup() -> dict:
	return {
		"buying_settings": _apply_buying_settings(),
		"stock_settings": _apply_stock_settings(),
		"rejected_warehouse": _ensure_rejected_warehouse(),
	}


def _apply_buying_settings() -> dict:
	patch = {
		# C-01 + FR-BUY-36: PO mandatory before PI
		"po_required": "Yes",
		# FR-BUY-43: PR mandatory before PI
		"pr_required": "Yes",
		# FR-BUY-40: maintain same rate from RFQ → PO → PR → PI (Warn, not Stop)
		"maintain_same_rate": 1,
		"maintain_same_rate_action": "Warn",
		# FR-BUY-64: keep last-purchase-rate tracking ON
		"disable_last_purchase_rate": 0,
		# FR-BUY-75: ensure transaction-date-based exchange rate
		"use_transaction_date_exchange_rate": 1,
		# FR-BUY-50: never bill rejected qty
		"bill_for_rejected_quantity_in_purchase_invoice": 0,
		# Allow multiple line items per doc (sensible default)
		"allow_multiple_items": 1,
		# Subcontracting is out of scope per FR-BUY-55..61
		"auto_create_subcontracting_order": 0,
	}
	current = frappe.db.get_value(
		"Buying Settings", None, list(patch.keys()), as_dict=True,
	) or {}
	changes = {
		k: {"from": current.get(k), "to": v}
		for k, v in patch.items()
		if current.get(k) != v
	}
	if changes:
		settings = frappe.get_single("Buying Settings")
		for k, v in patch.items():
			settings.set(k, v)
		settings.save(ignore_permissions=True)
	return changes


def _apply_stock_settings() -> dict:
	"""FR-BUY-48: strict no over-receipt.
	FR-SELL-64: enable stock reservation for confirmed Sales Orders."""
	patch = {
		"over_delivery_receipt_allowance": 0,
		"allow_negative_stock": 0,
		"enable_stock_reservation": 1,
	}
	current = frappe.db.get_value(
		"Stock Settings", None, list(patch.keys()), as_dict=True,
	) or {}
	changes = {
		k: {"from": current.get(k), "to": v}
		for k, v in patch.items()
		if current.get(k) != v
	}
	if changes:
		settings = frappe.get_single("Stock Settings")
		for k, v in patch.items():
			settings.set(k, v)
		settings.save(ignore_permissions=True)
	return changes


def _ensure_rejected_warehouse() -> str:
	"""FR-BUY-49 — rejected-goods warehouse for failed inspections."""
	full_name = f"{REJECTED_WAREHOUSE} - {ABBR}"
	if frappe.db.exists("Warehouse", full_name):
		return f"existing:{full_name}"
	parent = f"All Warehouses - {ABBR}"
	if not frappe.db.exists("Warehouse", parent):
		frappe.throw(f"Parent warehouse {parent!r} missing.")
	doc = frappe.get_doc({
		"doctype": "Warehouse",
		"warehouse_name": REJECTED_WAREHOUSE,
		"parent_warehouse": parent,
		"company": COMPANY,
		"is_group": 0,
		"disabled": 0,
	})
	doc.insert(ignore_permissions=True)
	return f"created:{doc.name}"
