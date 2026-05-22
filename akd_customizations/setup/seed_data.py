"""
Test-data seeder for the Accounting module.

ALL RECORDS ARE PREFIXED "TEST-" SO THEY CAN BE PURGED CLEANLY.
DO NOT RUN AGAINST A PRODUCTION SITE THAT HAS REAL TRANSACTIONS.

Two entry points:

  seed_all()       — base seed: masters + happy-path SI/PI/PE/JE.
                     4 cost centres + 4 FX rates + 3 customers + 3 suppliers
                     + 5 items + 4 SI + 3 PI + 2 PE + 1 JE.

  seed_scenarios() — edge-case scenarios layered on top of seed_all():
                     A. Credit-limit breach negative test (FR-SELL-09)
                     B. Unallocated Payment Entry for reconciliation (FR-ACC-68)
                     C. Exchange-rate revaluation period-end JE (FR-ACC-21)
                     D. Invoice cancel + unlink payment (FR-ACC-82)

Usage:
  bench --site akd.com execute akd_customizations.setup.seed_data.seed_all
  bench --site akd.com execute akd_customizations.setup.seed_data.seed_scenarios
  bench --site akd.com execute akd_customizations.setup.seed_data.purge
"""

from datetime import date, timedelta

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

COST_CENTRES = ["Sales", "Admin", "Finance", "HR"]
DEFAULT_CC = "Finance"  # for JEs that don't carry an explicit CC

CUSTOMERS = [
	{
		"customer_name": "TEST-CUST-001 ADNOC Test",
		"customer_group": "Government",
		"territory": "United Arab Emirates",
		"default_currency": "AED",
		"payment_terms": "AKD Customer Standard",
		"credit_limit_aed": 500_000,
	},
	{
		"customer_name": "TEST-CUST-002 First Bank Nigeria Test",
		"customer_group": "Commercial",
		"territory": "Rest Of The World",
		"default_currency": "USD",
		"payment_terms": "AKD Customer Standard",
		"credit_limit_aed": 1_000_000,
	},
	{
		"customer_name": "TEST-CUST-003 Acme USA Test",
		"customer_group": "Commercial",
		"territory": "Rest Of The World",
		"default_currency": "USD",
		"payment_terms": "AKD 50/50 Split",
		"credit_limit_aed": 500_000,
	},
]

SUPPLIERS = [
	{
		"supplier_name": "TEST-SUPP-001 TechVendor LLC",
		"supplier_group": "Local",
		"country": "United Arab Emirates",
		"default_currency": "AED",
		"payment_terms": "AKD Supplier Standard",
	},
	{
		"supplier_name": "TEST-SUPP-002 AWS Cloud Test",
		"supplier_group": "Services",
		"country": "United States",
		"default_currency": "USD",
		"payment_terms": "AKD Supplier Standard",
	},
	{
		"supplier_name": "TEST-SUPP-003 ConsultingCo India Test",
		"supplier_group": "Services",
		"country": "India",
		"default_currency": "USD",
		"payment_terms": None,  # AKD-PIA Single
	},
]

ITEMS = [
	{
		"item_code": "TEST-ITEM-CONSULT",
		"item_name": "Senior Consultant Hour (TEST)",
		"item_group": "Services",
		"is_stock_item": 0,
		"standard_rate": 850.0,
	},
	{
		"item_code": "TEST-ITEM-ADVISORY",
		"item_name": "Advisory Retainer Monthly (TEST)",
		"item_group": "Services",
		"is_stock_item": 0,
		"standard_rate": 25_000.0,
	},
	{
		"item_code": "TEST-ITEM-AI",
		"item_name": "AI Platform Implementation (TEST)",
		"item_group": "Services",
		"is_stock_item": 0,
		"standard_rate": 75_000.0,
	},
	{
		"item_code": "TEST-ITEM-CLOUD",
		"item_name": "Cloud Subscription Monthly (TEST)",
		"item_group": "Services",
		"is_stock_item": 0,
		"standard_rate": 5_000.0,
	},
	{
		"item_code": "TEST-ITEM-LICENSE",
		"item_name": "Software License Annual (TEST)",
		"item_group": "Services",
		"is_stock_item": 0,
		"standard_rate": 12_000.0,
	},
]


# ─────────────────────────────────────────────────────────────────────────────
# Public entry points
# ─────────────────────────────────────────────────────────────────────────────


def seed_all() -> dict:
	report = {
		"cost_centres": _ensure_cost_centres(),
		"exchange_rates": _ensure_fx_rates(),
		"multi_ccy_accounts": _ensure_multi_currency_accounts(),
		"customers": _seed_customers(),
		"suppliers": _seed_suppliers(),
		"items": _seed_items(),
		"sales_invoices": _seed_sales_invoices(),
		"purchase_invoices": _seed_purchase_invoices(),
		"payment_entries": _seed_payment_entries(),
		"journal_entries": _seed_journal_entries(),
	}
	frappe.db.commit()
	return report


