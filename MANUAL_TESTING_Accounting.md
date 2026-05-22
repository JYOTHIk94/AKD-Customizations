# AKD Accounting — Manual Testing Data & Test Plan

**Site:** `akd.com` · **Bench:** `/home/jyothi/v16-bench` · **Login as:** Administrator

## How to load / refresh the test data

```bash
bench --site akd.com execute akd_customizations.setup.orchestrator.run --kwargs "{'full': False}"
bench --site akd.com migrate
bench --site akd.com execute akd_customizations.setup.seed_data.seed_all
bench --site akd.com execute akd_customizations.setup.seed_data.seed_scenarios
bench --site akd.com clear-cache
```

To start clean between runs:

```bash
bench --site akd.com execute akd_customizations.setup.seed_data.purge
# then re-seed
```

---

# Part 1 — Test data on the site

### Company (BRD Section 3)

| Field | Value | BRD |
| :-- | :-- | :-- |
| Legal name | AKD Consulting LLC | Q1 |
| Abbreviation | AKD | Q2 |
| Default currency | AED | Q3 / FR-ACC-19 |
| Country | United Arab Emirates | Q4 |
| Tax ID / TRN | 104661110700003 | Q8 / Q39 |
| Registration details | CR / Trade Licence: 1403338 | Q9 |
| Address | 3302 Prism Tower, Business Bay, Dubai | Q10 |
| Perpetual inventory | OFF (periodic per BRD) | FR-ACC-79 |

### Banks & Bank Accounts (FR-ACC-49, 50)

| Bank | Bank Account name | Linked GL | Currency | Mode of Payment wired |
| :-- | :-- | :-- | :-- | :-- |
| RAK Bank | RAK Bank - Current AED | `RAK Bank - Current AED - AKD` | AED | Bank Transfer + Cheque |
| RAK Bank | RAK Bank - Current USD | `RAK Bank - Current USD - AKD` | USD | — |

### Cost Centres (FR-ACC-12, flat per FR-ACC-13)

| Name | Used by | BRD |
| :-- | :-- | :-- |
| Sales - AKD | All Sales Invoices | FR-ACC-12 |
| Admin - AKD | All Purchase Invoices | FR-ACC-12 |
| Finance - AKD | Journal Entries | FR-ACC-12 |
| HR - AKD | (HR payments — none seeded) | FR-ACC-12 |

### Payment Terms & Templates (FR-ACC-44, 45, 48)

| Payment Term | Credit days | Portion % | Use |
| :-- | --: | --: | :-- |
| AKD-Net-30 | 30 | 100 | Customer standard |
| AKD-Net-45 | 45 | 100 | Supplier standard |
| AKD-Net-60 | 60 | 100 | Customer extended |
| AKD-PIA | 0 | 100 | Supplier advance |
| AKD-Advance-50 | 0 | 50 | 50/50 split — advance |
| AKD-Delivery-50 | 30 | 50 | 50/50 split — delivery |

| Template | Terms |
| :-- | :-- |
| AKD Customer Standard | Net 30 (100%) |
| AKD Supplier Standard | Net 45 (100%) |
| AKD 50/50 Split | Advance-50 (50%) + Delivery-50 (50%) |

### UAE VAT Templates (FR-ACC-23..27)

| Template (Sales) | Rate | Account head | Template (Purchase) |
| :-- | --: | :-- | :-- |
| UAE VAT 5% - AKD | 5% | VAT 5% - AKD | UAE VAT 5% - AKD |
| UAE VAT Zero - AKD | 0% | VAT Zero - AKD | UAE VAT Zero - AKD |
| UAE VAT Exempted - AKD | 0% | VAT Exempted - AKD | UAE VAT Exempted - AKD |
| UAE Excise 50% - AKD | 50% | (excise) | UAE Excise 50% - AKD |
| UAE Excise 100% - AKD | 100% | (excise) | UAE Excise 100% - AKD |

> BRD names `VAT Output` / `VAT Input` exist as separate accounts (scaffolded). UAE-regional accounts are still active — see Known Issues #2.

### Customers (3 seeded)

| Name | Group | Territory | Default ccy | Payment terms | Credit limit AED |
| :-- | :-- | :-- | :-- | :-- | --: |
| TEST-CUST-001 ADNOC Test | Government | United Arab Emirates | AED | AKD Customer Standard | 500,000 |
| TEST-CUST-002 First Bank Nigeria Test | Commercial | Rest Of The World | USD | AKD Customer Standard | 1,000,000 |
| TEST-CUST-003 Acme USA Test | Commercial | Rest Of The World | USD | AKD 50/50 Split | 500,000 |

