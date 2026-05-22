"""
Test-data seeder for the CRM module — exercises the BRD Section 7 flow.

ALL RECORDS CARRY THE TAG "TEST-CRM" SO THEY PURGE CLEANLY.
DO NOT RUN ON A PRODUCTION SITE WITH REAL CRM DATA.

Entry points:
  seed_all()  — UTM Source + Campaign + Opportunity Type + Lost Reason +
                Prospect + Lead + Opportunity (from the Lead), fully linked.
  purge()     — delete every TEST-CRM record.

What gets covered:
  FR-CRM-06   Lead with utm_source
  FR-CRM-09   Lead enters the round-robin Assignment Rule scope
  FR-CRM-19   Opportunity Lost Reason master
  FR-CRM-20   Opportunity Type (pipeline)
  FR-CRM-21   Prospect (organisation) distinct from Lead
  FR-CRM-25   Opportunity ready to flip to "Converted" → Customer hook
  FR-CRM-30   Campaign (header only)

Usage:
  bench --site akd.com execute akd_customizations.setup.seed_crm.seed_all
  bench --site akd.com execute akd_customizations.setup.seed_crm.purge
"""

import frappe

from akd_customizations.setup import crm

COMPANY = "AKD Consulting LLC"
TAG = "TEST-CRM"

UTM_SOURCE = f"{TAG} Source"
OPP_TYPE = f"{TAG} Type"
LOST_REASON = f"{TAG} Lost"
CAMPAIGN = f"{TAG} Campaign"
PROSPECT = f"{TAG} Prospect Co"


def seed_all() -> dict:
	crm.setup()  # reuse the real masters / roles / permissions

	report = {
		"utm_source": _ensure_simple("UTM Source", UTM_SOURCE, prompt=True),
		"opportunity_type": _ensure_simple("Opportunity Type", OPP_TYPE, prompt=True),
		"lost_reason": _ensure_lost_reason(),
		"campaign": _ensure_campaign(),
		"prospect": _ensure_prospect(),
	}
	report["lead"] = _ensure_lead()
	report["opportunity"] = _ensure_opportunity(report["lead"])
	frappe.db.commit()
	return report


def _ensure_simple(doctype: str, name: str, prompt: bool) -> str:
	if frappe.db.exists(doctype, name):
		return f"existing:{name}"
	doc = frappe.new_doc(doctype)
	if prompt:
		doc.name = name
	doc.insert(ignore_permissions=True)
	return f"created:{name}"


def _ensure_lost_reason() -> str:
	if frappe.db.exists("Opportunity Lost Reason", LOST_REASON):
		return f"existing:{LOST_REASON}"
	frappe.get_doc({
		"doctype": "Opportunity Lost Reason", "lost_reason": LOST_REASON,
	}).insert(ignore_permissions=True)
	return f"created:{LOST_REASON}"


def _ensure_campaign() -> str:
	if frappe.db.exists("Campaign", {"campaign_name": CAMPAIGN}):
		return f"existing:{CAMPAIGN}"
	doc = frappe.get_doc({
		"doctype": "Campaign", "campaign_name": CAMPAIGN,
	}).insert(ignore_permissions=True)
	return f"created:{doc.name}"


def _ensure_prospect() -> str:
	if frappe.db.exists("Prospect", PROSPECT):
		return f"existing:{PROSPECT}"
	frappe.get_doc({
		"doctype": "Prospect",
		"company_name": PROSPECT,
		"company": COMPANY,
		"no_of_employees": "11-50",
	}).insert(ignore_permissions=True)
	return f"created:{PROSPECT}"


def _ensure_lead() -> str:
	existing = frappe.db.get_value(
		"Lead", {"company_name": ["like", f"{TAG}%"]}, "name"
	)
	if existing:
		return f"existing:{existing}"
	doc = frappe.get_doc({
		"doctype": "Lead",
		"lead_name": f"{TAG} Jane Prospect",
		"company_name": f"{TAG} Org",
		"email_id": "jane.testcrm@example.com",
		"status": "Lead",
		"utm_source": UTM_SOURCE,
		"company": COMPANY,
	}).insert(ignore_permissions=True)
	return f"created:{doc.name}"


def _ensure_opportunity(lead_ref: str) -> str:
	lead = lead_ref.split(":", 1)[1]
	existing = frappe.db.get_value(
		"Opportunity", {"party_name": lead}, "name"
	)
	if existing:
		return f"existing:{existing}"
	doc = frappe.get_doc({
		"doctype": "Opportunity",
		"opportunity_from": "Lead",
		"party_name": lead,
		"opportunity_type": OPP_TYPE,
		"status": "Open",
		"company": COMPANY,
		"opportunity_amount": 25000,
		"probability": 40,
	}).insert(ignore_permissions=True)
	return f"created:{doc.name}"


def purge() -> dict:
	deleted: dict[str, list] = {}

	def _del(dt: str, names) -> None:
		for n in set(names):
			try:
				frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
				deleted.setdefault(dt, []).append(n)
			except Exception as e:
				deleted.setdefault(f"{dt}:errors", []).append(f"{n}: {e}")

	# Children of the chain first.
	_del("Opportunity", frappe.db.get_list(
		"Opportunity",
		filters={"customer_name": ["like", f"{TAG}%"]}, pluck="name",
	) + frappe.db.get_list(
		"Opportunity",
		filters={"party_name": ["like", f"{TAG}%"]}, pluck="name",
	))
	# Customer auto-created by the FR-CRM-25 won-deal hook.
	_del("Customer", frappe.db.get_list(
		"Customer", filters={"customer_name": ["like", f"{TAG}%"]}, pluck="name",
	))
	_del("Lead", frappe.db.get_list(
		"Lead", filters={"company_name": ["like", f"{TAG}%"]}, pluck="name",
	))
	_del("Prospect", frappe.db.get_list(
		"Prospect", filters={"name": ["like", f"{TAG}%"]}, pluck="name",
	))
	_del("Campaign", frappe.db.get_list(
		"Campaign", filters={"campaign_name": ["like", f"{TAG}%"]}, pluck="name",
	))
	_del("Opportunity Type", frappe.db.get_list(
		"Opportunity Type", filters={"name": ["like", f"{TAG}%"]}, pluck="name",
	))
	_del("Opportunity Lost Reason", frappe.db.get_list(
		"Opportunity Lost Reason",
		filters={"name": ["like", f"{TAG}%"]}, pluck="name",
	))
	_del("UTM Source", frappe.db.get_list(
		"UTM Source", filters={"name": ["like", f"{TAG}%"]}, pluck="name",
	))

	frappe.db.commit()
	return deleted