FX_RATES = {
	("USD", "AED"): 3.6725,
	("EUR", "AED"): 4.00,
	("GBP", "AED"): 4.65,
	("NGN", "AED"): 0.0040,
}


def _ensure_fx_rates() -> list[str]:
	"""Seed Currency Exchange rows back-dated 90 days so historical SI/PI
	postings (up to -60 days) find a rate."""
	old_date = date.today() - timedelta(days=90)
	created = []
	for (from_ccy, to_ccy), rate in FX_RATES.items():
		exists = frappe.db.exists("Currency Exchange", {
			"from_currency": from_ccy,
			"to_currency": to_ccy,
			"date": old_date,
		})
		if exists:
			continue
		doc = frappe.get_doc({
			"doctype": "Currency Exchange",
			"from_currency": from_ccy,
			"to_currency": to_ccy,
			"date": old_date,
			"exchange_rate": rate,
			"for_buying": 1,
			"for_selling": 1,
		})
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created


def _conversion_rate(from_ccy: str, to_ccy: str = "AED") -> float:
	if from_ccy == to_ccy:
		return 1.0
	rate = FX_RATES.get((from_ccy, to_ccy))
	if not rate:
		frappe.throw(f"No seed FX rate {from_ccy}→{to_ccy}")
	return rate


def purge() -> dict:
	"""Cancel and delete all TEST-* records and TEST-WIRE-* PEs.

	ERPNext overwrites Payment Entry.remarks during validate, so we
	can't filter PE by remarks — use reference_no like 'TEST-%' instead.
	SI/PI/JE keep our remarks tag intact and are filtered by that.
	"""
	deleted = {}

	def _candidates(dt: str) -> list[str]:
		names: list[str] = []
		# 1) TEST-prefixed names (Item/Customer/Supplier autoname)
		names += frappe.db.get_list(dt, filters={"name": ["like", "TEST-%"]}, pluck="name")
		# 2) docs with our seed tag in remarks (SI/PI/JE)
		if dt in ("Sales Invoice", "Purchase Invoice"):
			names += frappe.db.get_list(
				dt, filters={"remarks": ["like", "TEST-SEED%"]}, pluck="name",
			)
		if dt == "Journal Entry":
			names += frappe.db.get_list(
				dt, filters={"user_remark": ["like", "TEST-SEED%"]}, pluck="name",
			)
		# 3) Payment Entries — match by reference_no (remarks gets overwritten)
		if dt == "Payment Entry":
			names += frappe.db.get_list(
				dt, filters={"reference_no": ["like", "TEST-%"]}, pluck="name",
			)
		return list(set(names))

	# Cancel submitted docs first
	for dt in (
		"Journal Entry", "Payment Entry",
		"Sales Invoice", "Purchase Invoice",
		"Exchange Rate Revaluation",
	):
		for n in _candidates(dt):
			doc = frappe.get_doc(dt, n)
			if doc.docstatus != 1:
				continue
			try:
				doc.cancel()
				deleted.setdefault(f"{dt}:cancelled", []).append(n)
			except Exception as e:
				deleted.setdefault(f"{dt}:cancel-errors", []).append(f"{n}: {e}")

	# Delete everything that matches
	for dt in (
		"Exchange Rate Revaluation",
		"Journal Entry", "Payment Entry",
		"Sales Invoice", "Purchase Invoice",
		"Item", "Customer", "Supplier",
	):
		for n in _candidates(dt):
			try:
				frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
				deleted.setdefault(dt, []).append(n)
			except Exception as e:
				deleted.setdefault(f"{dt}:errors", []).append(f"{n}: {e}")

	frappe.db.commit()
	return deleted


# ─────────────────────────────────────────────────────────────────────────────
# Master data seeders
# ─────────────────────────────────────────────────────────────────────────────


def _ensure_multi_currency_accounts() -> list[str]:
	"""Create USD-denominated AR and AP sub-accounts so USD SI/PI can post."""
	# Pick the right parents from whatever the CoA template produced
	ar_parent = _find_group_account(["Accounts Receivable", "Debtors"])
	ap_parent = _find_group_account(["Accounts Payable", "Creditors"])

	created = []
	for name, parent, atype, currency in [
		("Debtors USD", ar_parent, "Receivable", "USD"),
		("Creditors USD", ap_parent, "Payable", "USD"),
	]:
		full = f"{name} - {ABBR}"
		if frappe.db.exists("Account", full):
			continue
		if not parent:
			frappe.throw(f"No parent group for {name} — checked AR/AP/Debtors/Creditors.")
		doc = frappe.get_doc({
			"doctype": "Account",
			"account_name": name,
			"parent_account": parent,
			"company": COMPANY,
			"account_type": atype,
			"account_currency": currency,
			"is_group": 0,
		})
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created


