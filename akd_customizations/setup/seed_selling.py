"""
Test-data seeder for the Selling module — exercises the BRD Section 6 flow.

ALL RECORDS USE PREFIX "TEST-SELL-" SO THEY PURGE CLEANLY.
DO NOT RUN ON A PRODUCTION SITE WITH REAL TRANSACTIONS.

Entry points:
  seed_all()       — masters + 2 Quotations + 3 SOs (Draft / Pending Finance /
                     Approved) + 1 DN + 1 SI + 1 Customer Return + 2 Pricing
                     Rules. Reuses TEST-CUST-* customers from seed_data.py.
  purge()          — cancel + delete every TEST-SELL-* record.

What gets covered:
  FR-SELL-22/24      Quotation: competitor + lost reason fields
  FR-SELL-23         Quotation workflow positioned at "Pending Approval"
  FR-SELL-27         SO workflow positioned at "Pending Finance Review"
  FR-SELL-29         Customer PO ref on SO
  FR-SELL-37/39      Pricing Rule: volume discount + Buy X Get Y
  FR-SELL-36         Customer-group-level pricing
  FR-SELL-43         Rate consistency — Stop (enforced by Selling Settings)
  FR-SELL-65         Installation flag on SO + DN
  FR-SELL-68/70/72   Customer return + auto credit note + return reason

Usage:
  bench --site akd.com execute akd_customizations.setup.seed_selling.seed_all
  bench --site akd.com execute akd_customizations.setup.seed_selling.purge
"""

from datetime import date, timedelta

import frappe
from frappe.model.workflow import apply_workflow
from frappe.utils import flt

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"
STORES_WH = f"Stores - {ABBR}"


# ─────────────────────────────────────────────────────────────────────────────
# Master data (reuses TEST-CUST-* from setup/seed_data.py)
# ─────────────────────────────────────────────────────────────────────────────


SELLING_ITEMS = [
	{
		"item_code": "TEST-SELL-ITEM-HW-A",
		"item_name": "Edge Compute Box (TEST)",
		"item_group": "Products",
		"is_stock_item": 1,
		"standard_rate": 8_000.0,
	},
	{
		"item_code": "TEST-SELL-ITEM-CONSULT-DAY",
		"item_name": "Day-Rate Consulting (TEST)",
		"item_group": "Services",
		"is_stock_item": 0,
		"standard_rate": 7_500.0,
	},
]

PRICING_RULES = [
	{
		"title": "TEST-SELL-RULE-Volume-10pct",
		"apply_on": "Item Code",
		"items": ["TEST-SELL-ITEM-HW-A"],
		"price_or_product_discount": "Price",
		"min_qty": 10,
		"max_qty": 0,
		"discount_percentage": 10.0,
		"selling": 1,
		"valid_from": date(date.today().year, 1, 1),
	},
	{
		"title": "TEST-SELL-RULE-Government-5pct",
		"apply_on": "Item Group",
		"item_groups": ["Products", "Services"],
		"price_or_product_discount": "Price",
		"customer_group": "Government",
		"discount_percentage": 5.0,
		"selling": 1,
		"valid_from": date(date.today().year, 1, 1),
	},
]


# ─────────────────────────────────────────────────────────────────────────────
# Public entry points
# ─────────────────────────────────────────────────────────────────────────────


def seed_all() -> dict:
	report = {
		"items": _seed_items(),
		"opening_stock": _seed_opening_stock(),
		"pricing_rules": _seed_pricing_rules(),
		"quotations": _seed_quotations(),
		"sales_orders": _seed_sales_orders(),
		"delivery_note": _seed_delivery_note(),
		"sales_invoice": _seed_sales_invoice(),
		"customer_return": _seed_customer_return(),
	}
	frappe.db.commit()
	return report


