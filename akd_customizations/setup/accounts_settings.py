"""
Accounts Settings — global accounting flags per the BRD.

BRD references:
  FR-ACC-78  — over-billing above delivery/order not allowed (allowance = 0)
  FR-ACC-79  — periodic inventory (perpetual disabled at Company level;
               Quark's recommendation to switch to perpetual stays parked)
  FR-ACC-80  — stale exchange rates not allowed; stale_days = 365
  FR-ACC-81  — automatic party matching = Yes
  FR-ACC-82  — unlink payment on cancellation of invoice = Yes
"""

import frappe

STALE_DAYS = 365


def apply() -> dict:
	settings = frappe.get_single("Accounts Settings")

	changes = {}

	def _set(field: str, value):
		if settings.get(field) != value:
			changes[field] = {"from": settings.get(field), "to": value}
			settings.set(field, value)

	# FR-ACC-78: over-billing allowance = 0%
	_set("over_billing_allowance", 0)

	# FR-ACC-80: do NOT allow stale exchange rates; cap at 365 days
	_set("allow_stale", 0)
	_set("stale_days", STALE_DAYS)

	# FR-ACC-81: automatic party matching on payment reconciliation
	_set("automatically_fetch_payment_terms", 1)

	# FR-ACC-82: unlink payment on cancellation
	_set("unlink_payment_on_cancellation_of_invoice", 1)

	# Defer accounting entries are auto-processed monthly if AKD ever enables
	# deferred revenue/expense (FR-ACC-62). They are NOT enabled today
	# (FR-ACC-60, FR-ACC-61) — flag is harmless when no deferred docs exist.
	_set("automatically_process_deferred_accounting_entry", 1)

	if changes:
		settings.save(ignore_permissions=True)

	return changes