def _find_group_account(candidates: list[str]) -> str | None:
	for needle in candidates:
		full = f"{needle} - {ABBR}"
		if frappe.db.exists("Account", full):
			if frappe.db.get_value("Account", full, "is_group"):
				return full
		# Also try by account_name (no abbr suffix variant)
		acc = frappe.db.get_value("Account", {
			"company": COMPANY, "is_group": 1, "account_name": needle,
		}, "name")
		if acc:
			return acc
	return None


def _ensure_cost_centres() -> list[str]:
	parent = f"{COMPANY} - {ABBR}"
	if not frappe.db.exists("Cost Center", parent):
		frappe.throw(f"Parent cost center {parent!r} missing.")

	created = []
	for cc in COST_CENTRES:
		name = f"{cc} - {ABBR}"
		if frappe.db.exists("Cost Center", name):
			continue
		doc = frappe.get_doc({
			"doctype": "Cost Center",
			"cost_center_name": cc,
			"parent_cost_center": parent,
			"company": COMPANY,
			"is_group": 0,
		})
		doc.insert(ignore_permissions=True)
		created.append(name)
	return created


def _seed_customers() -> list[str]:
	touched = []
	for c in CUSTOMERS:
		if frappe.db.exists("Customer", c["customer_name"]):
			# Refresh credit limit in case the row was seeded with old value.
			doc = frappe.get_doc("Customer", c["customer_name"])
			target_limit = c.get("credit_limit_aed") or 0
			row = next(
				(r for r in (doc.credit_limits or []) if r.company == COMPANY),
				None,
			)
			if row and row.credit_limit != target_limit:
				row.credit_limit = target_limit
				doc.save(ignore_permissions=True)
				touched.append(f"updated:{doc.name}")
			continue

		doc = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": c["customer_name"],
			"customer_type": "Company",
			"customer_group": c["customer_group"],
			"territory": c["territory"],
			"default_currency": c["default_currency"],
			"payment_terms": c["payment_terms"],
			"credit_limits": [
				{"company": COMPANY, "credit_limit": c["credit_limit_aed"]},
			] if c.get("credit_limit_aed") else [],
		})
		doc.insert(ignore_permissions=True)
		touched.append(doc.name)
	return touched


def _seed_suppliers() -> list[str]:
	created = []
	for s in SUPPLIERS:
		if frappe.db.exists("Supplier", s["supplier_name"]):
			continue
		doc = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": s["supplier_name"],
			"supplier_type": "Company",
			"supplier_group": s["supplier_group"],
			"country": s["country"],
			"default_currency": s["default_currency"],
			"payment_terms": s["payment_terms"],
		})
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created


def _seed_items() -> list[str]:
	created = []
	for i in ITEMS:
		if frappe.db.exists("Item", i["item_code"]):
			continue
		doc = frappe.get_doc({
			"doctype": "Item",
			"item_code": i["item_code"],
			"item_name": i["item_name"],
			"item_group": i["item_group"],
			"is_stock_item": i["is_stock_item"],
			"standard_rate": i["standard_rate"],
			"include_item_in_manufacturing": 0,
			"item_defaults": [{
				"company": COMPANY,
				"default_warehouse": f"Stores - {ABBR}",
				"selling_cost_center": f"Sales - {ABBR}",
				"buying_cost_center": f"Admin - {ABBR}",
			}],
		})
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created


# ─────────────────────────────────────────────────────────────────────────────
# Transactional seeders — all marked with remarks "TEST-SEED..." for purge()
# ─────────────────────────────────────────────────────────────────────────────


