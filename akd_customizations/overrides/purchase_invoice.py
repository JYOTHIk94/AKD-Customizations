"""
Purchase Invoice doc_event hooks.

All AKD-specific Purchase Invoice validations live in this file and are wired
through `doc_events` in hooks.py. Pure frappe API only — no ERPNext core
imports.

BRD references:
  FR-BUY-43      Purchase Receipt mandatory before Purchase Invoice.
  FR-BUY-78/80   Returns processed as Credit Note — return reason captured.
  FR-BUY-50      Rejected-warehouse qty on PR must not be billed.
"""

import frappe
from frappe import _
from frappe.utils import flt


def validate_return_reason(doc, method=None) -> None:
	"""FR-BUY-80 — supplier debit note must record a return reason."""
	if doc.is_return and not doc.get("akd_return_reason"):
		frappe.throw(
			_("Return Reason is mandatory on a supplier debit note "
			  "(FR-BUY-80)."),
			title=_("Return Reason Required"),
		)


def validate_pr_link(doc, method=None) -> None:
	"""FR-BUY-43 — PR mandatory before PI for stock items.

	Skipped for: return invoices, service-only items (no PR generated),
	and PIs explicitly marked `update_stock` (treats PI as PR).
	"""
	if doc.is_return or doc.get("update_stock"):
		return

	stock_lines_missing_pr = [
		row.item_code for row in (doc.items or [])
		if frappe.db.get_value("Item", row.item_code, "is_stock_item")
		and not row.get("purchase_receipt")
	]
	if stock_lines_missing_pr:
		frappe.throw(
			_("Purchase Receipt is mandatory before invoicing stock items "
			  "(FR-BUY-43). Missing PR link on: {0}.").format(
				", ".join(stock_lines_missing_pr)
			),
			title=_("Purchase Receipt Required"),
		)


def validate_rejected_not_billed(doc, method=None) -> None:
	"""FR-BUY-50 — qty received into rejected warehouse cannot be billed."""
	if doc.is_return:
		return

	for row in (doc.items or []):
		pr_detail = row.get("pr_detail")
		if not pr_detail:
			continue
		rejected_qty = flt(frappe.db.get_value(
			"Purchase Receipt Item", pr_detail, "rejected_qty"
		))
		received_qty = flt(frappe.db.get_value(
			"Purchase Receipt Item", pr_detail, "received_qty"
		))
		if rejected_qty and flt(row.qty) > (received_qty - rejected_qty):
			frappe.throw(
				_("Item {0}: cannot bill more than (received − rejected) "
				  "= {1} (FR-BUY-50).").format(
					row.item_code,
					f"{(received_qty - rejected_qty):.2f}",
				),
				title=_("Rejected Qty Cannot Be Billed"),
			)
