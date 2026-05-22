"""
Chart of Accounts mapping helper.

Two operations:
  • import_odoo_coa() — bulk-create/upsert Account records from a CSV exported
    from AKD's existing Odoo install (FR-ACC-01..04).
  • validate_mapping() — post-import sanity check that every Odoo code resolves
    to a real ERPNext account with the expected root type.

Expected CSV columns (utf-8, comma-delimited, header on row 1):
  odoo_code         — original Odoo account code (kept for audit)
  account_name      — ERPNext account name WITHOUT the company suffix
  parent_account    — name of the parent group account (also no suffix)
  root_type         — Asset|Liability|Income|Expense|Equity (FR-ACC-05)
  account_type      — Bank|Cash|Receivable|Payable|Tax|Stock|... (optional)
  account_number    — numeric or alphanumeric (FR-ACC-03)
  is_group          — 1 if it's a parent / 0 if it's a leaf

The importer:
  1. Processes group rows first, then leaves (topological sort by depth).
  2. Refuses to overwrite the 3 scaffold accounts (VAT Output, VAT Input,
     Exchange Gain/Loss) — those carry BRD-mandated names and are referenced
     by accounting/bootstrap.py.
  3. Idempotent — re-running the same CSV is a no-op.

Usage:
  bench --site akd.com execute \\
    akd_customizations.utils.coa_mapper.import_odoo_coa \\
    --kwargs "{'csv_path': 'sites/akd.com/private/files/akd_migration/coa_mapping.csv',
               'mode': 'dry-run'}"
"""

import csv

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

# Accounts whose names are referenced by other helpers (accounting/bootstrap.py
# tax templates, Mode of Payment wiring, FX gain/loss config). The importer
# must not rename or merge these — if the Odoo CSV claims them, skip and warn.
PROTECTED_ACCOUNTS = {
	"VAT Output",
	"VAT Input",
	"Exchange Gain/Loss",
	"Accounts Receivable",
	"Accounts Payable",
}

VALID_ROOT_TYPES = {"Asset", "Liability", "Income", "Expense", "Equity"}


def import_odoo_coa(csv_path: str, mode: str = "dry-run", company: str = COMPANY) -> dict:
	"""Bulk-create/upsert Accounts from an Odoo CoA CSV.

	mode:
	  'dry-run' — parse, validate, return what would change; no DB writes.
	  'commit'  — apply changes and frappe.db.commit().
	"""
	if mode not in ("dry-run", "commit"):
		frappe.throw("mode must be 'dry-run' or 'commit'")

	abbr = frappe.db.get_value("Company", company, "abbr")
	if not abbr:
		frappe.throw(f"Company {company!r} not found.")

	rows = _read_csv(csv_path)
	_validate_rows(rows)

	# Process groups first, sorted by depth so parents exist before children.
	rows.sort(key=lambda r: (0 if r["is_group"] else 1, _depth(r["parent_account"], rows)))

	plan = {
		"to_create": [],
		"to_update": [],
		"skipped_protected": [],
		"errors": [],
	}

	for row in rows:
		name = row["account_name"]
		if name in PROTECTED_ACCOUNTS:
			plan["skipped_protected"].append(name)
			continue

		full_name = f"{name} - {abbr}"
		parent_full = f"{row['parent_account']} - {abbr}" if row["parent_account"] else None

		existing = frappe.db.get_value("Account", full_name,
			["name", "root_type", "account_type", "account_number", "parent_account", "is_group"],
			as_dict=True,
		)

		if existing:
			diff = _diff(existing, row, parent_full)
			if diff:
				plan["to_update"].append({"name": full_name, "changes": diff})
				if mode == "commit":
					frappe.db.set_value("Account", full_name, diff)
			continue

		# Need to create. Parent must already exist (group rows are processed first).
		if parent_full and not frappe.db.exists("Account", parent_full):
			plan["errors"].append(
				f"Cannot create {full_name}: parent {parent_full!r} missing"
			)
			continue

		plan["to_create"].append(full_name)
		if mode == "commit":
			doc = frappe.get_doc({
				"doctype": "Account",
				"account_name": name,
				"parent_account": parent_full,
				"company": company,
				"root_type": row["root_type"],
				"account_type": row["account_type"] or None,
				"account_number": row["account_number"] or None,
				"is_group": row["is_group"],
			})
			doc.insert(ignore_permissions=True)

	if mode == "commit":
		frappe.db.commit()

	return plan


def validate_mapping(csv_path: str, company: str = COMPANY) -> dict:
	"""Post-import check that every Odoo code resolves to a real account."""
	abbr = frappe.db.get_value("Company", company, "abbr")
	rows = _read_csv(csv_path)

	missing = []
	wrong_type = []
	for row in rows:
		full_name = f"{row['account_name']} - {abbr}"
		acc = frappe.db.get_value(
			"Account", {"name": full_name, "company": company},
			["name", "root_type"], as_dict=True,
		)
		if not acc:
			missing.append({"odoo_code": row["odoo_code"], "lookup": full_name})
			continue
		if row["root_type"] and acc.root_type != row["root_type"]:
			wrong_type.append({
				"account": acc.name,
				"expected": row["root_type"],
				"actual": acc.root_type,
			})

	return {"checked": len(rows), "missing": missing, "wrong_type": wrong_type}


def _read_csv(csv_path: str) -> list[dict]:
	with open(csv_path, newline="", encoding="utf-8-sig") as f:
		reader = csv.DictReader(f)
		rows = []
		for raw in reader:
			rows.append({
				"odoo_code": (raw.get("odoo_code") or "").strip(),
				"account_name": (raw.get("account_name") or "").strip(),
				"parent_account": (raw.get("parent_account") or "").strip(),
				"root_type": (raw.get("root_type") or "").strip(),
				"account_type": (raw.get("account_type") or "").strip(),
				"account_number": (raw.get("account_number") or "").strip(),
				"is_group": int((raw.get("is_group") or "0").strip() or 0),
			})
		return rows


def _validate_rows(rows: list[dict]) -> None:
	seen = set()
	for row in rows:
		name = row["account_name"]
		if not name:
			frappe.throw(f"CSV row missing account_name: {row}")
		if name in seen:
			frappe.throw(f"Duplicate account_name in CSV: {name}")
		seen.add(name)
		if row["root_type"] and row["root_type"] not in VALID_ROOT_TYPES:
			frappe.throw(
				f"Invalid root_type {row['root_type']!r} for {name}; "
				f"must be one of {sorted(VALID_ROOT_TYPES)}"
			)


def _depth(parent_name: str, rows: list[dict]) -> int:
	if not parent_name:
		return 0
	depth = 1
	current = parent_name
	by_name = {r["account_name"]: r["parent_account"] for r in rows}
	while current in by_name and by_name[current]:
		current = by_name[current]
		depth += 1
		if depth > 20:
			frappe.throw(f"CoA hierarchy too deep / cyclic at {parent_name!r}")
	return depth


def _diff(existing: dict, row: dict, parent_full: str | None) -> dict:
	"""Return only fields whose target value differs from the existing row."""
	target = {
		"root_type": row["root_type"] or existing.get("root_type"),
		"account_type": row["account_type"] or existing.get("account_type"),
		"account_number": row["account_number"] or existing.get("account_number"),
		"parent_account": parent_full or existing.get("parent_account"),
		"is_group": row["is_group"],
	}
	return {k: v for k, v in target.items() if existing.get(k) != v}