def _seed_sales_invoices() -> list[str]:
	"""4 SIs covering basic/USD/split-term/overdue."""
	today = date.today()
	sales_tax_template = "UAE VAT 5% - AKD"  # UAE-regional, exists
	output_acc = "VAT 5% - AKD"

	scenarios = [
		# (customer, currency, posting_date_offset_days, items, payment_terms, remarks_tag)
		{
			"customer": "TEST-CUST-001 ADNOC Test",
			"currency": "AED",
			"posting_offset": -10,
			"items": [("TEST-ITEM-CONSULT", 40, 850), ("TEST-ITEM-ADVISORY", 1, 25_000)],
			"payment_terms": "AKD Customer Standard",
			"tag": "SI-01-AED-Basic",
		},
		{
			"customer": "TEST-CUST-002 First Bank Nigeria Test",
			"currency": "USD",
			"posting_offset": -5,
			"items": [("TEST-ITEM-AI", 1, 75_000)],
			"payment_terms": "AKD Customer Standard",
			"tag": "SI-02-USD-MultiCcy",
		},
		{
			"customer": "TEST-CUST-003 Acme USA Test",
			"currency": "USD",
			"posting_offset": -2,
			"items": [("TEST-ITEM-CLOUD", 12, 5_000)],
			"payment_terms": "AKD 50/50 Split",
			"tag": "SI-03-USD-Split",
		},
		{
			"customer": "TEST-CUST-001 ADNOC Test",
			"currency": "AED",
			"posting_offset": -60,
			"items": [("TEST-ITEM-LICENSE", 5, 12_000)],
			"payment_terms": "AKD Customer Standard",
			"tag": "SI-04-AED-Overdue",
		},
	]

	created = []
	for s in scenarios:
		remarks = f"TEST-SEED {s['tag']}"
		# Idempotency: skip if a draft/submitted SI exists with this remarks tag
		existing = frappe.db.get_value(
			"Sales Invoice", {"remarks": remarks}, "name",
		)
		if existing:
			created.append(f"existing:{existing}")
			continue

		debit_to = (
			f"Debtors USD - {ABBR}" if s["currency"] == "USD"
			else _resolve_receivable_account(s["currency"])
		)
		doc = frappe.get_doc({
			"doctype": "Sales Invoice",
			"customer": s["customer"],
			"company": COMPANY,
			"currency": s["currency"],
			"conversion_rate": _conversion_rate(s["currency"]),
			"debit_to": debit_to,
			"posting_date": today + timedelta(days=s["posting_offset"]),
			"set_posting_time": 1,
			"payment_terms_template": s["payment_terms"],
			"taxes_and_charges": sales_tax_template,
			"cost_center": f"Sales - {ABBR}",
			"remarks": remarks,
			"items": [
				{
					"item_code": code, "qty": qty, "rate": rate,
					"cost_center": f"Sales - {ABBR}",
				}
				for (code, qty, rate) in s["items"]
			],
			"taxes": [{
				"charge_type": "On Net Total",
				"account_head": output_acc,
				"description": "UAE VAT 5%",
				"rate": 5,
				"cost_center": f"Sales - {ABBR}",
			}],
		})
		doc.insert(ignore_permissions=True)
		doc.submit()
		created.append(doc.name)
	return created


def _seed_purchase_invoices() -> list[str]:
	today = date.today()
	purchase_tax_template = "UAE VAT 5% - AKD"
	input_acc = "VAT 5% - AKD"
	expense_acc = _resolve_expense_account()

	scenarios = [
		{
			"supplier": "TEST-SUPP-001 TechVendor LLC",
			"currency": "AED",
			"posting_offset": -8,
			"items": [("TEST-ITEM-LICENSE", 2, 11_000)],
			"tag": "PI-01-AED-Basic",
		},
		{
			"supplier": "TEST-SUPP-002 AWS Cloud Test",
			"currency": "USD",
			"posting_offset": -3,
			"items": [("TEST-ITEM-CLOUD", 6, 4_500)],
			"tag": "PI-02-USD-FX",
		},
		{
			"supplier": "TEST-SUPP-003 ConsultingCo India Test",
			"currency": "USD",
			"posting_offset": -1,
			"items": [("TEST-ITEM-CONSULT", 80, 600)],
			"tag": "PI-03-USD-PIA",
		},
	]

	created = []
	for s in scenarios:
		remarks = f"TEST-SEED {s['tag']}"
		existing = frappe.db.get_value(
			"Purchase Invoice", {"remarks": remarks}, "name",
		)
		if existing:
			created.append(f"existing:{existing}")
			continue

		credit_to = (
			f"Creditors USD - {ABBR}" if s["currency"] == "USD"
			else _resolve_payable_account(s["currency"])
		)
		doc = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"supplier": s["supplier"],
			"company": COMPANY,
			"currency": s["currency"],
			"conversion_rate": _conversion_rate(s["currency"]),
			"credit_to": credit_to,
			"posting_date": today + timedelta(days=s["posting_offset"]),
			"set_posting_time": 1,
			"bill_no": f"INV-{s['tag']}",
			"bill_date": today + timedelta(days=s["posting_offset"]),
			"taxes_and_charges": purchase_tax_template,
			"cost_center": f"Admin - {ABBR}",
			"remarks": remarks,
			"items": [
				{
					"item_code": code, "qty": qty, "rate": rate,
					"expense_account": expense_acc,
					"cost_center": f"Admin - {ABBR}",
				}
				for (code, qty, rate) in s["items"]
			],
			"taxes": [{
				"charge_type": "On Net Total",
				"account_head": input_acc,
				"description": "UAE VAT 5%",
				"rate": 5,
				"category": "Total",
				"add_deduct_tax": "Add",
				"cost_center": f"Admin - {ABBR}",
			}],
		})
		doc.insert(ignore_permissions=True)
		doc.submit()
		created.append(doc.name)
	return created