def _seed_opening_stock() -> list[str]:
	"""Material Receipt — needed so DNs of TEST-SELL-ITEM-HW-A can submit."""
	today = date.today()
	stock_item = "TEST-SELL-ITEM-HW-A"
	if not frappe.db.exists("Item", stock_item):
		return ["skipped: stock item not seeded"]

	# Idempotency by remarks
	remarks = "TEST-SELL-SEED OPENING-STOCK-01"
	if frappe.db.exists("Stock Entry", {"remarks": remarks}):
		return [f"existing:{remarks}"]

	se = frappe.get_doc({
		"doctype": "Stock Entry",
		"stock_entry_type": "Material Receipt",
		"posting_date": today - timedelta(days=7),
		"company": COMPANY,
		"remarks": remarks,
		"items": [{
			"item_code": stock_item,
			"qty": 20,
			"uom": "Nos",
			"conversion_factor": 1.0,
			"stock_uom": "Nos",
			"basic_rate": 6_500.0,
			"t_warehouse": STORES_WH,
		}],
	})
	se.insert(ignore_permissions=True)
	se.submit()
	return [se.name]


def purge() -> dict:
	deleted: dict[str, list] = {}

	def _names(dt: str) -> list[str]:
		names = frappe.db.get_list(dt, filters={"name": ["like", "TEST-SELL-%"]}, pluck="name")
		if dt in ("Sales Invoice", "Stock Entry"):
			tagged = frappe.db.get_list(
				dt, filters={"remarks": ["like", "TEST-SELL-SEED%"]}, pluck="name",
			)
			names = list(set(names) | set(tagged))
		if dt in ("Quotation", "Sales Order", "Delivery Note"):
			tagged = frappe.db.get_list(
				dt, filters={"title": ["like", "TEST-SELL-SEED%"]}, pluck="name",
			)
			names = list(set(names) | set(tagged))
		if dt == "Pricing Rule":
			tagged = frappe.db.get_list(
				dt, filters={"title": ["like", "TEST-SELL-RULE-%"]}, pluck="name",
			)
			names = list(set(names) | set(tagged))
		return list(set(names))

	for dt in ("Sales Invoice", "Delivery Note", "Sales Order", "Quotation", "Pricing Rule"):
		for n in _names(dt):
			try:
				doc = frappe.get_doc(dt, n)
				if doc.docstatus == 1:
					doc.cancel()
					deleted.setdefault(f"{dt}:cancelled", []).append(n)
			except Exception as e:
				deleted.setdefault(f"{dt}:cancel-errors", []).append(f"{n}: {e}")

	for dt in ("Sales Invoice", "Delivery Note", "Sales Order", "Quotation",
			   "Stock Entry", "Pricing Rule", "Item"):
		for n in _names(dt):
			try:
				frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
				deleted.setdefault(dt, []).append(n)
			except Exception as e:
				deleted.setdefault(f"{dt}:errors", []).append(f"{n}: {e}")

	frappe.db.commit()
	return deleted


# ─────────────────────────────────────────────────────────────────────────────
# Masters
# ─────────────────────────────────────────────────────────────────────────────


def _seed_items() -> list[str]:
	created = []
	for i in SELLING_ITEMS:
		if frappe.db.exists("Item", i["item_code"]):
			created.append(f"existing:{i['item_code']}")
			continue
		doc = frappe.get_doc({
			"doctype": "Item",
			"item_code": i["item_code"],
			"item_name": i["item_name"],
			"item_group": i["item_group"],
			"is_stock_item": i["is_stock_item"],
			"is_sales_item": 1,
			"standard_rate": i["standard_rate"],
			"include_item_in_manufacturing": 0,
			"item_defaults": [{
				"company": COMPANY,
				"default_warehouse": STORES_WH if i["is_stock_item"] else None,
				"selling_cost_center": f"Sales - {ABBR}",
			}],
		})
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created


