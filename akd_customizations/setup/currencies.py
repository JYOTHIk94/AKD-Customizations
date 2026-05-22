"""
Multi-currency enablement.

BRD: FR-ACC-19 — Transaction currencies USD, AED.
     FR-BUY-74 — Multi-currency purchasing: USD, EUR, GBP, AED, NGN.
     FR-SELL-72 — Sales: USD, NGN, AED + potentially other African ccys.
     FR-BUY-75 — Exchange rates on transaction date.

What this does (idempotent):
  • Enables AED, USD, EUR, GBP, NGN on the global Currency master.
  • Seeds today's reference rates if a row for today doesn't already exist
    (the existing 90-day-old seed in seed_data.py covers historical posting).

Note: setup/seed_data.py also seeds these FX rates 90 days back so historical
SI/PI postings find a rate. This module ensures TODAY has rates so new
transactions don't hit "stale" rule (Accounts Settings stale_days = 365).

Usage:
  bench --site akd.com execute akd_customizations.setup.currencies.setup
"""

from datetime import date

import frappe

CURRENCIES = ["AED", "USD", "EUR", "GBP", "NGN"]

# Reference rates against AED (current ~2026 levels). AKD edits at sign-off.
FX_RATES_TO_AED = {
	"USD": 3.6725,
	"EUR": 4.00,
	"GBP": 4.65,
	"NGN": 0.0040,
}


def setup() -> dict:
	enabled = _enable_currencies()
	rates_seeded = _seed_today_rates()
	frappe.db.commit()
	return {"enabled": enabled, "today_fx_rates": rates_seeded}


def _enable_currencies() -> list[str]:
	results = []
	for ccy in CURRENCIES:
		if not frappe.db.exists("Currency", ccy):
			results.append(f"missing:{ccy}")
			continue
		current = frappe.db.get_value("Currency", ccy, "enabled")
		if current:
			results.append(f"already-enabled:{ccy}")
			continue
		frappe.db.set_value("Currency", ccy, "enabled", 1)
		results.append(f"enabled:{ccy}")
	return results


def _seed_today_rates() -> list[str]:
	today = date.today()
	results = []
	for from_ccy, rate in FX_RATES_TO_AED.items():
		if frappe.db.exists("Currency Exchange", {
			"from_currency": from_ccy, "to_currency": "AED", "date": today,
		}):
			results.append(f"exists:{from_ccy}-AED-{today}")
			continue
		doc = frappe.get_doc({
			"doctype": "Currency Exchange",
			"from_currency": from_ccy,
			"to_currency": "AED",
			"date": today,
			"exchange_rate": rate,
			"for_buying": 1,
			"for_selling": 1,
		})
		doc.insert(ignore_permissions=True)
		results.append(f"created:{doc.name}")
	return results
