"""
Projects module setup — BRD §8 (FR-PROJ-01..63).

Decisions (defaults adopted, confirm at sign-off):
  D-PROJ-1  Lite HR footprint IN scope — Holiday List + Activity Type/Cost +
            Employee (master = AKD data; Activity Cost per employee at CRP).
  D-PROJ-2  No project templates (FR-PROJ-11/12 = No).
  D-PROJ-3  Project status workflow Open→In Progress→Completed (native Project
            status has no "In Progress").
  D-PROJ-5  Project portal enabled (FR-PROJ-52) — standard ERPNext web view.

BRD references:
  FR-PROJ-06/07  Project Types + categorise
  FR-PROJ-20     Task Types
  FR-PROJ-31/37/44  Activity Types (costing/billing rates — 0 placeholders,
                 CRP §12.5 Q34)
  FR-PROJ-33     Prevent overlapping time entries (Projects Settings)
  FR-PROJ-45     Sales Invoice from timesheet (fetch_timesheet_in_sales_invoice)
  FR-PROJ-53/54/55  Holiday List + Company default (placeholder, CRP)
  FR-PROJ-60     Roles: Projects Manager/User (native) + Timesheet User
  FR-PROJ-61     Restrict project creation to managers (Custom DocPerm)
  FR-PROJ-62     Users see only assigned projects (permission_query — see
                 overrides/project_permissions.py, wired in hooks)
  FR-PROJ-27/32/63  Project status + Timesheet approval workflows
  FR-PROJ-49/56  Resource Utilization Query Report

Usage:
  bench --site akd.com execute akd_customizations.setup.projects.setup
"""

from datetime import date, timedelta

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

ROLES = ["Timesheet User"]  # Projects Manager/User native; Read-only Viewer (CRM)

PROJECT_TYPES = ["Advisory", "AI", "IT Implementation"]          # FR-PROJ-06
TASK_TYPES = ["Analysis", "Design", "Development", "Review",
			  "Deployment", "Project Management"]                 # FR-PROJ-20
# FR-PROJ-31/37/44 — rates 0 until AKD provides them (CRP §12.5 Q34).
ACTIVITY_TYPES = ["Consulting", "Implementation", "Project Management",
				  "Support", "Travel"]

HOLIDAY_LIST = f"AKD Holidays {date.today().year}"
# UAE weekend placeholder (Fri/Sat) — AKD confirms official calendar at CRP.
WEEKLY_OFF_DAYS = {4, 5}  # Mon=0 … Fri=4, Sat=5

_FULL = "rwcds"
_PERMS = {
	# FR-PROJ-61 — only managers create Projects (Projects User no create/delete).
	"Project": {
		"System Manager": _FULL, "Projects Manager": _FULL,
		"Projects User": "rw", "Timesheet User": "r",
		"Read-only Viewer": "r",
	},
	"Task": {
		"System Manager": _FULL, "Projects Manager": _FULL,
		"Projects User": "rwc", "Timesheet User": "r",
		"Read-only Viewer": "r",
	},
	"Timesheet": {
		"System Manager": _FULL, "Projects Manager": _FULL,
		"Projects User": "rwc", "Timesheet User": "rwc",
		"Read-only Viewer": "r",
	},
}
_PTYPE = {"r": "read", "w": "write", "c": "create", "d": "delete", "s": "submit"}

_REPORT_ROLES = ["System Manager", "Projects Manager", "Projects User",
				 "Read-only Viewer"]
_REPORTS = {
	"AKD Resource Utilization": ("Timesheet", """
SELECT tsd.activity_type AS "Activity::150",
       ts.employee_name AS "Employee::180",
       tsd.project AS "Project:Link/Project:160",
       SUM(tsd.hours) AS "Hours:Float:90",
       SUM(tsd.billing_hours) AS "Billable Hrs:Float:110",
       ROUND(100*SUM(tsd.billing_hours)/NULLIF(SUM(tsd.hours),0),1)
         AS "Utilization %%:Float:110"
FROM `tabTimesheet Detail` tsd
JOIN `tabTimesheet` ts ON ts.name = tsd.parent
WHERE ts.docstatus < 2
GROUP BY ts.employee_name, tsd.activity_type, tsd.project
ORDER BY 4 DESC
"""),
}

# Every state/action the two workflows reference must exist as a master
# (frappe Workflow.states[].state → Workflow State; transitions[].action →
# Workflow Action Master). "Draft"/"Approve"/"Reject" already exist site-wide.
WORKFLOW_STATES = [
	("Open", "Info"),
	("In Progress", "Primary"),
	("Completed", "Success"),
	("Cancelled", "Danger"),
	("Draft", ""),
	("Pending Timesheet Approval", "Warning"),
	("Timesheet Approved", "Success"),
	("Timesheet Rejected", "Danger"),
]
WORKFLOW_ACTIONS = ["Start", "Complete", "Cancel",
					"Submit for Approval", "Approve", "Reject"]