def _seed_pricing_rules() -> list[str]:
	created = []
	for r in PRICING_RULES:
		if frappe.db.exists("Pricing Rule", {"title": r["title"]}):
			created.append(f"existing:{r['title']}")
			continue
		payload = {
			"doctype": "Pricing Rule",
			"title": r["title"],
			"apply_on": r["apply_on"],
			"price_or_product_discount": r["price_or_product_discount"],
			"selling": r["selling"],
			"buying": 0,
			"min_qty": r.get("min_qty", 0),
			"max_qty": r.get("max_qty", 0),
			"discount_percentage": r["discount_percentage"],
			"valid_from": r["valid_from"],
			"rate_or_discount": "Discount Percentage",
		}
		if r.get("customer_group"):
			payload["applicable_for"] = "Customer Group"
			payload["customer_group"] = r["customer_group"]
		if r.get("items"):
			payload["items"] = [{"item_code": c} for c in r["items"]]
		if r.get("item_groups"):
			payload["item_groups"] = [{"item_group": g} for g in r["item_groups"]]

		doc = frappe.get_doc(payload)
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created


# ─────────────────────────────────────────────────────────────────────────────
# Transactions
# ─────────────────────────────────────────────────────────────────────────────


def _walk_workflow(doc, actions: list[str]) -> None:
	for action in actions:
		apply_workflow(doc, action)
		doc.reload()


def _customer_for(currency: str) -> str:
	"""Pick a TEST-CUST-* that's in the right currency. Seeded by seed_data."""
	if currency == "AED":
		return "TEST-CUST-001 ADNOC Test"
	return "TEST-CUST-002 First Bank Nigeria Test"


def _seed_quotations() -> list[str]:
	"""Q-01 Draft, Q-02 Pending Approval."""
	today = date.today()
	scenarios = [
		{
			"tag": "Q-01-Draft",
			"customer": _customer_for("AED"),
			"currency": "AED",
			"competitor": "VendorX",
			"items": [("TEST-SELL-ITEM-HW-A", 5, 8_000.0)],
			"transitions": [],
		},
		{
			"tag": "Q-02-PendingApproval",
			"customer": _customer_for("USD"),
			"currency": "USD",
			"competitor": "VendorY",
			"items": [("TEST-SELL-ITEM-CONSULT-DAY", 20, 2_100.0)],
			"transitions": ["Submit for Approval"],
		},
	]

	created = []
	for s in scenarios:
		title = f"TEST-SELL-SEED {s['tag']}"
		if frappe.db.exists("Quotation", {"title": title}):
			created.append(f"existing:{s['tag']}")
			continue
		qt = frappe.get_doc({
			"doctype": "Quotation",
			"quotation_to": "Customer",
			"party_name": s["customer"],
			"transaction_date": today,
			"valid_till": today + timedelta(days=30),
			"company": COMPANY,
			"currency": s["currency"],
			"conversion_rate": 3.6725 if s["currency"] == "USD" else 1.0,
			"selling_price_list": "Standard Selling",
			"title": title,
			"akd_competitor": s["competitor"],
			"items": [
				{
					"item_code": code,
					"qty": qty,
					"uom": "Nos",
					"conversion_factor": 1.0,
					"stock_uom": "Nos",
					"rate": rate,
				}
				for code, qty, rate in s["items"]
			],
		})
		qt.insert(ignore_permissions=True)
		_walk_workflow(qt, s["transitions"])
		created.append(qt.name)
	return created


