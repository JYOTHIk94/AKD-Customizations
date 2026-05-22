"""
Quality module setup — lightweight Pass/Fail QMS for a consulting firm.

BRD references (Section 9):
  FR-QA-06/48  Incoming inspection for ALL supplier deliveries (C-09 resolved
               Yes; Buying FR-BUY-46 "Always" already assumes this).
  FR-QA-08/09  Outgoing / final inspection, trigger = Delivery Note.
  FR-QA-10/11  No predefined parameters (AKD reviews document deliverables) —
               a single generic Pass/Fail criterion is used instead.
  FR-QA-12     Acceptance criteria = Pass / Fail.
  FR-QA-14     Inspection mandatory before stock acceptance.
  FR-QA-25/33  Quality Procedure register exists so NC / Review / CAPA can
               link to it (version tracking = native Frappe document history).
  FR-QA-31..37 Non-Conformance + CAPA (Quality Action) flow.
  FR-QA-55..58 Roles: Quality Manager (native) + Quality Inspector /
               Quality Auditor / Process Owner.

Resolved conflicts assumed (pending AKD sign-off):
  C-09 → incoming Quality Inspection ON (Q50 + FR-BUY-46 win over Quality Q6).

Out of scope per BRD: Quality Goals/KPIs (FR-QA-16/19/20 = No),
Quality Feedback (FR-QA-38..41 = No), MRM meetings (FR-QA-42..45),
quality dashboards / trend analysis (FR-QA-52..54).

Usage:
  bench --site akd.com execute akd_customizations.setup.quality.setup
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

# FR-QA-56/57/58 — desired permission matrix (permlevel 0). Defining the FULL
# set as Custom DocPerm intentionally DROPS the over-broad ERPNext defaults
# (Non Conformance → every "Employee"; Quality Action/Review/Procedure → every
# "Desk User"), so NC visibility becomes Management + Quality only (FR-QA-57).
#   flags: r=read w=write c=create d=delete s=submit
_FULL = "rwcds"
_PERMS = {
	# FR-QA-56 — only Inspectors (and Manager) create inspection reports;
	# FR-QA-58 — Auditor read-only.
	"Quality Inspection": {
		"System Manager": _FULL, "Quality Manager": _FULL,
		"Quality Inspector": "rwcs", "Quality Auditor": "r",
	},
	# FR-QA-57 — Management + Quality team only (no Employee).
	"Non Conformance": {
		"System Manager": _FULL, "Quality Manager": _FULL,
		"Quality Inspector": "rwc", "Quality Auditor": "r",
	},
	"Quality Action": {
		"System Manager": _FULL, "Quality Manager": _FULL,
		"Quality Inspector": "rwc", "Quality Auditor": "r",
	},
	"Quality Review": {
		"System Manager": _FULL, "Quality Manager": _FULL,
		"Quality Inspector": "rwc", "Quality Auditor": "r",
	},
	"Quality Procedure": {
		"System Manager": _FULL, "Quality Manager": _FULL,
		"Quality Inspector": "rwc", "Quality Auditor": "r",
		"Process Owner": "r",
	},
	"Quality Goal": {
		"System Manager": _FULL, "Quality Manager": _FULL,
		"Quality Inspector": "rwc", "Quality Auditor": "r",
	},
}
_PTYPE = {"r": "read", "w": "write", "c": "create", "d": "delete", "s": "submit"}

# FR-QA-51 — quality reports. Query Reports (is_standard="No") restricted to
# Management + Quality. Native Supplier Scorecard covers "Supplier Quality
# Scorecard"; "Quality Goal vs Actual" is N/A (FR-QA-16/20 — no measured KPI).
_REPORT_ROLES = [
	"System Manager", "Quality Manager", "Quality Inspector", "Quality Auditor",
]
_REPORTS = {
	"AKD Quality Inspection Summary": ("Quality Inspection", """
SELECT qi.name AS "Inspection:Link/Quality Inspection:150",
       qi.report_date AS "Date:Date:90",
       qi.inspection_type AS "Type::90",
       qi.reference_type AS "Ref Type::110",
       qi.reference_name AS "Reference::150",
       qi.item_code AS "Item:Link/Item:150",
       qi.status AS "Status::90",
       qi.quality_inspection_template AS "Template::140"
FROM `tabQuality Inspection` qi
ORDER BY qi.report_date DESC
"""),
	"AKD Defect Analysis": ("Quality Inspection", """
SELECT qi.item_code AS "Item:Link/Item:180",
       COUNT(qi.name) AS "Inspections:Int:110",
       SUM(qi.status='Rejected') AS "Rejected:Int:90",
       ROUND(100*SUM(qi.status='Rejected')/COUNT(qi.name),1) AS "Defect %:Float:90"
FROM `tabQuality Inspection` qi
GROUP BY qi.item_code
ORDER BY 4 DESC
"""),
	"AKD Non-Conformance Log": ("Non Conformance", """
SELECT nc.name AS "NC:Link/Non Conformance:140",
       nc.subject AS "Subject::260",
       nc.akd_nc_trigger AS "Trigger::140",
       nc.status AS "Status::90",
       nc.procedure AS "Procedure:Link/Quality Procedure:200",
       nc.creation AS "Raised On:Datetime:140"
