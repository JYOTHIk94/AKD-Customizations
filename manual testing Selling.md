# AKD Selling Module — Manual Testing Script

**Site:** akd.com   **Company:** AKD Consulting LLC   **Tester:** _______________   **Date:** _______________

Source BRD: `AKD_Implementation_BRD_v4` — Section 6 (FR-SELL-01 → FR-SELL-93).

Seed runs:
```
bench --site akd.com execute akd_customizations.setup.seed_data.seed_all       # accounting + customer masters
bench --site akd.com execute akd_customizations.setup.seed_selling.seed_all    # selling masters + transactions
```

Reset:
```
bench --site akd.com execute akd_customizations.setup.seed_selling.purge
```

---

## 0. Pre-requisites

| # | Item | Details |
|---|---|---|
| P1 | Admin access | Logged in as **Administrator** for solo testing |
| P2 | Selling Settings applied | SO Required = Yes; DN Required = Yes; Rate consistency = Stop; Validate Selling Price = Yes |
| P3 | Master data loaded | Customer Groups (8) + Territories (UAE + Africa) per master_data |
| P4 | Customer custom fields visible | Account Group + Industry on Customer form |
| P5 | Seed transactions loaded | Quotations / SOs / DNs / SIs / returns / pricing rules from seed_selling |
| P6 | Test users (optional) | Sales User, Sales Manager, Accounts Manager, Stock User |

---

## 1. Customer Master (FR-SELL-05 → 13)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-01 | FR-SELL-05 | CRM → Customer → New. Look at **Customer Group** dropdown. | Shows Oil & Gas, Utility, Government, Marine, Telecom, Banking & Finance, Healthcare, Aviation. |  |
| TS-SELL-02 | FR-SELL-05 | Same form — open the **AKD Segmentation** section. | Account Group (Domestic / Export) + Industry (8 BRD industries + Other) fields visible. |  |
| TS-SELL-03 | FR-SELL-07 | Customer → Customer Group tree view. | Hierarchical structure: AKD Industries → 8 child groups. |  |
| TS-SELL-04 | FR-SELL-13/14 | Open Territory tree. | Middle East (UAE/SA/QA/KW/OM/BH) and Africa (NG/ZA/KE/EG/GH). |  |
| TS-SELL-05 | FR-SELL-09 | Open `TEST-CUST-001 ADNOC Test`. Credit Limits tab. | Row for AKD Consulting LLC with 500 000 AED. |  |
| TS-SELL-06 | FR-SELL-09 | Create new SI for ADNOC totalling 5 M AED. Submit. | Stopped — `validate_credit_limit` hook throws Credit Limit Exceeded. |  |
| TS-SELL-07 | FR-SELL-08 | Customer → New → **Customer Type**. | Options: Company / Individual / Partnership. |  |
| TS-SELL-08 | FR-SELL-10 | Internal customer flag on a customer. | `is_internal_customer` checkbox available. |  |

---

## 2. Quotation Workflow (FR-SELL-18 → 27)

Seed:
- `SAL-QTN-2026-00001` — Draft, 5 hardware boxes to ADNOC, AED
- `SAL-QTN-2026-00002` — Pending Approval, 20 consulting days to First Bank Nigeria, USD

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-09 | FR-SELL-18 | Selling → Quotation → New. | Form opens; "Customer" / "Lead" picker. |  |
| TS-SELL-10 | FR-SELL-19 | Pick `Quotation To = Lead` and choose any lead. | Lead-based quote saves. |  |
| TS-SELL-11 | FR-SELL-20 | Open `SAL-QTN-2026-00001`. **Valid Till** field. | 30 days from today. |  |
| TS-SELL-12 | FR-SELL-21 | After expiry, change status to Lost. **Lost Reason** field. | Dropdown: Price / Competitor Selected / Timing / Technical Fit / Budget Withdrawn / No Decision / Other. |  |
| TS-SELL-13 | FR-SELL-22 | On `SAL-QTN-2026-00001` — **Competitor** field. | Shows "VendorX". |  |
| TS-SELL-14 | FR-SELL-23 | Open `SAL-QTN-2026-00001`. Click **Submit for Approval**. | State → Pending Approval. Sales Manager receives email. |  |
| TS-SELL-15 | FR-SELL-23 | (As Sales Manager) Open `SAL-QTN-2026-00002` → **Approve**. | State → Approved, docstatus = 1. Customer email goes out with AKD Quotation print attached. |  |
| TS-SELL-16 | FR-SELL-23 | (As Sales Manager) Click **Reject** on a Pending Approval quote. | State → Rejected. |  |
| TS-SELL-17 | FR-SELL-24 | From an expired (post valid_till) submitted quotation, click "Create → Sales Order". | Allowed — Selling Settings has `allow_sales_order_creation_for_expired_quotation = 1`. |  |
| TS-SELL-18 | FR-SELL-27 | From an Approved quote, create SO. | SO drafts with quote items + rates. |  |