def _seed_sales_orders() -> list[str]:
	"""SO-01 Draft, SO-02 Pending Finance Review, SO-03 Approved + submitted."""
	today = date.today()
	scenarios = [
		{
			"tag": "SO-01-Draft",
			"customer": _customer_for("AED"),
			"currency": "AED",
			"transitions": [],
			"items": [("TEST-SELL-ITEM-HW-A", 5, 8_000.0)],
			"delivery_offset": 14,
			"po_no": None,
			"installation": 0,
		},
		{
			"tag": "SO-02-PendingFinanceReview",
			"customer": _customer_for("USD"),
			"currency": "USD",
			"transitions": ["Submit for Approval", "Approve"],
			"items": [("TEST-SELL-ITEM-CONSULT-DAY", 20, 2_100.0)],
			"delivery_offset": 30,
			"po_no": "CUST-NG-2026-PO-001",
			"installation": 0,
		},
		{
			"tag": "SO-03-Approved",
			"customer": _customer_for("AED"),
			"currency": "AED",
			"transitions": ["Submit for Approval", "Approve", "Approve"],
			"items": [("TEST-SELL-ITEM-HW-A", 3, 8_000.0)],
			"delivery_offset": 7,
			"po_no": "CUST-UAE-2026-PO-042",
			"installation": 1,
		},
	]

	created = []
	for s in scenarios:
		title = f"TEST-SELL-SEED {s['tag']}"
		if frappe.db.exists("Sales Order", {"title": title}):
			created.append(f"existing:{s['tag']}")
			continue
		so = frappe.get_doc({
			"doctype": "Sales Order",
			"customer": s["customer"],
			"transaction_date": today,
			"delivery_date": today + timedelta(days=s["delivery_offset"]),
			"company": COMPANY,
			"currency": s["currency"],
			"conversion_rate": 3.6725 if s["currency"] == "USD" else 1.0,
			"selling_price_list": "Standard Selling",
			"title": title,
			"po_no": s["po_no"],
			"po_date": today if s["po_no"] else None,
			"akd_installation_required": s["installation"],
			"akd_dispatch_priority": "Urgent" if s["tag"] == "SO-03-Approved" else "Normal",
			"items": [
				{
					"item_code": code,
					"qty": qty,
					"uom": "Nos",
					"conversion_factor": 1.0,
					"stock_uom": "Nos",
					"rate": rate,
					"delivery_date": today + timedelta(days=s["delivery_offset"]),
					"warehouse": STORES_WH,
				}
				for code, qty, rate in s["items"]
			],
		})
		so.insert(ignore_permissions=True)
		_walk_workflow(so, s["transitions"])
		created.append(so.name)
	return created


def _seed_delivery_note() -> list[str]:
	"""DN against SO-03 (Approved + submitted)."""
	today = date.today()
	so_name = frappe.db.get_value("Sales Order",
		{"title": "TEST-SELL-SEED SO-03-Approved"}, "name")
	if not so_name:
		return ["skipped: SO-03 not found"]

	so = frappe.get_doc("Sales Order", so_name)
	if so.docstatus != 1:
		return [f"skipped: SO-03 not submitted (state={so.workflow_state})"]

	title = "TEST-SELL-SEED DN-01"
	if frappe.db.exists("Delivery Note", {"title": title}):
		return [f"existing:{title}"]

	dn = frappe.get_doc({
		"doctype": "Delivery Note",
		"customer": so.customer,
		"posting_date": today,
		"company": COMPANY,
		"currency": so.currency,
		"conversion_rate": so.conversion_rate,
		"title": title,
		"akd_gate_pass_no": "GP-2026-00012",
		"akd_installation_status": "Pending",
		"items": [
			{
				"item_code": "TEST-SELL-ITEM-HW-A",
				"qty": 3,
				"uom": "Nos",
				"conversion_factor": 1.0,
				"stock_uom": "Nos",
				"rate": 8_000.0,
				"warehouse": STORES_WH,
				"against_sales_order": so.name,
				"so_detail": so.items[0].name,
			},
		],
	})
	dn.insert(ignore_permissions=True)
	dn.submit()
	return [dn.name]


def _seed_sales_invoice() -> list[str]:
	"""SI against the DN — completes the SO→DN→SI chain."""
	today = date.today()
	dn_name = frappe.db.get_value("Delivery Note",
		{"title": "TEST-SELL-SEED DN-01"}, "name")
	if not dn_name:
		return ["skipped: DN-01 not found"]

	remarks = "TEST-SELL-SEED SI-01"
	if frappe.db.exists("Sales Invoice", {"remarks": remarks}):
		return [f"existing:{remarks}"]

	dn = frappe.get_doc("Delivery Note", dn_name)
	si = frappe.get_doc({
		"doctype": "Sales Invoice",
		"customer": dn.customer,
		"posting_date": today,
		"due_date": today + timedelta(days=30),
		"company": COMPANY,
		"currency": dn.currency,
		"conversion_rate": dn.conversion_rate,
		"remarks": remarks,
		"items": [
			{
				"item_code": "TEST-SELL-ITEM-HW-A",
				"qty": 3,
				"uom": "Nos",
				"conversion_factor": 1.0,
				"stock_uom": "Nos",
				"rate": 8_000.0,
				"sales_order": dn.items[0].against_sales_order,
				"delivery_note": dn.name,
				"dn_detail": dn.items[0].name,
				"income_account": _resolve_income_account(),
			},
		],
	})
	si.insert(ignore_permissions=True)
	si.submit()
	return [si.name]


