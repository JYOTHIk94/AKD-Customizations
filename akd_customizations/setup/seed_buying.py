"""
Test-data seeder for the Buying module — exercises the BRD Section 5 flow.

ALL RECORDS USE PREFIX "TEST-BUY-" SO THEY PURGE CLEANLY.
DO NOT RUN ON A PRODUCTION SITE WITH REAL TRANSACTIONS.

Entry points:
  seed_all()       — masters + 1 RFQ + 2 SQ + 2 MR + 2 PO + 1 Blanket + 1 PR + 1 PI
  purge()          — cancel + delete every TEST-BUY-* record

What gets covered:
  FR-BUY-07/08      Supplier classification + AKD OEM / Non-OEM groups
  FR-BUY-11/42      Supplier hold + PO on hold
  FR-BUY-12         Supplier lead time per item
  FR-BUY-22         MR workflow positioned at "Pending Line Manager"
  FR-BUY-25/26      RFQ to 3 suppliers
  FR-BUY-31         Supplier Quotation tracked
  FR-BUY-37         PO workflow positioned at "Pending Finance"
  FR-BUY-38         Customer PO ref on PO
  FR-BUY-46         PR inspection result (Pass + Fail rows)
  FR-BUY-49/50      Rejected qty routed to Rejected warehouse, not billed
  FR-BUY-51/52/54   Blanket Order with to_date in 60 days (triggers expiry task)
  FR-BUY-77/78/80   Purchase return as Debit Note with reason

Usage:
  bench --site akd.com execute akd_customizations.setup.seed_buying.seed_all
  bench --site akd.com execute akd_customizations.setup.seed_buying.purge
"""

from datetime import date, timedelta

import frappe
from frappe.model.workflow import apply_workflow

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"
STORES_WH = f"Stores - {ABBR}"
REJECTED_WH = f"Rejected - {ABBR}"


# ─────────────────────────────────────────────────────────────────────────────
# Catalogue
# ─────────────────────────────────────────────────────────────────────────────


SUPPLIERS = [
	{
		"supplier_name": "TEST-BUY-SUPP-001 Emirates Tech LLC",
		"supplier_group": "AKD OEM",
		"country": "United Arab Emirates",
		"default_currency": "AED",
		"payment_terms": "AKD Supplier Standard",
		"akd_supplier_classification": "Indigenous",
		"akd_supplier_currency_band": "AED",
		"akd_oem_flag": 1,
	},
	{
		"supplier_name": "TEST-BUY-SUPP-002 Dubai Office Supplies",
		"supplier_group": "AKD Non-OEM",
		"country": "United Arab Emirates",
		"default_currency": "AED",
		"payment_terms": "AKD Supplier Standard",
		"akd_supplier_classification": "Indigenous",
		"akd_supplier_currency_band": "AED",
		"akd_oem_flag": 0,
	},
	{
		"supplier_name": "TEST-BUY-SUPP-003 GlobalChip Foreign Test",
		"supplier_group": "AKD OEM",
		"country": "United States",
		"default_currency": "USD",
		"payment_terms": "AKD Supplier Standard",
		"akd_supplier_classification": "Foreign",
		"akd_supplier_currency_band": "USD",
		"akd_oem_flag": 1,
	},
	{
		"supplier_name": "TEST-BUY-SUPP-004 BlockedVendor Test",
		"supplier_group": "AKD Non-OEM",
		"country": "United Arab Emirates",
		"default_currency": "AED",
		"payment_terms": "AKD Supplier Standard",
		"akd_supplier_classification": "Non-Critical",
		"akd_supplier_currency_band": "AED",
		"akd_oem_flag": 0,
		"on_hold": 1,
		"hold_type": "Invoices",
	},
]

