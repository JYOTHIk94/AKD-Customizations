"""
Fixed Assets module setup — trimmed per BRD §10 (most features = No).

BRD references (Section 10):
  FR-FA-03/04  Asset categories: Furniture & Fittings, IT Equipment
  FR-FA-21/22  Depreciate; method varies by category (D-FA-1 — default
               Straight Line for both pending CRP §12.7 Q28)
  FR-FA-23     Useful life: Furniture 5 yr, IT 3 yr
  FR-FA-24     Posting frequency = Quarterly (3 months)
  FR-FA-25     Daily pro-rata (exact days) = finance-book daily_prorata_based
  FR-FA-26     Salvage = fixed amount (per-asset expected_value_after_useful_life;
               category salvage % left 0)
  FR-FA-54     Disposal gain/loss account = Other Income → Company.disposal_account
  FR-FA-78     Automatic depreciation posting (no manual)
  FR-FA-08/30..35  CWIP / construction OFF (enable_cwip_accounting = 0)
  FR-FA-65     Reports: Fixed Asset Register + Depreciation Schedule (standard)
  FR-FA-71..75 Accountant manages; NO role/disposal/posting restrictions
               (so no Custom DocPerm / new roles here)

Account model (BRD §12.7 Q10/Q11 — per-category GL left blank, so the ERPNext
default is used): a per-category Fixed Asset account, plus a SHARED
Accumulated Depreciation + Depreciation Expense account, plus a disposal
gain/loss account under Other Income.

Disposal approval (FR-FA-55) lives in overrides/asset_disposal.py.

Usage:
  bench --site akd.com execute akd_customizations.setup.fixed_assets.setup
"""

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"

# ERPNext makes Asset.location mandatory even though location tracking is
# OFF (FR-FA-10). One default Location lets assets be created at all.
DEFAULT_LOCATION = "AKD Head Office"

FREQUENCY_MONTHS = 3  # FR-FA-24 Quarterly
CATEGORIES = {
	"Furniture & Fittings": {"method": "Straight Line", "life_years": 5},
	"IT Equipment": {"method": "Straight Line", "life_years": 3},
}

FA_PARENTS = ["Fixed Assets", "Fixed Asset"]
ACCDEP_PARENTS = ["Fixed Assets"]
DEPEXP_PARENTS = ["Indirect Expenses", "Administrative Expenses", "Expenses"]
DISPOSAL_PARENTS = ["Indirect Income", "Other Income", "Income"]


def setup() -> dict:
	acc = _ensure_accounts()
	report = {
		"accounts": acc,
		"accounts_settings": _apply_accounts_settings(),
		"company_defaults": _wire_company_defaults(acc),
		"location": _ensure_location(),
		"asset_categories": _ensure_categories(acc),
	}
	frappe.db.commit()
	frappe.logger("akd_setup").info({"fixed_assets": report})
	return report


# ── account scaffolding ──────────────────────────────────────────────────────

def _resolve_group(candidates: list[str]) -> str:
	for cand in candidates:
		full = f"{cand} - {ABBR}"
		if frappe.db.exists("Account", {"name": full, "is_group": 1}):
			return full
	frappe.throw(f"No GROUP parent account in CoA from {candidates}.")


def _ensure_ledger(account_name: str, parent_group: str, root_type: str,
				   account_type: str | None) -> str:
	full = f"{account_name} - {ABBR}"
	if frappe.db.exists("Account", full):
		return full
	frappe.get_doc({
		"doctype": "Account",
		"account_name": account_name,
		"parent_account": parent_group,
		"company": COMPANY,
		"root_type": root_type,
		"account_type": account_type,
		"is_group": 0,
	}).insert(ignore_permissions=True)
	return full


def _shared_ledger(preferred: list[str], fallback_name: str,
				   parent_candidates: list[str], root_type: str,
				   account_type: str | None) -> str:
	"""Reuse an existing standard ledger if present, else create one."""
	for name in preferred:
		full = f"{name} - {ABBR}"
		if frappe.db.exists("Account", {"name": full, "is_group": 0}):
			return full
	return _ensure_ledger(fallback_name, _resolve_group(parent_candidates),
						   root_type, account_type)


