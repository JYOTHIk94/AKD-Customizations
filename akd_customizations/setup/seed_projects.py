"""
Test-data seeder for the Projects module — BRD §8 flow.

ALL RECORDS CARRY THE TAG "TEST-PROJ" SO THEY PURGE CLEANLY.
DO NOT RUN ON A PRODUCTION SITE WITH REAL PROJECTS.

seed_all() — Employee + Activity Cost + Project + 2 Tasks (milestone +
dependency, weighted) + a draft Timesheet (billable).
purge()    — cancel + delete every TEST-PROJ record.

Covers: FR-PROJ-06/18/22/28/31/38/48 plus the lite-HR footprint.

Usage:
  bench --site akd.com execute akd_customizations.setup.seed_projects.seed_all
  bench --site akd.com execute akd_customizations.setup.seed_projects.purge
"""

from datetime import date, datetime, timedelta

import frappe

from akd_customizations.setup import projects

COMPANY = "AKD Consulting LLC"
TAG = "TEST-PROJ"
EMP_NAME = f"{TAG} Tester"
PROJECT = f"{TAG} Alpha"


def seed_all() -> dict:
	projects.setup()  # reuse real masters / roles / workflows / permissions
	report = {
		"employee": _ensure_employee(),
		"activity_cost": _ensure_activity_cost(),
		"project": _ensure_project(),
	}
	report["tasks"] = _ensure_tasks()
	report["timesheet"] = _ensure_timesheet()
	frappe.db.commit()
	return report


def _ensure_employee() -> str:
	existing = frappe.db.get_value("Employee",
								   {"employee_name": EMP_NAME}, "name")
	if existing:
		return f"existing:{existing}"
	gender = "Male" if frappe.db.exists("Gender", "Male") else \
		frappe.db.get_value("Gender", {}, "name")
	doc = frappe.get_doc({
		"doctype": "Employee",
		"first_name": EMP_NAME,
		"company": COMPANY,
		"status": "Active",
		"gender": gender,
		"date_of_birth": date(1990, 1, 1),
		"date_of_joining": date(2025, 1, 1),
	}).insert(ignore_permissions=True)
	return f"created:{doc.name}"


def _ensure_activity_cost() -> str:
	emp = frappe.db.get_value("Employee", {"employee_name": EMP_NAME}, "name")
	if frappe.db.exists("Activity Cost",
						{"employee": emp, "activity_type": "Consulting"}):
		return "existing"
	frappe.get_doc({
		"doctype": "Activity Cost",
		"activity_type": "Consulting",
		"employee": emp,
		"costing_rate": 150,
		"billing_rate": 300,
	}).insert(ignore_permissions=True)
	return f"created:Consulting@{emp}"


def _ensure_project() -> str:
	existing = frappe.db.get_value("Project",
								   {"project_name": PROJECT}, "name")
	if existing:
		return f"existing:{existing}"
	emp_user = frappe.db.get_value(
		"Employee", {"employee_name": EMP_NAME}, "user_id")
	doc = frappe.get_doc({
		"doctype": "Project",
		"project_name": PROJECT,
		"project_type": "Advisory",
		"company": COMPANY,
		"status": "Open",
		"is_active": "Yes",
		"percent_complete_method": "Task Weight",
		"expected_start_date": date.today(),
		"expected_end_date": date.today() + timedelta(days=120),
		"estimated_costing": 50000,
		"users": [{"user": emp_user}] if emp_user else [],
	}).insert(ignore_permissions=True)
	return f"created:{doc.name}"


def _ensure_tasks() -> list[str]:
	project = frappe.db.get_value("Project", {"project_name": PROJECT}, "name")
	today = date.today()
	out = []
	a = frappe.db.get_value("Task", {"subject": f"{TAG} Discovery"}, "name")
	if not a:
		a = frappe.get_doc({
			"doctype": "Task", "subject": f"{TAG} Discovery",
			"project": project, "status": "Open", "priority": "High",
			"task_weight": 0.4, "type": "Analysis",
			"exp_start_date": today,
			"exp_end_date": today + timedelta(days=30),
		}).insert(ignore_permissions=True).name
		out.append(f"created:{a}")
	else:
		out.append(f"existing:{a}")

	b = frappe.db.get_value("Task", {"subject": f"{TAG} Go-Live"}, "name")
	if not b:
		b = frappe.get_doc({
			"doctype": "Task", "subject": f"{TAG} Go-Live",
			"project": project, "status": "Open", "priority": "Medium",
			"task_weight": 0.6, "is_milestone": 1, "type": "Deployment",
			"exp_start_date": today + timedelta(days=31),
			"exp_end_date": today + timedelta(days=120),
			"depends_on": [{"task": a}],
		}).insert(ignore_permissions=True).name
		out.append(f"created:{b} (milestone, depends on Discovery)")
	else:
		out.append(f"existing:{b}")

	# ERPNext zeroes task_weight at insert when the project has no weighted
	# tasks yet — force it post-insert so weighted % progress (FR-PROJ-22/23)
	# is demonstrable, then recompute the project.
	frappe.db.set_value("Task", a, "task_weight", 0.4)
	frappe.db.set_value("Task", b, "task_weight", 0.6)
	prj = frappe.get_doc("Project", project)
	prj.flags.ignore_permissions = True
	prj.save()  # Project.validate recomputes percent_complete from task weights
	return out


def _ensure_timesheet() -> str:
	emp = frappe.db.get_value("Employee", {"employee_name": EMP_NAME}, "name")
	project = frappe.db.get_value("Project", {"project_name": PROJECT}, "name")
	if frappe.db.exists("Timesheet", {"employee": emp, "parent_project": project}):
		return "existing"
	start = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=9)
	doc = frappe.get_doc({
		"doctype": "Timesheet",
		"company": COMPANY,
		"employee": emp,
		"time_logs": [{
			"activity_type": "Consulting",
			"from_time": start,
			"to_time": start + timedelta(hours=4),
			"hours": 4,
			"project": project,
			"is_billable": 1,
			"billing_hours": 4,
		}],
	}).insert(ignore_permissions=True)
	return f"created:{doc.name} (draft, 4 billable hrs)"


def purge() -> dict:
	deleted: dict[str, list] = {}

	def _del(dt: str, names) -> None:
		for n in set(names):
			try:
				d = frappe.get_doc(dt, n)
				if d.docstatus == 1:
					d.cancel()
				frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
				deleted.setdefault(dt, []).append(n)
			except Exception as e:
				deleted.setdefault(f"{dt}:errors", []).append(f"{n}: {e}")

	emp = frappe.db.get_value("Employee", {"employee_name": EMP_NAME}, "name")
	_del("Timesheet", frappe.db.get_list(
		"Timesheet", filters={"employee": emp}, pluck="name") if emp else [])
	_del("Task", frappe.db.get_list(
		"Task", filters={"subject": ["like", f"{TAG}%"]}, pluck="name"))
	_del("Project", frappe.db.get_list(
		"Project", filters={"project_name": ["like", f"{TAG}%"]}, pluck="name"))
	if emp:
		_del("Activity Cost", frappe.db.get_list(
			"Activity Cost", filters={"employee": emp}, pluck="name"))
		_del("Employee", [emp])
	frappe.db.commit()
	return deleted