---

## 3. Sales Order Workflow (FR-SELL-25 → 36)

Seed:
- `SAL-ORD-2026-00001` — Draft
- `SAL-ORD-2026-00002` — Pending Finance Review (customer PO: CUST-NG-2026-PO-001)
- `SAL-ORD-2026-00003` — **Approved + submitted** (customer PO: CUST-UAE-2026-PO-042, installation required)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-19 | FR-SELL-25 | Open `SAL-ORD-2026-00001`. **Submit for Approval**. | State → Pending Sales Manager. |  |
| TS-SELL-20 | FR-SELL-27 | (As Sales Manager) **Approve** `SAL-ORD-2026-00001`. | State → Pending Finance Review. Email to Accounts Manager. |  |
| TS-SELL-21 | FR-SELL-27 | (As Accounts Manager) **Approve** `SAL-ORD-2026-00002`. | State → Approved, docstatus = 1. Customer email + warehouse email with SO print. |  |
| TS-SELL-22 | FR-SELL-28 | Open `SAL-ORD-2026-00003`. **Customer PO No** field. | Shows "CUST-UAE-2026-PO-042". |  |
| TS-SELL-23 | FR-SELL-29 | Try to create another SO with same po_no. | Allowed — multiple SOs per customer PO permitted. |  |
| TS-SELL-24 | FR-SELL-30 | Each SO line has its own **Delivery Date**. | Field present per row. |  |
| TS-SELL-25 | FR-SELL-32 | On a submitted SO, click **Close**. Then **Re-open**. | Status toggles Closed ↔ Submitted. |  |
| TS-SELL-26 | FR-SELL-36 | Open `SAL-ORD-2026-00003`. Tick **Place On Hold**. | Hold Reason becomes mandatory. |  |

---

## 4. Pricing Rules (FR-SELL-33 → 46)

Seed:
- `TEST-SELL-RULE-Volume-10pct` — 10% off HW-A when qty ≥ 10
- `TEST-SELL-RULE-Government-5pct` — 5% off all Products + Services for Government customers

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-27 | FR-SELL-33 | Stock → Item Price. | Shows entries for TEST-SELL items. |  |
| TS-SELL-28 | FR-SELL-37 | Create new SO for ADNOC (Govt customer) with 5 of HW-A. | TEST-SELL-RULE-Government-5pct kicks in; 5% off applied automatically. |  |
| TS-SELL-29 | FR-SELL-37 | Change qty to 12. | Both rules eligible; system picks the one configured first per ranking. (Document which.) |  |
| TS-SELL-30 | FR-SELL-39 | Selling → Pricing Rule → New. Use **Product Discount** to add Buy 5 Get 1 Free. | Rule saves; tested via SO. |  |
| TS-SELL-31 | FR-SELL-40 | Edit a rule; set "Min Margin %". | Field present; honoured at SO entry. |  |
| TS-SELL-32 | FR-SELL-41 | New SO for HW-A at rate 1 AED (below valuation 6 500). | Stopped — Selling Settings validate_selling_price = 1. |  |
| TS-SELL-33 | FR-SELL-42 | On an SO line, edit price-list rate manually. | Allowed — `editable_price_list_rate = 1`. |  |
| TS-SELL-34 | FR-SELL-43 | Create Quotation at 100 / SO at 90 / SI at 80. | SI submission **stopped** — `maintain_same_rate_action = Stop`. |  |
| TS-SELL-35 | FR-SELL-44 | Create a Product Bundle (Stock → Product Bundle → New) including HW-A + Consulting. | Bundle saves and is sellable. |  |

---

## 5. Delivery Note + Installation (FR-SELL-61 → 67)