def setup() -> dict:
	report = {
		"roles": _ensure_roles(),
		"project_types": _ensure_named("Project Type", "project_type", PROJECT_TYPES),
		"task_types": _ensure_prompt("Task Type", TASK_TYPES),
		"activity_types": _ensure_activity_types(),
		"holiday_list": _ensure_holiday_list(),
		"projects_settings": _apply_projects_settings(),
		"workflow_states": _ensure_workflow_states(),
		"workflow_actions": _ensure_workflow_actions(),
		"workflows": _ensure_workflows(),
		"reports": _ensure_reports(),
		"permissions": apply_permissions(),
	}
	frappe.db.commit()
	frappe.logger("akd_setup").info({"projects": report})
	return report


def _ensure_roles() -> list[str]:
	out = []
	for r in ROLES:
		if frappe.db.exists("Role", r):
			out.append(f"existing:{r}")
			continue
		frappe.get_doc({"doctype": "Role", "role_name": r,
						"desk_access": 1, "is_custom": 1}).insert(ignore_permissions=True)
		out.append(f"created:{r}")
	return out


def _ensure_named(doctype: str, field: str, names: list[str]) -> list[str]:
	out = []
	for n in names:
		if frappe.db.exists(doctype, n):
			out.append(f"existing:{n}")
			continue
		frappe.get_doc({"doctype": doctype, field: n}).insert(ignore_permissions=True)
		out.append(f"created:{n}")
	return out


def _ensure_prompt(doctype: str, names: list[str]) -> list[str]:
	"""Prompt-autonamed masters (Task Type) — name set explicitly."""
	out = []
	for n in names:
		if frappe.db.exists(doctype, n):
			out.append(f"existing:{n}")
			continue
		doc = frappe.new_doc(doctype)
		doc.name = n
		doc.insert(ignore_permissions=True)
		out.append(f"created:{n}")
	return out


def _ensure_activity_types() -> list[str]:
	out = []
	for a in ACTIVITY_TYPES:
		if frappe.db.exists("Activity Type", a):
			out.append(f"existing:{a}")
			continue
		frappe.get_doc({
			"doctype": "Activity Type", "activity_type": a,
			"costing_rate": 0, "billing_rate": 0,   # CRP §12.5 Q34
		}).insert(ignore_permissions=True)
		out.append(f"created:{a}")
	return out


def _ensure_holiday_list() -> str:
	"""FR-PROJ-53/55 — placeholder weekend calendar; AKD supplies the real
	public-holiday list at CRP."""
	if frappe.db.exists("Holiday List", HOLIDAY_LIST):
		_set_company_holiday_list()
		return f"existing:{HOLIDAY_LIST}"

	yr = date.today().year
	start, end = date(yr, 1, 1), date(yr, 12, 31)
	holidays, d = [], start
	while d <= end:
		if d.weekday() in WEEKLY_OFF_DAYS:
			holidays.append({"holiday_date": d, "description": "Weekly Off",
							  "weekly_off": 1})
		d += timedelta(days=1)

	frappe.get_doc({
		"doctype": "Holiday List",
		"holiday_list_name": HOLIDAY_LIST,
		"from_date": start, "to_date": end,
		"holidays": holidays,
	}).insert(ignore_permissions=True)
	_set_company_holiday_list()
	return f"created:{HOLIDAY_LIST} ({len(holidays)} weekly-off days)"


def _set_company_holiday_list() -> None:
	if frappe.db.get_value("Company", COMPANY, "default_holiday_list") != HOLIDAY_LIST:
		frappe.db.set_value("Company", COMPANY, "default_holiday_list", HOLIDAY_LIST)


def _apply_projects_settings() -> dict:
	patch = {
		"ignore_user_time_overlap": 0,       # FR-PROJ-33
		"ignore_employee_time_overlap": 0,   # FR-PROJ-33
		"fetch_timesheet_in_sales_invoice": 1,  # FR-PROJ-45
	}
	current = frappe.db.get_value("Projects Settings", None,
								  list(patch.keys()), as_dict=True) or {}
	changes = {k: {"from": current.get(k), "to": v}
			   for k, v in patch.items() if current.get(k) != v}
	if changes:
		s = frappe.get_single("Projects Settings")
		for k, v in patch.items():
			s.set(k, v)
		s.save(ignore_permissions=True)
	return changes


