"""
Master-data scaffold — Customer Groups, Supplier Groups, Territories.

BRD references:
  FR-SELL-05 — Customer classification dimensions: Customer Groups
               (Oil & Gas, Utility, Government, Marine, Telecom, Banking,
               Healthcare), Region, Account Group (Domestic/Export), Industry
  FR-SELL-07 — Hierarchical customer groups required
  FR-SELL-13..17 — Territories: Africa and Middle East (hierarchical)
  FR-BUY-07 — Supplier classification: Indigenous, Foreign, Service-based,
              Critical, Non-Critical, currency-based
  FR-BUY-08 — Supplier groups: OEM, non-OEM

This module covers the GROUP / TERRITORY hierarchies only. The classification
dimensions (Indigenous/Foreign, Domestic/Export, Industry) are implemented
as Custom Fields shipped via fixtures/custom_field.json.

Sales Persons + Commission scaffolding (FR-SELL-55..62) is deferred — needs
AKD-confirmed Sales Person list which is still open.
"""

import frappe

# ─── Customer Groups (industries that buy from AKD) ──────────────────────────
# Per FR-SELL-05; AKD said the explicit list "to be created in ERP per
# standard". This is Quark's recommendation, easy to extend.
CUSTOMER_GROUPS = {
	"AKD Industries": {  # parent group under All Customer Groups
		"is_group": 1,
		"children": [
			"Oil & Gas",
			"Utility",
			"Government",
			"Marine",
			"Telecom",
			"Banking & Finance",
			"Healthcare",
			"Aviation",
		],
	},
}

# ─── Supplier Groups (FR-BUY-08) ────────────────────────────────────────────
SUPPLIER_GROUPS = ["OEM", "non-OEM"]

# ─── Territories (FR-SELL-13..17) ────────────────────────────────────────────
# Hierarchical: Africa and Middle East (Africa & ME explicit in BRD Q17).
# Sub-regions are illustrative — AKD's Q30 left territory specifics blank,
# so these are placeholders matched to AKD's likely sales footprint.
TERRITORIES = {
	"Middle East": {
		"is_group": 1,
		"children": [
			"United Arab Emirates",   # already exists from Setup Wizard
			"Saudi Arabia",
			"Qatar",
			"Kuwait",
			"Oman",
			"Bahrain",
		],
	},
	"Africa": {
		"is_group": 1,
		"children": [
			"Nigeria",
			"South Africa",
			"Kenya",
			"Egypt",
			"Ghana",
		],
	},
}


def setup() -> dict:
	return {
		"customer_groups": _ensure_customer_groups(),
		"supplier_groups": _ensure_supplier_groups(),
		"territories": _ensure_territories(),
	}


def _ensure_customer_groups() -> list[str]:
	created = []
	for parent_name, spec in CUSTOMER_GROUPS.items():
		if not frappe.db.exists("Customer Group", parent_name):
			doc = frappe.get_doc({
				"doctype": "Customer Group",
				"customer_group_name": parent_name,
				"parent_customer_group": "All Customer Groups",
				"is_group": 1,
			})
			doc.insert(ignore_permissions=True)
			created.append(parent_name)

		for child in spec["children"]:
			if frappe.db.exists("Customer Group", child):
				# If exists but wrong parent, re-parent under our AKD parent
				current_parent = frappe.db.get_value(
					"Customer Group", child, "parent_customer_group",
				)
				if current_parent != parent_name:
					frappe.db.set_value(
						"Customer Group", child, "parent_customer_group", parent_name,
					)
					created.append(f"reparented:{child}")
				continue
			doc = frappe.get_doc({
				"doctype": "Customer Group",
				"customer_group_name": child,
				"parent_customer_group": parent_name,
				"is_group": 0,
			})
			doc.insert(ignore_permissions=True)
			created.append(child)
	return created


def _ensure_supplier_groups() -> list[str]:
	created = []
	for name in SUPPLIER_GROUPS:
		if frappe.db.exists("Supplier Group", name):
			continue
		doc = frappe.get_doc({
			"doctype": "Supplier Group",
			"supplier_group_name": name,
			"parent_supplier_group": "All Supplier Groups",
			"is_group": 0,
		})
		doc.insert(ignore_permissions=True)
		created.append(name)
	return created


def _ensure_territories() -> list[str]:
	created = []
	for parent_name, spec in TERRITORIES.items():
		if not frappe.db.exists("Territory", parent_name):
			doc = frappe.get_doc({
				"doctype": "Territory",
				"territory_name": parent_name,
				"parent_territory": "All Territories",
				"is_group": 1,
			})
			doc.insert(ignore_permissions=True)
			created.append(parent_name)

		for child in spec["children"]:
			if frappe.db.exists("Territory", child):
				current_parent = frappe.db.get_value(
					"Territory", child, "parent_territory",
				)
				if current_parent != parent_name:
					frappe.db.set_value(
						"Territory", child, "parent_territory", parent_name,
					)
					created.append(f"reparented:{child}")
				continue
			doc = frappe.get_doc({
				"doctype": "Territory",
				"territory_name": child,
				"parent_territory": parent_name,
				"is_group": 0,
			})
			doc.insert(ignore_permissions=True)
			created.append(child)
	return created