FROM `tabNon Conformance` nc
ORDER BY nc.creation DESC
"""),
	"AKD CAPA Status": ("Quality Action", """
SELECT qa.name AS "Action:Link/Quality Action:130",
       qa.corrective_preventive AS "Type::100",
       qa.status AS "Status::90",
       qa.date AS "Date:Date:90",
       qa.procedure AS "Procedure:Link/Quality Procedure:190",
       qa.review AS "Review:Link/Quality Review:140",
       qa.akd_supplier AS "Supplier:Link/Supplier:170"
FROM `tabQuality Action` qa
ORDER BY qa.date DESC
"""),
	"AKD Customer Complaint Trend": ("Non Conformance", """
SELECT DATE_FORMAT(nc.creation,'%%Y-%%m') AS "Month::90",
       COUNT(nc.name) AS "Complaints:Int:110",
       SUM(nc.status='Open') AS "Open:Int:80",
       SUM(nc.status='Resolved') AS "Resolved:Int:90"
FROM `tabNon Conformance` nc
WHERE nc.akd_nc_trigger='Customer Complaint'
GROUP BY DATE_FORMAT(nc.creation,'%%Y-%%m')
ORDER BY 1 DESC
"""),
	"AKD Audit Findings Summary": ("Non Conformance", """
SELECT nc.name AS "Finding:Link/Non Conformance:140",
       nc.subject AS "Subject::280",
       nc.status AS "Status::90",
       nc.procedure AS "Procedure:Link/Quality Procedure:200",
       nc.creation AS "Logged:Datetime:140"
