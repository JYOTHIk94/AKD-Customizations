# AKD Buying Module — Manual Testing Script

**Site:** akd.com   **Company:** AKD Consulting LLC   **Tester:** _______________   **Date:** _______________

Source BRD: `AKD_Implementation_BRD_v4` — Section 5 (FR-BUY-01 → FR-BUY-96).
All seed records used below are created by:
```
bench --site akd.com execute akd_customizations.setup.seed_buying.seed_all
```

To reset: `bench --site akd.com execute akd_customizations.setup.seed_buying.purge`.

---

## 0. Pre-requisites

| # | Item | Details |
|---|---|---|
| P1 | Site available | http://akd.com:8002 logged in as **Administrator** for setup |
| P2 | Buying Settings applied | PO Required = Yes; PR Required = Yes; Rate consistency = Warn; Bill rejected qty = No |
| P3 | Stock Settings applied | Over-delivery allowance = 0 % |
| P4 | Rejected warehouse exists | `Rejected - AKD` |
| P5 | Seed data loaded | Run `seed_buying.seed_all` once |
| P6 | Test users created | Need: **Purchase User**, **Purchase Manager**, **Projects User**, **Accounts Manager**, **Stock Manager** (Administrator is acceptable for solo testing) |
| P7 | Email outbound configured | At least the SMTP test from System Settings; needed for notification + scheduler tests |

---

## 1. Supplier Master (FR-BUY-07, 08, 09, 11)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-01 | FR-BUY-08 | Buying → Supplier → New. Type "ACME Test 01". **Supplier Group** field shows AKD OEM + AKD Non-OEM in dropdown. | Both AKD groups present alongside ERPNext defaults. | |
| TS-BUY-02 | FR-BUY-07 | Open `TEST-BUY-SUPP-001 Emirates Tech LLC`. Scroll to the **AKD Classification** section. | Section visible with: Supplier Classification = Indigenous, Currency Band = AED, OEM Supplier = ticked. | |
| TS-BUY-03 | FR-BUY-07 | Open `TEST-BUY-SUPP-003 GlobalChip Foreign Test`. | Classification = Foreign, Currency Band = USD, OEM = ticked. | |
| TS-BUY-04 | FR-BUY-11 | Open `TEST-BUY-SUPP-004 BlockedVendor Test`. Try to create a **Purchase Invoice** for this supplier. | System should warn/block invoice creation because `Hold Type = Invoices`. | |
| TS-BUY-05 | FR-BUY-11 | Same supplier — try to create a **Purchase Order**. | Allowed (only invoices are blocked). | |
| TS-BUY-06 | FR-BUY-09 | Open any supplier → **Supplier Type** field shows Company / Individual / Partnership / Proprietorship. | Field present with correct options. | |
| TS-BUY-07 | FR-BUY-10 | Open Item `TEST-BUY-ITEM-LAPTOP` → Supplier Items tab. | 2 rows: Emirates Tech (ET-LAPTOP-14) + GlobalChip (GC-NB-14). | |
| TS-BUY-08 | FR-BUY-12 | Open same Item — **Lead Time Days** = 14. | Field shown and populated. | |

---

## 2. Material Request Workflow (FR-BUY-20 → 24)

Seed MRs:
- `MAT-MR-2026-00001` — Draft (laptops + printer)
- `MAT-MR-2026-00002` — Pending Line Manager (chairs)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-09 | FR-BUY-20 | Buying → Material Request → New. Required fields: Type, Purpose, Items. | Form opens; "Purchase" available as Material Request Type. | |
| TS-BUY-10 | FR-BUY-21 | Material Request Type dropdown. | Shows: Purchase, Material Transfer, Material Issue, Manufacture, Customer Provided, Material Consumption. | |
| TS-BUY-11 | FR-BUY-22 | Open `MAT-MR-2026-00001` (Draft). Click **Submit for Approval**. | Workflow state moves to "Pending Line Manager". Email goes out to Purchase Manager. | |
| TS-BUY-12 | FR-BUY-22 | Log in as user with **Purchase Manager** role. Open `MAT-MR-2026-00002`. Click **Approve**. | Moves to "Pending Management". Email to Stock Manager. | |
| TS-BUY-13 | FR-BUY-22 | Log in as **Stock Manager**. Approve. | Workflow state = Approved, docstatus = 1 (Submitted). | |
| TS-BUY-14 | FR-BUY-22 | At any state, click **Reject**. | State = Rejected, no further actions allowed. | |
| TS-BUY-15 | FR-BUY-24 | From an Approved MR → "Create" → Purchase Order. | PO draft created with line items copied across. | |