### Suppliers (3 seeded)

| Name | Group | Country | Default ccy | Payment terms |
| :-- | :-- | :-- | :-- | :-- |
| TEST-SUPP-001 TechVendor LLC | Local | United Arab Emirates | AED | AKD Supplier Standard |
| TEST-SUPP-002 AWS Cloud Test | Services | United States | USD | AKD Supplier Standard |
| TEST-SUPP-003 ConsultingCo India Test | Services | India | USD | — |

### Items (5 seeded — all `Services`, non-stock)

| Item code | Name | Standard rate (AED) |
| :-- | :-- | --: |
| TEST-ITEM-CONSULT | Senior Consultant Hour | 850 |
| TEST-ITEM-ADVISORY | Advisory Retainer Monthly | 25,000 |
| TEST-ITEM-AI | AI Platform Implementation | 75,000 |
| TEST-ITEM-CLOUD | Cloud Subscription Monthly | 5,000 |
| TEST-ITEM-LICENSE | Software License Annual | 12,000 |

### FX rates (90 days back, covers all back-dated postings)

| From | To | Rate | Date |
| :-- | :-- | --: | :-- |
| USD | AED | 3.6725 | T − 90 days |
| EUR | AED | 4.00 | T − 90 days |
| GBP | AED | 4.65 | T − 90 days |
| NGN | AED | 0.0040 | T − 90 days |
| USD | AED | 3.8000 | today (FX revaluation scenario) |

---

# Part 2 — Seeded transactions (for verification + exploration)

### Sales Invoices

| Name | Customer | Currency | Grand total | Status | Posting date | Tests |
| :-- | :-- | :-- | --: | :-- | :-- | :-- |
| ACC-SINV-2026-00001 | ADNOC | AED | 61,950 | **Paid** | T−10d | basic AED, Net 30, fully receivable |
| ACC-SINV-2026-00002 | First Bank Nigeria | USD | 78,750 | **Unpaid** | T−5d | multi-currency, Debtors USD |
| ACC-SINV-2026-00003 | Acme USA | USD | 63,000 | **Partly Paid** | T−2d | 50/50 split-term, 31,500 USD remaining |
| ACC-SINV-2026-00004 | ADNOC | AED | 63,000 | **Overdue** | T−60d | back-dated, due-date breach |
| ACC-SINV-2026-00006 | ADNOC | AED | 5,355 | **Cancelled** | today | FR-ACC-82 unlink-payment test |

### Purchase Invoices

| Name | Supplier | Currency | Grand total | Posting date | Tests |
| :-- | :-- | :-- | --: | :-- | :-- |
| ACC-PINV-2026-00001 | TechVendor LLC | AED | 23,100 | T−8d | basic AED |
| ACC-PINV-2026-00002 | AWS Cloud Test | USD | 28,350 | T−3d | multi-currency, Creditors USD |
| ACC-PINV-2026-00003 | ConsultingCo India Test | USD | 50,400 | T−1d | USD with PIA terms |

### Payment Entries

| Name | Party | Ccy | Paid | Unallocated | Tests |
| :-- | :-- | :-- | --: | --: | :-- |
| ACC-PAY-2026-00001 | ADNOC | AED | 61,950 | 0 | full payment of SI-01 |
| ACC-PAY-2026-00002 | Acme USA | USD | 31,500 | 0 | 50% advance against SI-03 |
| ACC-PAY-2026-00003 | First Bank Nigeria | USD | 5,000 | 5,000 | **unallocated** — for Payment Reconciliation test |
| ACC-PAY-2026-00004 | ADNOC | AED | 5,355 | 5,355 | post-cancel of SI-05 — FR-ACC-82 |

### Journal Entries

| Name | Voucher type | Total | Tests |
| :-- | :-- | --: | :-- |
| ACC-JV-2026-00001 | Write Off Entry | 250 | FR-ACC-55 — manual JE |
| ACC-JV-2026-00002 | Exchange Rate Revaluation | 827,859.38 | FR-ACC-21 — period-end FX, gain 8,032.50 AED |

### Exchange Rate Revaluation

| Name | Date | Accounts revalued | Linked JV |
| :-- | :-- | :-- | :-- |
| ACC-ERR-2026-00001 | today | Debtors USD (2 parties), Creditors USD (2 parties), RAK Bank USD | ACC-JV-2026-00002 |

