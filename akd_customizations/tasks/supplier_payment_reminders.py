"""
Daily reminder digest of upcoming and overdue supplier payments.

BRD: FR-ACC-34 — automatic payment reminders for due invoices.

Sends one email per day to Finance listing:
  - Overdue Purchase Invoices (due_date < today, outstanding > 0)
  - Upcoming Purchase Invoices (due within next 7 days)
"""

import frappe
from frappe.utils import add_days, fmt_money, getdate, today

REMINDER_RECIPIENTS = ["finance@akd-consulting.ae"]
UPCOMING_WINDOW_DAYS = 7


def send() -> None:
	overdue = _query(operator="<", reference_date=today())
	upcoming = _query(
		operator="between",
		reference_date=today(),
		end_date=add_days(today(), UPCOMING_WINDOW_DAYS),
	)
	if not overdue and not upcoming:
		return

	subject = (
		f"AKD Payments Due — {len(overdue)} overdue, {len(upcoming)} due in {UPCOMING_WINDOW_DAYS} days"
	)
	message = _format_message(overdue, upcoming)

	frappe.sendmail(
		recipients=REMINDER_RECIPIENTS,
		subject=subject,
		message=message,
		reference_doctype="Purchase Invoice",
	)


def _query(operator: str, reference_date: str, end_date: str | None = None) -> list[dict]:
	if operator == "<":
		filters = {
			"docstatus": 1,
			"outstanding_amount": [">", 0],
			"due_date": ["<", reference_date],
		}
	else:
		filters = {
			"docstatus": 1,
			"outstanding_amount": [">", 0],
			"due_date": ["between", [reference_date, end_date]],
		}

	return frappe.get_all(
		"Purchase Invoice",
		filters=filters,
		fields=[
			"name", "supplier", "supplier_name", "posting_date", "due_date",
			"currency", "outstanding_amount", "grand_total",
		],
		order_by="due_date asc",
	)


def _format_message(overdue: list[dict], upcoming: list[dict]) -> str:
	def _table(rows: list[dict], heading: str) -> str:
		if not rows:
			return f"<h4>{heading}: none</h4>"
		body = "".join(
			f"<tr>"
			f"<td>{r.name}</td>"
			f"<td>{r.supplier_name or r.supplier}</td>"
			f"<td>{r.due_date}</td>"
			f"<td style='text-align:right'>{fmt_money(r.outstanding_amount, currency=r.currency)}</td>"
			f"</tr>"
			for r in rows
		)
		return (
			f"<h4>{heading}</h4>"
			"<table border='1' cellpadding='6' cellspacing='0'>"
			"<tr><th>Invoice</th><th>Supplier</th><th>Due Date</th><th>Outstanding</th></tr>"
			f"{body}"
			"</table>"
		)

	return (
		"<p>Auto-generated supplier payment digest:</p>"
		+ _table(overdue, "Overdue invoices")
		+ "<br />"
		+ _table(upcoming, f"Due within {UPCOMING_WINDOW_DAYS} days")
	)
