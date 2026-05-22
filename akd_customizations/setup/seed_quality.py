"""
Test-data seeder for the Quality module — exercises the BRD Section 9 flow.

ALL RECORDS CARRY THE TAG "TEST-QA-SEED" SO THEY PURGE CLEANLY.
DO NOT RUN ON A PRODUCTION SITE WITH REAL QUALITY RECORDS.

Entry points:
  seed_all()  — 1 Quality Procedure + 1 Non-Conformance + 1 CAPA (Quality
                Action) + 1 Quality Review, fully linked.
  purge()     — cancel + delete every TEST-QA-SEED record.

What gets covered:
  FR-QA-25/33  Quality Procedure + NC linked to it
  FR-QA-31/32  Non-Conformance with trigger (akd_nc_trigger)
  FR-QA-34/35/36  CAPA (Quality Action) with resolution + deadline + status
  FR-QA-37     CAPA linked to the Quality Review
  FR-QA-50     CAPA linked to a Supplier (akd_supplier)
  FR-QA-26/30  Quality Review with status
  FR-QA-48/12  Incoming Quality Inspection (Accepted, Pass/Fail template)
               against the TEST-BUY Purchase Receipt

The end-to-end "QI mandatory before stock acceptance" enforcement (FR-QA-14,
C-09) is exercised via setup/seed_buying.py + quality.enable_inspection_on_items
on real items — the QI seeded here is a ready-made sample for inspection.

Usage:
  bench --site akd.com execute akd_customizations.setup.seed_quality.seed_all
  bench --site akd.com execute akd_customizations.setup.seed_quality.purge
"""

from datetime import date, timedelta

import frappe

from akd_customizations.setup import quality

TAG = "TEST-QA-SEED"
PROCEDURE = f"TEST-QA-PROC {TAG}"


def seed_all() -> dict:
	# Reuse the real setup masters (roles / parameter / template / procedures).
	quality.setup()

	report = {
		"procedure": _seed_procedure(),
		"non_conformance": _seed_non_conformance(),
	}
	report["quality_review"] = _seed_quality_review()
	report["quality_action"] = _seed_quality_action(
		nc=report["non_conformance"], review=report["quality_review"]
	)
	report["quality_inspection"] = _seed_quality_inspection()
	frappe.db.commit()
	return report


def _seed_quality_inspection() -> str:
	"""FR-QA-48/12 — Incoming Quality Inspection against the TEST-BUY Purchase
	Receipt (left in Draft as an inspectable sample). Skips cleanly if the
	Buying seed has not been loaded."""
	existing = frappe.db.get_value(
		"Quality Inspection", {"remarks": ["like", f"%{TAG}%"]}, "name"
	)
	if existing:
		return f"existing:{existing}"

	pr = frappe.db.get_value(
		"Purchase Receipt",
		{"remarks": ["like", "%TEST-BUY%"], "docstatus": 1},
		"name",
	)
	if not pr:
		return "skipped: no TEST-BUY Purchase Receipt — run seed_buying.seed_all first"

	pr_doc = frappe.get_doc("Purchase Receipt", pr)
	item_code = pr_doc.items[0].item_code

	# ERPNext blocks a QI on an item that doesn't require inspection
	# (FR-QA-48/14). Turn it on for this one item before inspecting.
	quality.enable_inspection_on_items({"name": item_code})

	doc = frappe.get_doc({
		"doctype": "Quality Inspection",
		"inspection_type": "Incoming",
		"reference_type": "Purchase Receipt",
		"reference_name": pr,
		"item_code": item_code,
		"sample_size": 1,
		"report_date": date.today(),
		"inspected_by": "Administrator",
		"quality_inspection_template": quality.TEMPLATE,
		"status": "Accepted",
		"remarks": f"Incoming QI sample (Draft). Tag: {TAG}",
		"readings": [{
			"specification": quality.PARAMETER,
			"status": "Accepted",
			"numeric": 0,
		}],
	}).insert(ignore_permissions=True)
	return f"created:{doc.name}"


