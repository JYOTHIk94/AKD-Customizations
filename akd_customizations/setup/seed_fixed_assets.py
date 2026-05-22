"""
Test-data seeder for the Fixed Assets module — BRD Section 10 flow.

ALL RECORDS CARRY THE TAG "TEST-FA" SO THEY PURGE CLEANLY.
DO NOT RUN ON A PRODUCTION SITE WITH REAL ASSETS.

Entry points:
  seed_all()  — fixed-asset Item + 2 Assets (one plain, one pre-approved for
                disposal) under the IT Equipment category.
  purge()     — cancel + delete every TEST-FA record.

Covers:
  FR-FA-03/04  Asset Category (IT Equipment)
  FR-FA-21..26 Depreciable existing asset (quarterly, daily pro-rata)
  FR-FA-55     `akd_disposal_approved` flag on the second asset

Usage:
  bench --site akd.com execute akd_customizations.setup.seed_fixed_assets.seed_all
  bench --site akd.com execute akd_customizations.setup.seed_fixed_assets.purge
"""

from datetime import date

import frappe
from dateutil.relativedelta import relativedelta

from akd_customizations.setup import fixed_assets

COMPANY = "AKD Consulting LLC"
TAG = "TEST-FA"
CATEGORY = "IT Equipment"
LOCATION = f"{TAG} Location"
ITEM = f"{TAG}-ITEM-PC"


def seed_all() -> dict:
	fixed_assets.setup()  # reuse the real categories / accounts / settings
	report = {
		"location": _ensure_location(),
		"item": _ensure_item(),
	}
	report["asset_plain"] = _ensure_asset(f"{TAG} PC 01", approved=False)
	report["asset_approved"] = _ensure_asset(f"{TAG} PC 02", approved=True)
	frappe.db.commit()
	return report


def _ensure_location() -> str:
	if frappe.db.exists("Location", LOCATION):
		return f"existing:{LOCATION}"
	frappe.get_doc({"doctype": "Location", "location_name": LOCATION}) \
		.insert(ignore_permissions=True)
	return f"created:{LOCATION}"


def _ensure_item() -> str:
	if frappe.db.exists("Item", ITEM):
		return f"existing:{ITEM}"
	group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") \
		or "All Item Groups"
	frappe.get_doc({
		"doctype": "Item",
		"item_code": ITEM,
		"item_name": f"{TAG} Workstation PC",
		"item_group": group,
		"is_fixed_asset": 1,
		"is_stock_item": 0,
		"asset_category": CATEGORY,
	}).insert(ignore_permissions=True)
	return f"created:{ITEM}"


def _ensure_asset(asset_name: str, approved: bool) -> str:
	existing = frappe.db.get_value("Asset", {"asset_name": asset_name}, "name")
	if existing:
		return f"existing:{existing}"
	doc = frappe.get_doc({
		"doctype": "Asset",
		"asset_name": asset_name,
		"akd_asset_tag": asset_name,          # FR-FA-06/07 manual unique tag
		"item_code": ITEM,
		"asset_category": CATEGORY,
		"company": COMPANY,
		"location": LOCATION,
		"asset_type": "Existing Asset",
		"gross_purchase_amount": 6000,
		"net_purchase_amount": 6000,
		"asset_quantity": 1,
		"available_for_use_date": date.today() - relativedelta(years=1),
		"purchase_date": date.today() - relativedelta(years=1),
		"akd_disposal_approved": 1 if approved else 0,
		"akd_disposal_remarks": "Seed: pre-approved for disposal test"
			if approved else None,
	})
	doc.insert(ignore_permissions=True)
	return f"created:{doc.name} (disposal_approved={int(approved)})"


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

	_del("Asset", frappe.db.get_list(
		"Asset", filters={"asset_name": ["like", f"{TAG}%"]}, pluck="name"))
	_del("Item", frappe.db.get_list(
		"Item", filters={"item_code": ["like", f"{TAG}%"]}, pluck="name"))
	_del("Location", frappe.db.get_list(
		"Location", filters={"location_name": ["like", f"{TAG}%"]}, pluck="name"))
	frappe.db.commit()
	return deleted
