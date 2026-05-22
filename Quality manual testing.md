# AKD Quality Module — Manual Testing Script

**Site:** akd.com   **Company:** AKD Consulting LLC   **Tester:** _______________   **Date:** _______________

Source BRD: `AKD_Implementation_BRD_v4` — Section 9 (FR-QA-01 → FR-QA-58).

Setup (run once, as Administrator):
```
bench --site akd.com migrate                                              # ships roles + custom fields
bench --site akd.com execute akd_customizations.setup.quality.setup       # parameter + template + procedures + goal + roles + permissions
bench --site akd.com execute akd_customizations.setup.seed_buying.seed_all # provides the Purchase Receipt the QI references
bench --site akd.com execute akd_customizations.setup.seed_quality.seed_all
```
Enable mandatory inspection on the real item master (run after items are loaded):
```
bench --site akd.com execute akd_customizations.setup.quality.enable_inspection_on_items
```
Reset: `bench --site akd.com execute akd_customizations.setup.seed_quality.purge`

Seed creates: 1 Quality Procedure, 1 Non-Conformance, 1 Quality Review, 1 CAPA
(Quality Action), 1 Incoming Quality Inspection — all tagged `TEST-QA-SEED`.

---

## 0. Pre-requisites

| # | Item | Details |
|---|---|---|
| P1 | Site available | `http://akd.com:8002`, logged in as **Administrator** for setup |
| P2 | C-09 signed off | Incoming Quality Inspection = ON (resolves Quality Q6 vs Q50; matches Buying FR-BUY-46) |
| P3 | Quality setup applied | `quality.setup` run — template `AKD Pass-Fail`, parameter `AKD Acceptance`, 3 procedures, goal `AKD Quality Review`, roles, permissions |
| P4 | Buying seed loaded | `seed_buying.seed_all` (the seeded QI references a TEST-BUY Purchase Receipt) |
| P5 | Test users | Quality Manager, Quality Inspector, Quality Auditor (Administrator OK for solo testing) |

---

## 1. Masters & roles (FR-QA-10, 11, 12, 25, 55)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-QA-01 | FR-QA-10/12 | Quality &gt; Quality Inspection Template &gt; `AKD Pass-Fail` | 1 parameter row `AKD Acceptance`, **non-numeric**, value "Accepted" | |
| TS-QA-02 | FR-QA-11 | Quality Inspection Parameter list | `AKD Acceptance` present (single generic criterion — no measurement params) | |
| TS-QA-03 | FR-QA-25/33 | Quality Procedure list | 3 procedures: Outgoing Deliverable Review, Supplier Quality, Process Deviation | |
| TS-QA-04 | FR-QA-55 | Role List → filter custom | `Quality Inspector`, `Quality Auditor`, `Process Owner` exist; `Quality Manager` native present | |
| TS-QA-05 | FR-QA-55 | Role Profile `AKD Quality` | Bundles Quality Manager + Inspector + Auditor | |

## 2. Incoming inspection — C-09 / FR-QA-48 / FR-QA-14

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-QA-06 | FR-QA-48/12 | Open seeded Quality Inspection `MAT-QA-2026-00001` (remarks ~ "TEST-QA-SEED") | Type **Incoming**, ref = a TEST-BUY Purchase Receipt, template `AKD Pass-Fail`, 1 reading `AKD Acceptance` = Accepted, status **Accepted** | |
| TS-QA-07 | FR-QA-48 | Open the inspected item (from that QI) | `Inspection Required before Purchase` = ticked, template = `AKD Pass-Fail` (set by the seed) | |
| TS-QA-08 | FR-QA-14 | After `enable_inspection_on_items`, create a new Purchase Receipt for an inspection item and try to **Submit** without a QI | System blocks / requires QI before stock acceptance | |
| TS-QA-09 | FR-QA-12 | Create a new Incoming QI, set status **Rejected** | Rejected qty routes to `Rejected - AKD` (ties to Buying FR-BUY-49/50) | |

## 3. Outgoing inspection — FR-QA-08 / FR-QA-09

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-QA-10 | FR-QA-08/09 | Create a Delivery Note for an inspection-required item, try to Submit without QI | QI (type **Outgoing**) required before dispatch | |

## 4. Non-Conformance & CAPA — FR-QA-31..37, 50

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-QA-11 | FR-QA-31/32 | Open seeded Non Conformance (`subject` ~ "TEST-QA-SEED") | **NC Trigger** field present; value = `Process Deviation`; linked to procedure | |
| TS-QA-12 | FR-QA-32 | Edit NC Trigger dropdown | Options: Customer Complaint / Process Deviation / Audit Finding | |
| TS-QA-13 | FR-QA-34/35/36 | Open seeded Quality Action | `corrective_preventive`=Corrective, 1 resolution row with `completion_by` = +14 days, status Open | |
| TS-QA-14 | FR-QA-37 | Same Quality Action | `review` links the seeded Quality Review | |
| TS-QA-15 | FR-QA-50 | Same Quality Action | **Supplier** field present, set to `TEST-BUY-SUPP-001` (corrective-action request to supplier) | |

## 5. Quality Review — FR-QA-26, 27, 30

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-QA-16 | FR-QA-26/30 | Open seeded Quality Review (`additional_information` ~ "TEST-QA-SEED") | Linked to goal `AKD Quality Review` + procedure; status options Open/Passed/Failed | |
| TS-QA-17 | FR-QA-27 | Scheduler / run `quality_review_reminder.send` manually | Monthly reminder email lists any Open review | |

## 6. Supplier quality (reused from Buying) — FR-QA-46, 47, 49

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-QA-18 | FR-QA-46/49 | Supplier Scorecard for a TEST-BUY supplier | `AKD Quality` criterion (25% weight) present; standing computed | |

## 7. Access control — FR-QA-56, 57, 58

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-QA-19 | FR-QA-56 | Log in as Quality Inspector | Can create Quality Inspection (create + submit allowed) | |
| TS-QA-20 | FR-QA-58 | Log in as Quality Auditor | Read-only on all Quality docs (no create/write/submit) | |
| TS-QA-21 | FR-QA-57 | Log in as a plain Employee / Desk user | Non Conformance **not visible** (Management + Quality only) | |

---

## Notes

- **FR-QA-56/57/58 permissions are BUILT** — `setup/quality.apply_permissions()` replaces the over-broad ERPNext defaults (Non Conformance was open to every *Employee*; Quality Action/Review/Procedure to every *Desk User*) with a Management + Quality Custom DocPerm matrix. TS-QA-19..21 should now pass.
- **Quality Goal anchor (design note):** ERPNext v16 makes `Quality Review.goal` mandatory and copies the goal's objectives into the review — a review cannot exist without a Quality Goal. So one placeholder goal `AKD Quality Review` (Monthly, single qualitative objective) is created even though FR-QA-16/19/20 say "no measurable KPIs". **Flag to AKD at sign-off** — platform constraint, not added scope.

## Out of scope (BRD-annotated — confirm, do not test)
Quality Goals/KPIs beyond the anchor (FR-QA-16/19/20) · Quality Feedback (FR-QA-38–41) · MRM meetings/minutes (FR-QA-42–45) · Quality dashboards / trend analysis / MRM data (FR-QA-52–54).

