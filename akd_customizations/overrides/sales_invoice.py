"""
Sales Invoice doc_event hooks.

All AKD-specific Sales Invoice validations live in this file and are wired
through `doc_events` in hooks.py. We do not import or call ERPNext core
modules from here — every check is implemented against the doc + frappe API
only, so the custom app stays decoupled from internal ERPNext refactors.

BRD references:
  FR-SELL-09     Customer credit limits — per company.
  FR-SELL-26     Delivery Note mandatory before Sales Invoice (C-02 → Yes).
  FR-SELL-31     Skip DN requirement for Service Sales / Subscription orders.
  FR-SELL-68/70  Customer returns + auto credit note must record a reason.
"""

import frappe
from frappe import _
from frappe.utils import flt

_DN_EXEMPT_SALES_TYPES = {"Service Sales", "Subscription / Recurring"}


def validate_credit_limit(doc, method=None) -> None:
	"""FR-SELL-09 — block SI submission when customer would exceed credit limit."""
	if doc.is_return:
		return

	limit = _customer_credit_limit(doc.customer, doc.company)
	if not limit:
		return

	exposure = _customer_outstanding(doc.customer, doc.company) + flt(doc.grand_total)
	if exposure > limit:
		frappe.throw(
			_("Customer {0} would exceed credit limit {1} {2}. "
			  "Total exposure with this invoice: {3} (FR-SELL-09).").format(
				doc.customer,
				f"{flt(limit):,.2f}",
				doc.currency,
				f"{exposure:,.2f}",
			),
			title=_("Credit Limit Exceeded"),
		)


def validate_so_dn_required(doc, method=None) -> None:
	"""FR-SELL-26 — Delivery Note linkage is mandatory on Sales Invoice items.

	This replaces the trigger of ERPNext core's `so_dn_required()` so the
	rule lives in AKD's app (Selling Settings `dn_required`/`so_required`
	are flipped to "No" so core early-exits). FR-SELL-31 lets us skip the
	DN check for Service Sales / Subscription orders.

	Skipped for:
	  - return invoices (credit notes)
	  - POS invoices (`is_pos`)
	  - debit notes
	  - lines marked `update_stock` on the invoice (treats SI as DN)
	  - service-only sales (per FR-SELL-31, via linked SO `akd_sales_type`)
	"""
	if doc.is_return or doc.get("is_pos") or doc.get("is_debit_note"):
		return
	if doc.get("update_stock"):
		return

	missing_dn = []
	for row in (doc.items or []):
		if not row.get("item_code"):
			continue
		if row.get("delivery_note"):
			continue
		# Per-customer override (mirrors ERPNext's `Customer.dn_required` flag
		# semantics, but read once on the SO context).
		sales_order = row.get("sales_order")
		if sales_order and _is_service_only(sales_order):
			continue
		if frappe.db.get_value("Customer", doc.customer, "dn_required"):
			continue
		missing_dn.append(row.item_code)

	if missing_dn:
		frappe.throw(
			_("Delivery Note linkage is mandatory on Sales Invoice items "
			  "(FR-SELL-26). Missing on: {0}.").format(", ".join(missing_dn)),
			title=_("Delivery Note Required"),
		)


def _is_service_only(sales_order: str) -> bool:
	sales_type = frappe.db.get_value("Sales Order", sales_order, "akd_sales_type")
	return sales_type in _DN_EXEMPT_SALES_TYPES


def validate_return_reason(doc, method=None) -> None:
	"""FR-SELL-68/70 — credit notes must record a return reason."""
	if doc.is_return and not doc.get("akd_return_reason"):
		frappe.throw(
			_("Return Reason is mandatory on a credit note (FR-SELL-68/70)."),
			title=_("Return Reason Required"),
		)


def _customer_credit_limit(customer: str, company: str) -> float:
	limit = frappe.db.get_value(
		"Customer Credit Limit",
		{"parent": customer, "company": company},
		"credit_limit",
	)
	return flt(limit)


def _customer_outstanding(customer: str, company: str) -> float:
	result = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(outstanding_amount), 0)
		FROM `tabSales Invoice`
		WHERE customer = %s AND company = %s AND docstatus = 1
		""",
		(customer, company),
	)
	return flt(result[0][0]) if result else 0.0