def _seed_payment_entries() -> list[str]:
	"""Pay SI-01 in full, SI-03 50% advance."""
	today = date.today()
	bank_acc = f"RAK Bank - Current AED - {ABBR}"

	created = []

	# Full payment of SI-01 (AED basic)
	si_01 = frappe.db.get_value(
		"Sales Invoice",
		{"remarks": "TEST-SEED SI-01-AED-Basic", "docstatus": 1},
		["name", "grand_total", "outstanding_amount", "customer"],
		as_dict=True,
	)
	if si_01 and si_01.outstanding_amount > 0:
		pe_remarks = "TEST-SEED PE-01-Full-SI-01"
		# ERPNext overwrites `remarks` during PE validate; use reference_no
		# (which is preserved verbatim) as the idempotency key.
		if not frappe.db.exists("Payment Entry", {"reference_no": "TEST-WIRE-001"}):
			# Use SI-01's actual debit_to so paid_from matches Party Account.
			si_01_debit_to = frappe.db.get_value("Sales Invoice", si_01.name, "debit_to")
			pe = frappe.get_doc({
				"doctype": "Payment Entry",
				"payment_type": "Receive",
				"company": COMPANY,
				"posting_date": today,
				"mode_of_payment": "Bank Transfer",
				"party_type": "Customer",
				"party": si_01.customer,
				"paid_from": si_01_debit_to,
				"paid_from_account_currency": "AED",
				"paid_to": bank_acc,
				"paid_to_account_currency": "AED",
				"paid_amount": si_01.outstanding_amount,
				"received_amount": si_01.outstanding_amount,
				"reference_no": "TEST-WIRE-001",
				"reference_date": today,
				"remarks": pe_remarks,
				"references": [{
					"reference_doctype": "Sales Invoice",
					"reference_name": si_01.name,
					"allocated_amount": si_01.outstanding_amount,
				}],
			})
			pe.insert(ignore_permissions=True)
			pe.submit()
			created.append(pe.name)

	# 50% advance against SI-03 (USD split)
	si_03 = frappe.db.get_value(
		"Sales Invoice",
		{"remarks": "TEST-SEED SI-03-USD-Split", "docstatus": 1},
		["name", "grand_total", "customer", "currency"],
		as_dict=True,
	)
	if si_03:
		pe_remarks = "TEST-SEED PE-02-Partial-SI-03"
		if not frappe.db.exists("Payment Entry", {"reference_no": "TEST-WIRE-002"}):
			half = round(si_03.grand_total / 2.0, 2)
			# Use SI-03's actual debit_to (set to Debtors USD - AKD)
			ar_usd = frappe.db.get_value("Sales Invoice", si_03.name, "debit_to")
			pe = frappe.get_doc({
				"doctype": "Payment Entry",
				"payment_type": "Receive",
				"company": COMPANY,
				"posting_date": today,
				"mode_of_payment": "Bank Transfer",
				"party_type": "Customer",
				"party": si_03.customer,
				"paid_from": ar_usd,
				"paid_from_account_currency": "USD",
				"paid_to": f"RAK Bank - Current USD - {ABBR}",
				"paid_to_account_currency": "USD",
				"paid_amount": half,
				"received_amount": half,
				"source_exchange_rate": 3.6725,
				"target_exchange_rate": 3.6725,
				"reference_no": "TEST-WIRE-002",
				"reference_date": today,
				"remarks": pe_remarks,
				"references": [{
					"reference_doctype": "Sales Invoice",
					"reference_name": si_03.name,
					"allocated_amount": half,
				}],
			})
			pe.insert(ignore_permissions=True)
			pe.submit()
			created.append(pe.name)

	return created


def _seed_journal_entries() -> list[str]:
	"""1 manual write-off JE."""
	today = date.today()
	remarks = "TEST-SEED JE-01-WriteOff"
	if frappe.db.exists("Journal Entry", {"user_remark": remarks}):
		return [f"existing:{remarks}"]

	ar_acc = _resolve_receivable_account("AED")
	je = frappe.get_doc({
		"doctype": "Journal Entry",
		"voucher_type": "Write Off Entry",
		"company": COMPANY,
		"posting_date": today,
		"user_remark": remarks,
		"accounts": [
			{
				"account": "Write Off - AKD",
				"debit_in_account_currency": 250.0,
				"cost_center": f"{DEFAULT_CC} - {ABBR}",
			},
			{
				"account": ar_acc,
				"credit_in_account_currency": 250.0,
				"party_type": "Customer",
				"party": "TEST-CUST-001 ADNOC Test",
				"cost_center": f"{DEFAULT_CC} - {ABBR}",
			},
		],
	})
	je.insert(ignore_permissions=True)
	je.submit()
	return [je.name]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _resolve_expense_account() -> str:
	"""Pick a leaf expense account to use as default on PI lines."""
	candidates = [
		"Office Maintenance Expenses",
		"Office Rent",
		"Operating Expense",
		"Direct Expenses",
		"Indirect Expenses",
	]
	for c in candidates:
		full = f"{c} - {ABBR}"
		if frappe.db.exists("Account", full) and not frappe.db.get_value("Account", full, "is_group"):
			return full
	# Fallback: any leaf expense account
	acc = frappe.db.get_value(
		"Account",
		{"company": COMPANY, "is_group": 0, "root_type": "Expense"},
		"name",
	)
	if not acc:
		frappe.throw("No leaf Expense account found in CoA.")
	return acc


