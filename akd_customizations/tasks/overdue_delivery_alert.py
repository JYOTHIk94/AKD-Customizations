"""
Daily digest of POs whose expected delivery date has passed without full receipt.

BRD: FR-BUY-82 (Delayed-deliveries report) + FR-BUY-90 (email notifications for
overdue deliveries).

Sends one email per day to Procurement listing:
  - PO Items with schedule_date < today and received_qty < qty
  - Grouped by supplier
"""

import frappe
from frappe.utils import fmt_money, getdate, today

ALERT_RECIPIENTS = ["procurement@akd-consulting.ae"]
CC_RECIPIENTS = ["finance@akd-consulting.ae"]


def send() -> None:
	overdue = _query_overdue_lines()
	if not overdue:
		return

	subject = f"AKD Procurement — {len(overdue)} overdue PO lines"
	frappe.sendmail(
		recipients=ALERT_RECIPIENTS,
		cc=CC_RECIPIENTS,
		subject=subject,
		message=_format_message(overdue),
		reference_doctype="Purchase Order",
	)


def _query_overdue_lines() -> list[dict]:
	return frappe.db.sql(
		"""
		SELECT
			po.name              AS po_name,
			po.supplier          AS supplier,
			po.supplier_name     AS supplier_name,
			po.currency          AS currency,
			poi.item_code        AS item_code,
			poi.item_name        AS item_name,
			poi.schedule_date    AS schedule_date,
			poi.qty              AS ordered_qty,
			poi.received_qty     AS received_qty,
			(poi.qty - poi.received_qty)         AS pending_qty,
			(poi.qty - poi.received_qty) * poi.rate AS pending_amount,
			DATEDIFF(%(today)s, poi.schedule_date) AS days_overdue
		FROM `tabPurchase Order` po
		JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
		WHERE po.docstatus = 1
		  AND po.status NOT IN ('Closed', 'Completed', 'Cancelled', 'On Hold')
		  AND poi.schedule_date < %(today)s
		  AND poi.received_qty < poi.qty
		ORDER BY po.supplier_name ASC, poi.schedule_date ASC
		""",
		{"today": today()},
		as_dict=True,
	)


def _format_message(rows: list[dict]) -> str:
	body = "".join(
		f"<tr>"
		f"<td>{r.po_name}</td>"
		f"<td>{r.supplier_name or r.supplier}</td>"
		f"<td>{r.item_name or r.item_code}</td>"
		f"<td>{r.schedule_date}</td>"
		f"<td style='text-align:right'>{r.days_overdue}</td>"
		f"<td style='text-align:right'>{r.pending_qty:g}</td>"
		f"<td style='text-align:right'>{fmt_money(r.pending_amount, currency=r.currency)}</td>"
		f"</tr>"
		for r in rows
	)
	return (
		"<p>Auto-generated overdue PO digest (FR-BUY-82). "
		"POs past their expected delivery date with pending receipt:</p>"
		"<table border='1' cellpadding='6' cellspacing='0'>"
		"<tr>"
		"<th>PO</th><th>Supplier</th><th>Item</th>"
		"<th>Expected</th><th>Days Late</th>"
		"<th>Pending Qty</th><th>Pending Value</th>"
		"</tr>"
		f"{body}"
		"</table>"
		"<p style='margin-top: 12px; color: #555;'>"
		"Action: chase the supplier or update the schedule date with a revised commitment."
		"</p>"
	)
