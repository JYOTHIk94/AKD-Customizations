"""
Weekly sales-target progress digest.

BRD: FR-SELL-17  Sales targets by territory.
     FR-SELL-59  Sales targets for salespeople / territories.
     FR-SELL-82  Sales target vs actual reports.
     FR-SELL-90  Email notifications for SO events.

For every Sales Person who has a target row matching the current fiscal year,
compute actual sales achieved YTD (Submitted Sales Invoices) and report the
attainment %. Same for Territories.

Send weekly. Recipients: Sales Manager + General Manager.
"""

from datetime import date

import frappe
from frappe.utils import flt, fmt_money

RECIPIENTS = ["sales@akd-consulting.ae", "gm@akd-consulting.ae"]


def send() -> None:
	year = date.today().year
	fy_start = date(year, 1, 1)
	fy_end = date(year, 12, 31)

	sp_rows = _sales_person_progress(fy_start, fy_end)
	terr_rows = _territory_progress(fy_start, fy_end)

	if not sp_rows and not terr_rows:
		return

	subject = f"AKD Sales target progress — week ending {date.today()}"
	frappe.sendmail(
		recipients=RECIPIENTS,
		subject=subject,
		message=_format_message(sp_rows, terr_rows),
		reference_doctype="Sales Person",
	)


def _sales_person_progress(fy_start, fy_end) -> list[dict]:
	"""Use Sales Person hierarchy + Target Detail child rows."""
	people = frappe.get_all(
		"Sales Person",
		filters={"enabled": 1},
		fields=["name", "sales_person_name"],
	)
	rows = []
	for p in people:
		targets = frappe.get_all(
			"Target Detail",
			filters={"parent": p.name, "fiscal_year": str(fy_start.year)},
			fields=["target_amount", "target_qty"],
		)
		target_amount = sum(flt(t.target_amount) for t in targets)
		if not target_amount:
			continue
		actual = flt(frappe.db.sql(
			"""
			SELECT COALESCE(SUM(sit.allocated_amount), 0)
			FROM `tabSales Team` sit
			JOIN `tabSales Invoice` si ON si.name = sit.parent
			WHERE sit.sales_person = %s
			  AND si.docstatus = 1
			  AND si.posting_date BETWEEN %s AND %s
			""",
			(p.name, fy_start, fy_end),
		)[0][0])
		rows.append({
			"name": p.sales_person_name or p.name,
			"target": target_amount,
			"actual": actual,
			"pct": (actual / target_amount * 100) if target_amount else 0,
		})
	return sorted(rows, key=lambda r: -r["pct"])


def _territory_progress(fy_start, fy_end) -> list[dict]:
	terrs = frappe.get_all("Territory", filters={"is_group": 0}, fields=["name"])
	rows = []
	for t in terrs:
		targets = frappe.get_all(
			"Target Detail",
			filters={"parent": t.name, "fiscal_year": str(fy_start.year)},
			fields=["target_amount"],
		)
		target_amount = sum(flt(x.target_amount) for x in targets)
		if not target_amount:
			continue
		actual = flt(frappe.db.sql(
			"""
			SELECT COALESCE(SUM(grand_total), 0)
			FROM `tabSales Invoice`
			WHERE territory = %s
			  AND docstatus = 1
			  AND posting_date BETWEEN %s AND %s
			""",
			(t.name, fy_start, fy_end),
		)[0][0])
		rows.append({
			"name": t.name,
			"target": target_amount,
			"actual": actual,
			"pct": (actual / target_amount * 100) if target_amount else 0,
		})
	return sorted(rows, key=lambda r: -r["pct"])


def _format_message(sp_rows: list[dict], terr_rows: list[dict]) -> str:
	def _table(rows: list[dict], heading: str) -> str:
		if not rows:
			return f"<h4>{heading}: no targets set</h4>"
		body = "".join(
			f"<tr>"
			f"<td>{r['name']}</td>"
			f"<td style='text-align:right'>{fmt_money(r['target'])}</td>"
			f"<td style='text-align:right'>{fmt_money(r['actual'])}</td>"
			f"<td style='text-align:right; "
			f"color: {'#2a8' if r['pct'] >= 100 else '#c33' if r['pct'] < 50 else '#888'}'>"
			f"{r['pct']:.1f}%</td>"
			f"</tr>"
			for r in rows
		)
		return (
			f"<h4>{heading}</h4>"
			"<table border='1' cellpadding='6' cellspacing='0'>"
			"<tr><th>Name</th><th>YTD Target</th><th>YTD Actual</th><th>Attainment</th></tr>"
			f"{body}"
			"</table>"
		)

	return (
		"<p>Auto-generated weekly sales target progress (FR-SELL-82):</p>"
		+ _table(sp_rows, "By Sales Person")
		+ "<br />"
		+ _table(terr_rows, "By Territory")
	)