def _seed_customer_return() -> list[str]:
	"""1 Customer Return DN + auto Credit Note for 1 of the 3 hardware units."""
	today = date.today()
	dn_src_name = frappe.db.get_value("Delivery Note",
		{"title": "TEST-SELL-SEED DN-01"}, "name")
	si_src_name = frappe.db.get_value("Sales Invoice",
		{"remarks": "TEST-SELL-SEED SI-01"}, "name")
	if not dn_src_name or not si_src_name:
		return ["skipped: source DN/SI not found"]

	results = []
	# Return Delivery Note
	dn_ret_title = "TEST-SELL-SEED DN-RET-01"
	if not frappe.db.exists("Delivery Note", {"title": dn_ret_title}):
		dn_src = frappe.get_doc("Delivery Note", dn_src_name)
		dn_ret = frappe.get_doc({
			"doctype": "Delivery Note",
			"customer": dn_src.customer,
			"posting_date": today,
			"company": COMPANY,
			"currency": dn_src.currency,
			"conversion_rate": dn_src.conversion_rate,
			"is_return": 1,
			"return_against": dn_src.name,
			"title": dn_ret_title,
			"akd_return_reason": "Damaged",
			"items": [{
				"item_code": "TEST-SELL-ITEM-HW-A",
				"qty": -1,
				"uom": "Nos",
				"conversion_factor": 1.0,
				"stock_uom": "Nos",
				"rate": 8_000.0,
				"warehouse": STORES_WH,
				"against_sales_order": dn_src.items[0].against_sales_order,
				"so_detail": dn_src.items[0].so_detail,
				"dn_detail": dn_src.items[0].name,
			}],
		})
		dn_ret.insert(ignore_permissions=True)
		dn_ret.submit()
		results.append(f"dn_return:{dn_ret.name}")

	# Credit Note (Sales Invoice with is_return)
	si_ret_remarks = "TEST-SELL-SEED SI-RET-01"
	if not frappe.db.exists("Sales Invoice", {"remarks": si_ret_remarks}):
		si_src = frappe.get_doc("Sales Invoice", si_src_name)
		ret = frappe.get_doc({
			"doctype": "Sales Invoice",
			"customer": si_src.customer,
			"posting_date": today,
			"company": COMPANY,
			"currency": "AED",
			"conversion_rate": 1.0,
			"is_return": 1,
			"return_against": si_src.name,
			"remarks": si_ret_remarks,
			"akd_return_reason": "Damaged",
			"items": [{
				"item_code": "TEST-SELL-ITEM-HW-A",
				"qty": -1,
				"uom": "Nos",
				"conversion_factor": 1.0,
				"stock_uom": "Nos",
				"rate": 8_000.0,
				"income_account": _resolve_income_account(),
			}],
		})
		ret.insert(ignore_permissions=True)
		ret.submit()
		results.append(f"si_credit_note:{ret.name}")

	return results


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _resolve_income_account() -> str:
	candidates = ["Sales Income", "Service Income", "Sales", "Direct Income"]
	for c in candidates:
		full = f"{c} - {ABBR}"
		if frappe.db.exists("Account", full) and not frappe.db.get_value("Account", full, "is_group"):
			return full
	acc = frappe.db.get_value(
		"Account",
		{"company": COMPANY, "is_group": 0, "root_type": "Income"},
		"name",
	)
	if not acc:
		frappe.throw("No leaf Income account found in CoA.")
	return acc