---

## 3. Request for Quotation + Supplier Quotation (FR-BUY-25 → 34)

Seed: `PUR-RFQ-2026-00001` (3 suppliers, laptops). `PUR-SQTN-2026-00001` (Local AED), `PUR-SQTN-2026-00002` (Foreign USD).

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-16 | FR-BUY-25 | Buying → RFQ → New. Add 2 suppliers and 1 item. Try to **Submit**. | System warns / requires minimum 3 suppliers (per AKD policy — manual policy check). | |
| TS-BUY-17 | FR-BUY-26 | Open `PUR-RFQ-2026-00001`. Verify 3 supplier rows present. | Emirates Tech + Dubai Office Supplies + GlobalChip. | |
| TS-BUY-18 | FR-BUY-27 | On the RFQ, click **Email** → Send. | Email composer opens pre-filled with supplier email addresses. | |
| TS-BUY-19 | FR-BUY-28 | RFQ → upload an attachment (e.g. specs.pdf). | Attachment persists on the doc and is sent with the email. | |
| TS-BUY-20 | FR-BUY-29 | From RFQ → Buying → "Supplier Quotation Comparison" report. | Side-by-side table showing the 2 seeded SQs at AED 4900 and USD 1350. | |
| TS-BUY-21 | FR-BUY-31 | Open `PUR-SQTN-2026-00001`. Verify it links back to the RFQ. | "request_for_quotation" field on line item = `PUR-RFQ-2026-00001`. | |
| TS-BUY-22 | FR-BUY-32 | Open `PUR-SQTN-2026-00001`. **Valid Till** date is populated (today + 30 days). | Valid till displayed. | |
| TS-BUY-23 | FR-BUY-33 | On the SQ line, **Supplier Part No** field is shown. | Field present. | |
| TS-BUY-24 | FR-BUY-29 | From SQ → "Create" → Purchase Order. | PO draft generated with supplier's quoted rate. | |

---

## 4. Purchase Order Workflow (FR-BUY-35 → 42)

Seed POs:
- `PUR-ORD-2026-00001` — Draft (chairs)
- `PUR-ORD-2026-00002` — Pending Finance (laptops)
- `PUR-ORD-2026-00003` — Approved + submitted (laptops, 3-way match basis)
- `PUR-ORD-2026-00004` — Approved + submitted (chairs, return basis)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-25 | FR-BUY-37 | Open `PUR-ORD-2026-00001` (Draft). Click **Submit for Approval**. | State → Pending Purchase Review. Email to Purchase Manager. | |
| TS-BUY-26 | FR-BUY-37 | As Purchase Manager → approve `PUR-ORD-2026-00001`. | State → Pending End User. Email to Projects User. | |
| TS-BUY-27 | FR-BUY-37 | As Projects User → approve. | State → Pending Finance. Email to Accounts Manager. | |
| TS-BUY-28 | FR-BUY-37 | As Accounts Manager → approve `PUR-ORD-2026-00002`. | State → Approved, docstatus = 1. Supplier email triggers (AKD PO print attached). | |
| TS-BUY-29 | FR-BUY-38 | Open `PUR-ORD-2026-00003`. **Customer PO Reference** field = `CUST-PO-2026-0099`. | Field visible with that value. | |
| TS-BUY-30 | FR-BUY-39 | On any PO line, set a `Schedule Date`. | Field present and saves per-line. | |
| TS-BUY-31 | FR-BUY-40 | Create a PR with rate **higher** than the parent PO. | Warning shown (not blocked) — Buying Settings says Warn. | |
| TS-BUY-32 | FR-BUY-42 | Open `PUR-ORD-2026-00003`. Tick **Place On Hold**. **Hold Reason** must now be mandatory. | Hold Reason becomes mandatory; PO is on hold. | |
| TS-BUY-33 | FR-BUY-42 | Try to create a Purchase Receipt against the on-hold PO. | Receipt creation should be blocked or warned. | |
| TS-BUY-34 | FR-BUY-41 | New PO → tick "Drop Ship" on a line. | Field is hidden / not relevant — Drop Ship is OUT OF SCOPE per BRD. | |