---

# Part 3 — Manual test cases (run these in the UI)

## A — Company & masters

| # | Step | URL / location | Expected | BRD |
| :-- | :-- | :-- | :-- | :-- |
| A1 | Open Company doctype | `/app/company/AKD Consulting LLC` | TRN, registration, address, AED, country UAE, perpetual=Off, exchange_gain_loss_account=`Exchange Gain/Loss - AKD` | Section 3, FR-ACC-22, 79 |
| A2 | Open Fiscal Year 2026 | `/app/fiscal-year/2026` | 01-Jan-2026 → 31-Dec-2026, Company tagged | FR-ACC-16 |
| A3 | Accounts Settings | `/app/accounts-settings` | over_billing=0, stale_days=365, allow_stale=0, unlink_payment_on_cancel=1 | FR-ACC-78, 80, 82 |
| A4 | Currency Exchange Settings | `/app/currency-exchange-settings` | provider = `frankfurter.dev` (BRD wants exchangerate.host — deferred pending API key) | FR-ACC-20 |
| A5 | Cost Center tree | `/app/cost-center` | 4 leaf cost centres under AKD root: Sales, Admin, Finance, HR | FR-ACC-12 |
| A6 | Customer Group tree | `/app/customer-group` | AKD Industries → 8 children (Oil & Gas, Utility, Government, Marine, Telecom, B&F, Healthcare, Aviation) | FR-SELL-05 |
| A7 | Territory tree | `/app/territory` | Middle East (UAE + 5) and Africa (Nigeria + 4) | FR-SELL-13..17 |
| A8 | Bank Account list | `/app/bank-account` | RAK Bank Current AED + USD, both `is_company_account=1` | FR-ACC-49, 50 |
| A9 | Modes of Payment | `/app/mode-of-payment/Bank Transfer` | Default account row: AKD Consulting LLC → RAK Bank - Current AED - AKD | FR-ACC-46 |

## B — Customer & Supplier inspection

| # | Step | Expected |
| :-- | :-- | :-- |
| B1 | Open `/app/customer/TEST-CUST-001 ADNOC Test` | Group=Government (under AKD Industries), Territory=UAE, Default ccy=AED, Credit Limit 500,000 |
| B2 | Customer form — scroll to **AKD Segmentation** section | `akd_account_group` + `akd_industry` Select fields visible (FR-SELL-05) |
| B3 | Open `/app/customer/TEST-CUST-002 First Bank Nigeria Test` | Default ccy=USD, credit limit 1,000,000 |
| B4 | Open `/app/supplier/TEST-SUPP-002 AWS Cloud Test` | Group=Services, country=US, ccy=USD |
| B5 | Supplier form — scroll to **AKD Classification** section | `akd_supplier_classification` + `akd_supplier_currency_band` + `akd_oem_flag` visible (FR-BUY-07, 08) |

## C — Sales Invoice — happy paths

| # | Step | Expected | BRD |
| :-- | :-- | :-- | :-- |
| C1 | `/app/sales-invoice/ACC-SINV-2026-00001` | Status=Paid, grand_total 61,950 AED, GL entries 4 rows (Debtors / Sales / VAT / Round Off?) | FR-ACC-44, 89 |
| C2 | Same form → **Print** → "AKD Sales Invoice" | A4 PDF, TRN=104661110700003 visible, items table, totals, bank box, footer | FR-ACC-93..96 |
| C3 | `/app/sales-invoice/ACC-SINV-2026-00002` | Status=Unpaid, currency USD, conversion_rate 3.6725, base_grand_total ≈ 289,209 AED | FR-ACC-19, 21 |
| C4 | `/app/sales-invoice/ACC-SINV-2026-00003` → **Payment Schedule** tab | 2 rows: 31,500 USD due today, 31,500 USD due +30d | FR-ACC-48 |
| C5 | `/app/sales-invoice/ACC-SINV-2026-00004` | Status=**Overdue** (red badge), due date in the past | FR-ACC-89 |
| C6 | Create new SI (`/app/sales-invoice/new`) — customer=TEST-CUST-001, item=TEST-ITEM-CONSULT, qty=2 | Save → submit. GL impact: Debtors dr / Sales cr / VAT 5% cr | FR-ACC-23..27 |

## D — Purchase Invoice

