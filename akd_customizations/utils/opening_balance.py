"""
Opening-balance orchestrator for AKD Odoo → ERPNext cut-over.

BRD: FR-ACC-75 (opening balances from Odoo), FR-ACC-76 (datasets: CoA & balances,
Customer Outstanding, Supplier Outstanding, Bank Balances).

Input CSVs are expected at: sites/<site>/private/files/akd_migration/
  - coa_mapping.csv         (Odoo account code → ERPNext account name)
  - ar_outstanding.csv      (one row per open Sales Invoice)
  - ap_outstanding.csv      (one row per open Purchase Invoice)
  - bank_balances.csv       (one row per bank account)

Usage:
  bench --site dhh.com execute \\
    akd_customizations.utils.opening_balance.run \\
    --kwargs "{'mode': 'dry-run'}"

  bench --site dhh.com execute \\
    akd_customizations.utils.opening_balance.run \\
    --kwargs "{'mode': 'commit', 'company': 'AKD Consulting LLC'}"
"""

import os

import frappe

from akd_customizations.utils import (
	ar_outstanding_import,
	ap_outstanding_import,
	bank_balance_jv,
)

COMPANY = "AKD Consulting LLC"


def run(mode: str = "dry-run", company: str = COMPANY) -> dict:
	if mode not in ("dry-run", "commit"):
		frappe.throw("mode must be 'dry-run' or 'commit'")

	base_dir = _migration_dir()
	if not os.path.isdir(base_dir):
		frappe.throw(f"Migration folder missing: {base_dir}")

	report = {
		"mode": mode,
		"company": company,
		"ar": ar_outstanding_import.run(
			csv_path=os.path.join(base_dir, "ar_outstanding.csv"),
			company=company,
			commit=(mode == "commit"),
		),
		"ap": ap_outstanding_import.run(
			csv_path=os.path.join(base_dir, "ap_outstanding.csv"),
			company=company,
			commit=(mode == "commit"),
		),
		"bank": bank_balance_jv.run(
			csv_path=os.path.join(base_dir, "bank_balances.csv"),
			company=company,
			commit=(mode == "commit"),
		),
	}

	if mode == "commit":
		frappe.db.commit()

	frappe.logger("akd_migration").info(report)
	return report


def _migration_dir() -> str:
	return frappe.get_site_path("private", "files", "akd_migration")