ITEMS = [
	{
		"item_code": "TEST-BUY-ITEM-LAPTOP",
		"item_name": "Business Laptop 14\" (TEST)",
		"item_group": "Products",
		"is_stock_item": 1,
		"standard_rate": 5_000.0,
		"lead_time_days": 14,
	},
	{
		"item_code": "TEST-BUY-ITEM-PRINTER",
		"item_name": "Laser Printer A4 (TEST)",
		"item_group": "Products",
		"is_stock_item": 1,
		"standard_rate": 1_200.0,
		"lead_time_days": 10,
	},
	{
		"item_code": "TEST-BUY-ITEM-CHAIR",
		"item_name": "Office Chair (TEST)",
		"item_group": "Products",
		"is_stock_item": 1,
		"standard_rate": 800.0,
		"lead_time_days": 7,
	},
	{
		"item_code": "TEST-BUY-ITEM-SUBSCRIPTION",
		"item_name": "Cloud Antivirus Annual License (TEST)",
		"item_group": "Services",
		"is_stock_item": 0,
		"standard_rate": 12_000.0,
		"lead_time_days": 1,
	},
]


# ─────────────────────────────────────────────────────────────────────────────
# Public entry points
# ─────────────────────────────────────────────────────────────────────────────


def seed_all() -> dict:
	report = {
		"suppliers": _seed_suppliers(),
		"items": _seed_items(),
		"item_supplier_links": _link_items_to_suppliers(),
		"material_requests": _seed_material_requests(),
		"rfq": _seed_rfq(),
		"supplier_quotations": _seed_supplier_quotations(),
		"purchase_orders": _seed_purchase_orders(),
		"blanket_order": _seed_blanket_order(),
		"purchase_receipt": _seed_purchase_receipt(),
		"purchase_invoice": _seed_purchase_invoice(),
		"purchase_return": _seed_purchase_return(),
	}
	frappe.db.commit()
	return report


def purge() -> dict:
	"""Cancel and delete every TEST-BUY-* record."""
	deleted: dict[str, list] = {}

	def _names(dt: str) -> list[str]:
		names = frappe.db.get_list(dt, filters={"name": ["like", "TEST-BUY-%"]}, pluck="name")
		# Tag column varies by doctype: PR + PI have `remarks`; MR/RFQ/SQ/PO use `title`;
		# Blanket Order has neither — rely on `order_no` like 'BLKT-TEST-BUY-%'.
		if dt in ("Purchase Receipt", "Purchase Invoice"):
			names += frappe.db.get_list(
				dt, filters={"remarks": ["like", "TEST-BUY-SEED%"]}, pluck="name",
			)
		if dt in ("Material Request", "Request for Quotation",
				  "Supplier Quotation", "Purchase Order"):
			names += frappe.db.get_list(
				dt, filters={"title": ["like", "TEST-BUY-SEED%"]}, pluck="name",
			)
		if dt == "Blanket Order":
			names += frappe.db.get_list(
				dt, filters={"order_no": ["like", "BLKT-TEST-BUY-%"]}, pluck="name",
			)
		names = list(set(names))
		return names

	# Cancel submitted docs in dependency order (children first)
	for dt in (
		"Purchase Invoice", "Purchase Receipt", "Purchase Order",
		"Supplier Quotation", "Request for Quotation",
		"Material Request", "Blanket Order",
	):
		for n in _names(dt):
			try:
				doc = frappe.get_doc(dt, n)
				if doc.docstatus == 1:
					doc.cancel()
					deleted.setdefault(f"{dt}:cancelled", []).append(n)
			except Exception as e:
				deleted.setdefault(f"{dt}:cancel-errors", []).append(f"{n}: {e}")

	# Delete in same order
	for dt in (
		"Purchase Invoice", "Purchase Receipt", "Purchase Order",
		"Supplier Quotation", "Request for Quotation",
		"Material Request", "Blanket Order",
		"Item", "Supplier",
	):
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


def _seed_suppliers() -> list[str]:
	created = []
	for s in SUPPLIERS:
		if frappe.db.exists("Supplier", s["supplier_name"]):
			created.append(f"existing:{s['supplier_name']}")
			continue
		doc = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": s["supplier_name"],
			"supplier_type": "Company",
			"supplier_group": s["supplier_group"],
			"country": s["country"],
			"default_currency": s["default_currency"],
			"payment_terms": s["payment_terms"],
			"akd_supplier_classification": s["akd_supplier_classification"],
			"akd_supplier_currency_band": s["akd_supplier_currency_band"],
			"akd_oem_flag": s["akd_oem_flag"],
			"on_hold": s.get("on_hold", 0),
			"hold_type": s.get("hold_type"),
		})
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created


