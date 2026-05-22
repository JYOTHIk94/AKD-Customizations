"""
Blanket Order expiry & renewal-reminder digest.

BRD: FR-BUY-54 — track contract expiry and renewal dates.

Sends a daily email when blanket orders are within 30 days of `to_date` or
have already expired. Procurement is expected to either renew (extend to_date)
or close the order.
"""

import frappe
from frappe.utils import add_days, getdate, today

ALERT_RECIPIENTS = ["procurement@akd-consulting.ae"]
CC_RECIPIENTS = ["finance@akd-consulting.ae"]
EXPIRY_WINDOW_DAYS = 30


def send() -> None:
	threshold = add_days(today(), EXPIRY_WINDOW_DAYS)

	expiring = frappe.get_all(
		"Blanket Order",
		filters={
			"docstatus": 1,
			"to_date": ["between", [today(), threshold]],
		},
		fields=[
			"name", "blanket_order_type", "supplier_name", "customer_name",
			"from_date", "to_date", "order_no",
		],
		order_by="to_date asc",
	)
	expired = frappe.get_all(
		"Blanket Order",
		filters={
			"docstatus": 1,
			"to_date": ["<", today()],
		},
		fields=[
			"name", "blanket_order_type", "supplier_name", "customer_name",
			"from_date", "to_date", "order_no",
		],
		order_by="to_date desc",
		limit=50,
	)

	if not expiring and not expired:
		return

	subject = (
		f"AKD Blanket Orders — {len(expired)} expired, "
		f"{len(expiring)} expiring within {EXPIRY_WINDOW_DAYS} days"
	)
	frappe.sendmail(
		recipients=ALERT_RECIPIENTS,
		cc=CC_RECIPIENTS,
		subject=subject,
		message=_format_message(expired, expiring),
		reference_doctype="Blanket Order",
	)


def _format_message(expired: list[dict], expiring: list[dict]) -> str:
	def _table(rows: list[dict], heading: str) -> str:
		if not rows:
			return f"<h4>{heading}: none</h4>"
		body = "".join(
			f"<tr>"
			f"<td>{r.name}</td>"
			f"<td>{r.blanket_order_type}</td>"
			f"<td>{r.supplier_name or r.customer_name or ''}</td>"
			f"<td>{r.from_date}</td>"
			f"<td>{r.to_date}</td>"
			f"<td>{r.order_no or ''}</td>"
			f"</tr>"
			for r in rows
		)
		return (
			f"<h4>{heading}</h4>"
			"<table border='1' cellpadding='6' cellspacing='0'>"
			"<tr>"
			"<th>Blanket Order</th><th>Type</th><th>Party</th>"
			"<th>From</th><th>To</th><th>Ref</th>"
			"</tr>"
			f"{body}"
			"</table>"
		)

	return (
		"<p>Auto-generated Blanket Order expiry digest (FR-BUY-54):</p>"
		+ _table(expired, "Expired (action needed)")
		+ "<br />"
		+ _table(expiring, f"Expiring within {EXPIRY_WINDOW_DAYS} days")
		+ "<p style='margin-top: 12px; color: #555;'>"
		"Action: renew the contract by extending the to_date, or close the "
		"blanket order if the relationship has ended."
		"</p>"
	)