| # | Step | Expected |
| :-- | :-- | :-- |
| D1 | `/app/purchase-invoice/ACC-PINV-2026-00001` | AED 23,100, VAT 5% input, supplier TechVendor |
| D2 | `/app/purchase-invoice/ACC-PINV-2026-00002` | USD 28,350, credit_to = `Creditors USD - AKD` |
| D3 | Create new PI (`/app/purchase-invoice/new`) — supplier=TEST-SUPP-001, item=TEST-ITEM-LICENSE, qty=1 | Save+submit; VAT 5% Input - AKD posts a debit |

## E — Payments & Reconciliation

| # | Step | Expected | BRD |
| :-- | :-- | :-- | :-- |
| E1 | `/app/payment-entry/ACC-PAY-2026-00001` | Receive payment, allocated 61,950 against SI-01, status=Submitted | FR-ACC-46, 68 |
| E2 | `/app/payment-entry/ACC-PAY-2026-00003` | **unallocated_amount = 5,000 USD**, no References | FR-ACC-68 |
| E3 | `/app/payment-reconciliation` | Company=AKD, party_type=Customer, party=TEST-CUST-002 → **Get Unreconciled Entries** → PE-99 should appear ready to match against SI-02 | FR-ACC-68 |
| E4 | After reconcile, PE-99.unallocated should drop to 0; SI-02 outstanding drops by 5,000 USD | (manual UI step) | FR-ACC-68 |

## F — Journal & FX Revaluation

| # | Step | Expected | BRD |
| :-- | :-- | :-- | :-- |
| F1 | `/app/journal-entry/ACC-JV-2026-00001` | Write-Off Entry, dr Write Off - AKD 250, cr Debtors 250 (party=ADNOC) | FR-ACC-55 |
| F2 | `/app/journal-entry/ACC-JV-2026-00002` | Voucher type=Exchange Rate Revaluation, net P&L impact = `Exchange Gain/Loss - AKD` credit 8,032.50 | FR-ACC-21 |
| F3 | `/app/exchange-rate-revaluation/ACC-ERR-2026-00001` | 5 USD account rows, current 3.6725 → new 3.80 | FR-ACC-21 |

## G — Standard reports (FR-ACC-89)

| # | Report | URL | Verify |
| :-- | :-- | :-- | :-- |
| G1 | General Ledger | `/app/query-report/General Ledger` | Filter: Company=AKD, From=01-Jan-2026, To=today → 31 GL rows |
| G2 | Accounts Receivable | `/app/query-report/Accounts Receivable` | Outstanding: ADNOC 63,000; First Bank Nigeria 289,209 AED-eq; Acme 115,683.75 AED-eq |
| G3 | Accounts Payable | `/app/query-report/Accounts Payable` | TechVendor 23,100; AWS 104,115; ConsultingCo 185,094 (AED-eq) |
| G4 | Trial Balance | `/app/query-report/Trial Balance` | Total debit = total credit; non-zero rows for Debtors, Creditors, Bank, Sales, VAT |
| G5 | Profit and Loss Statement | `/app/query-report/Profit and Loss Statement` | Income from SI items (~360K AED-eq); Expenses from PI lines |
| G6 | Balance Sheet | `/app/query-report/Balance Sheet` | Assets = Liabilities + Equity; verify VAT Output > VAT Input (Net VAT payable) |
| G7 | VAT Audit Report | `/app/query-report/VAT Audit Report` | UAE VAT 5% rows from both Sales (output) and Purchase (input) |
| G8 | Customer Ledger Summary | `/app/query-report/Customer Ledger Summary` | One row per TEST customer |

## H — Negative / edge-case tests

| # | Scenario | How to test | Expected | BRD |
| :-- | :-- | :-- | :-- | :-- |
| H1 | Credit-limit breach | Create SI: customer=TEST-CUST-001, item=TEST-ITEM-AI qty=11 (rate 75K → grand 866K AED) → Submit | **Block** with message `Customer ... would exceed credit limit 500,000.00 AED. Total exposure with this invoice: …` | FR-SELL-09 |
| H2 | Invoice cancel + unlink payment | Open SI-01 (paid) → Cancel | SI moves to Cancelled; PE-01 references emptied; PE-01.unallocated_amount = 61,950 | FR-ACC-82 |
| H3 | Over-billing | Open SI-01 → make a Return / try to invoice qty > delivered (only meaningful with DN; if BRD says DN not used, this is N/A) | Blocked or warned | FR-ACC-78 |
| H4 | Stale FX rate | Create USD SI dated `today − 400 days` (no rate seeded that far back) | Blocked: "Exchange Rate is mandatory…" (stale rate cap 365 days) | FR-ACC-80 |
| H5 | Cancel PE without invoice | Open PE-01 → Cancel (after H2 unlinks) | PE moves to Cancelled, GL entries reversed | FR-ACC-82 |