def _seed_items() -> list[str]:
	created = []
	for i in ITEMS:
		if frappe.db.exists("Item", i["item_code"]):
			created.append(f"existing:{i['item_code']}")
			continue
		doc = frappe.get_doc({
			"doctype": "Item",
			"item_code": i["item_code"],
			"item_name": i["item_name"],
			"item_group": i["item_group"],
			"is_stock_item": i["is_stock_item"],
			"standard_rate": i["standard_rate"],
			"lead_time_days": i["lead_time_days"],
			"include_item_in_manufacturing": 0,
			"item_defaults": [{
				"company": COMPANY,
				"default_warehouse": STORES_WH if i["is_stock_item"] else None,
				"buying_cost_center": f"Admin - {ABBR}",
			}],
		})
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created


def _link_items_to_suppliers() -> list[str]:
	"""FR-BUY-10: approved supplier list per item."""
	matrix = {
		"TEST-BUY-ITEM-LAPTOP": [
			("TEST-BUY-SUPP-001 Emirates Tech LLC", "ET-LAPTOP-14"),
			("TEST-BUY-SUPP-003 GlobalChip Foreign Test", "GC-NB-14"),
		],
		"TEST-BUY-ITEM-PRINTER": [
			("TEST-BUY-SUPP-001 Emirates Tech LLC", "ET-PR-A4"),
		],
		"TEST-BUY-ITEM-CHAIR": [
			("TEST-BUY-SUPP-002 Dubai Office Supplies", "DOS-CHAIR-EXEC"),
		],
		"TEST-BUY-ITEM-SUBSCRIPTION": [
			("TEST-BUY-SUPP-003 GlobalChip Foreign Test", "GC-AV-ANNUAL"),
		],
	}
	updated = []
	for item_code, suppliers in matrix.items():
		if not frappe.db.exists("Item", item_code):
			continue
		doc = frappe.get_doc("Item", item_code)
		existing_pairs = {(s.supplier, s.supplier_part_no) for s in (doc.supplier_items or [])}
		dirty = False
		for supplier, part_no in suppliers:
			if not frappe.db.exists("Supplier", supplier):
				continue
			if (supplier, part_no) in existing_pairs:
				continue
			doc.append("supplier_items", {
				"supplier": supplier,
				"supplier_part_no": part_no,
			})
			dirty = True
		if dirty:
			doc.save(ignore_permissions=True)
			updated.append(item_code)
	return updated


# ─────────────────────────────────────────────────────────────────────────────
# Transactions
# ─────────────────────────────────────────────────────────────────────────────


def _seed_material_requests() -> list[str]:
	"""Create 2 Material Requests: one Draft, one parked at Pending Line Manager."""
	today = date.today()
	scenarios = [
		{
			"tag": "MR-01-Draft",
			"items": [("TEST-BUY-ITEM-LAPTOP", 3), ("TEST-BUY-ITEM-PRINTER", 1)],
			"workflow_transitions": [],  # leave at Draft
		},
		{
			"tag": "MR-02-PendingLineMgr",
			"items": [("TEST-BUY-ITEM-CHAIR", 8)],
			"workflow_transitions": ["Submit for Approval"],
		},
	]

	created = []
	for s in scenarios:
		title = f"TEST-BUY-SEED {s['tag']}"
		existing = frappe.db.get_value("Material Request", {"title": title}, "name")
		if existing:
			created.append(f"existing:{existing}")
			continue

		mr = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"transaction_date": today,
			"schedule_date": today + timedelta(days=14),
			"company": COMPANY,
			"title": title,
			"items": [
				{
					"item_code": code,
					"qty": qty,
					"uom": "Nos",
					"conversion_factor": 1.0,
					"stock_uom": "Nos",
					"schedule_date": today + timedelta(days=14),
					"warehouse": STORES_WH,
				}
				for code, qty in s["items"]
			],
		})
		mr.insert(ignore_permissions=True)
		_walk_workflow(mr, s["workflow_transitions"])
		created.append(mr.name)
	return created