Seed: `MAT-DN-2026-00001` (3 HW-A units from SO-03, installation=Pending)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-36 | FR-SELL-26 | Try to create a Sales Invoice without a Delivery Note. | System throws — DN Required = Yes. |  |
| TS-SELL-37 | FR-SELL-61 | Open `MAT-DN-2026-00001`. | DN form; AKD Dispatch section visible. |  |
| TS-SELL-38 | FR-SELL-62 | Open `SAL-ORD-2026-00003`. Verify partial delivery. | 3 of 3 already delivered. Could create another DN for residual qty if SO had more. |  |
| TS-SELL-39 | FR-SELL-63 | Open SO with Drop Ship line. | Drop Ship checkbox per item; sets supplier. (Allowed by BRD.) |  |
| TS-SELL-40 | FR-SELL-64 | Submit SO. Open Item ledger → Reserved Qty. | qty reserved appears (if perpetual; periodic skips this). |  |
| TS-SELL-41 | FR-SELL-65 | On `SAL-ORD-2026-00003`. **Installation Required** flag set; **Dispatch Priority = Urgent**. | Values shown. |  |
| TS-SELL-42 | FR-SELL-65 | Open `MAT-DN-2026-00001`. **Installation Status** field. | Set to Pending. Change to In Progress → Completed. |  |
| TS-SELL-43 | FR-SELL-66 | From DN → Print → packing slip. | Packing slip prints. |  |
| TS-SELL-43b | — | DN custom field — **Gate Pass No** | Shows "GP-2026-00012" on seed DN. |  |

---

## 6. Customer Returns + Credit Notes (FR-SELL-68 → 71)

Seed: `MAT-DN-2026-00002` (return of 1 HW-A) + `ACC-SINV-2026-00014` (credit note)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-44 | FR-SELL-68 | Open `MAT-DN-2026-00002`. | Return DN, qty = -1, reason = Damaged. |  |
| TS-SELL-45 | FR-SELL-69 | From `ACC-SINV-2026-00013` (positive SI) → "Create → Return / Credit Note". | New SI opens with `is_return = 1`, qty negative. |  |
| TS-SELL-46 | FR-SELL-70 | Submit the credit note. | Customer balance decreases by the return amount. |  |
| TS-SELL-47 | FR-SELL-71 | (As Sales User) try to submit a credit note. | Blocked — only Sales Manager / Accounts Manager allowed. (Permission test.) |  |
| TS-SELL-48 | FR-SELL-72 | Customers can return goods → enabled across modules. | Confirmed via the seeded chain. |  |

---

## 7. Multi-currency Sales (FR-SELL-72 → 73)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-49 | FR-SELL-72 | New SO for `TEST-CUST-002 First Bank Nigeria Test`. | Currency defaults to USD; conversion rate populated. |  |
| TS-SELL-50 | FR-SELL-73 | Look at customer's **Default Currency**. | USD. |  |
| TS-SELL-51 | FR-SELL-72 | Change SO currency to NGN. | NGN available in dropdown; conversion rate auto-fetched. |  |
| TS-SELL-52 | — | Try EUR, GBP. | Both enabled per Currency master; rates seeded today. |  |

---

## 8. Sales Partners + Commission (FR-SELL-55 → 60)

Seed: `AKD OEM Partner Placeholder A` (Middle East, 0% commission), `…Placeholder B` (Africa).

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-53 | FR-SELL-60 | Selling → Sales Partner → list. | 2 OEM partners present (Placeholder A, B). |  |
| TS-SELL-54 | FR-SELL-57 | Open Placeholder A. **Partner Type** = OEM. **Commission Rate** = 0%. | Confirmed; AKD edits at sign-off. |  |
| TS-SELL-55 | FR-SELL-55 | On `SAL-ORD-2026-00003` → **Sales Team** child table. Add 2 Sales Persons. | Both saved with allocated_percentage. |  |
| TS-SELL-56 | FR-SELL-58 | Allocate 60/40 split between two Sales Persons. | Sum = 100% — saves. |  |
| TS-SELL-57 | FR-SELL-58 | Set total to 110%. | Blocked — must sum to 100. |  |

---

## 9. Sales Targets (FR-SELL-17, 59, 82)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-58 | FR-SELL-17 | Open Territory `United Arab Emirates`. **Targets** child table. Add 2026 target = 5 M AED. | Saved. |  |
| TS-SELL-59 | FR-SELL-59 | Selling → Sales Person → New. Add a target for 2026. | Saved. |  |
| TS-SELL-60 | FR-SELL-82 | `bench --site akd.com execute akd_customizations.tasks.sales_target_progress.send` | Weekly digest email sent with two tables (By Sales Person, By Territory) showing YTD attainment. |  |

---

## 10. Notifications (FR-SELL-90, FR-ACC-100)

