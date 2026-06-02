"""
Sales Order doc_event hooks.

All AKD-specific Sales Order validations live in this file and are wired
through `doc_events` in hooks.py. We do not import or call ERPNext core
modules — every check is implemented against the doc + frappe API only.

BRD references:
  FR-SELL-28     Customer PO number tracked on Sales Orders.
  FR-SELL-32/36  Close / re-open + hold workflow (akd_on_hold + akd_hold_reason).
  FR-SELL-65     Installation flag on SO drives DN installation lifecycle.
  FR-SELL-58     Multi-salesperson commission split must total 100%.
"""

import frappe
from frappe import _
from frappe.utils import flt


def validate_customer_po(doc, method=None) -> None:
	"""FR-SELL-28 — customer PO is required for Product & Project sales.

	Service-only orders (consulting day rate, subscriptions) often don't
	have a customer PO, so we gate the requirement by `akd_sales_type`.
	"""
	if doc.is_return:
		return

	requires_po = doc.get("akd_sales_type") in {
		"Product Sales",
		"Project-based Sales",
	}
	if requires_po and not (doc.po_no or "").strip():
		frappe.throw(
			_("Customer PO No is required for {0} (FR-SELL-28).").format(
				doc.akd_sales_type
			),
			title=_("Customer PO Required"),
		)


def validate_hold_state(doc, method=None) -> None:
	"""FR-SELL-32/36 — held SOs cannot be submitted or progressed.

	The hold-reason field already uses `mandatory_depends_on`, but that only
	gates the form save. This blocks submission and keeps any downstream
	transactions from advancing while the hold is on.
	"""
	if not doc.get("akd_on_hold"):
		return

	if not (doc.get("akd_hold_reason") or "").strip():
		frappe.throw(
			_("Hold Reason is mandatory when Sales Order is on hold."),
			title=_("Hold Reason Required"),
		)

	if doc.docstatus == 1:
		frappe.throw(
			_("Sales Order {0} is on hold — release the hold before submitting "
			  "(FR-SELL-36).").format(doc.name or ""),
			title=_("Sales Order On Hold"),
		)


def validate_installation_flag(doc, method=None) -> None:
	"""FR-SELL-65 — Service-only sales should not require installation."""
	if doc.get("akd_installation_required") and doc.get("akd_sales_type") == "Service Sales":
		frappe.throw(
			_("Installation Required cannot be set on Service Sales orders "
			  "(FR-SELL-65)."),
			title=_("Invalid Installation Flag"),
		)


def validate_commission_split(doc, method=None) -> None:
	"""FR-SELL-58 — sales team commission shares must sum to 100% (±0.01)."""
	team = doc.get("sales_team") or []
	if not team:
		return

	total = sum(flt(row.allocated_percentage) for row in team)
	if abs(total - 100.0) > 0.01:
		frappe.throw(
			_("Sales Team commission split must total 100% (currently {0}%) "
			  "— FR-SELL-58.").format(f"{total:.2f}"),
			title=_("Invalid Commission Split"),
		)