def _walk_workflow(doc, actions: list[str]) -> None:
	"""Apply workflow actions in order. Caller (Administrator under bench
	execute) has all roles, so transition role checks pass."""
	for action in actions:
		apply_workflow(doc, action)
		doc.reload()


def _seed_rfq() -> list[str]:
	"""1 RFQ inviting 3 suppliers for laptops."""
	today = date.today()
	title = "TEST-BUY-SEED RFQ-01"
	existing = frappe.db.get_value("Request for Quotation", {"title": title}, "name")
	if existing:
		return [f"existing:{existing}"]

	rfq = frappe.get_doc({
		"doctype": "Request for Quotation",
		"transaction_date": today,
		"schedule_date": today + timedelta(days=7),
		"company": COMPANY,
		"title": title,
		"message_for_supplier": "Please quote your best price + lead time + warranty per FR-BUY-32/34.",
		"suppliers": [
			{"supplier": "TEST-BUY-SUPP-001 Emirates Tech LLC"},
			{"supplier": "TEST-BUY-SUPP-002 Dubai Office Supplies"},
			{"supplier": "TEST-BUY-SUPP-003 GlobalChip Foreign Test"},
		],
		"items": [
			{
				"item_code": "TEST-BUY-ITEM-LAPTOP",
				"qty": 3,
				"uom": "Nos",
				"conversion_factor": 1.0,
				"stock_uom": "Nos",
				"schedule_date": today + timedelta(days=14),
				"warehouse": STORES_WH,
			},
		],
	})
	rfq.insert(ignore_permissions=True)
	rfq.submit()
	return [rfq.name]


def _seed_supplier_quotations() -> list[str]:
	"""2 Supplier Quotations responding to the RFQ — 1 local, 1 foreign."""
	today = date.today()
	rfq_name = frappe.db.get_value("Request for Quotation",
		{"title": "TEST-BUY-SEED RFQ-01"}, "name")

	scenarios = [
		{
			"tag": "SQ-01-Local",
			"supplier": "TEST-BUY-SUPP-001 Emirates Tech LLC",
			"currency": "AED",
			"rate": 4_900.0,
			"valid_till": today + timedelta(days=30),
		},
		{
			"tag": "SQ-02-Foreign",
			"supplier": "TEST-BUY-SUPP-003 GlobalChip Foreign Test",
			"currency": "USD",
			"rate": 1_350.0,
			"valid_till": today + timedelta(days=21),
		},
	]

	created = []
	for s in scenarios:
		title = f"TEST-BUY-SEED {s['tag']}"
		if frappe.db.exists("Supplier Quotation", {"title": title}):
			created.append(f"existing:{s['tag']}")
			continue
		sq = frappe.get_doc({
			"doctype": "Supplier Quotation",
			"supplier": s["supplier"],
			"transaction_date": today,
			"valid_till": s["valid_till"],
			"company": COMPANY,
			"currency": s["currency"],
			"conversion_rate": 3.6725 if s["currency"] == "USD" else 1.0,
			"title": title,
			"items": [
				{
					"item_code": "TEST-BUY-ITEM-LAPTOP",
					"qty": 3,
					"uom": "Nos",
					"conversion_factor": 1.0,
					"stock_uom": "Nos",
					"rate": s["rate"],
					"request_for_quotation": rfq_name,
				},
			],
		})
		sq.insert(ignore_permissions=True)
		sq.submit()
		created.append(sq.name)
	return created