def _seed_procedure() -> str:
	if frappe.db.exists("Quality Procedure", PROCEDURE):
		return f"existing:{PROCEDURE}"
	frappe.get_doc({
		"doctype": "Quality Procedure",
		"quality_procedure_name": PROCEDURE,
		"is_group": 0,
	}).insert(ignore_permissions=True)
	return f"created:{PROCEDURE}"


def _seed_non_conformance() -> str:
	existing = frappe.db.get_value(
		"Non Conformance", {"subject": ["like", f"%{TAG}%"]}, "name"
	)
	if existing:
		return f"existing:{existing}"
	doc = frappe.get_doc({
		"doctype": "Non Conformance",
		"subject": f"Delivable rework needed — {TAG}",
		"procedure": PROCEDURE,
		"status": "Open",
		"details": f"Seeded non-conformance for UAT. Tag: {TAG}",
		"akd_nc_trigger": "Process Deviation",
	}).insert(ignore_permissions=True)
	return f"created:{doc.name}"


def _seed_quality_review() -> str:
	existing = frappe.db.get_value(
		"Quality Review", {"additional_information": ["like", f"%{TAG}%"]}, "name"
	)
	if existing:
		return f"existing:{existing}"
	doc = frappe.get_doc({
		"doctype": "Quality Review",
		"date": date.today(),
		"procedure": PROCEDURE,
		"goal": quality.GOAL,
		"status": "Open",
		"additional_information": f"Monthly review (seed). Tag: {TAG}",
	}).insert(ignore_permissions=True)
	return f"created:{doc.name}"


def _seed_quality_action(nc: str, review: str) -> str:
	existing = frappe.db.get_value(
		"Quality Action",
		{"resolutions.problem": ["like", f"%{TAG}%"]},
		"name",
	)
	if existing:
		return f"existing:{existing}"

	supplier = frappe.db.get_value(
		"Supplier", {"name": ["like", "TEST-BUY-SUPP-001%"]}, "name"
	)
	review_name = review.split(":", 1)[1]

	doc = frappe.get_doc({
		"doctype": "Quality Action",
		"corrective_preventive": "Corrective",
		"date": date.today(),
		"procedure": PROCEDURE,
		"status": "Open",
		"review": review_name,
		"akd_supplier": supplier,
		"resolutions": [{
			"problem": f"Repeated minor defect on deliverable. Tag: {TAG}",
			"resolution": "Add peer-review checkpoint before dispatch.",
			"status": "Open",
			"completion_by": date.today() + timedelta(days=14),
		}],
	}).insert(ignore_permissions=True)
	return f"created:{doc.name}"


def purge() -> dict:
	deleted: dict[str, list] = {}

	def _del(dt: str, names: list[str]) -> None:
		for n in set(names):
			try:
				doc = frappe.get_doc(dt, n)
				if doc.docstatus == 1:
					doc.cancel()
				frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
				deleted.setdefault(dt, []).append(n)
			except Exception as e:
				deleted.setdefault(f"{dt}:errors", []).append(f"{n}: {e}")

	# Children first.
	_del("Quality Inspection", frappe.db.get_list(
		"Quality Inspection",
		filters={"remarks": ["like", f"%{TAG}%"]}, pluck="name",
	))
	_del("Quality Action", frappe.db.get_list(
		"Quality Action",
		filters={"resolutions.problem": ["like", f"%{TAG}%"]}, pluck="name",
	))
	_del("Quality Review", frappe.db.get_list(
		"Quality Review",
		filters={"additional_information": ["like", f"%{TAG}%"]}, pluck="name",
	))
	_del("Non Conformance", frappe.db.get_list(
		"Non Conformance",
		filters={"subject": ["like", f"%{TAG}%"]}, pluck="name",
	))
	_del("Quality Procedure", frappe.db.get_list(
		"Quality Procedure",
		filters={"quality_procedure_name": ["like", f"%{TAG}%"]}, pluck="name",
	))

	frappe.db.commit()
	return deleted