def _ensure_workflow_states() -> list[str]:
	out = []
	for name, style in WORKFLOW_STATES:
		if frappe.db.exists("Workflow State", name):
			out.append(f"existing:{name}")
			continue
		frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": name,
						"style": style}).insert(ignore_permissions=True)
		out.append(f"created:{name}")
	return out


def _ensure_workflow_actions() -> list[str]:
	out = []
	for name in WORKFLOW_ACTIONS:
		if frappe.db.exists("Workflow Action Master", name):
			out.append(f"existing:{name}")
			continue
		frappe.get_doc({"doctype": "Workflow Action Master",
						"workflow_action_name": name}).insert(ignore_permissions=True)
		out.append(f"created:{name}")
	return out


def _ensure_workflows() -> list[str]:
	out = []

	# FR-PROJ-27 — Project status workflow (Project is not submittable).
	if not frappe.db.exists("Workflow", "AKD Project Status"):
		frappe.get_doc({
			"doctype": "Workflow",
			"workflow_name": "AKD Project Status",
			"document_type": "Project",
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"states": [
				{"state": "Open", "doc_status": "0", "allow_edit": "Projects User"},
				{"state": "In Progress", "doc_status": "0", "allow_edit": "Projects User"},
				{"state": "Completed", "doc_status": "0", "allow_edit": "Projects Manager"},
				{"state": "Cancelled", "doc_status": "0", "allow_edit": "Projects Manager"},
			],
			"transitions": [
				{"state": "Open", "action": "Start", "next_state": "In Progress",
				 "allowed": "Projects User"},
				{"state": "In Progress", "action": "Complete", "next_state": "Completed",
				 "allowed": "Projects Manager"},
				{"state": "Open", "action": "Cancel", "next_state": "Cancelled",
				 "allowed": "Projects Manager"},
				{"state": "In Progress", "action": "Cancel", "next_state": "Cancelled",
				 "allowed": "Projects Manager"},
			],
		}).insert(ignore_permissions=True)
		out.append("created:AKD Project Status")
	else:
		out.append("existing:AKD Project Status")

	# FR-PROJ-32/63 — Timesheet approval (Timesheet is submittable).
	if not frappe.db.exists("Workflow", "AKD Timesheet Approval"):
		frappe.get_doc({
			"doctype": "Workflow",
			"workflow_name": "AKD Timesheet Approval",
			"document_type": "Timesheet",
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"states": [
				{"state": "Draft", "doc_status": "0", "allow_edit": "Timesheet User"},
				{"state": "Pending Timesheet Approval", "doc_status": "0",
				 "allow_edit": "Timesheet User"},
				{"state": "Timesheet Approved", "doc_status": "1",
				 "allow_edit": "Projects Manager"},
				{"state": "Timesheet Rejected", "doc_status": "0",
				 "allow_edit": "Timesheet User"},
			],
			"transitions": [
				{"state": "Draft", "action": "Submit for Approval",
				 "next_state": "Pending Timesheet Approval", "allowed": "Timesheet User"},
				{"state": "Pending Timesheet Approval", "action": "Approve",
				 "next_state": "Timesheet Approved", "allowed": "Projects Manager"},
				{"state": "Pending Timesheet Approval", "action": "Reject",
				 "next_state": "Timesheet Rejected", "allowed": "Projects Manager"},
			],
		}).insert(ignore_permissions=True)
		out.append("created:AKD Timesheet Approval")
	else:
		out.append("existing:AKD Timesheet Approval")
	return out


def _ensure_reports() -> list[str]:
	out = []
	for name, (ref, query) in _REPORTS.items():
		sql = query.strip()
		roles = [{"role": r} for r in _REPORT_ROLES if frappe.db.exists("Role", r)]
		if frappe.db.exists("Report", name):
			doc = frappe.get_doc("Report", name)
			doc.report_type = "Query Report"
			doc.ref_doctype = ref
			doc.query = sql
			doc.set("roles", roles)
			doc.save(ignore_permissions=True)
			out.append(f"updated:{name}")
			continue
		frappe.get_doc({
			"doctype": "Report", "report_name": name, "ref_doctype": ref,
			"report_type": "Query Report", "is_standard": "No",
			"query": sql, "roles": roles,
		}).insert(ignore_permissions=True)
		out.append(f"created:{name}")
	return out


def apply_permissions() -> dict:
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
				update_permission_property(doctype, role, 0, ptype,
										   1 if letter in flags else 0, validate=False)
			applied.append(f"{role}:{flags}")
		out[doctype] = applied
	frappe.clear_cache()
	return out