FROM `tabNon Conformance` nc
WHERE nc.akd_nc_trigger='Audit Finding'
ORDER BY nc.creation DESC
"""),
}

# FR-QA-55 — Quality Manager ships with ERPNext; create the other three.
ROLES = ["Quality Inspector", "Quality Auditor", "Process Owner"]

PARAMETER = "AKD Acceptance"
TEMPLATE = "AKD Pass-Fail"

# FR-QA-25/33 — minimal procedure register; pure NC/Review/CAPA link targets.
PROCEDURES = [
	"AKD Outgoing Deliverable Review",
	"AKD Supplier Quality",
	"AKD Process Deviation",
]

# ERPNext v16 constraint: Quality Review.goal is mandatory and validate()
# copies the goal's objectives into the review — a Quality Review cannot
# exist without a Quality Goal. FR-QA-26/27 (Monthly reviews = Yes) therefore
# REQUIRES one anchor goal, even though FR-QA-16/19/20 say no measurable KPIs.
# This single placeholder carries one qualitative (non-numeric) objective.
GOAL = "AKD Quality Review"
GOAL_PROCEDURE = "AKD Outgoing Deliverable Review"
# FR-QA-18 — objectives tracked. Qualitative only: FR-QA-16/20 say no
# measurable KPI / target-vs-actual, so `target` is a qualitative marker.
GOAL_OBJECTIVES = [
	"Deliverable / service acceptance (Pass/Fail) — FR-QA-12",
	"Defect rate",
	"Customer complaints",
	"On-time delivery",
	"Supplier quality score",
]
GOAL_TARGET = "Qualitative"
# Exact text of an interim placeholder objective shipped earlier — pruned on
# reconcile so the goal carries only the FR-QA-18 set (not generally
# destructive: only this known string is removed).
_LEGACY_OBJECTIVES = {
	"Deliverable / service acceptance — qualitative review "
	"(no numeric KPI per FR-QA-16)",
}


def setup() -> dict:
	report = {
		"roles": _ensure_roles(),
		"parameter": _ensure_parameter(),
		"template": _ensure_template(),
		"procedures": _ensure_procedures(),
		"goal": _ensure_goal(),
		"reports": _ensure_reports(),
		"permissions": apply_permissions(),
	}
	frappe.db.commit()
	frappe.logger("akd_setup").info({"quality": report})
	return report


def _ensure_roles() -> list[str]:
	"""FR-QA-55 — quality roles. Shipped as fixtures too; created here so
	orchestrator.run() is self-sufficient before a fixtures sync."""
	out = []
	for role in ROLES:
		if frappe.db.exists("Role", role):
			out.append(f"existing:{role}")
			continue
		frappe.get_doc({
			"doctype": "Role",
			"role_name": role,
			"desk_access": 1,
			"is_custom": 1,
		}).insert(ignore_permissions=True)
		out.append(f"created:{role}")
	return out


def _ensure_parameter() -> str:
	"""FR-QA-10/11 — single non-numeric criterion (no measurement params)."""
	if frappe.db.exists("Quality Inspection Parameter", PARAMETER):
		return f"existing:{PARAMETER}"
	frappe.get_doc({
		"doctype": "Quality Inspection Parameter",
		"parameter": PARAMETER,
		"description": "Deliverable / goods accepted — Pass or Fail.",
	}).insert(ignore_permissions=True)
	return f"created:{PARAMETER}"


def _ensure_template() -> str:
	"""FR-QA-12 — generic Pass/Fail Quality Inspection Template, used for both
	incoming (FR-QA-48) and outgoing (FR-QA-08) inspections."""
	if frappe.db.exists("Quality Inspection Template", TEMPLATE):
		return f"existing:{TEMPLATE}"
	frappe.get_doc({
		"doctype": "Quality Inspection Template",
		"quality_inspection_template_name": TEMPLATE,
		"item_quality_inspection_parameter": [{
			"specification": PARAMETER,
			"value": "Accepted",
			"numeric": 0,
		}],
	}).insert(ignore_permissions=True)
	return f"created:{TEMPLATE}"


def _ensure_procedures() -> list[str]:
	out = []
	for name in PROCEDURES:
		if frappe.db.exists("Quality Procedure", name):
			out.append(f"existing:{name}")
			continue
		frappe.get_doc({
			"doctype": "Quality Procedure",
			"quality_procedure_name": name,
			"is_group": 0,
		}).insert(ignore_permissions=True)
		out.append(f"created:{name}")
	return out


def _ensure_goal() -> str:
	"""Anchor Quality Goal (FR-QA-26/27) — ERPNext requires it for reviews.
	Idempotently reconciles the FR-QA-18 objective list onto an existing
	goal (new objectives flow into the NEXT Quality Review, not past ones)."""
	rows = [{"objective": o, "target": GOAL_TARGET} for o in GOAL_OBJECTIVES]

	if not frappe.db.exists("Quality Goal", GOAL):
		frappe.get_doc({
			"doctype": "Quality Goal",
			"goal": GOAL,
			"frequency": "Monthly",
			"procedure": GOAL_PROCEDURE,
			"objectives": rows,
		}).insert(ignore_permissions=True)
		return f"created:{GOAL}"

	doc = frappe.get_doc("Quality Goal", GOAL)
	kept = [
		o for o in (doc.objectives or [])
		if (o.objective or "").strip() not in _LEGACY_OBJECTIVES
	]
	pruned = len(doc.objectives or []) - len(kept)
	have = {(o.objective or "").strip() for o in kept}
	added = [o for o in GOAL_OBJECTIVES if o not in have]
	if pruned or added:
		doc.set("objectives", [
			{"objective": o.objective, "target": o.target} for o in kept
		])
		for o in added:
			doc.append("objectives", {"objective": o, "target": GOAL_TARGET})
		doc.save(ignore_permissions=True)
		return f"updated:{GOAL} (+{len(added)} / -{pruned})"
	return f"existing:{GOAL}"


def apply_permissions() -> dict:
	"""FR-QA-56/57/58 — replace the over-broad default perms with a
	Management + Quality matrix. Idempotent (re-running just re-asserts).

	  bench --site akd.com execute \\
	    akd_customizations.setup.quality.apply_permissions
	"""
	out = {}
	for doctype, role_flags in _PERMS.items():
		applied = []
		for role, flags in role_flags.items():
			if not frappe.db.exists("Role", role):
				applied.append(f"skip(no role):{role}")
				continue
			# Creates a Custom DocPerm row (read=1) if absent.
			add_permission(doctype, role, 0)
			want = {p: (letter in flags) for letter, p in _PTYPE.items()}
			for ptype, value in want.items():
				update_permission_property(
					doctype, role, 0, ptype, 1 if value else 0, validate=False
				)
			applied.append(f"{role}:{flags}")
		out[doctype] = applied
	frappe.clear_cache()
	return out


def _ensure_reports() -> list[str]:
	"""FR-QA-51 — create/refresh the quality Query Reports. Idempotent:
	re-running re-asserts the SQL and the role restriction."""
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


def enable_inspection_on_items(item_filters: dict | None = None) -> dict:
	"""FR-QA-14/48/08 — turn on mandatory incoming + outgoing inspection and
	attach the Pass/Fail template on stock items.

	ERPNext v16 has no global "QI mandatory" switch — it is enforced per Item.
	Call this AFTER the real item master is loaded (or pass filters to scope
	it). Defaults to every stock-maintained, non-disabled Item.

	  bench --site akd.com execute \\
	    akd_customizations.setup.quality.enable_inspection_on_items
	"""
	if not frappe.db.exists("Quality Inspection Template", TEMPLATE):
		_ensure_template()

	filters = {"is_stock_item": 1, "disabled": 0}
	if item_filters:
		filters.update(item_filters)

	updated, skipped = [], []
	for item in frappe.get_all("Item", filters=filters, pluck="name"):
		doc = frappe.get_doc("Item", item)
		dirty = False
		if not doc.inspection_required_before_purchase:
			doc.inspection_required_before_purchase = 1
			dirty = True
		if not doc.inspection_required_before_delivery:
			doc.inspection_required_before_delivery = 1
			dirty = True
		if doc.quality_inspection_template != TEMPLATE:
			doc.quality_inspection_template = TEMPLATE
			dirty = True
		if dirty:
			doc.save(ignore_permissions=True)
			updated.append(item)
		else:
			skipped.append(item)
	frappe.db.commit()
	return {"updated": updated, "already_set": skipped, "template": TEMPLATE}
