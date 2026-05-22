"""
Opportunity doc_event — auto-create ERPNext Customer on deal won.

BRD: FR-CRM-25 — auto-create Customer from CRM deal on deal won.
     (Conflict D-CRM-1: FR-CRM-56 marks this "out of scope"; §12.4 Q65 — the
     exact stage — is blank. Implemented on status = "Converted"; AKD changes
     the trigger stage at sign-off.)

Idempotent: skips if the party is already a Customer or one with the same
name already exists.
"""

import frappe

WON_STATUS = "Converted"


def _leaf_customer_group(preferred: str | None) -> str:
	"""Customer.customer_group must be a non-group node."""
	if preferred and not frappe.db.get_value("Customer Group", preferred, "is_group"):
		return preferred
	default = frappe.db.get_single_value("Selling Settings", "customer_group")
	if default and not frappe.db.get_value("Customer Group", default, "is_group"):
		return default
	leaf = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
	if not leaf:
		frappe.throw("No non-group Customer Group exists to assign the Customer.")
	return leaf


def create_customer_on_won(doc, method=None) -> None:
	if doc.status != WON_STATUS:
		return
	if doc.opportunity_from == "Customer":
		return

	cust_name = (doc.customer_name or "").strip()
	if not cust_name or frappe.db.exists("Customer", cust_name):
		return

	customer = frappe.get_doc({
		"doctype": "Customer",
		"customer_name": cust_name,
		"customer_type": "Company",
		"customer_group": _leaf_customer_group(doc.get("customer_group")),
	})
	# Territory link on Customer must be a leaf — only carry it if non-group.
	terr = doc.get("territory")
	if terr and not frappe.db.get_value("Territory", terr, "is_group"):
		customer.territory = terr
	customer.flags.ignore_permissions = True
	customer.insert()
	frappe.msgprint(
		f"Customer <b>{customer.name}</b> created from won opportunity "
		f"{doc.name} (FR-CRM-25).",
		alert=True,
	)