| ID | Trigger | Recipient | Steps | P/F |
|---|---|---|---|---|
| TS-SELL-61 | Quotation → Pending Approval | Sales Manager | Submit `SAL-QTN-2026-00001` for Approval → check Sales Manager inbox. |  |
| TS-SELL-62 | Quotation → Approved | Customer + sales@ | Approve → customer receives email with AKD Quotation print. |  |
| TS-SELL-63 | SO → Pending Sales Manager / Pending Finance Review | Sales Manager + Accounts Manager | Walk SO through workflow. |  |
| TS-SELL-64 | SO → Approved | Customer + sales + warehouse | Approve. Customer gets SO print; warehouse gets dispatch trigger. |  |
| TS-SELL-65 | DN submitted (not return) | Customer + sales@ | Submit fresh DN → customer email with AKD Delivery Note attached. |  |
| TS-SELL-66 | DN submitted (is_return) | Sales Manager + finance@ | Submit return DN → internal email; suggests issuing Credit Note. |  |
| TS-SELL-67 | SI submitted | Customer | Already covered by AKD Sales Invoice Submitted notification. |  |

---

## 11. Scheduled Tasks (FR-SELL-20, 82)

| ID | Task | Command | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-68 | Quotation expiry digest | `bench --site akd.com execute akd_customizations.tasks.quotation_expiry_alert.send` | Digest to sales@ if any submitted Quotation has `valid_till` ≤ today+7 or already expired (with no SO). |  |
| TS-SELL-69 | Sales target progress | `bench --site akd.com execute akd_customizations.tasks.sales_target_progress.send` | Weekly digest to sales@ + gm@. |  |

---

## 12. Print Formats (FR-SELL-93, FR-ACC-93)

| ID | Doc | Print Format | Elements to verify | P/F |
|---|---|---|---|---|
| TS-SELL-70 | `SAL-QTN-2026-00002` | AKD Quotation | Logo, TRN, customer + addr, Valid Till, Competitor, totals, terms, A4 |  |
| TS-SELL-71 | `SAL-ORD-2026-00003` | AKD Sales Order | Customer PO, Delivery Date, Installation flag, totals |  |
| TS-SELL-72 | `MAT-DN-2026-00001` | AKD Delivery Note | Gate Pass No, Installation Status, ship-to addr, SO ref column |  |
| TS-SELL-73 | `MAT-DN-2026-00002` | AKD Delivery Note | Title = **CUSTOMER RETURN NOTE**, Return Reason shown |  |
| TS-SELL-74 | `ACC-SINV-2026-00013` | AKD Sales Invoice | VAT breakdown, bank box, TRN |  |
| TS-SELL-75 | `ACC-SINV-2026-00014` | AKD Sales Invoice | Title shows credit-note variant; Return Reason populated |  |

---

## 13. Role-Based Permissions (FR-SELL-87 → 89)

| ID | BRD | User | Action | Expected | P/F |
|---|---|---|---|---|---|
| TS-SELL-76 | FR-SELL-87 | Sales User | Create quotation. | Allowed. |  |
| TS-SELL-77 | FR-SELL-87 | Sales User | On Pending Approval quote, click Approve. | Action button hidden — Sales Manager only. |  |
| TS-SELL-78 | FR-SELL-88 | Sales User | Apply 50% discount on a line. | Capped (manual policy — see Pricing Rules section). |  |
| TS-SELL-79 | FR-SELL-89 | Sales Rep | View list — should only see assigned territory. | User Permission on Territory enforces this. (Manual user-setup required.) |  |
| TS-SELL-80 | — | Sales Manager | Approve a Quotation while logged in. | Workflow transition succeeds. |  |

---

## 14. Reports (FR-SELL-81 → 84)

| ID | Report | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-81 | Sales Analytics | Selling → Reports → Sales Analytics. | Pivot view by item/customer/period. |  |
| TS-SELL-82 | Sales Order Trends | Same module. | Trend chart visible. |  |
| TS-SELL-83 | Quotation Trends | Same module. | Trend chart. |  |
| TS-SELL-84 | Territory-wise Sales | Same module. | Group-by-territory totals. |  |
| TS-SELL-85 | Sales Person Summary | Same module. | Shows commission allocations. |  |
| TS-SELL-86 | Customer Credit Balance | Accounts → Customer Credit Balance. | Shows credit limit vs outstanding for ADNOC, First Bank, ACME. |  |
| TS-SELL-87 | Lost Quotations | Filter Quotations by status=Lost. | Shows quotations with Lost Reason populated. |  |
| TS-SELL-88 | Payment Terms Status | Accounts → AR Aging. | Buckets 0-30 / 31-60 / 61-90 etc. populated. |  |

---

## 15. Edge-case Scenarios