---

## 5. Purchase Receipt + Quality Inspection (FR-BUY-43 → 50)

Seed: `MAT-PRE-2026-00001` (laptop, 2 of 3, Pass), `MAT-PRE-2026-00002` (chairs, all received, Pass).

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-35 | FR-BUY-43 | Try to create a Purchase Invoice that does NOT reference a Purchase Receipt. | System throws "Purchase Receipt Required for item …". | |
| TS-BUY-36 | FR-BUY-44 | Create PI from `MAT-PRE-2026-00001` → submit. Open GL → see 3-way match GL entries (PO → PR → PI). | Match passes; GL balanced. | |
| TS-BUY-37 | FR-BUY-46 | Open `MAT-PRE-2026-00001`. Scroll to **Inspection Result**. | Field = Pass. | |
| TS-BUY-38 | FR-BUY-46 | Create new PR → set Inspection Result = Fail → save. | Field saves; can still submit but flagged. | |
| TS-BUY-39 | FR-BUY-47 | Open `PUR-ORD-2026-00003` (3 laptops ordered). 2 are already received via `MAT-PRE-2026-00001`. Create another PR for 1 remaining. | Partial receipt completes the order. | |
| TS-BUY-40 | FR-BUY-48 | Try to receive 4 chairs against PUR-ORD-2026-00004 (which ordered 4) — change qty to 5. | Stopped: over-delivery = 0 % per Stock Settings. | |
| TS-BUY-41 | FR-BUY-49 | New PR line — Rejected Qty > 0 → must set Rejected Warehouse. | Field becomes mandatory; default = `Rejected - AKD`. | |
| TS-BUY-42 | FR-BUY-50 | Submit a PR with Rejected Qty = 1. Then create a PI from it. | PI line shows only the accepted qty; rejected qty NOT billed. | |

---

## 6. Purchase Invoice (FR-ACC + FR-BUY-44, 66, 67, 68, 70)

Seed: `ACC-PINV-2026-00004` (3-way matched laptop PI), `ACC-PINV-2026-00005` (chair PI), `ACC-PINV-2026-00006` (Debit Note return).

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-43 | FR-BUY-66/67 | Create new PI → apply Purchase Taxes & Charges Template "AKD UAE VAT 5%". | Template populates taxes child table with VAT Input 5 %. | |
| TS-BUY-44 | FR-BUY-68 | On a new PI add a row: account head = TDS / WHT account, rate = 5 %, add/deduct = Deduct. | Tax line saves; reduces grand total. (Automated path covered in **Section 18 — Withholding Tax / TDS**.) | |
| TS-BUY-45 | FR-BUY-70/71/72 | On a submitted PR, click "Create Landed Cost Voucher". Add Freight + Customs + Insurance lines. Distribute = "By Amount". | LCV creates GL postings; item valuation rate increased. | |
| TS-BUY-46 | FR-BUY-67 | Open `ACC-PINV-2026-00004` print preview → choose **AKD Purchase Invoice** format. | A4 layout, logo, TRN, supplier, lines, VAT breakdown, grand total, signatures. | |
| TS-BUY-47 | FR-ACC-78 | Try to over-bill on a PI: set qty > received qty. | Stopped: over-billing allowance = 0 % per Accounts Settings. | |

---

## 7. Multi-currency Purchasing (FR-BUY-74 → 76)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-48 | FR-BUY-74 | Create new PO with supplier `TEST-BUY-SUPP-003 GlobalChip Foreign Test` (USD). | Currency defaults to USD, conversion rate populates from today's fx. | |
| TS-BUY-49 | FR-BUY-75 | Change PO transaction_date to 30 days ago. | Conversion rate recomputes using historical Currency Exchange row. | |
| TS-BUY-50 | FR-BUY-76 | On the PO, set Price List Currency = AED, transaction Currency = USD. | Both saved; rates computed accordingly. | |

