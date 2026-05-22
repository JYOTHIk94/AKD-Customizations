"""
CRM module setup — ERPNext built-in CRM (Lead / Opportunity / Prospect).

ERPNext v16 note: the old "Lead Source" doctype is gone — lead origin is now
`Lead.utm_source` → **UTM Source** (FR-CRM-06). Lead has no native SLA fields,
so first-response monitoring is task-based (tasks/crm_first_response_overdue).

BRD references (Section 7):
  FR-CRM-06   Lead sources                → UTM Source masters
  FR-CRM-09   Round-robin auto-assignment → Assignment Rule (Lead)
  FR-CRM-12   Prevent duplicate leads by email → CRM Settings
  FR-CRM-19   Opportunity lost reasons    → Opportunity Lost Reason masters
  FR-CRM-20   Multiple pipelines          → Opportunity Type (single Sales
              Stage list is a v16 limitation — D-CRM-4)
  FR-CRM-25   Auto-create Customer on deal won → overrides/opportunity.py
  FR-CRM-30   Campaigns (header only)      → Campaign masters
  FR-CRM-59   Territory-wise + Forecast reports → Query Reports
  FR-CRM-63   Roles                       → Marketing User / CRM Admin /
              Read-only Viewer (+ native Sales Manager / Sales User)
  FR-CRM-64/65/66  Data scoping + no lead delete → Custom DocPerm +
              permission_query (overrides/crm_permissions.py)

Out of scope per BRD: web-form capture, Kanban, drip/open-click/unsubscribe,
WhatsApp/SMS/social, email send-receive, call logging, telephony,
appointments, contract templates/e-sign, custom dashboards.

Usage:
  bench --site akd.com execute akd_customizations.setup.crm.setup
"""

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

# FR-CRM-63 — Sales Manager / Sales User ship with ERPNext.
ROLES = ["Marketing User", "CRM Admin", "Read-only Viewer"]

# FR-CRM-06 — primary lead sources (UTM Source in v16).
UTM_SOURCES = [
	"Website", "Phone / Walk-in", "Referral", "Social Media",
	"Email Campaign", "Trade Show / Event", "Paid Advertising",
	"Partner / Channel", "Cold Outreach",
]

# FR-CRM-30 — campaign types, header only (no automation).
CAMPAIGNS = [
	"Email Drip / Nurture", "Event / Webinar", "Product Launch",
	"Seasonal Promotion", "Referral Program", "Social Media",
]

# FR-CRM-20 — pipelines via Opportunity Type (AKD service lines + Maintenance).
OPPORTUNITY_TYPES = ["Advisory", "Platforms", "Sustained Services", "Maintenance"]

# FR-CRM-19 — placeholder lost-reason list; final list = CRP (§12.4 Q22).
OPPORTUNITY_LOST_REASONS = [
	"Price", "Lost to Competitor", "No Budget",
	"Timing / No Decision", "Requirement Not Met",
]

ASSIGNMENT_RULE = "AKD Lead Round Robin"

# FR-CRM-63..66 — permission matrix (no submit; Lead/Opp are not submittable).
# Full Custom DocPerm set intentionally REPLACES native perms.
#   r=read w=write c=create d=delete
_FULL = "rwcd"
_PERMS = {
	# FR-CRM-66 — only System Manager / CRM Admin may delete a Lead.
	"Lead": {
		"System Manager": _FULL, "CRM Admin": _FULL,
		"Sales Manager": "rwc", "Sales User": "rwc",
		"Marketing User": "r", "Read-only Viewer": "r",
	},
	"Opportunity": {
		"System Manager": _FULL, "CRM Admin": _FULL,
		"Sales Manager": _FULL, "Sales User": "rwc",
		"Marketing User": "r", "Read-only Viewer": "r",
	},
	"Prospect": {
		"System Manager": _FULL, "CRM Admin": _FULL,
		"Sales Manager": "rwc", "Sales User": "rwc",
		"Marketing User": "rwc", "Read-only Viewer": "r",
	},
	"Campaign": {
		"System Manager": _FULL, "CRM Admin": _FULL,
		"Marketing User": "rwc", "Sales Manager": "r",
		"Sales User": "r", "Read-only Viewer": "r",
	},
}
_PTYPE = {"r": "read", "w": "write", "c": "create", "d": "delete"}

