"""
Single-command setup entry for the AKD ERPNext v16 implementation.

Two phases:

  run() — Module 1 (Foundation) + Module 2 conflict-free steps. Always safe.
    foundation         — Company, FY, currencies, Banks, Bank Accounts
    accounts_settings  — global Accounts Settings flags
    scaffold_accounts  — VAT Output/Input, Exchange Gain/Loss
    exchange_rate      — Currency Exchange Settings provider + Company FX accts
    role_profiles      — 3 AKD Role Profiles
    (full=True)        — accounting.bootstrap.setup_akd_company: cost centres + tax
                         templates + MoP wiring. Requires CoA to expose
                         VAT Output / VAT Input / RAK Bank accounts.

  run_module_2() — drives the Module 2 close-out steps that need AKD input:
    coa_import         — only if odoo_csv_path is given
    vat_consolidation  — only if vat_action is given ("freeze" | "rename")
    accounting_setup   — runs accounting.bootstrap.setup_akd_company

All steps are idempotent.
"""

import frappe

from akd_customizations.setup import (
	accounts_settings,
	buying,
	crm,
	currencies,
	exchange_rate,
	fixed_assets,
	foundation,
	landed_cost,
	master_data,
	modes_of_payment,
	projects,
	quality,
	role_profiles,
	scaffold_accounts,
	selling,
	vat_consolidation,
	wht,
)
from akd_customizations.accounting import bootstrap as accounting_setup
from akd_customizations.utils import coa_mapper


def run(full: bool = True) -> dict:
	report = {}

	report["foundation"] = foundation.setup()
	report["accounts_settings"] = accounts_settings.apply()
	report["scaffold_accounts"] = scaffold_accounts.add()
	report["exchange_rate"] = exchange_rate.apply()
	report["currencies"] = currencies.setup()
	report["quality"] = quality.setup()
	report["crm"] = crm.setup()
	report["projects"] = projects.setup()
	report["role_profiles"] = role_profiles.ensure()
	report["modes_of_payment"] = modes_of_payment.wire()
	report["master_data"] = master_data.setup()
	report["buying"] = buying.setup()
	report["selling"] = selling.setup()
	report["landed_cost"] = landed_cost.setup()
	report["wht"] = wht.setup()
	report["fixed_assets"] = fixed_assets.setup()

	if full:
		report["accounting"] = accounting_setup.setup_akd_company()

	frappe.db.commit()
	frappe.logger("akd_setup").info(report)
	return report


def run_module_2(
	odoo_csv_path: str | None = None,
	vat_action: str | None = None,
	mode: str = "dry-run",
) -> dict:
	"""Module 2 close-out: CoA import + VAT consolidation + accounting setup.

	Args:
	  odoo_csv_path: path to the Odoo CoA CSV. If None, CoA import is skipped.
	  vat_action: 'freeze' or 'rename' to deal with the UAE-regional VAT
	              accounts. If None, the UAE-regional accounts are left in
	              place and accounting_setup may post to either set —
	              read the BRD before choosing.
	  mode: 'dry-run' or 'commit'. Applies to CoA import only.
	"""
	report = {}

	if odoo_csv_path:
		report["coa_import"] = coa_mapper.import_odoo_coa(odoo_csv_path, mode=mode)
		if mode == "dry-run":
			# Stop before any further state change — let the user review.
			return report

	if vat_action == "freeze":
		report["vat_consolidation"] = vat_consolidation.freeze_regional()
	elif vat_action == "rename":
		report["vat_consolidation"] = vat_consolidation.rename_regional()
	elif vat_action is not None:
		frappe.throw(f"Unknown vat_action: {vat_action!r}")

	report["accounting"] = accounting_setup.setup_akd_company()

	frappe.db.commit()
	frappe.logger("akd_setup").info(report)
	return report
