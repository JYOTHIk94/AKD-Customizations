"""
Selling / Order-to-Cash setup — Selling Settings.

BRD references (Section 6):
  FR-SELL-25  Sales Order mandatory before Delivery Note (C-02 → Yes)
  FR-SELL-26  Delivery Note mandatory before Sales Invoice (C-02 → Yes)
  FR-SELL-27  SO approval workflow required (process in ERP)
  FR-SELL-41  Validate selling price ≥ purchase/valuation rate
  FR-SELL-42  Price-list rates editable on transactions
  FR-SELL-43  Rate consistency Quotation → SI — Stop (not Warn, stricter than Buying)
  FR-SELL-24  Convert expired Quotation to SO — allow
  FR-SELL-29  Multiple SOs against a single customer PO — allow
  FR-SELL-58  Multiple salespeople share commission — enable tracking
"""

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"


def setup() -> dict:
	return {
		"selling_settings": _apply_selling_settings(),
		"nigeria_vat_template": _create_nigeria_vat_template(),
	}


def _create_nigeria_vat_template() -> str:
	"""FR-SELL-50: Sales tax type for Nigeria — VAT 7.5%.

	Posts to the same VAT Output account as UAE sales for now. If AKD splits
	books per region later, change account_head to a Nigeria-specific GL.
	"""
	name = f"AKD Nigeria VAT 7.5% - {ABBR}"
	if frappe.db.exists("Sales Taxes and Charges Template", name):
		return f"existing:{name}"

	vat_output = _find_vat_output_account()
	if not vat_output:
		return "skipped: VAT Output account missing in CoA"

	doc = frappe.get_doc({
		"doctype": "Sales Taxes and Charges Template",
		"title": "AKD Nigeria VAT 7.5%",
		"company": COMPANY,
		"taxes": [{
			"doctype": "Sales Taxes and Charges",
			"charge_type": "On Net Total",
			"account_head": vat_output,
			"description": "Nigeria VAT 7.5%",
			"rate": 7.5,
			"included_in_print_rate": 0,
		}],
	})
	doc.insert(ignore_permissions=True)
	return f"created:{doc.name}"


def _find_vat_output_account() -> str | None:
	for candidate in ["VAT Output", "Output VAT", "VAT 5%"]:
		acc = frappe.db.sql(
			"""SELECT name FROM `tabAccount`
			   WHERE company = %s AND is_group = 0
			     AND (account_name = %s OR name LIKE %s) LIMIT 1""",
			(COMPANY, candidate, f"{candidate}%"),
		)
		if acc:
			return acc[0][0]
	return None


def _apply_selling_settings() -> dict:
	patch = {
		# FR-SELL-25 + 26 — C-02 resolved Yes, but enforcement now lives in
		# AKD hooks: overrides.delivery_note.validate_so_required and
		# overrides.sales_invoice.validate_so_dn_required. Setting these to
		# "No" so ERPNext core's so_dn_required() / DN.so_required() early-exit
		# and our doc_event is the single source of truth.
		"so_required": "No",
		"dn_required": "No",
		# FR-SELL-43 — stop rate change quotation → SI (selling is strict)
		"maintain_same_sales_rate": 1,
		"maintain_same_rate_action": "Stop",
		# FR-SELL-42 — rates editable on transactions
		"editable_price_list_rate": 1,
		# FR-SELL-41 — selling price must cover valuation
		"validate_selling_price": 1,
		# FR-SELL-45 — bundle component rates editable
		"editable_bundle_item_rates": 1,
		# Reasonable defaults
		"allow_negative_rates_for_items": 0,
		# FR-SELL-29 — multiple SOs per customer PO
		"allow_against_multiple_purchase_orders": 1,
		# FR-SELL-24 — allow SO from expired Quotation
		"allow_sales_order_creation_for_expired_quotation": 1,
		# FR-SELL-58 — track multiple salespeople commission split
		"enable_tracking_sales_commissions": 1,
		# Default selling price list (pending AKD list import)
		"selling_price_list": frappe.db.get_value(
			"Selling Settings", None, "selling_price_list"
		) or "Standard Selling",
	}

	current = frappe.db.get_value(
		"Selling Settings", None, list(patch.keys()), as_dict=True,
	) or {}
	changes = {
		k: {"from": current.get(k), "to": v}
		for k, v in patch.items()
		if current.get(k) != v
	}
	if changes:
		settings = frappe.get_single("Selling Settings")
		for k, v in patch.items():
			settings.set(k, v)
		settings.save(ignore_permissions=True)
	return changes
