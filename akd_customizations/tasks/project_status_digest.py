"""
Weekly project-status digest.

BRD: FR-PROJ-24 — periodic project status updates.
     FR-PROJ-25 — frequency = Weekly.
     FR-PROJ-58 — scheduled project-status email reports.

Lists active projects with % complete, billed vs cost, and any tasks that are
Overdue, so the PMO has a Monday snapshot. (Detailed scheduled reports are
also delivered via Auto Email Report fixtures.)
"""

import frappe

ALERT_RECIPIENTS = ["pmo@akd-consulting.ae"]


def send() -> None:
	projects = frappe.get_all(
		"Project",
		filters={"status": ["!=", "Cancelled"], "is_active": "Yes"},
		fields=["name", "project_name", "status", "percent_complete",
				"expected_end_date", "total_costing_amount",
				"total_billed_amount"],
		order_by="expected_end_date asc",
		limit=100,
	)
	if not projects:
		return

	overdue = frappe.db.count("Task", {"status": "Overdue"})
	frappe.sendmail(
		recipients=ALERT_RECIPIENTS,
		subject=(
			f"AKD Weekly Project Status — {len(projects)} active, "
			f"{overdue} overdue task(s)"
		),
		message=_format(projects, overdue),
	)


def _format(projects: list, overdue: int) -> str:
	rows = [
		"<h3>AKD Weekly Project Status</h3>",
		f"<p>Overdue tasks across all projects: <b>{overdue}</b></p>",
		"<table border=1 cellpadding=4 cellspacing=0>",
		"<tr><th>Project</th><th>Status</th><th>% Complete</th>"
		"<th>Expected End</th><th>Cost</th><th>Billed</th></tr>",
	]
	for p in projects:
		rows.append(
			f"<tr><td>{p.get('project_name') or p['name']}</td>"
			f"<td>{p.get('status')}</td>"
			f"<td>{p.get('percent_complete') or 0:.0f}%</td>"
			f"<td>{p.get('expected_end_date') or '—'}</td>"
			f"<td>{p.get('total_costing_amount') or 0:,.0f}</td>"
			f"<td>{p.get('total_billed_amount') or 0:,.0f}</td></tr>"
		)
	rows.append("</table>")
	return "\n".join(rows)
