"""
Sales Invoice doc_event hooks.

BRD: FR-SELL-09 — customer credit limits per company.

ERPNext already enforces credit limits when configured on Customer. This wrapper
exists to add AKD-specific messaging and to bypass-control via a single switch
should that ever be needed during cut-over.
"""

import frappe
from frappe.utils import flt


def validate_credit_limit(doc, method=None) -> None:
	"""Hard-stop Sales Invoice submission if customer credit limit is exceeded."""
	if doc.is_return:
		return
	limit = _customer_credit_limit(doc.customer, doc.company)
	if not limit:
		return

	exposure = _customer_outstanding(doc.customer, doc.company) + flt(doc.grand_total)
	if exposure > limit:
		frappe.throw(
			f"Customer {doc.customer} would exceed credit limit "
			f"{flt(limit):,.2f} {doc.currency}. "
			f"Total exposure with this invoice: {exposure:,.2f}.",
			title="Credit Limit Exceeded",
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