---

## 8. Blanket Orders + Contract Expiry (FR-BUY-51 → 54)

Seed: `MFG-BLR-2026-00001` (chairs, to_date = today + 60 d).

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-51 | FR-BUY-51 | Open `MFG-BLR-2026-00001`. | Supplier, item, qty, to_date displayed. | |
| TS-BUY-52 | FR-BUY-52 | From the Blanket Order → "Create" → Purchase Order. | PO created with rate copied from blanket. | |
| TS-BUY-53 | FR-BUY-54 | Manually trigger the scheduled task: `bench --site akd.com execute akd_customizations.tasks.blanket_order_expiry.send` | Email goes to procurement@ with `MFG-BLR-2026-00001` in the "expiring within 30 days" table (currently 60d, so won't appear). Move to_date inside 30d and re-run → it appears. | |
| TS-BUY-54 | FR-BUY-53 | Try to create a PO that exceeds blanket order qty (>50). | Warning or block on over-blanket-order amount. | |

---

## 9. Returns / Debit Notes (FR-BUY-77 → 80)

Seed: `ACC-PINV-2026-00006` — debit note returning 1 chair, reason = Damaged.

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-55 | FR-BUY-77 | From `ACC-PINV-2026-00005` (chair PI) → "Create" → Return / Debit Note. | New PI opens with `is_return = 1`, qty negative. | |
| TS-BUY-56 | FR-BUY-78 | Submit the return PI. | Treated as Debit Note in supplier statement; supplier balance decreases. | |
| TS-BUY-57 | FR-BUY-80 | Open `ACC-PINV-2026-00006`. **Return Reason** field shown. | Field populated with "Damaged" (Select options: Damaged, Quality Issue, Wrong Item, Excess Delivery, Other). | |
| TS-BUY-58 | FR-BUY-79 | Permission check: Purchase User tries to submit a return PI. | Blocked (Purchase Manager role required for returns). | |

---

## 10. Supplier Scorecard (FR-BUY-15 → 19)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-59 | FR-BUY-15/19 | Run `bench --site akd.com execute akd_customizations.setup.scorecard.attach_to_supplier --kwargs "{'supplier': 'TEST-BUY-SUPP-001 Emirates Tech LLC'}"`. | A Supplier Scorecard record is created for that supplier with 5 criteria + 4 standings. | |
| TS-BUY-60 | FR-BUY-16 | Open the scorecard. **Criteria** child table. | 5 rows: On-Time Delivery (30%), Quality (25%), Pricing (20%), Responsiveness (15%), Compliance (10%). | |
| TS-BUY-61 | FR-BUY-18 | Open same scorecard. **Standings** child table. | 4 rows; AKD Average + AKD Poor both have warn_pos + warn_rfqs = 1, prevent flags = 0. | |
| TS-BUY-62 | FR-BUY-17 | Period field on scorecard. | Set to "Per Month" (quarterly aggregation done via report). | |

---

## 11. Notifications (FR-BUY-90, FR-ACC-100)

| ID | Trigger | Recipient | Steps to verify | P/F |
|---|---|---|---|---|
| TS-BUY-63 | PO submitted to "Pending Purchase Review" | Purchase Manager | Submit PO `PUR-ORD-2026-00001` for Approval → check inbox for `Purchase Manager`. | |
| TS-BUY-64 | PO finally Approved | Supplier + procurement@ | Walk a PO all the way to Approved → supplier receives email with **AKD Purchase Order** print format attached. | |
| TS-BUY-65 | Purchase Receipt submitted | Finance + Purchase Manager | Submit a new PR → check email digest. | |
| TS-BUY-66 | MR awaits Line Manager / Management | Purchase Manager + Stock Manager | Move MR to "Pending Line Manager" → email goes out. | |

---

## 12. Scheduled Tasks (FR-BUY-82, FR-BUY-54, FR-ACC-34)

Manually fire daily tasks to test:

| ID | Task | Command | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-67 | Overdue PO delivery digest | `bench --site akd.com execute akd_customizations.tasks.overdue_delivery_alert.send` | If any PO line schedule_date < today and received < qty, an email lands at procurement@ with the digest table. | |
| TS-BUY-68 | Blanket order expiry digest | `bench --site akd.com execute akd_customizations.tasks.blanket_order_expiry.send` | Reports expired + expiring-within-30-days; with seed data (60d), the digest is empty unless to_date is shortened. | |
| TS-BUY-69 | Supplier payment reminders | `bench --site akd.com execute akd_customizations.tasks.supplier_payment_reminders.send` | Digest of overdue + due-within-7-days PIs. | |

---

## 13. Print Formats (FR-BUY-90, FR-ACC-93)

For each, open the listed doc, click Print, choose the indicated format, save as PDF, and check the listed elements.

| ID | Doc | Print Format | Elements to verify | P/F |
|---|---|---|---|---|
| TS-BUY-70 | `PUR-ORD-2026-00003` | AKD Purchase Order | Logo, TRN, supplier addr, items, Customer PO Ref, totals, signatures, A4 | |
| TS-BUY-71 | `PUR-RFQ-2026-00001` | AKD Request for Quotation | 3 suppliers section, items, response form for supplier | |
| TS-BUY-72 | `MAT-PRE-2026-00001` | AKD Purchase Receipt | Inspection Result row, items, rejected qty column | |
| TS-BUY-73 | `ACC-PINV-2026-00004` | AKD Purchase Invoice | VAT breakdown, supplier TRN, due date, grand total | |
| TS-BUY-74 | `ACC-PINV-2026-00006` | AKD Purchase Invoice | Title = **Debit Note**, Return Reason shown | |

---

## 14. Role-Based Permissions (FR-BUY-87 → 89, FR-BUY-86)

Tests need users assigned to one role only.

| ID | BRD | User | Action | Expected | P/F |
|---|---|---|---|---|---|
| TS-BUY-75 | FR-BUY-87 | Purchase User | Try to create + submit a PO directly. | Allowed to create + Submit for Approval; cannot Approve. | |
| TS-BUY-76 | FR-BUY-88 | Purchase User | On a PO at "Pending Purchase Review" — try **Approve**. | Action button hidden. | |
| TS-BUY-77 | FR-BUY-88 | Purchase Manager | Same PO — Approve button visible and works. | Transitions to Pending End User. | |
| TS-BUY-78 | FR-BUY-89 | Any approver | Try to create PO above 1 M AED. | No amount-based limits per BRD — submission proceeds. | |
| TS-BUY-79 | FR-BUY-87 | Stock User | Try to create a PO. | Blocked — Stock User does not have create permission on PO. | |

---

## 15. Reports (FR-BUY-81 → 83)

| ID | Report | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-80 | Purchase Analytics | Buying → Reports → Purchase Analytics. Filter for Company = AKD. | Pivot view of purchases by item / supplier / period. | |
| TS-BUY-81 | Procurement Tracker | Same module, "Procurement Tracker" report. | Shows seed PO + PR + PI in their respective columns. | |
| TS-BUY-82 | Supplier Quotation Comparison | Buying → Supplier Quotation Comparison filtered by RFQ `PUR-RFQ-2026-00001`. | Side-by-side comparison of the 2 quotes. | |
| TS-BUY-83 | Item-wise Purchase History | Buying → Item-wise Purchase History. Filter Item = `TEST-BUY-ITEM-LAPTOP`. | Shows the seed PR and PI rows for laptops. | |
| TS-BUY-84 | Supplier Scorecard Summary | Buying → Supplier Scorecard. | Each supplier with attached scorecard shows current grade and standing. | |
| TS-BUY-85 | Pending Items to Order | Buying → Pending Items to Order. | Shows MR lines not yet converted to PO. | |
| TS-BUY-86 | Subcontracted Items to Receive | Buying → Subcontracted Items to Receive. | Empty — subcontracting OOS per FR-BUY-55. | |

---

## 16. Edge-case Scenarios (negative & boundary)

| ID | Scenario | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-87 | RFQ to fewer than 3 suppliers | Create RFQ with only 1 supplier. Submit. | Submitted — policy compliance is manual; tester to flag. | |
| TS-BUY-88 | PO without Item Tax Template | Create PO; do NOT apply taxes_and_charges template. Submit. | Submits but invoice would not have VAT — tester to flag if AKD wants Stop. | |
| TS-BUY-89 | Blocked supplier — full block | Change BlockedVendor to `Hold Type = All`. Try a new PO. | Blocked. | |
| TS-BUY-90 | Negative qty on PR | Try to set qty = -1 on a new PR line. | Validation error. | |
| TS-BUY-91 | Stale FX rate | Set system date to 366 days in the future. Try to post a USD PI. | Blocked — Accounts Settings stale_days = 365 (FR-ACC-80). | |
| TS-BUY-92 | Currency mismatch on PR | Open `PUR-ORD-2026-00003` (AED), then change PR currency to USD. | Blocked — PR currency must match PO. | |

---

## 17. Workflow End-to-End Smoke Test

A single sweeping run that exercises the full PR-to-pay loop. **One tester, ~10 minutes.**

| Step | Action | Pass criterion |
|---|---|---|
| 1 | Run `seed_buying.seed_all` | All masters + transactions land |
| 2 | Open `MAT-MR-2026-00001`, click **Submit for Approval** | State → Pending Line Manager |
| 3 | (As Purchase Manager) Approve → (As Stock Manager) Approve | State → Approved, docstatus = 1 |
| 4 | From the MR, create a Purchase Order | PO Draft opens with same items |
| 5 | Walk PO through 3 approval steps | State → Approved |
| 6 | From PO, create Purchase Receipt with full qty + inspection = Pass | PR submitted; stock posts to Stores - AKD |
| 7 | From PR, create Purchase Invoice | PI inherits qty + rate; 3-way match GL posts |
| 8 | Print PI in **AKD Purchase Invoice** format | A4 PDF renders with logo + TRN + VAT |
| 9 | From PI, create a Return (qty = -1) with reason = Quality Issue | Debit Note submits; supplier balance reduced |
| 10 | Run all 3 daily tasks manually | Emails arrive at the configured addresses |

---

## 18. Withholding Tax / TDS (FR-BUY-68)

Seed: account `Tax Deducted at Source - AKD`; categories `AKD WHT 5%`, `AKD WHT 10%` (both wired to AKD Consulting LLC).

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-93 | FR-BUY-68 | Buying → Supplier → open `TEST-BUY-SUPP-003 GlobalChip Foreign Test`. In **Tax Withholding Category** field, choose `AKD WHT 10%`. Save. | Category persists on the Supplier. |  |
| TS-BUY-94 | FR-BUY-68 | Create a new Purchase Invoice for that supplier. Add line item (any TEST-BUY item, qty 1, rate 1000). Tick **Apply Tax Withholding Amount**. | A tax row auto-adds for 10% of net total = 100 (deduct). Grand total reduced. |  |
| TS-BUY-95 | FR-BUY-68 | Submit the PI. Open General Ledger. | A credit posts to `Tax Deducted at Source - AKD` for the WHT amount. |  |
| TS-BUY-96 | FR-BUY-68 | Open `AKD WHT 5%`. View the rates child table. | Single row: rate = 5%, from = Jan 1 current FY, to = Dec 31 current FY. |  |
| TS-BUY-97 | FR-BUY-68 | Buying → Supplier → new Supplier without WHT category. Create PI → tick Apply WHT. | Stopped — supplier has no category configured. |  |

---

## 19. Landed Cost (FR-BUY-70, 71, 72)

Seed accounts (under `Stock Expenses - AKD`):
- `Freight and Shipping Charges - AKD`
- `Customs Duty - AKD`
- `Insurance — Inward - AKD`
- `Handling Charges - AKD`
- `Inspection Fees - AKD`

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-98 | FR-BUY-70 | Open `MAT-PRE-2026-00001` (laptop PR). Click "Create" → **Landed Cost Voucher**. | LCV draft opens with the PR pre-populated. |  |
| TS-BUY-99 | FR-BUY-71 | On the LCV, add 5 rows in **Taxes and Charges**: account heads = each of the 5 landed-cost accounts; amount = 100/200/50/30/20 AED. | 5 charge rows save. Total = 400. |  |
| TS-BUY-100 | FR-BUY-72 | On the LCV, set **Distribute Charges Based On** = `Amount`. Click Submit. | Charges distribute by line amount; item valuation rate increases proportionally. |  |
| TS-BUY-101 | FR-BUY-70 | Open the original PR's stock ledger. | Valuation rate of the laptop is now PO rate + allocated landed cost share. |  |
| TS-BUY-102 | FR-BUY-73 | Try to auto-populate landed cost from a PI rate (no helper exists). | Confirmed manual-only — FR-BUY-73 says auto-set No. |  |

---

## 20. Multi-currency (FR-BUY-74, 75, 76, FR-ACC-19, 20)

Seed: 5 currencies enabled (AED/USD/EUR/GBP/NGN); today's FX rates seeded against AED.

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-103 | FR-BUY-74 | System Settings (admin only) → list of Currencies → filter Enabled = 1. | AED, USD, EUR, GBP, NGN present. |  |
| TS-BUY-104 | FR-BUY-74 | New PO with supplier `TEST-BUY-SUPP-003 GlobalChip Foreign Test`. **Currency** field. | Defaults to USD (supplier's default); dropdown also shows AED, EUR, GBP, NGN. |  |
| TS-BUY-105 | FR-BUY-75 | On the new USD PO, set transaction_date = today. Conversion rate field. | Auto-fills 3.6725 from today's Currency Exchange row. |  |
| TS-BUY-106 | FR-BUY-75 | Change transaction_date to 30 days ago (historical seed has rate). | Conversion rate refreshes to the seeded historical value. |  |
| TS-BUY-107 | FR-BUY-76 | On the PO, change **Price List** to a AED list while keeping currency USD. | Price List Currency ≠ Transaction Currency persists; rates compute via FX. |  |
| TS-BUY-108 | FR-ACC-20 | Currency Exchange Settings (singleton). Verify Service Provider. | Set to `exchangerate.host` (or `frankfurter.dev` if API key still pending). |  |
| TS-BUY-109 | FR-ACC-80 | Set system date 366 days in the future. Try a USD PO. | Stopped — stale FX rate. |  |
| TS-BUY-110 | FR-BUY-74 | Create PI in NGN against the BlockedVendor supplier — system asks for Debtors NGN / Creditors NGN. | Either pre-existing or prompts to add multi-currency AP account. |  |

---

## 21. BRD Coverage-Gap Test Cases (FR-BUY points not covered above)

These exercise FR-BUY requirements that the sections above did not test. Some
verify in-scope behaviour; the last three confirm BRD "No"/out-of-scope.

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-BUY-111 | FR-BUY-06 | Create a PO for a **service** item (`is_stock_item = 0`), submit, then create a Purchase Invoice directly (no PR). | Service purchase flows PO → PI; PR not demanded for non-stock items. | |
| TS-BUY-112 | FR-BUY-06 | Create a PO for a **capital-equipment** item (`is_fixed_asset = 1`, asset category set). Receive + invoice it. | On PI submit, an **Asset** is auto-created under the item's Asset Category (ties Fixed Assets module). | |
| TS-BUY-113 | FR-BUY-06 | Create a PO for a **consumable** item and a **subcontracting**-type line. | Consumable purchases normally; subcontracting line flagged out-of-scope (FR-BUY-55) — tester notes. | |
| TS-BUY-114 | FR-BUY-14 | Buying → Supplier → New. Tick **Is Internal Supplier**, set *Represents Company* = AKD Consulting LLC. Save. | Internal (inter-company) supplier saved and selectable on an inter-company PO. | |
| TS-BUY-115 | FR-BUY-23 | Open `TEST-BUY-ITEM-CHAIR` → set a Reorder Level + Reorder Qty. Run `bench --site akd.com execute erpnext.stock.reorder_item.reorder_item`. | **No** Material Request is auto-created — auto-reorder is intentionally OFF per FR-BUY-23. | |
| TS-BUY-116 | FR-BUY-24 | Create 2 Material Requests (same supplier, different items). New Purchase Order → **Get Items From → Material Request**, pick both. | A single PO consolidates lines from both MRs. | |
| TS-BUY-117 | FR-BUY-34 | Open `PUR-SQTN-2026-00001`. On the item row set **Lead Time Days** = 21. Save. | Per-quotation-item lead time persists. | |
| TS-BUY-118 | FR-BUY-36 | Create a Purchase Invoice **without** linking any Purchase Order. Submit. | Blocked — "Purchase Order Required" (po_required = Yes; conflict C-01 resolution). | |
| TS-BUY-119 | FR-BUY-62 | Buying → Price List → confirm a Buying price list exists. Add an Item Price for `TEST-BUY-ITEM-LAPTOP` on it. Create a PO. | PO line rate auto-fetches from the buying price list. | |
| TS-BUY-120 | FR-BUY-63 | Add an Item Price for the laptop scoped to **Supplier = `TEST-BUY-SUPP-001`**. Create a PO for that supplier. | Supplier-specific price applied (overrides generic price list). | |
| TS-BUY-121 | FR-BUY-64 | Submit PO→PR→PI for the laptop at rate 4900. Create a **new** PO for the same item. | **Last Purchase Rate** auto-populates 4900 (disable_last_purchase_rate = 0). | |
| TS-BUY-122 | FR-BUY-65 | Create a buying **Pricing Rule**: qty ≥ 10 → 5 % discount, valid date range = this month. PO qty 10, then qty 5. | Discount applies at qty 10, not at qty 5; outside the date range it does not apply. | |
| TS-BUY-123 | FR-BUY-69 | New PO for `TEST-BUY-SUPP-003` (foreign). Set **Incoterm** = FOB + named place. Submit, print. | Incoterm field present, saves, and prints on the AKD Purchase Order format. | |
| TS-BUY-124 | FR-BUY-91 | Open submitted `PUR-ORD-2026-00003` → **Create → Auto Repeat**. Frequency = Monthly, start = today. | Auto Repeat created; a recurring/standing PO is generated on the schedule. | |
| TS-BUY-125 | FR-BUY-84 / 92 / 93 | Confirm there is **no** purchase budget-vs-actual enforcement on PO submit, and no e-procurement / barcode-GRN entry points. | All confirmed OUT OF SCOPE per BRD (C-08, FR-BUY-92/93) — documentation check, not Pass/Fail. | |

---

## 22. Open Items Pending AKD Input (do NOT mark Pass/Fail)

| Item | Status |
|---|---|
| Specific KPI thresholds in Supplier Scorecard (Q17) | Awaiting AKD |
| Approver user emails for each workflow state (Q39) | Awaiting AKD |
| WHT rates table (Nigeria + others) (Q70) | Awaiting AKD |
| Return reasons list — currently uses placeholder options (Q84) | Awaiting AKD |
| RAK Bank statement CSV mapping (FR-ACC-53) | Awaiting sample |

---

## Sign-off

| Section | Total | Pass | Fail | Notes |
|---|---|---|---|---|
| 1. Supplier Master | 8 | | | |
| 2. Material Request | 7 | | | |
| 3. RFQ + SQ | 9 | | | |
| 4. Purchase Order | 10 | | | |
| 5. Purchase Receipt + QI | 8 | | | |
| 6. Purchase Invoice | 5 | | | |
| 7. Multi-currency (basic) | 3 | | | |
| 8. Blanket Orders | 4 | | | |
| 9. Returns | 4 | | | |
| 10. Supplier Scorecard | 4 | | | |
| 11. Notifications | 4 | | | |
| 12. Scheduled Tasks | 3 | | | |
| 13. Print Formats | 5 | | | |
| 14. Permissions | 5 | | | |
| 15. Reports | 7 | | | |
| 16. Edge cases | 6 | | | |
| 17. E2E smoke | 1 | | | |
| 18. WHT / TDS | 5 | | | |
| 19. Landed Cost | 5 | | | |
| 20. Multi-currency (extended) | 8 | | | |
| 21. BRD coverage-gap | 15 | | | |
| **Total** | **126** | | | |

**Tester signature:** _______________   **Date:** _______________
**Implementation partner sign-off (Quark Cyber Systems):** _______________   **Date:** _______________
**Client sign-off (AKD Consulting LLC):** _______________   **Date:** _______________