| ID | Scenario | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-89 | SO without DN | Try to invoice an SO without a DN line. | Blocked — DN Required = Yes. |  |
| TS-SELL-90 | Over-deliver beyond SO | Try DN with qty > SO qty. | Blocked — controlled by Stock Settings over-delivery allowance = 0%. |  |
| TS-SELL-91 | Quotation past validity → SO | From an expired Quotation, click Create SO. | Allowed; SO acknowledges expired quote. |  |
| TS-SELL-92 | Rate higher in SO than Quote | Edit SO line rate higher than parent quote. | Stopped (FR-SELL-43). |  |
| TS-SELL-93 | Customer over credit limit | Try SO totalling 5M for ADNOC (limit 500K). | Validate hook stops on SI submit. |  |
| TS-SELL-94 | Negative qty SO line | New SO line with qty = -1. | Validation error. |  |

---

## 16. WHT / Withholding on Sales (FR-SELL-54)

Seed (shared with Buying): `AKD WHT 5%`, `AKD WHT 10%` categories.

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-SELL-95 | FR-SELL-54 | Open `TEST-CUST-002 First Bank Nigeria Test`. **Tax Withholding Category** field. Set `AKD WHT 5%`. Save. | Customer tags the WHT. |  |
| TS-SELL-96 | FR-SELL-54 | Create a new Sales Invoice for that customer for USD 10 000. Tick **Apply Tax Withholding Amount**. | A deduct row for 5% appears; grand total reduces by 500 USD. |  |
| TS-SELL-97 | FR-SELL-54 | Submit. Open GL. | Credit posts to Tax Deducted at Source - AKD. |  |

---

## 17. Workflow End-to-End Smoke Test

A single sweeping run that exercises Lead-to-Cash. **One tester, ~10 minutes.**

| Step | Action | Pass criterion |
|---|---|---|
| 1 | Run `seed_data.seed_all` then `seed_selling.seed_all` | All masters + transactions land |
| 2 | Open `SAL-QTN-2026-00001` → Submit for Approval | State → Pending Approval |
| 3 | (Sales Manager) Approve | State → Approved, customer email sent with Quotation print |
| 4 | From the approved Quotation → Create Sales Order | Drafts SO with same items |
| 5 | Walk SO through both approvals | State → Approved, docstatus = 1, customer email |
| 6 | From SO → Create Delivery Note → Submit | DN posts; stock reduces |
| 7 | From DN → Create Sales Invoice → Submit | SI posts; debtor balance increases |
| 8 | Print SI in **AKD Sales Invoice** format | A4 PDF, TRN, VAT, bank box |
| 9 | From SI → Create Return / Credit Note (qty = -1) | Credit note submits; debtor balance reduces |
| 10 | Run quotation_expiry + sales_target_progress tasks | Emails generated to configured addresses |

---

## 18. Open Items Pending AKD Input

| Item | Status |
|---|---|
| Specific Customer Group list (Q8 open) | Awaiting AKD |
| SO approval thresholds / approvers per state (Q31 partial) | Awaiting AKD |
| Discount / pricing rule final structure (Q42 open) | Awaiting AKD |
| Blanket order overage allowance benchmark (Q53 open) | Awaiting AKD |
| OEM partner real names + commission rates (FR-SELL-60) | Awaiting AKD |
| Default selling price list import | Awaiting AKD |
| Loyalty program — out of scope (FR-SELL-74) | Skip |
| Subscription module — auto-repeat to be used instead (FR-SELL-75) | Confirmed Auto Repeat path |

---

## Sign-off

| Section | Total | Pass | Fail | Notes |
|---|---|---|---|---|
| 1. Customer Master | 8 | | | |
| 2. Quotation Workflow | 10 | | | |
| 3. Sales Order Workflow | 8 | | | |
| 4. Pricing Rules | 9 | | | |
| 5. Delivery Note + Installation | 9 | | | |
| 6. Customer Returns | 5 | | | |
| 7. Multi-currency | 4 | | | |
| 8. Sales Partners + Commission | 5 | | | |
| 9. Sales Targets | 3 | | | |
| 10. Notifications | 7 | | | |
| 11. Scheduled Tasks | 2 | | | |
| 12. Print Formats | 6 | | | |
| 13. Permissions | 5 | | | |
| 14. Reports | 8 | | | |
| 15. Edge cases | 6 | | | |
| 16. WHT on Sales | 3 | | | |
| 17. E2E smoke | 1 | | | |
| **Total** | **99** | | | |

**Tester signature:** _______________   **Date:** _______________
**Implementation partner sign-off (Quark Cyber Systems):** _______________   **Date:** _______________
**Client sign-off (AKD Consulting LLC):** _______________   **Date:** _______________