def _ensure_accounts() -> dict:
	fa_parent = _resolve_group(FA_PARENTS)
	out = {"fixed_asset": {}}
	for cat in CATEGORIES:
		out["fixed_asset"][cat] = _ensure_ledger(
			cat, fa_parent, "Asset", "Fixed Asset")

	out["accumulated_depreciation"] = _shared_ledger(
		["Accumulated Depreciation"], "Accumulated Depreciation",
		ACCDEP_PARENTS, "Asset", "Accumulated Depreciation")
	out["depreciation_expense"] = _shared_ledger(
		["Depreciation", "Depreciation Expense"], "Depreciation",
		DEPEXP_PARENTS, "Expense", "Depreciation")
	# FR-FA-54 — disposal gain/loss posts to Other Income.
	out["disposal"] = _shared_ledger(
		["Gain or Loss on Asset Disposal", "Gain/Loss on Asset Disposal"],
		"Gain or Loss on Asset Disposal",
		DISPOSAL_PARENTS, "Income", "Income Account")
	frappe.db.commit()
	return out


def _apply_accounts_settings() -> dict:
	"""FR-FA-78 — automatic depreciation posting, no manual intervention."""
	field = "book_asset_depreciation_entry_automatically"
	if frappe.db.get_single_value("Accounts Settings", field) == 1:
		return {field: "already 1"}
	s = frappe.get_single("Accounts Settings")
	s.set(field, 1)
	s.save(ignore_permissions=True)
	return {field: "set 1"}


def _wire_company_defaults(acc: dict) -> dict:
	"""FR-FA-54 disposal account + depreciation defaults on Company."""
	cost_center = frappe.db.get_value("Company", COMPANY, "cost_center")
	patch = {
		"disposal_account": acc["disposal"],
		"depreciation_expense_account": acc["depreciation_expense"],
		"accumulated_depreciation_account": acc["accumulated_depreciation"],
	}
	if cost_center and frappe.db.exists("Cost Center", cost_center):
		patch["depreciation_cost_center"] = cost_center

	current = frappe.db.get_value("Company", COMPANY, list(patch.keys()),
								  as_dict=True) or {}
	changes = {k: {"from": current.get(k), "to": v}
			   for k, v in patch.items() if current.get(k) != v}
	if changes:
		c = frappe.get_doc("Company", COMPANY)
		for k, v in patch.items():
			c.set(k, v)
		c.save(ignore_permissions=True)
	return changes


def _ensure_location() -> str:
	if frappe.db.exists("Location", DEFAULT_LOCATION):
		return f"existing:{DEFAULT_LOCATION}"
	frappe.get_doc({
		"doctype": "Location", "location_name": DEFAULT_LOCATION,
	}).insert(ignore_permissions=True)
	return f"created:{DEFAULT_LOCATION}"


def _ensure_categories(acc: dict) -> list[str]:
	out = []
	for cat, cfg in CATEGORIES.items():
		if frappe.db.exists("Asset Category", cat):
			out.append(f"existing:{cat}")
			continue
		total_deps = cfg["life_years"] * (12 // FREQUENCY_MONTHS)
		frappe.get_doc({
			"doctype": "Asset Category",
			"asset_category_name": cat,
			"enable_cwip_accounting": 0,        # FR-FA-08/31 — no CWIP
			"non_depreciable_category": 0,      # FR-FA-21 — depreciate
			"finance_books": [{
				"depreciation_method": cfg["method"],          # D-FA-1
				"total_number_of_depreciations": total_deps,
				"frequency_of_depreciation": FREQUENCY_MONTHS,  # FR-FA-24
				"daily_prorata_based": 1,                       # FR-FA-25
				"salvage_value_percentage": 0,                  # FR-FA-26
			}],
			"accounts": [{
				"company_name": COMPANY,
				"fixed_asset_account": acc["fixed_asset"][cat],
				"accumulated_depreciation_account":
					acc["accumulated_depreciation"],
				"depreciation_expense_account": acc["depreciation_expense"],
			}],
		}).insert(ignore_permissions=True)
		out.append(f"created:{cat} ({cfg['method']}, {total_deps} q-periods)")
	return out
