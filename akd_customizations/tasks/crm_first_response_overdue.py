"""
CRM lead first-response SLA monitor.

BRD: FR-CRM-41 — SLA for lead response time.
     FR-CRM-42 — SLA targets vary by priority / source (single default here;
                 AKD provides the target table at CRP — §12.4 Q48).
     FR-CRM-43 — SLA tracking on deals (Opportunities) too.
     FR-CRM-44 — SLA breach notifications.

ERPNext v16 Lead has no native SLA fields and the BRD puts working-hours /
holiday SLA out of scope (no HR). So this is a calendar-naive (24×7) daily
digest: leads still un-actioned past the response window are flagged to the
CRM managers.

Response window is a single default until AKD supplies the per-priority /
per-source matrix (§12.4 Q48).
"""

import frappe
from frappe.utils import add_to_date, now_datetime

RESPONSE_WINDOW_HOURS = 24  # default — AKD to confirm (CRP Q48)
ALERT_RECIPIENTS = ["crm@akd-consulting.ae"]
OPEN_STATUSES = ["Lead", "Open"]


def _no_response(doctype: str, name: str) -> bool:
	"""A logged Communication against the record = first response made."""
	return not frappe.db.exists(
		"Communication",
		{"reference_doctype": doctype, "reference_name": name},
	)


def send() -> None:
	threshold = add_to_date(now_datetime(), hours=-RESPONSE_WINDOW_HOURS)

	# FR-CRM-41 — leads with no first response.
	leads = frappe.get_all(
		"Lead",
		filters={"status": ["in", OPEN_STATUSES], "creation": ["<", threshold]},
		fields=["name", "lead_name", "company_name", "lead_owner",
				"utm_source", "creation"],
		order_by="creation asc", limit=100,
	)
	lead_breached = [l for l in leads if _no_response("Lead", l["name"])]

	# FR-CRM-43 — SLA tracking on deals (Opportunities) too.
	opps = frappe.get_all(
		"Opportunity",
		filters={"status": "Open", "creation": ["<", threshold]},
		fields=["name", "customer_name", "opportunity_owner",
				"opportunity_amount", "creation"],
		order_by="creation asc", limit=100,
	)
	opp_breached = [o for o in opps if _no_response("Opportunity", o["name"])]

	if not lead_breached and not opp_breached:
		return

	frappe.sendmail(
		recipients=ALERT_RECIPIENTS,
		subject=(
			f"AKD CRM SLA breach — {len(lead_breached)} lead(s), "
			f"{len(opp_breached)} deal(s) past {RESPONSE_WINDOW_HOURS}h"
		),
		message=_format(lead_breached, opp_breached),
	)


def _format(leads: list, opps: list) -> str:
	out = []
	if leads:
		out.append(
			f"<h3>Leads — no first response after "
			f"{RESPONSE_WINDOW_HOURS}h</h3><ul>"
		)
		for r in leads:
			out.append(
				f"<li><b>{r['name']}</b> — {r.get('lead_name') or ''} "
				f"({r.get('company_name') or '—'}), source "
				f"{r.get('utm_source') or '—'}, owner "
				f"{r.get('lead_owner') or 'unassigned'}, "
				f"created {r['creation']}</li>"
			)
		out.append("</ul>")
	if opps:
		out.append(
			f"<h3>Opportunities — no first response after "
			f"{RESPONSE_WINDOW_HOURS}h</h3><ul>"
		)
		for r in opps:
			out.append(
				f"<li><b>{r['name']}</b> — {r.get('customer_name') or '—'}, "
				f"amount {r.get('opportunity_amount') or 0}, owner "
				f"{r.get('opportunity_owner') or 'unassigned'}, "
				f"created {r['creation']}</li>"
			)
		out.append("</ul>")
	return "\n".join(out)