_REPORT_ROLES = [
	"System Manager", "CRM Admin", "Sales Manager",
	"Marketing User", "Read-only Viewer",
]
# FR-CRM-59 — the two reports ERPNext does not ship out of the box. Pipeline /
# conversion / source / campaign-efficiency / first-response are standard.
_REPORTS = {
	"AKD CRM Territory-wise Analysis": ("Opportunity", """
SELECT o.territory AS "Territory:Link/Territory:180",
       COUNT(o.name) AS "Opportunities:Int:120",
       SUM(o.status='Open') AS "Open:Int:80",
       SUM(o.status='Converted') AS "Won:Int:80",
       SUM(o.status='Lost') AS "Lost:Int:80",
       ROUND(SUM(o.opportunity_amount),2) AS "Pipeline Value:Float:140"
FROM `tabOpportunity` o
GROUP BY o.territory
ORDER BY 6 DESC
"""),
	"AKD CRM Lead Source Analysis": ("Lead", """
SELECT l.utm_source AS "Source:Link/UTM Source:200",
       COUNT(l.name) AS "Leads:Int:90",
       SUM(l.status='Converted') AS "Converted:Int:100",
       ROUND(100*SUM(l.status='Converted')/COUNT(l.name),1) AS "Conv %%:Float:90"
FROM `tabLead` l
GROUP BY l.utm_source
ORDER BY 2 DESC
"""),
	"AKD CRM Forecast / Revenue Projection": ("Opportunity", """
SELECT o.name AS "Opportunity:Link/Opportunity:150",
       o.customer_name AS "Party::200",
       o.sales_stage AS "Stage::140",
       o.probability AS "Prob %%:Percent:80",
       o.opportunity_amount AS "Amount:Float:130",
       ROUND(o.opportunity_amount*o.probability/100,2) AS "Weighted:Float:130",
       o.expected_closing AS "Expected Close:Date:120"
FROM `tabOpportunity` o
WHERE o.status IN ('Open','Quotation','Replied')
ORDER BY o.expected_closing
"""),
}


def setup() -> dict:
	report = {
		"roles": _ensure_roles(),
		"utm_sources": _ensure_named("UTM Source", UTM_SOURCES, prompt=True),
		"opportunity_types": _ensure_named(
			"Opportunity Type", OPPORTUNITY_TYPES, prompt=True
		),
		"lost_reasons": _ensure_lost_reasons(),
		"campaigns": _ensure_campaigns(),
		"crm_settings": _apply_crm_settings(),
		"assignment_rule": _ensure_assignment_rule(),
		"reports": _ensure_reports(),
		"permissions": apply_permissions(),
	}
	frappe.db.commit()
	frappe.logger("akd_setup").info({"crm": report})
	return report


def _ensure_roles() -> list[str]:
	out = []
	for role in ROLES:
		if frappe.db.exists("Role", role):
			out.append(f"existing:{role}")
			continue
		frappe.get_doc({
			"doctype": "Role", "role_name": role,
			"desk_access": 1, "is_custom": 1,
		}).insert(ignore_permissions=True)
		out.append(f"created:{role}")
	return out


def _ensure_named(doctype: str, names: list[str], prompt: bool) -> list[str]:
	"""Create simple prompt-autonamed masters (UTM Source, Opportunity Type)."""
	out = []
	for name in names:
		if frappe.db.exists(doctype, name):
			out.append(f"existing:{name}")
			continue
		doc = frappe.new_doc(doctype)
		if prompt:
			doc.name = name
		doc.insert(ignore_permissions=True)
		out.append(f"created:{name}")
	return out


def _ensure_lost_reasons() -> list[str]:
	out = []
	for reason in OPPORTUNITY_LOST_REASONS:
		if frappe.db.exists("Opportunity Lost Reason", reason):
			out.append(f"existing:{reason}")
			continue
		frappe.get_doc({
			"doctype": "Opportunity Lost Reason", "lost_reason": reason,
		}).insert(ignore_permissions=True)
		out.append(f"created:{reason}")
	return out


def _ensure_campaigns() -> list[str]:
	"""FR-CRM-30 — header-only Campaign masters (naming-series autoname, so
	keyed on campaign_name for idempotency)."""
	out = []
	for name in CAMPAIGNS:
		if frappe.db.exists("Campaign", {"campaign_name": name}):
			out.append(f"existing:{name}")
			continue
		frappe.get_doc({
			"doctype": "Campaign", "campaign_name": name,
		}).insert(ignore_permissions=True)
		out.append(f"created:{name}")
	return out


def _apply_crm_settings() -> dict:
	"""FR-CRM-12 — prevent duplicate leads by email (uncheck the allow flag).
	FR-CRM-23 — auto-create Contact so multiple contacts per org work."""
	patch = {
		"allow_lead_duplication_based_on_emails": 0,
		"auto_creation_of_contact": 1,
	}
	current = frappe.db.get_value(
		"CRM Settings", None, list(patch.keys()), as_dict=True
	) or {}
	changes = {
		k: {"from": current.get(k), "to": v}
		for k, v in patch.items() if current.get(k) != v
	}
	if changes:
		s = frappe.get_single("CRM Settings")
		for k, v in patch.items():
			s.set(k, v)
		s.save(ignore_permissions=True)
	return changes


