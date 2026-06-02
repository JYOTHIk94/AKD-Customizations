"""
Delivery Note doc_event hooks.

All AKD-specific Delivery Note validations live in this file and are wired
through `doc_events` in hooks.py. We do not import or call ERPNext core
modules — every check is implemented against the doc + frappe API only.

BRD references:
  FR-SELL-25     Sales Order mandatory before Delivery Note (C-02 → Yes).
  FR-SELL-65     Installation lifecycle — DN.akd_installation_status must
                 be Pending/In Progress/Completed when SO required install.
  FR-SELL-68/72  Customer returns are captured as is_return DNs and must
                 record a return reason.
"""

import frappe
from frappe import _


def validate_so_required(doc, method=None) -> None:
	"""FR-SELL-25 — Sales Order linkage is mandatory on Delivery Note items.

	Replaces the trigger of ERPNext core's `DeliveryNote.so_required()`.
	Per-customer override (`Customer.so_required` flag) is honoured to mirror
	core semantics.
	"""
	if doc.is_return:
		return
	if frappe.db.get_value("Customer", doc.customer, "so_required"):
		return

	missing_so = [
		row.item_code for row in (doc.items or [])
		if row.get("item_code") and not row.get("against_sales_order")
	]
	if missing_so:
		frappe.throw(
			_("Sales Order linkage is mandatory on Delivery Note items "
			  "(FR-SELL-25). Missing on: {0}.").format(", ".join(missing_so)),
			title=_("Sales Order Required"),
		)


def validate_return_reason(doc, method=None) -> None:
	"""FR-SELL-68/72 — return DN must record a reason."""
	if doc.is_return and not doc.get("akd_return_reason"):
		frappe.throw(
			_("Return Reason is mandatory on a return Delivery Note "
			  "(FR-SELL-68/72)."),
			title=_("Return Reason Required"),
		)


def validate_installation_status(doc, method=None) -> None:
	"""FR-SELL-65 — keep DN install status consistent with the source SO.

	If any DN item is linked to an SO that has `akd_installation_required`
	checked, the DN's `akd_installation_status` cannot stay at "Not Required".
	"""
	if doc.is_return:
		return

	if doc.get("akd_installation_status") and doc.akd_installation_status != "Not Required":
		return

	so_names = {row.against_sales_order for row in (doc.items or []) if row.get("against_sales_order")}
	if not so_names:
		return

	requires_install = frappe.db.get_value(
		"Sales Order",
		{"name": ("in", list(so_names)), "akd_installation_required": 1},
		"name",
	)
	if requires_install:
		frappe.throw(
			_("Sales Order {0} requires installation — set Installation Status "
			  "to Pending / In Progress / Completed (FR-SELL-65).").format(
				requires_install
			),
			title=_("Installation Status Required"),
		)