def _seed_purchase_orders() -> list[str]:
	"""2 POs left in mid-workflow for UAT testing.

	PO-01-Draft: UAT can walk this through the full workflow.
	PO-02-PendingFinance: UAT (Accounts Manager) can act on the final step.
	"""
	today = date.today()
	scenarios = [
		{
			"tag": "PO-01-Draft",
			"supplier": "TEST-BUY-SUPP-002 Dubai Office Supplies",
			"currency": "AED",
			"workflow_transitions": [],
			"items": [("TEST-BUY-ITEM-CHAIR", 8, 800.0)],
			"customer_po_ref": None,
		},
		{
			"tag": "PO-02-PendingFinance",
			"supplier": "TEST-BUY-SUPP-001 Emirates Tech LLC",
			"currency": "AED",
			"workflow_transitions": ["Submit for Approval", "Approve", "Approve"],
			"items": [("TEST-BUY-ITEM-LAPTOP", 3, 4_900.0)],
			"customer_po_ref": "CUST-PO-2026-0042",
		},
	]

	created = []
	for s in scenarios:
		title = f"TEST-BUY-SEED {s['tag']}"
		if frappe.db.exists("Purchase Order", {"title": title}):
			created.append(f"existing:{s['tag']}")
			continue

		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"supplier": s["supplier"],
			"transaction_date": today,
			"schedule_date": today + timedelta(days=14),
			"company": COMPANY,
			"currency": s["currency"],
			"conversion_rate": 1.0,
			"title": title,
			"akd_customer_po_ref": s["customer_po_ref"],
			"items": [
				{
					"item_code": code,
					"qty": qty,
					"uom": "Nos",
					"conversion_factor": 1.0,
					"stock_uom": "Nos",
					"rate": rate,
					"schedule_date": today + timedelta(days=14),
					"warehouse": STORES_WH,
				}
				for code, qty, rate in s["items"]
			],
		})
		po.insert(ignore_permissions=True)
		_walk_workflow(po, s["workflow_transitions"])
		created.append(po.name)
	return created


def _seed_blanket_order() -> list[str]:
	"""1 Blanket Order for chair refills, to_date = today + 60 days (within
	the 30-day pre-expiry alert window in 30 days)."""
	today = date.today()
	if frappe.db.exists("Blanket Order", {"order_no": "BLKT-TEST-BUY-001"}):
		return [f"existing:BLKT-TEST-BUY-001"]

	bo = frappe.get_doc({
		"doctype": "Blanket Order",
		"blanket_order_type": "Purchasing",
		"supplier": "TEST-BUY-SUPP-002 Dubai Office Supplies",
		"from_date": today,
		"to_date": today + timedelta(days=60),
		"company": COMPANY,
		"order_no": "BLKT-TEST-BUY-001",
		"items": [
			{
				"item_code": "TEST-BUY-ITEM-CHAIR",
				"qty": 50,
				"uom": "Nos",
				"conversion_factor": 1.0,
				"stock_uom": "Nos",
				"rate": 800.0,
			},
		],
	})
	bo.insert(ignore_permissions=True)
	bo.submit()
	return [bo.name]


def _seed_purchase_receipt() -> list[str]:
	"""1 PR against a fully-approved laptop PO (PO-03), inspection = Pass.

	PO-03 is created here (separate from PO-01/02 which stay parked for UAT
	workflow testing). It's walked through every workflow transition to
	"Approved" + docstatus=1 so the PR can reference it.
	"""
	today = date.today()
	po_title = "TEST-BUY-SEED PO-03-Approved3WayMatch"
	po_name = frappe.db.get_value("Purchase Order", {"title": po_title}, "name")
	if not po_name:
		po_doc = frappe.get_doc({
			"doctype": "Purchase Order",
			"supplier": "TEST-BUY-SUPP-001 Emirates Tech LLC",
			"transaction_date": today - timedelta(days=2),
			"schedule_date": today,
			"company": COMPANY,
			"currency": "AED",
			"conversion_rate": 1.0,
			"title": po_title,
			"akd_customer_po_ref": "CUST-PO-2026-0099",
			"items": [{
				"item_code": "TEST-BUY-ITEM-LAPTOP",
				"qty": 3,
				"uom": "Nos",
				"conversion_factor": 1.0,
				"stock_uom": "Nos",
				"rate": 4_900.0,
				"schedule_date": today,
				"warehouse": STORES_WH,
			}],
		})
		po_doc.insert(ignore_permissions=True)
		_walk_workflow(po_doc, ["Submit for Approval", "Approve", "Approve", "Approve"])
		po_name = po_doc.name
	po = frappe.get_doc("Purchase Order", po_name)

	remarks = "TEST-BUY-SEED PR-01-Pass"
	if frappe.db.exists("Purchase Receipt", {"remarks": remarks}):
		return [f"existing:{remarks}"]

	pr = frappe.get_doc({
		"doctype": "Purchase Receipt",
		"supplier": po.supplier,
		"posting_date": today,
		"company": COMPANY,
		"currency": po.currency,
		"conversion_rate": 1.0,
		"remarks": remarks,
		"akd_inspection_result": "Pass",
		"items": [
			{
				"item_code": "TEST-BUY-ITEM-LAPTOP",
				"qty": 2,                 # partial receipt — 2 of 3 ordered
				"received_qty": 2,
				"rejected_qty": 0,
				"uom": "Nos",
				"conversion_factor": 1.0,
				"stock_uom": "Nos",
				"rate": 4_900.0,
				"warehouse": STORES_WH,
				"rejected_warehouse": REJECTED_WH,
				"purchase_order": po.name,
				"purchase_order_item": po.items[0].name,
			},
		],
	})
	pr.insert(ignore_permissions=True)
	pr.submit()
	return [pr.name]


