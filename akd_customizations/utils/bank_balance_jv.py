"""
Bank opening balance Journal Entry.

Expected CSV columns:
  bank_account, currency, posting_date, balance

Creates one Journal Entry per row: Dr Bank Account, Cr Temporary Opening.
"""

import csv

import frappe
from frappe.utils import flt


def run(csv_path: str, company: str, commit: bool) -> dict:
	rows = _read_csv(csv_path)
	created, errors = [], []
	total_aed_equiv = 0.0

	for row in rows:
		try:
			doc = _build_jv(row, company)
			total_aed_equiv += flt(doc.total_debit)
			if commit:
				doc.insert(ignore_permissions=True)
				doc.submit()
				created.append(doc.name)
			else:
				created.append(f"DRYRUN:{row['bank_account']}")
		except Exception as e:
			errors.append({"row": row, "reason": str(e)})

	return {
		"created": len(created),
		"errors": errors,
		"total_aed_equiv": total_aed_equiv,
	}


def _build_jv(row: dict, company: str):
	bank_account = row["bank_account"].strip()
	gl_account = frappe.db.get_value("Bank Account", bank_account, "account")
	if not gl_account:
		frappe.throw(f"Bank Account {bank_account!r} has no GL account linked.")

	abbr = frappe.get_cached_value("Company", company, "abbr")
	temp_opening = f"Temporary Opening - {abbr}"
	if not frappe.db.exists("Account", temp_opening):
		frappe.throw(f"Account {temp_opening!r} missing. Create it under Equity before import.")

	balance = flt(row["balance"])
	currency = row.get("currency") or "AED"

	return frappe.get_doc({
		"doctype": "Journal Entry",
		"voucher_type": "Opening Entry",
		"company": company,
		"posting_date": row["posting_date"],
		"is_opening": "Yes",
		"multi_currency": 1 if currency != "AED" else 0,
		"user_remark": f"Opening balance for {bank_account}",
		"accounts": [
			{
				"account": gl_account,
				"debit_in_account_currency": balance,
				"account_currency": currency,
			},
			{
				"account": temp_opening,
				"credit_in_account_currency": balance,
				"account_currency": currency,
			},
		],
	})


def _read_csv(path: str) -> list[dict]:
	with open(path, newline="", encoding="utf-8-sig") as f:
		return list(csv.DictReader(f))
