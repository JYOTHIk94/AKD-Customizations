"""
Open Sales Invoice importer for opening AR balances.

Expected CSV columns:
  invoice_no, customer, posting_date, due_date, currency, conversion_rate,
  outstanding_amount, debit_to, remarks

Strategy:
  Create an "opening" Sales Invoice per row with a single line item against the
  configured "Temporary Opening" account so AR aging reproduces the Odoo state.
"""

import csv
from typing import Any

import frappe
from frappe.utils import flt

OPENING_LINE_DESCRIPTION = "Opening AR balance imported from Odoo"


def run(csv_path: str, company: str, commit: bool) -> dict:
	rows = _read_csv(csv_path)
	created, skipped, errors = [], [], []
	total = 0.0

	for row in rows:
		invoice_no = (row.get("invoice_no") or "").strip()
		if not invoice_no:
			errors.append({"row": row, "reason": "missing invoice_no"})
			continue
		if frappe.db.exists("Sales Invoice", {"bill_no": invoice_no, "company": company}):
			skipped.append(invoice_no)
			continue

		try:
			doc = _build_invoice(row, company)
			total += flt(doc.outstanding_amount or doc.grand_total)
			if commit:
				doc.insert(ignore_permissions=True)
				doc.submit()
				created.append(doc.name)
			else:
				created.append(f"DRYRUN:{invoice_no}")
		except Exception as e:
			errors.append({"row": row, "reason": str(e)})

	return {
		"created": len(created),
		"skipped": len(skipped),
		"errors": errors,
		"total_amount": total,
	}


def _build_invoice(row: dict, company: str) -> Any:
	customer = row["customer"].strip()
	if not frappe.db.exists("Customer", customer):
		frappe.throw(f"Customer not found: {customer}")

	doc = frappe.get_doc({
		"doctype": "Sales Invoice",
		"company": company,
		"customer": customer,
		"posting_date": row["posting_date"],
		"due_date": row.get("due_date"),
		"currency": row.get("currency") or "AED",
		"conversion_rate": flt(row.get("conversion_rate")) or 1.0,
		"is_opening": "Yes",
		"update_stock": 0,
		"set_posting_time": 1,
		"bill_no": row["invoice_no"],
		"remarks": row.get("remarks") or OPENING_LINE_DESCRIPTION,
		"debit_to": row.get("debit_to") or _default_debit_to(company),
		"items": [{
			"item_code": _opening_item(),
			"description": OPENING_LINE_DESCRIPTION,
			"qty": 1,
			"rate": flt(row["outstanding_amount"]),
			"income_account": _temporary_opening_account(company),
		}],
	})
	doc.set_missing_values()
	return doc


def _read_csv(path: str) -> list[dict]:
	with open(path, newline="", encoding="utf-8-sig") as f:
		return list(csv.DictReader(f))


def _default_debit_to(company: str) -> str:
	return frappe.get_cached_value("Company", company, "default_receivable_account") \
		or frappe.throw(f"No default receivable account for {company}")


def _temporary_opening_account(company: str) -> str:
	abbr = frappe.get_cached_value("Company", company, "abbr")
	candidate = f"Temporary Opening - {abbr}"
	if not frappe.db.exists("Account", candidate):
		frappe.throw(f"Account {candidate!r} missing. Create it under Equity before import.")
	return candidate


def _opening_item() -> str:
	"""Return a generic 'Opening' item code; create if missing."""
	code = "AKD-OPENING-AR"
	if not frappe.db.exists("Item", code):
		frappe.get_doc({
			"doctype": "Item",
			"item_code": code,
			"item_name": "Opening AR Balance",
			"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups",
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_sales_item": 1,
			"include_item_in_manufacturing": 0,
		}).insert(ignore_permissions=True)
	return code