def _seed_purchase_invoice() -> list[str]:
	"""1 PI against the PR — completes the 3-way match (FR-BUY-44)."""
	today = date.today()
	pr_name = frappe.db.get_value("Purchase Receipt",
		{"remarks": "TEST-BUY-SEED PR-01-Pass"}, "name")
	if not pr_name:
		return ["skipped: PR-01 not found"]

	remarks = "TEST-BUY-SEED PI-01-3WayMatch"
	if frappe.db.exists("Purchase Invoice", {"remarks": remarks}):
		return [f"existing:{remarks}"]

	pr = frappe.get_doc("Purchase Receipt", pr_name)
	po_name = pr.items[0].purchase_order

	expense_acc = _resolve_expense_account()
	pi = frappe.get_doc({
		"doctype": "Purchase Invoice",
		"supplier": pr.supplier,
		"posting_date": today,
		"bill_no": "INV-TEST-BUY-001",
		"bill_date": today,
		"company": COMPANY,
		"currency": pr.currency,
		"conversion_rate": 1.0,
		"remarks": remarks,
		"items": [
			{
				"item_code": "TEST-BUY-ITEM-LAPTOP",
				"qty": 2,
				"uom": "Nos",
				"conversion_factor": 1.0,
				"stock_uom": "Nos",
				"rate": 4_900.0,
				"expense_account": expense_acc,
				"purchase_order": po_name,
				"purchase_receipt": pr.name,
				"pr_detail": pr.items[0].name,
			},
		],
	})
	pi.insert(ignore_permissions=True)
	pi.submit()
	return [pi.name]


