# AKD CRM Module — Manual Testing Script

**Site:** akd.com   **Company:** AKD Consulting LLC   **Tester:** _______________   **Date:** _______________

Source BRD: `AKD_Implementation_BRD_v4` — Section 7 (FR-CRM-01 → FR-CRM-69).
CRM is delivered on **ERPNext built-in CRM** (Lead / Opportunity / Prospect) —
no separate Frappe CRM app. v16 note: lead origin = **UTM Source** (the old
"Lead Source" doctype was removed).

Setup (run once, as Administrator):
```
bench --site akd.com migrate                                          # roles + fixtures + permission hooks
bench --site akd.com execute akd_customizations.setup.crm.setup       # UTM sources, opp types, lost reasons, campaigns, assignment rule, reports, permissions
bench --site akd.com execute akd_customizations.setup.seed_crm.seed_all
```
Reset: `bench --site akd.com execute akd_customizations.setup.seed_crm.purge`

Seed creates (tag `TEST-CRM`): 1 UTM Source, 1 Campaign, 1 Opportunity Type,
1 Lost Reason, 1 Prospect, 1 Lead, 1 Opportunity (from the Lead).

---

## 0. Pre-requisites

| # | Item | Details |
|---|---|---|
| P1 | Site available | `http://akd.com:8002`, Administrator for setup |
| P2 | Decisions | D-CRM-1 (won→Customer stage, §12.4 Q65), D-CRM-3/4 acknowledged |
| P3 | crm.setup applied | UTM sources, opp types, lost reasons, campaigns, assignment rule, reports, permissions |
| P4 | Test users | Sales User, Sales Manager, Marketing User, CRM Admin, Read-only Viewer (Administrator OK solo) |

---

## 1. Masters & roles (FR-CRM-06, 19, 20, 30, 63)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-CRM-01 | FR-CRM-06 | UTM Source list | 9 sources (Website…Cold Outreach) present |  |
| TS-CRM-02 | FR-CRM-20 | Opportunity Type list | Advisory, Platforms, Sustained Services, Maintenance |  |
| TS-CRM-03 | FR-CRM-19 | Opportunity Lost Reason list | 5 reasons (Price, Lost to Competitor, …) |  |
| TS-CRM-04 | FR-CRM-30 | Campaign list | 6 header-only campaigns (Email Drip…Social Media) |  |
| TS-CRM-05 | FR-CRM-63 | Role list + Role Profile `AKD CRM` | Marketing User, CRM Admin, Read-only Viewer exist; profile bundles Sales Mgr/User + Marketing User + CRM Admin |  |

## 2. Lead pipeline (FR-CRM-09, 12)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-CRM-06 | FR-CRM-12 | Create a Lead with email `jane.testcrm@example.com` (duplicate of seed) | Blocked — duplicate email (CRM Settings: allow-duplication unchecked) |  |
| TS-CRM-07 | FR-CRM-09 | Assignment Rule `AKD Lead Round Robin` | document_type=Lead, rule=Round Robin; active when Sales Users exist (disabled until then) |  |
| TS-CRM-08 | FR-CRM-06 | Open seeded Lead (`company_name` ~ TEST-CRM) | `utm_source` = `TEST-CRM Source`, status Lead |  |

## 3. Opportunity → won → Customer (FR-CRM-15, 18, 19, 25, 57)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-CRM-09 | FR-CRM-15/20 | Open seeded Opportunity | from Lead, type `TEST-CRM Type`, amount 25000, probability 40 |  |
| TS-CRM-10 | FR-CRM-18/19 | Add a competitor + a lost reason on a test Opportunity | Both selectable from the seeded masters |  |
| TS-CRM-11 | FR-CRM-25 | Set seeded Opportunity status = **Converted** | Customer auto-created from `customer_name` (alert shown); re-saving does not duplicate |  |
| TS-CRM-12 | FR-CRM-57 | From an Opportunity, create Quotation | Quotation opens with AKD Quotation Approval workflow (reused from Selling) |  |

## 4. Territory & data scoping (FR-CRM-26, 64, 65, 66)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-CRM-13 | FR-CRM-64 | Log in as a plain **Sales User** (not Manager), open Lead list | Sees only Leads they own / are assigned |  |
| TS-CRM-14 | FR-CRM-65 | Log in as **Sales Manager** | Sees all Leads & Opportunities |  |
| TS-CRM-15 | FR-CRM-66 | As Sales User, try to delete a Lead | Delete not permitted (only CRM Admin / System Manager) |  |
| TS-CRM-16 | FR-CRM-63 | Log in as **Read-only Viewer** | Read-only on Lead/Opportunity/Prospect/Campaign |  |

## 5. SLA & reports (FR-CRM-41, 44, 59, 61)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-CRM-17 | FR-CRM-41/44 | Run `crm_first_response_overdue.send` with an old un-actioned Lead | Breach digest email lists the lead (24h default window — CRP Q48) |  |
| TS-CRM-18 | FR-CRM-59 | Run report **AKD CRM Territory-wise Analysis** | Opportunities grouped by territory with pipeline value |  |
| TS-CRM-19 | FR-CRM-59 | Run report **AKD CRM Forecast / Revenue Projection** | Open opps with weighted (amount × probability) value |  |
| TS-CRM-20 | FR-CRM-59 | Standard reports: Sales Pipeline Analytics, Lead Details, Campaign Efficiency, First Response Time | Available and return data |  |

---

## Notes
- **D-CRM-1 (FR-CRM-25 vs 56):** won→Customer is built on status **Converted**; AKD confirms the exact stage at sign-off (§12.4 Q65).
- **D-CRM-3:** "lead scoring" = standard qualification status (ERPNext v16 has no numeric lead score).
- **D-CRM-4:** ERPNext has a single global Sales Stage list — pipelines are segmented via Opportunity Type, not separate stage sets.
- **CRP inputs:** lost-reason list (Q22), territory list (Q30), SLA targets (Q48), CRM-sync company (Q68), migration source/volumes (Q79/Q81).

## Out of scope (BRD-annotated — do not test)
Web-form capture (07) · Kanban (17) · drip/open-click/unsubscribe (31/33/34) · WhatsApp/SMS/social (35) · email send-receive (36) · call logging (37) · telephony (38) · working-hours SLA (45) · appointments (46–49) · contract templates/e-sign/milestones/expiry (51–54) · custom dashboards (60).
