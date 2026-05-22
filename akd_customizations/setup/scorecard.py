"""
Supplier Scorecard provisioning helper.

BRD references (Section 5):
  FR-BUY-15  Supplier performance evaluation — Yes
  FR-BUY-16  KPIs: On-time Delivery, Quality, Pricing, Responsiveness, Compliance
  FR-BUY-17  Evaluation frequency — Quarterly (mapped to 'Per Month' in ERPNext
             and aggregated quarterly via report — Frappe doesn't ship a
             Quarterly period option)
  FR-BUY-18  Poor performers — warn only, no auto-block
  FR-BUY-19  Scorecard reports for management review

The 5 Criteria masters and 4 Standing masters ship as fixtures
(fixtures/supplier_scorecard_criteria.json + supplier_scorecard_standing.json).

This module attaches per-supplier Supplier Scorecard records that reference
those masters. Idempotent — re-running on an existing scorecard is a no-op.

Usage:
  bench --site dhh.com execute \\
    akd_customizations.setup.scorecard.attach_to_all_suppliers

  bench --site dhh.com execute \\
    akd_customizations.setup.scorecard.attach_to_supplier \\
    --kwargs "{'supplier': 'Acme Trading'}"
"""

import frappe

CRITERIA = [
	("AKD On-Time Delivery", 30.0),
	("AKD Quality", 25.0),
	("AKD Pricing Competitiveness", 20.0),
	("AKD Responsiveness", 15.0),
	("AKD Compliance", 10.0),
]

STANDINGS = [
	("AKD Excellent", "Green", 80.0, 100.0),
	("AKD Good", "Blue", 60.0, 79.99),
	("AKD Average", "Yellow", 40.0, 59.99),
	("AKD Poor", "Red", 0.0, 39.99),
]

PERIOD = "Per Month"


def attach_to_all_suppliers() -> dict:
	results = {"attached": [], "already_present": [], "errors": []}
	suppliers = frappe.get_all("Supplier", filters={"disabled": 0}, pluck="name")
	for supplier in suppliers:
		try:
			outcome = attach_to_supplier(supplier)
			results[outcome].append(supplier)
		except Exception as e:
			results["errors"].append({"supplier": supplier, "reason": str(e)})
	frappe.db.commit()
	return results


def attach_to_supplier(supplier: str) -> str:
	if frappe.db.exists("Supplier Scorecard", {"supplier": supplier}):
		return "already_present"

	doc = frappe.get_doc({
		"doctype": "Supplier Scorecard",
		"supplier": supplier,
		"period": PERIOD,
		"weighting_function": (
			"{total_score} = "
			+ " + ".join(f"({{{c.lower().replace(' ', '_').replace('-','_')}}})" for c, _ in CRITERIA)
		),
		"criteria": [
			{
				"criteria_name": name,
				"weight": weight,
				"max_score": 100.0,
				"formula": frappe.db.get_value("Supplier Scorecard Criteria", name, "formula"),
			}
			for name, weight in CRITERIA
		],
		"standings": [
			{
				"standing_name": name,
				"standing_color": color,
				"min_grade": lo,
				"max_grade": hi,
				"warn_rfqs": 1 if name in ("AKD Average", "AKD Poor") else 0,
				"warn_pos": 1 if name in ("AKD Average", "AKD Poor") else 0,
				"prevent_rfqs": 0,
				"prevent_pos": 0,
				"notify_employee": 1 if name in ("AKD Average", "AKD Poor") else 0,
			}
			for name, color, lo, hi in STANDINGS
		],
		# FR-BUY-18: warn only at scorecard level too
		"warn_rfqs": 1,
		"warn_pos": 1,
		"prevent_rfqs": 0,
		"prevent_pos": 0,
	})
	doc.insert(ignore_permissions=True)
	return "attached"