## I — Notification & scheduled report tests

| # | Trigger | Expected | BRD |
| :-- | :-- | :-- | :-- |
| I1 | Save+Submit any new Sales Invoice | Notification `AKD Sales Invoice Submitted` fires → email queued to `customer.contact_email` (check `/app/email-queue`) | FR-ACC-100 |
| I2 | Save+Submit a customer Payment Entry | Notification `AKD Payment Entry Received` fires | FR-ACC-100 |
| I3 | SI past due + outstanding > 0 | Notification `AKD Sales Invoice Overdue` fires 7 days after due | **CONFLICT FR-ACC-41** — flag for AKD |
| I4 | Auto Email Report (e.g. `AKD Monthly Profit and Loss`) | Run `/app/auto-email-report/AKD Monthly Profit and Loss` → click **Send Now**; an email should land per the recipient field | FR-ACC-89, 92 |
| I5 | `AKD Quarterly VAT Summary` | Same as I4 — produces VAT Audit Report XLSX | FR-ACC-25 |

## J — Period-close prep (FR-ACC-66)

| # | Step | Expected |
| :-- | :-- | :-- |
| J1 | Period End Closing Voucher | `/app/period-closing-voucher/new` → fill company, fiscal year. **Will fail** unless AKD names a "Period Closing Account" (Q91 open item) |
| J2 | Run Exchange Rate Revaluation manually | `/app/exchange-rate-revaluation/new` → company=AKD, posting_date=today, rounding_loss_allowance=0.05 → **Get Accounts** → submit. Creates a JV like ACC-JV-2026-00002 |
| J3 | Re-run "AKD Monthly Balance Sheet" Auto Email Report at month-end | Sends PDF Balance Sheet to finance@akd-consulting.ae |

---

# Part 4 — Quick verification queries (run via console)

```bash
bench --site akd.com console
```

| Want to verify… | Query |
| :-- | :-- |
| All seeded SIs by status | `frappe.db.get_list("Sales Invoice", fields=["name","status","grand_total","currency"])` |
| VAT account balance | `frappe.db.sql("SELECT account, SUM(debit), SUM(credit) FROM \`tabGL Entry\` WHERE account LIKE 'VAT%-AKD' AND is_cancelled=0 GROUP BY account")` |
| Customer outstanding | `frappe.db.sql("SELECT customer, SUM(outstanding_amount) FROM \`tabSales Invoice\` WHERE docstatus=1 GROUP BY customer")` |
| Supplier outstanding | `frappe.db.sql("SELECT supplier, SUM(outstanding_amount) FROM \`tabPurchase Invoice\` WHERE docstatus=1 GROUP BY supplier")` |
| FX revaluation impact | `frappe.db.sql("SELECT SUM(debit-credit) FROM \`tabGL Entry\` WHERE account='Exchange Gain/Loss - AKD' AND is_cancelled=0")` |

---

# Part 5 — Known issues / open items surfaced by testing

| # | Issue | BRD ref | Action |
| :-- | :-- | :-- | :-- |
| 1 | `AKD Sales Invoice Overdue` notification fires but BRD says no auto customer reminders | FR-ACC-41 | Confirm with AKD; disable notification if Q59 stands |
| 2 | UAE-regional `VAT 5%`/`VAT Zero`/`VAT Exempted` accounts coexist with BRD-named `VAT Output`/`VAT Input` | FR-ACC-26, 27 | AKD decides: freeze regional or rename |
| 3 | Standard CoA uses `Debtors`/`Creditors`, not `Accounts Receivable (A/R)`/`Accounts Payable (A/P)` | FR-ACC-07, 08 | Aligns after Odoo CoA import |
| 4 | Currency Exchange provider is `frankfurter.dev` (default), not `exchangerate.host` | FR-ACC-20 | AKD provides API key |
| 5 | No company logo uploaded → print format header missing image | FR-ACC-94 | AKD supplies PNG |
| 6 | Period Closing Account on Company is null | Q91 (open) | AKD names the account |
| 7 | No User records — only Role Profiles | FR-ACC-84 | AKD provides emails for 5 users |
| 8 | Periodic inventory (per BRD) — Quark recommends perpetual | FR-ACC-79 | Defer to CRP |
