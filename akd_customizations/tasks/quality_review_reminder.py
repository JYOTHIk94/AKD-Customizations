"""
Monthly Quality Review reminder.

BRD: FR-QA-26 — periodic quality reviews required.
     FR-QA-27 — quality-review frequency = Monthly.
     FR-QA-30 — review status tracked (Open / Passed / Failed).

Runs monthly. Reminds the Quality team to raise the period's Quality Review
and lists any reviews still Open from prior periods so nothing is left
unclosed (FR-QA-30).
"""

import frappe
from frappe.utils import get_first_day, get_last_day, today

ALERT_RECIPIENTS = ["quality@akd-consulting.ae"]


def send() -> None:
	period_start = get_first_day(today())
	period_end = get_last_day(today())

	already_raised = frappe.db.count(
		"Quality Review",
		{"date": ["between", [period_start, period_end]]},
	)
	open_reviews = frappe.get_all(
		"Quality Review",
		filters={"status": "Open"},
		fields=["name", "date", "procedure", "goal"],
		order_by="date asc",
		limit=50,
	)

	if already_raised and not open_reviews:
		return

	subject = (
		f"AKD Quality Review — {'raised' if already_raised else 'DUE'} for "
		f"{period_start.strftime('%B %Y')}"
		+ (f" · {len(open_reviews)} still Open" if open_reviews else "")
	)
	frappe.sendmail(
		recipients=ALERT_RECIPIENTS,
		subject=subject,
		message=_format_message(already_raised, open_reviews, period_start),
	)


def _format_message(already_raised: int, open_reviews: list, period_start) -> str:
	lines = [f"<h3>Monthly Quality Review — {period_start.strftime('%B %Y')}</h3>"]
	if not already_raised:
		lines.append(
			"<p><b>No Quality Review has been raised for this month yet.</b> "
			"Please create one (Quality &gt; Quality Review) and link it to the "
			"relevant Quality Procedure / objectives.</p>"
		)
	if open_reviews:
		lines.append(f"<p><b>{len(open_reviews)} review(s) still Open:</b></p><ul>")
		for r in open_reviews:
			lines.append(
				f"<li>{r['name']} — {r['date']} "
				f"(procedure: {r.get('procedure') or '—'})</li>"
			)
		lines.append("</ul>")
	return "\n".join(lines)