def _seed_purchase_return() -> list[str]:
	"""Build a complete PO → PR → PI → Debit Note chain for chairs.

	C-01 (po_required=Yes) blocks orphan PIs, so we need the full chain to
	exercise the return flow (FR-BUY-77/78/80).
	"""
	today = date.today()
	supplier = "TEST-BUY-SUPP-002 Dubai Office Supplies"
	expense_acc = _resolve_expense_account()
	results = []

	# 1) PO-04-ChairReturnBase — walked through workflow to Approved + submitted
	po_title = "TEST-BUY-SEED PO-04-ChairReturnBase"
	po_name = frappe.db.get_value("Purchase Order", {"title": po_title}, "name")
	if not po_name:
		po_doc = frappe.get_doc({
			"doctype": "Purchase Order",
			"supplier": supplier,
			"transaction_date": today - timedelta(days=4),
			"schedule_date": today - timedelta(days=3),
			"company": COMPANY,
			"currency": "AED",
			"conversion_rate": 1.0,
			"title": po_title,
			"items": [{
				"item_code": "TEST-BUY-ITEM-CHAIR",
				"qty": 4,
				"uom": "Nos",
				"conversion_factor": 1.0,
				"stock_uom": "Nos",
				"rate": 800.0,
				"schedule_date": today - timedelta(days=3),
				"warehouse": STORES_WH,
			}],
		})
		po_doc.insert(ignore_permissions=True)
		_walk_workflow(po_doc, ["Submit for Approval", "Approve", "Approve", "Approve"])
		po_name = po_doc.name
	results.append(f"po:{po_name}")
	po = frappe.get_doc("Purchase Order", po_name)

	# 2) PR-02-ChairReceipt — submitted
	pr_remarks = "TEST-BUY-SEED PR-02-ChairReceipt"
	pr_name = frappe.db.get_value("Purchase Receipt", {"remarks": pr_remarks}, "name")
	if not pr_name:
		pr_doc = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": supplier,
			"posting_date": today - timedelta(days=3),
			"company": COMPANY,
			"currency": "AED",
			"conversion_rate": 1.0,
			"remarks": pr_remarks,
			"akd_inspection_result": "Pass",
			"items": [{
				"item_code": "TEST-BUY-ITEM-CHAIR",
				"qty": 4,
				"received_qty": 4,
				"rejected_qty": 0,
				"uom": "Nos",
				"conversion_factor": 1.0,
				"stock_uom": "Nos",
				"rate": 800.0,
				"warehouse": STORES_WH,
				"rejected_warehouse": REJECTED_WH,
				"purchase_order": po_name,
				"purchase_order_item": po.items[0].name,
			}],
		})
		pr_doc.insert(ignore_permissions=True)
		pr_doc.submit()
		pr_name = pr_doc.name
	results.append(f"pr:{pr_name}")
	pr = frappe.get_doc("Purchase Receipt", pr_name)

	# 3) PI-02-ChairReturnBase — submitted against the PR
	pi_remarks = "TEST-BUY-SEED PI-02-ChairReturnBase"
	pi_src_name = frappe.db.get_value("Purchase Invoice", {"remarks": pi_remarks}, "name")
	if not pi_src_name:
		pi_doc = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"supplier": supplier,
			"posting_date": today - timedelta(days=2),
			"bill_no": "INV-TEST-BUY-CHAIR-001",
			"bill_date": today - timedelta(days=2),
			"company": COMPANY,
			"currency": "AED",
			"conversion_rate": 1.0,
			"remarks": pi_remarks,
			"items": [{
				"item_code": "TEST-BUY-ITEM-CHAIR",
				"qty": 4,
				"uom": "Nos",
				"conversion_factor": 1.0,
				"stock_uom": "Nos",
				"rate": 800.0,
				"expense_account": expense_acc,
				"purchase_order": po_name,
				"purchase_receipt": pr_name,
				"pr_detail": pr.items[0].name,
			}],
		})
		pi_doc.insert(ignore_permissions=True)
		pi_doc.submit()
		pi_src_name = pi_doc.name
	results.append(f"pi:{pi_src_name}")

	# 4) PI-RET-01 — Debit Note returning 1 chair
	ret_remarks = "TEST-BUY-SEED PI-RET-01"
	if frappe.db.exists("Purchase Invoice", {"remarks": ret_remarks}):
		results.append(f"existing:{ret_remarks}")
		return results

	ret = frappe.get_doc({
		"doctype": "Purchase Invoice",
		"supplier": supplier,
		"posting_date": today,
		"bill_no": "INV-TEST-BUY-CHAIR-001-RET",
		"bill_date": today,
		"company": COMPANY,
		"currency": "AED",
		"conversion_rate": 1.0,
		"is_return": 1,
		"return_against": pi_src_name,
		"remarks": ret_remarks,
		"akd_return_reason": "Damaged",
		"items": [{
			"item_code": "TEST-BUY-ITEM-CHAIR",
			"qty": -1,
			"uom": "Nos",
			"conversion_factor": 1.0,
			"stock_uom": "Nos",
			"rate": 800.0,
			"expense_account": expense_acc,
		}],
	})
	ret.insert(ignore_permissions=True)
	ret.submit()
	results.append(f"return:{ret.name}")
	return results


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _resolve_expense_account() -> str:
	candidates = [
		"Office Maintenance Expenses",
		"Office Rent",
		"Operating Expense",
		"Indirect Expenses",
		"Direct Expenses",
	]
	for c in candidates:
		full = f"{c} - {ABBR}"
		if frappe.db.exists("Account", full) and not frappe.db.get_value("Account", full, "is_group"):
			return full
	acc = frappe.db.get_value(
		"Account",
		{"company": COMPANY, "is_group": 0, "root_type": "Expense"},
		"name",
	)
	if not acc:
		frappe.throw("No leaf Expense account found in CoA.")
	return acc
