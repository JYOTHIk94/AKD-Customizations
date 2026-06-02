"""
Timesheet doc_event hooks.

BRD references:
  FR-PROJ-30  Time-logging granularity: Hours.
  FR-PROJ-33  Prevent overlapping time entries: Yes.
"""

import frappe
from frappe import _
from frappe.utils import flt, get_datetime


def validate_hour_granularity(doc, method=None) -> None:
	"""FR-PROJ-30 — hours must be > 0 and ≤ 24 per log row."""
	for row in (doc.time_logs or []):
		hours = flt(row.hours)
		if hours <= 0 or hours > 24:
			frappe.throw(
				_("Time log hours must be between 0 and 24 (FR-PROJ-30). "
				  "Got {0} on row {1}.").format(hours, row.idx),
				title=_("Invalid Time Log Hours"),
			)


def validate_no_overlap(doc, method=None) -> None:
	"""FR-PROJ-33 — block overlap with submitted Timesheets for same employee.

	In-document overlap (between rows of the current timesheet) is also caught.
	"""
	employee = doc.get("employee")
	if not employee:
		return

	rows = [
		(get_datetime(r.from_time), get_datetime(r.to_time), r.idx)
		for r in (doc.time_logs or [])
		if r.get("from_time") and r.get("to_time")
	]

	# In-document overlap.
	for i, (a_start, a_end, a_idx) in enumerate(rows):
		for b_start, b_end, b_idx in rows[i + 1:]:
			if a_start < b_end and b_start < a_end:
				frappe.throw(
					_("Time logs overlap between rows {0} and {1} "
					  "(FR-PROJ-33).").format(a_idx, b_idx),
					title=_("Overlapping Time Logs"),
				)

	# Cross-document overlap (vs other submitted/draft timesheets).
	for start, end, idx in rows:
		clash = frappe.db.sql(
			"""
			SELECT ts.name, tsl.idx
			FROM `tabTimesheet Detail` tsl
			JOIN `tabTimesheet` ts ON ts.name = tsl.parent
			WHERE ts.employee = %s
			  AND ts.name != %s
			  AND ts.docstatus < 2
			  AND tsl.from_time < %s
			  AND tsl.to_time > %s
			LIMIT 1
			""",
			(employee, doc.name or "", end, start),
		)
		if clash:
			frappe.throw(
				_("Row {0} overlaps Timesheet {1} row {2} (FR-PROJ-33).").format(
					idx, clash[0][0], clash[0][1]
				),
				title=_("Overlapping Time Logs"),
			)
