# AKD Projects Module — Manual Testing Script

**Site:** akd.com   **Company:** AKD Consulting LLC   **Tester:** _______________   **Date:** _______________

Source BRD: `AKD_Implementation_BRD_v4` — Section 8 (FR-PROJ-01 → FR-PROJ-63).
Delivered on ERPNext built-in Projects + a **lite-HR footprint** (Employee,
Holiday List, Activity Type/Cost — payroll/leave out, D-PROJ-1).

Setup (run once, as Administrator):
```
bench --site akd.com migrate                                            # roles + workflows + fixtures + permission hooks
bench --site akd.com execute akd_customizations.setup.projects.setup    # types, activities, holiday list, settings, workflows, perms
bench --site akd.com execute akd_customizations.setup.seed_projects.seed_all
```
Reset: `bench --site akd.com execute akd_customizations.setup.seed_projects.purge`

---

## 0. Pre-requisites

| # | Item | Details |
|---|---|---|
| P1 | Site available | `http://akd.com:8002`, Administrator |
| P2 | Decisions | D-PROJ-1 lite-HR in scope, D-PROJ-2 no templates, D-PROJ-3 status workflow, D-PROJ-5 portal — acknowledged |
| P3 | projects.setup applied | Project/Task/Activity types, Holiday List, workflows, permissions |
| P4 | Test users | Projects Manager, Projects User, Timesheet User, Read-only Viewer |

---

## 1. Masters & lite-HR (FR-PROJ-06, 20, 31, 53, 60)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-PROJ-01 | FR-PROJ-06 | Project Type list | Advisory, AI, IT Implementation |  |
| TS-PROJ-02 | FR-PROJ-20 | Task Type list | Analysis, Design, Development, Review, Deployment, Project Management |  |
| TS-PROJ-03 | FR-PROJ-31 | Activity Type list | Consulting, Implementation, Project Management, Support, Travel (rates 0 — CRP) |  |
| TS-PROJ-04 | FR-PROJ-53/54 | Company → default holiday list | `AKD Holidays <year>` set; weekly-off rows present |  |
| TS-PROJ-05 | FR-PROJ-60 | Role list + Role Profile `AKD Projects` | Timesheet User exists; profile = Projects Mgr/User + Timesheet User |  |
| TS-PROJ-06 | FR-PROJ-38 | Open seeded Activity Cost | Consulting @ employee: costing 150 / billing 300 |  |

## 2. Project & tasks (FR-PROJ-08, 18, 22, 23, 27)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-PROJ-07 | FR-PROJ-06/36 | Open seeded `TEST-PROJ Alpha` | type Advisory, estimated cost 50000, % method = Task Weight |  |
| TS-PROJ-08 | FR-PROJ-18/22 | Tasks tab | `Discovery` (wt 0.4) + `Go-Live` (wt 0.6, **milestone**, depends on Discovery) |  |
| TS-PROJ-09 | FR-PROJ-23 | Mark Discovery Completed | Project % complete moves ~40% (weighted) |  |
| TS-PROJ-10 | FR-PROJ-27 | Use the **AKD Project Status** workflow: Start → In Progress → Complete | Transitions gated (Start=Projects User, Complete=Projects Manager) |  |

## 3. Timesheets & costing (FR-PROJ-28, 32, 33, 45, 46, 63)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-PROJ-11 | FR-PROJ-28/46 | Open seeded Timesheet | 4 billable hrs, activity Consulting, linked to project |  |
| TS-PROJ-12 | FR-PROJ-33 | Add an overlapping time log (same employee, same window) | Blocked — overlapping time entries not allowed |  |
| TS-PROJ-13 | FR-PROJ-32/63 | Run the **AKD Timesheet Approval** workflow: Submit for Approval → Approve | Submit=Timesheet User; Approve=Projects Manager → docstatus Submitted |  |
| TS-PROJ-14 | FR-PROJ-45 | From the approved Timesheet, create Sales Invoice | SI fetches billable hours (Projects Settings) |  |

## 4. Governance (FR-PROJ-61, 62)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-PROJ-15 | FR-PROJ-61 | Log in as **Projects User**, try to create a Project | Not permitted (only Projects Manager / System Manager create) |  |
| TS-PROJ-16 | FR-PROJ-62 | Log in as a user not on the project team, open Project list | Sees only projects they own / are a team member of |  |
| TS-PROJ-17 | FR-PROJ-60 | Log in as Read-only Viewer | Read-only on Project/Task/Timesheet |  |

## 5. Reports & digest (FR-PROJ-49, 56, 58, 41)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-PROJ-18 | FR-PROJ-49/56 | Run report **AKD Resource Utilization** | Hours / billable hrs / utilization % by employee+activity+project |  |
| TS-PROJ-19 | FR-PROJ-56/41 | Run standard **Project Profitability** / **Project Summary** | Return data; cost vs billed reconciles |  |
| TS-PROJ-20 | FR-PROJ-24/25/58 | Run `project_status_digest.send` | Weekly snapshot email: active projects + overdue task count |  |

---

## Notes
- **D-PROJ-1 (lite HR):** Employee/Holiday List/Activity Cost are set up; payroll, leave, attendance are NOT in scope.
- **D-PROJ-2:** no Project Templates (FR-PROJ-11/12 = No).
- **D-PROJ-3:** Open→In Progress→Completed delivered via the **AKD Project Status** workflow (`workflow_state`); native `Project.status` stays Open/Completed/Cancelled for system logic.
- **CRP §12.5:** Activity Type **rates are 0** (Q34) and the Holiday List is a Fri/Sat **placeholder** (Q12) — AKD supplies real rates and the official UAE public-holiday calendar at CRP.
- Retainer/subscription billing (FR-PROJ-43) reuses Selling Auto Repeat (FR-SELL-75).

## Out of scope
Project templates (FR-PROJ-11/12) · §12.5 parking-lot Q67–71 · full HRMS (payroll/leave/attendance — only the lite footprint is in scope).