def _resolve_receivable_account(currency: str) -> str:
	"""Find a receivable account in the given currency, or the default AR."""
	acc = frappe.db.get_value("Account", {
		"company": COMPANY,
		"account_type": "Receivable",
		"is_group": 0,
		"account_currency": currency,
	}, "name")
	if acc:
		return acc
	return frappe.db.get_value("Account", {
		"company": COMPANY,
		"account_type": "Receivable",
		"is_group": 0,
	}, "name") or f"Debtors - {ABBR}"


def _resolve_payable_account(currency: str) -> str:
	acc = frappe.db.get_value("Account", {
		"company": COMPANY,
		"account_type": "Payable",
		"is_group": 0,
		"account_currency": currency,
	}, "name")
	if acc:
		return acc
	return frappe.db.get_value("Account", {
		"company": COMPANY,
		"account_type": "Payable",
		"is_group": 0,
	}, "name") or f"Creditors - {ABBR}"


# ─────────────────────────────────────────────────────────────────────────────
# Edge-case scenarios — exercise specific BRD flags
# ─────────────────────────────────────────────────────────────────────────────


def seed_scenarios() -> dict:
	"""Run scenarios A–D. Each commits independently so one failure doesn't
	roll back the rest."""
	report = {}
	for label, fn in [
		("A_credit_limit_breach", _scenario_credit_limit_breach),
		("B_unallocated_payment", _scenario_unallocated_payment),
		("C_fx_revaluation", _scenario_fx_revaluation),
		("D_cancel_unlink_payment", _scenario_cancel_unlink_payment),
	]:
		try:
			report[label] = fn()
			frappe.db.commit()
		except Exception as e:  # noqa: BLE001
			frappe.db.rollback()
			report[label] = {"error": f"{type(e).__name__}: {e}"}
	return report


# ───── A. Credit-limit breach negative test ──────────────────────────────────


def _scenario_credit_limit_breach() -> dict:
	"""Try to create a SI that exceeds TEST-CUST-001's credit limit. Expect
	overrides/sales_invoice.py:validate_credit_limit to throw. Pass = caught."""
	customer = "TEST-CUST-001 ADNOC Test"
	if not frappe.db.exists("Customer", customer):
		return {"status": "skipped", "reason": "base seed not run"}

	limit_row = frappe.db.get_value(
		"Customer Credit Limit",
		{"parent": customer, "company": COMPANY},
		["credit_limit"], as_dict=True,
	)
	if not limit_row:
		return {"status": "skipped", "reason": "no credit limit set"}

	current_outstanding = float(frappe.db.sql(
		"""SELECT COALESCE(SUM(outstanding_amount), 0) FROM `tabSales Invoice`
		   WHERE customer = %s AND company = %s AND docstatus = 1""",
		(customer, COMPANY),
	)[0][0])

	# Build an SI whose grand_total alone exceeds (limit - outstanding) * 110%
	headroom = float(limit_row.credit_limit) - current_outstanding
	breach_target = max(headroom * 1.5, 50_000)  # always cross the line
	# pick a qty of TEST-ITEM-AI (rate 75K) that crosses
	qty = max(1, int(breach_target / 75_000) + 2)

	remarks = "TEST-SEED SI-99-CreditBreach"
	if frappe.db.exists("Sales Invoice", {"remarks": remarks}):
		return {"status": "already-tested", "remarks": remarks}

	doc = frappe.get_doc({
		"doctype": "Sales Invoice",
		"customer": customer,
		"company": COMPANY,
		"currency": "AED",
		"conversion_rate": 1.0,
		"posting_date": date.today(),
		"set_posting_time": 1,
		"taxes_and_charges": "UAE VAT 5% - AKD",
		"cost_center": f"Sales - {ABBR}",
		"remarks": remarks,
		"items": [{
			"item_code": "TEST-ITEM-AI", "qty": qty, "rate": 75_000,
			"cost_center": f"Sales - {ABBR}",
		}],
		"taxes": [{
			"charge_type": "On Net Total",
			"account_head": "VAT 5% - AKD",
			"description": "UAE VAT 5%",
			"rate": 5,
			"cost_center": f"Sales - {ABBR}",
		}],
	})

	try:
		doc.insert(ignore_permissions=True)
		doc.submit()
	except frappe.exceptions.ValidationError as e:
		return {
			"status": "PASS — credit limit hook fired as expected",
			"customer": customer,
			"limit": limit_row.credit_limit,
			"current_outstanding": current_outstanding,
			"attempted_grand_total": doc.grand_total,
			"error_caught": str(e)[:200],
		}

	# Should not reach here — fail visibly
	return {
		"status": "FAIL — SI submitted without hitting credit limit",
		"si_name": doc.name,
		"grand_total": doc.grand_total,
		"limit": limit_row.credit_limit,
	}


# ───── B. Unallocated Payment Entry for Reconciliation ───────────────────────


