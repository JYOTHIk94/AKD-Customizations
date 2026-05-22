"""
Install / migrate hooks for akd_customizations.

Frappe auto-creates Module Def records only during `bench install-app`. Any
modules added to `modules.txt` after the initial install will be missing their
Module Def row. This helper ensures every module declared by this app exists.
"""

import os

import frappe


def ensure_module_defs() -> None:
	app = "akd_customizations"
	modules_txt = frappe.get_app_path(app, "modules.txt")
	if not os.path.isfile(modules_txt):
		return

	with open(modules_txt) as f:
		declared = [line.strip() for line in f if line.strip()]

	for module in declared:
		if frappe.db.exists("Module Def", module):
			frappe.db.set_value("Module Def", module, "app_name", app)
			continue
		frappe.get_doc({
			"doctype": "Module Def",
			"module_name": module,
			"app_name": app,
			"custom": 0,
		}).insert(ignore_permissions=True)

	frappe.db.commit()


def after_install() -> None:
	ensure_module_defs()


def after_migrate() -> None:
	ensure_module_defs()
	_rewire_modes_of_payment_if_company_exists()


def _rewire_modes_of_payment_if_company_exists() -> None:
	"""Standard fixture sync wipes the per-company `accounts` child rows on
	Mode of Payment; re-apply our wiring (Bank Transfer + Cheque → RAK AED)
	after every migrate so the system never sits in a broken state.

	No-op on fresh sites where the AKD company doesn't exist yet.
	"""
	if not frappe.db.exists("Company", "AKD Consulting LLC"):
		return
	try:
		from akd_customizations.setup import modes_of_payment
		modes_of_payment.wire()
	except Exception as e:  # noqa: BLE001 — log and continue migrate
		frappe.log_error(
			title="AKD: Mode of Payment re-wire failed during after_migrate",
			message=str(e),
		)
