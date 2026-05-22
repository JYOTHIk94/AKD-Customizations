"""
Quotation expiry / validity digest.

BRD: FR-SELL-20 — track quotation validity / expiry dates.
     FR-SELL-90 — email notifications for quotation events.

Sends a daily email when quotations are within 7 days of valid_till or have
already expired. Sales is expected to either revise + reissue, mark as Lost,
or escalate to the customer.
"""

import frappe
from frappe.utils import add_days, today

ALERT_RECIPIENTS = ["sales@akd-consulting.ae"]
EXPIRY_WINDOW_DAYS = 7


def send() -> None:
	threshold = add_days(today(), EXPIRY_WINDOW_DAYS)

	expiring = frappe.get_all(
		"Quotation",
		filters={
			"docstatus": 1,
			"status": ["not in", ["Ordered", "Lost", "Cancelled"]],
			"valid_till": ["between", [today(), threshold]],
		},
		fields=[
			"name", "customer_name", "party_name", "transaction_date",
			"valid_till", "currency", "grand_total",
		],
		order_by="valid_till asc",
	)
	expired = frappe.get_all(
		"Quotation",
		filters={
			"docstatus": 1,
			"status": ["not in", ["Ordered", "Lost", "Cancelled"]],
			"valid_till": ["<", today()],
		},
		fields=[
			"name", "customer_name", "party_name", "transaction_date",
			"valid_till", "currency", "grand_total",
		],
		order_by="valid_till desc",
		limit=50,
	)

	if not expiring and not expired:
		return

	subject = (
		f"AKD Quotations — {len(expired)} expired, "
		f"{len(expiring)} expiring within {EXPIRY_WINDOW_DAYS} days"
	)
	frappe.sendmail(
		recipients=ALERT_RECIPIENTS,
		subject=subject,
		message=_format_message(expired, expiring),
		reference_doctype="Quotation",
	)


def _format_message(expired: list[dict], expiring: list[dict]) -> str:
	from frappe.utils import fmt_money

	def _table(rows: list[dict], heading: str) -> str:
		if not rows:
			return f"<h4>{heading}: none</h4>"
		body = "".join(
			f"<tr>"
			f"<td>{r.name}</td>"
			f"<td>{r.customer_name or r.party_name or ''}</td>"
			f"<td>{r.transaction_date}</td>"
			f"<td>{r.valid_till}</td>"
			f"<td style='text-align:right'>{fmt_money(r.grand_total, currency=r.currency)}</td>"
			f"</tr>"
			for r in rows
		)
		return (
			f"<h4>{heading}</h4>"
			"<table border='1' cellpadding='6' cellspacing='0'>"
			"<tr>"
			"<th>Quotation</th><th>Customer</th><th>Issued</th>"
			"<th>Valid Till</th><th>Value</th>"
			"</tr>"
			f"{body}"
			"</table>"
		)

	return (
		"<p>Auto-generated Quotation expiry digest (FR-SELL-20):</p>"
		+ _table(expired, "Expired (no SO yet)")
		+ "<br />"
		+ _table(expiring, f"Expiring within {EXPIRY_WINDOW_DAYS} days")
		+ "<p style='margin-top: 12px; color: #555;'>"
		"Action: revise &amp; resend, ask customer for confirmation, "
		"or update status to Lost with a reason."
		"</p>"
	)