def _ensure_assignment_rule() -> str:
	"""FR-CRM-09 — round-robin Lead assignment. Users default to current
	enabled Sales Users; AKD edits the rule once real reps exist."""
	if frappe.db.exists("Assignment Rule", ASSIGNMENT_RULE):
		return f"existing:{ASSIGNMENT_RULE}"

	sales_users = frappe.get_all(
		"Has Role",
		filters={"role": "Sales User", "parenttype": "User"},
		pluck="parent",
	)
	sales_users = [
		u for u in set(sales_users)
		if frappe.db.get_value("User", u, "enabled")
		and u not in ("Administrator", "Guest")
	]

	doc = frappe.get_doc({
		"doctype": "Assignment Rule",
		"name": ASSIGNMENT_RULE,
		"document_type": "Lead",
		"rule": "Round Robin",
		"priority": 0,
		"disabled": 0 if sales_users else 1,
		"assign_condition": "status in ('Lead','Open')",
		"description": "FR-CRM-09 — round-robin Lead assignment to Sales Users.",
		"users": [{"user": u} for u in sales_users],
		"assignment_days": [
			{"day": d} for d in
			("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
		],
	})
	doc.insert(ignore_permissions=True)
	state = "disabled (no Sales Users yet)" if not sales_users else "active"
	return f"created:{ASSIGNMENT_RULE} ({state})"


def ensure_territory_assignment_rules(mapping: dict[str, list[str]]) -> dict:
	"""FR-CRM-27 — territory-based Lead assignment. One Assignment Rule per
	territory (round-robin within that territory's reps), priority above the
	default catch-all rule so territory routing wins; the default round-robin
	rule remains the fallback for leads with no/blank territory.

	Call at CRP with AKD's real territory→reps map (§12.4 Q30):
	  bench --site akd.com execute \\
	    akd_customizations.setup.crm.ensure_territory_assignment_rules \\
	    --kwargs "{'mapping': {'Middle East': ['a@x.com'], 'Africa': ['b@x.com']}}"
	"""
	out = {}
	for territory, users in mapping.items():
		if not frappe.db.exists("Territory", territory):
			out[territory] = "skip: territory missing"
			continue
		users = [u for u in users if frappe.db.exists("User", u)]
		rule_name = f"AKD Lead — {territory}"
		cond = (
			f"status in ('Lead','Open') and territory == {territory!r}"
		)
		if frappe.db.exists("Assignment Rule", rule_name):
			doc = frappe.get_doc("Assignment Rule", rule_name)
			doc.set("users", [{"user": u} for u in users])
			doc.disabled = 0 if users else 1
			doc.save(ignore_permissions=True)
			out[territory] = f"updated:{rule_name} ({len(users)} users)"
			continue
		frappe.get_doc({
			"doctype": "Assignment Rule",
			"name": rule_name,
			"document_type": "Lead",
			"rule": "Round Robin",
			"priority": 10,  # above the default catch-all (priority 0)
			"disabled": 0 if users else 1,
			"assign_condition": cond,
			"description": f"FR-CRM-27 — territory routing for {territory}.",
			"users": [{"user": u} for u in users],
			"assignment_days": [
				{"day": d} for d in
				("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
			],
		}).insert(ignore_permissions=True)
		out[territory] = f"created:{rule_name} ({len(users)} users)"
	frappe.db.commit()
	return out


def _ensure_reports() -> list[str]:
	"""FR-CRM-59 — the two non-standard Query Reports, role-restricted."""
	out = []
	for name, (ref_doctype, query) in _REPORTS.items():
		sql = query.strip()
		roles = [{"role": r} for r in _REPORT_ROLES if frappe.db.exists("Role", r)]
		if frappe.db.exists("Report", name):
			doc = frappe.get_doc("Report", name)
			doc.report_type = "Query Report"
			doc.ref_doctype = ref_doctype
			doc.query = sql
			doc.set("roles", roles)
			doc.save(ignore_permissions=True)
			out.append(f"updated:{name}")
			continue
		frappe.get_doc({
			"doctype": "Report",
			"report_name": name,
			"ref_doctype": ref_doctype,
			"report_type": "Query Report",
			"is_standard": "No",
			"query": sql,
			"roles": roles,
		}).insert(ignore_permissions=True)
		out.append(f"created:{name}")
	return out


def apply_permissions() -> dict:
	"""FR-CRM-63..66 — replace native perms with the CRM matrix. Idempotent."""
	from frappe.permissions import add_permission, update_permission_property

	out = {}
	for doctype, role_flags in _PERMS.items():
		applied = []
		for role, flags in role_flags.items():
			if not frappe.db.exists("Role", role):
				applied.append(f"skip(no role):{role}")
				continue
			add_permission(doctype, role, 0)
			for letter, ptype in _PTYPE.items():
				update_permission_property(
					doctype, role, 0, ptype,
					1 if letter in flags else 0, validate=False,
				)
			applied.append(f"{role}:{flags}")
		out[doctype] = applied
	frappe.clear_cache()
	return out
