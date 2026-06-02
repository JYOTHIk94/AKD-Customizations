"""
Purchase Receipt doc_event hooks.

BRD references:
  FR-BUY-46 / FR-QA-14 / FR-QA-48   Incoming inspection mandatory.
  FR-BUY-48                          Over-delivery above PO qty not accepted.
  FR-BUY-50                          Rejected qty must route to rejected warehouse.
"""

import frappe
from frappe import _
from frappe.utils import flt


def validate_no_over_receipt(doc, method=None) -> None:
	"""FR-BUY-48 — strict: received qty cannot exceed PO qty."""
	if doc.is_return:
		return

	for row in (doc.items or []):
		po_detail = row.get("purchase_order_item")
		if not po_detail:
			continue
		ordered_qty = flt(frappe.db.get_value(
			"Purchase Order Item", po_detail, "qty"
		))
		if not ordered_qty:
			continue
		if flt(row.received_qty) > ordered_qty:
			frappe.throw(
				_("Item {0}: received qty {1} exceeds PO qty {2} "
				  "(FR-BUY-48 — over-delivery not accepted).").format(
					row.item_code,
					f"{flt(row.received_qty):.2f}",
					f"{ordered_qty:.2f}",
				),
				title=_("Over-Receipt Not Allowed"),
			)


def validate_incoming_inspection(doc, method=None) -> None:
	"""FR-BUY-46 / FR-QA-48 — every PR line requires a passing Quality Inspection.

	C-09 was resolved Q50 "Yes — all", so we require an inspection link on
	every line (not just items flagged `inspection_required_before_purchase`).
	"""
	if doc.is_return:
		return

	missing = []
	failed = []
	for row in (doc.items or []):
		qi = row.get("quality_inspection")
		if not qi:
			missing.append(row.item_code)
			continue
		status = frappe.db.get_value("Quality Inspection", qi, "status")
		if status and status not in {"Accepted", "Submitted"}:
			failed.append(f"{row.item_code} ({status})")

	if missing:
		frappe.throw(
			_("Quality Inspection is required on every line "
			  "(FR-BUY-46 / FR-QA-48). Missing on: {0}.").format(
				", ".join(missing)
			),
			title=_("Quality Inspection Required"),
		)
	if failed:
		frappe.throw(
			_("Quality Inspection failed on: {0}.").format(", ".join(failed)),
			title=_("Quality Inspection Not Accepted"),
		)


def enforce_rejected_warehouse(doc, method=None) -> None:
	"""FR-BUY-50 — rejected qty must be routed to a rejected warehouse."""
	for row in (doc.items or []):
		if flt(row.get("rejected_qty")) > 0 and not row.get("rejected_warehouse"):
			frappe.throw(
				_("Item {0}: rejected qty must be routed to a Rejected "
				  "Warehouse (FR-BUY-50).").format(row.item_code),
				title=_("Rejected Warehouse Required"),
			)