def _scenario_unallocated_payment() -> dict:
	"""Create a PE with no `references` from TEST-CUST-002. It should show
	up in Payment Reconciliation as an unallocated receipt."""
	customer = "TEST-CUST-002 First Bank Nigeria Test"
	if not frappe.db.exists("Customer", customer):
		return {"status": "skipped", "reason": "base seed not run"}

	remarks = "TEST-SEED PE-99-Unallocated"
	# ERPNext overwrites PE.remarks during validate; use reference_no as key.
	if frappe.db.exists("Payment Entry", {"reference_no": "TEST-WIRE-099-UNALLOC"}):
		return {"status": "already-seeded"}

	# Customer is USD-default so post the PE in USD against Debtors USD.
	ar_usd = f"Debtors USD - {ABBR}"
	pe = frappe.get_doc({
		"doctype": "Payment Entry",
		"payment_type": "Receive",
		"company": COMPANY,
		"posting_date": date.today(),
		"mode_of_payment": "Bank Transfer",
		"party_type": "Customer",
		"party": customer,
		"paid_from": ar_usd,
		"paid_from_account_currency": "USD",
		"paid_to": f"RAK Bank - Current USD - {ABBR}",
		"paid_to_account_currency": "USD",
		"paid_amount": 5_000.0,
		"received_amount": 5_000.0,
		"source_exchange_rate": 3.6725,
		"target_exchange_rate": 3.6725,
		"reference_no": "TEST-WIRE-099-UNALLOC",
		"reference_date": date.today(),
		"remarks": remarks,
		# NO references[] — that's the point
	})
	pe.insert(ignore_permissions=True)
	pe.submit()

	# Sanity check: customer should now have unallocated balance
	unallocated_count = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabGL Entry`
		   WHERE party_type = 'Customer' AND party = %s
		     AND voucher_type = 'Payment Entry' AND voucher_no = %s
		     AND against_voucher = '' AND is_cancelled = 0""",
		(customer, pe.name),
	)[0][0]

	return {
		"status": "seeded",
		"pe": pe.name,
		"unallocated_gl_rows": unallocated_count,
		"reconcile_via": "Accounting → Payment Reconciliation → pick customer",
	}


# ───── C. Exchange-Rate Revaluation Period-End JE ────────────────────────────


def _scenario_fx_revaluation() -> dict:
	"""Insert a fresh USD→AED rate at today (different from the 90-day-old
	3.6725 seed), then create an Exchange Rate Revaluation doc for AKD and
	post the resulting JE. Tests FR-ACC-21 + Company.auto_exchange_rate_revaluation.

	v16 bug workaround: frappe/locale.py:get_locale_value() doesn't initialise
	`value` when `frappe.local.lang` is unset (happens under `bench execute`),
	which the Exchange Rate Revaluation flow trips. Pin lang explicitly.
	"""
	if not getattr(frappe.local, "lang", None):
		frappe.local.lang = "en"

	new_rate_today = 3.8000  # AED weakens vs USD
	today = date.today()

	# Seed today's rate
	if not frappe.db.exists("Currency Exchange", {
		"from_currency": "USD", "to_currency": "AED", "date": today,
	}):
		fx = frappe.get_doc({
			"doctype": "Currency Exchange",
			"from_currency": "USD",
			"to_currency": "AED",
			"date": today,
			"exchange_rate": new_rate_today,
			"for_buying": 1,
			"for_selling": 1,
		})
		fx.insert(ignore_permissions=True)

	# Check if revaluation already created — one per day max
	tag = "TEST-SEED FXREV-99"
	existing = frappe.db.exists("Exchange Rate Revaluation", {
		"company": COMPANY,
		"posting_date": today,
	})
	if existing:
		return {"status": "already-seeded-today", "err": existing}

	# Pull USD accounts with non-zero balance
	usd_accts = frappe.db.sql(
		"""SELECT name FROM `tabAccount`
		   WHERE company = %s AND account_currency = 'USD' AND is_group = 0""",
		(COMPANY,), as_dict=True,
	)
	if not usd_accts:
		return {"status": "skipped", "reason": "no USD accounts"}

	err = frappe.get_doc({
		"doctype": "Exchange Rate Revaluation",
		"company": COMPANY,
		"posting_date": today,
		"rounding_loss_allowance": 0.05,
		"remarks": tag,
	})

	# get_accounts_data populates child table with USD account balances
	try:
		accts = err.get_accounts_data()
	except Exception as e:
		return {"status": "error", "reason": f"{type(e).__name__}: {str(e)[:200]}"}
	if not accts:
		return {
			"status": "skipped",
			"reason": "Exchange Rate Revaluation found no zero-foreign-balance accounts",
			"note": "Normal if USD GL has no open balance; expected to fire after PI/SI cycle.",
		}

	for row in accts:
		err.append("accounts", row)
	err.insert(ignore_permissions=True)

	# Post the JEs the revaluation generates
	jv_response = err.make_jv_entries() if hasattr(err, "make_jv_entries") else None
	return {
		"status": "seeded",
		"err": err.name,
		"new_rate_today": new_rate_today,
		"accounts_revalued": len(accts),
		"jv": jv_response,
	}


# ───── D. Invoice cancel + unlink payment ────────────────────────────────────


def _scenario_cancel_unlink_payment() -> dict:
	"""Create SI-05 + PE-05 (full payment), then cancel SI-05. Verify that
	the PE got unlinked from references (FR-ACC-82 — unlink_payment_on_cancellation)."""
	customer = "TEST-CUST-001 ADNOC Test"
	if not frappe.db.exists("Customer", customer):
		return {"status": "skipped", "reason": "base seed not run"}

	si_remarks = "TEST-SEED SI-05-CancelUnlink"
	pe_remarks = "TEST-SEED PE-05-CancelUnlink"

	# Idempotency: if already done, report
	si = frappe.db.get_value("Sales Invoice", {"remarks": si_remarks},
		["name", "docstatus", "status"], as_dict=True)
	pe = frappe.db.get_value("Payment Entry", {"reference_no": "TEST-WIRE-005"},
		["name", "docstatus"], as_dict=True)
	if si and si.docstatus == 2:
		return {
			"status": "already-tested",
			"si": si.name, "si_status": si.status,
			"pe": pe.name if pe else None,
		}

	if not si:
		# Create SI-05 — small enough to slot under remaining credit headroom
		si_doc = frappe.get_doc({
			"doctype": "Sales Invoice",
			"customer": customer,
			"company": COMPANY,
			"currency": "AED",
			"conversion_rate": 1.0,
			"posting_date": date.today(),
			"set_posting_time": 1,
			"taxes_and_charges": "UAE VAT 5% - AKD",
			"cost_center": f"Sales - {ABBR}",
			"remarks": si_remarks,
			"items": [{
				"item_code": "TEST-ITEM-CONSULT", "qty": 6, "rate": 850,
				"cost_center": f"Sales - {ABBR}",
			}],
			"taxes": [{
				"charge_type": "On Net Total",
				"account_head": "VAT 5% - AKD",
				"description": "UAE VAT 5%",
				"rate": 5,
				"cost_center": f"Sales - {ABBR}",
			}],
		})
		si_doc.insert(ignore_permissions=True)
		si_doc.submit()
		si_name = si_doc.name
		si_debit_to = si_doc.debit_to
		grand_total = si_doc.grand_total
	else:
		si_name = si.name
		si_debit_to = frappe.db.get_value("Sales Invoice", si_name, "debit_to")
		grand_total = frappe.db.get_value("Sales Invoice", si_name, "grand_total")

	# Create the PE that fully pays SI-05 (if not done)
	if not pe:
		outstanding = frappe.db.get_value("Sales Invoice", si_name, "outstanding_amount")
		pe_doc = frappe.get_doc({
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"company": COMPANY,
			"posting_date": date.today(),
			"mode_of_payment": "Bank Transfer",
			"party_type": "Customer",
			"party": customer,
			"paid_from": si_debit_to,
			"paid_from_account_currency": "AED",
			"paid_to": f"RAK Bank - Current AED - {ABBR}",
			"paid_to_account_currency": "AED",
			"paid_amount": outstanding,
			"received_amount": outstanding,
			"reference_no": "TEST-WIRE-005",
			"reference_date": date.today(),
			"remarks": pe_remarks,
			"references": [{
				"reference_doctype": "Sales Invoice",
				"reference_name": si_name,
				"allocated_amount": outstanding,
			}],
		})
		pe_doc.insert(ignore_permissions=True)
		pe_doc.submit()
		pe_name = pe_doc.name
	else:
		pe_name = pe.name

	# Verify Accounts Settings has unlink on (FR-ACC-82)
	unlink_flag = frappe.db.get_single_value(
		"Accounts Settings", "unlink_payment_on_cancellation_of_invoice",
	)

	# Cancel the SI
	si_doc = frappe.get_doc("Sales Invoice", si_name)
	si_doc.cancel()

	# Re-fetch PE and check references
	pe_after = frappe.get_doc("Payment Entry", pe_name)
	references_after = [
		(r.reference_doctype, r.reference_name, r.allocated_amount)
		for r in (pe_after.references or [])
	]
	pe_unallocated = pe_after.unallocated_amount if hasattr(pe_after, "unallocated_amount") else None

	return {
		"status": "tested",
		"si": si_name,
		"si_docstatus": si_doc.docstatus,
		"pe": pe_name,
		"pe_docstatus": pe_after.docstatus,
		"pe_references_after_cancel": references_after,
		"pe_unallocated_amount": pe_unallocated,
		"accounts_setting_unlink_flag": unlink_flag,
		"expected": (
			"If FR-ACC-82 is honoured, pe_references_after_cancel should be "
			"empty (or have allocated_amount=0) and pe_unallocated_amount "
			f"should equal {grand_total}."
		),
	}
