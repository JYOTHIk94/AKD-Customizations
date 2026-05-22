"""
Exchange-rate configuration — auto-fetch + FX gain/loss accounts.

BRD references:
  FR-ACC-20  — exchange-rate source: auto-fetch (exchangerate.host)
  FR-ACC-21  — unrealised exchange gain/loss handled at period end
  FR-ACC-22  — separate exchange gain/loss account

Setup Wizard already wired Company.exchange_gain_loss_account to the Standard
CoA's "Exchange Gain/Loss - AKD" account. We:
  • try to flip Currency Exchange Settings.service_provider to
    "exchangerate.host" — requires an API key on v16; if AKD has not
    supplied one yet, we leave the default provider (frankfurter.dev,
    free, no key) in place and report status="deferred-missing-key".
  • point Company.unrealized_exchange_gain_loss_account at the same account
    (single-account model — AKD will reclass realised vs unrealised at close)
  • enable auto_exchange_rate_revaluation so period-end revaluation works
"""

import frappe

COMPANY = "AKD Consulting LLC"
ABBR = "AKD"
FX_GAIN_LOSS_ACCOUNT = f"Exchange Gain/Loss - {ABBR}"
TARGET_PROVIDER = "exchangerate.host"


def apply(exchangerate_host_access_key: str | None = None) -> dict:
	return {
		"provider": _set_provider(exchangerate_host_access_key),
		"company_fx": _set_company_fx_accounts(),
	}


def _set_provider(access_key: str | None) -> dict:
	current = frappe.db.get_value(
		"Currency Exchange Settings", None,
		["service_provider", "disabled", "access_key"], as_dict=True,
	) or {}

	if current.get("service_provider") == TARGET_PROVIDER and \
			not current.get("disabled") and current.get("access_key"):
		return {"status": "unchanged", "provider": TARGET_PROVIDER}

	# v16 exchangerate.host requires an access key. Without one, the validate
	# hook throws — so defer the provider switch and document the gap.
	if not access_key:
		return {
			"status": "deferred-missing-key",
			"current_provider": current.get("service_provider"),
			"reason": (
				"FR-ACC-20 requires exchangerate.host but v16 needs an API key. "
				"Re-run with apply(exchangerate_host_access_key='...') once AKD "
				"provisions one. Until then, the default frankfurter.dev provider "
				"keeps daily FX fetch working."
			),
		}

	settings = frappe.get_single("Currency Exchange Settings")
	settings.service_provider = TARGET_PROVIDER
	settings.access_key = access_key
	settings.disabled = 0
	settings.save(ignore_permissions=True)
	return {
		"status": "changed",
		"from": current.get("service_provider"),
		"to": TARGET_PROVIDER,
	}


def _set_company_fx_accounts() -> dict:
	if not frappe.db.exists("Account", FX_GAIN_LOSS_ACCOUNT):
		frappe.throw(
			f"Account {FX_GAIN_LOSS_ACCOUNT!r} missing — "
			"run scaffold_accounts.add first."
		)

	patch = {
		"exchange_gain_loss_account": FX_GAIN_LOSS_ACCOUNT,
		"unrealized_exchange_gain_loss_account": FX_GAIN_LOSS_ACCOUNT,  # FR-ACC-21
		"auto_exchange_rate_revaluation": 1,
	}
	current = frappe.db.get_value("Company", COMPANY, list(patch.keys()), as_dict=True) or {}
	changes = {
		k: {"from": current.get(k), "to": v}
		for k, v in patch.items()
		if current.get(k) != v
	}
	if changes:
		frappe.db.set_value("Company", COMPANY, patch)
	return changes
