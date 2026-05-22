# AKD Fixed Assets Module — Manual Testing Script

**Site:** akd.com   **Company:** AKD Consulting LLC   **Tester:** _______________   **Date:** _______________

Source BRD: `AKD_Implementation_BRD_v4` — Section 10 (FR-FA-01 → FR-FA-83).
Heavily trimmed module — ~50 of 83 items are BRD "No" (Maintenance, Movements,
CWIP, Revaluation, Insurance, Location/Custodian, Barcode all OFF).

Setup (run once, as Administrator):
```
bench --site akd.com migrate                                               # custom fields + doc_events
bench --site akd.com execute akd_customizations.setup.fixed_assets.setup    # categories, accounts, settings, company defaults
bench --site akd.com execute akd_customizations.setup.seed_fixed_assets.seed_all
```
Reset: `bench --site akd.com execute akd_customizations.setup.seed_fixed_assets.purge`

---

## 0. Pre-requisites

| # | Item | Details |
|---|---|---|
| P1 | Site available | `http://akd.com:8002`, Administrator |
| P2 | CoA present | accounting setup run (Fixed Assets / Income / Expense parents exist) |
| P3 | Decisions | D-FA-1 (method per category — default Straight Line), D-FA-2 (per-category GL), D-FA-3 (PI link) acknowledged |
| P4 | Users | Accountant = Accounts Manager / Accounts User (no new roles per FR-FA-71/72) |

---

## 1. Categories & accounts (FR-FA-03, 04, 22, 23, 24, 25)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-FA-01 | FR-FA-04 | Asset Category list | `Furniture & Fittings`, `IT Equipment` exist; CWIP unchecked |  |
| TS-FA-02 | FR-FA-23/24 | Open `IT Equipment` → finance book | method Straight Line, 12 depreciations, frequency 3 (Quarterly), **daily pro-rata ticked** |  |
| TS-FA-03 | FR-FA-23 | Open `Furniture & Fittings` finance book | 20 depreciations (5 yr × quarterly) |  |
| TS-FA-04 | FR-FA-22/D-FA-2 | Category → Accounts tab | fixed-asset + accumulated-depreciation + depreciation-expense accounts wired for AKD |  |
| TS-FA-05 | FR-FA-78 | Accounts Settings | `Automatically post depreciation entries` = ticked |  |
| TS-FA-06 | FR-FA-54 | Company → disposal account | set to `Gain or Loss on Asset Disposal - AKD` (Other Income) |  |

## 2. Asset lifecycle & depreciation (FR-FA-21, 25, 26)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-FA-07 | FR-FA-21 | Open seeded `TEST-FA PC 01`, submit | Depreciation schedule generated, quarterly rows, daily pro-rata amounts |  |
| TS-FA-08 | FR-FA-26 | Set `Expected Value After Useful Life` (fixed salvage amount) on the asset, re-derive | Schedule respects the fixed salvage amount (not a %) |  |
| TS-FA-09 | FR-FA-16 | Create a Purchase Invoice with a fixed-asset item (`TEST-FA-ITEM-PC`) | Asset auto-created under IT Equipment (note D-FA-3) |  |

## 3. Disposal approval (FR-FA-52, 53, 54, 55)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-FA-10 | FR-FA-55 | Submit `TEST-FA PC 01` (disposal **not** approved), try **Sell Asset** → submit the Sales Invoice | **Blocked**: "Disposal not approved for Asset(s)…" |  |
| TS-FA-11 | FR-FA-55 | Try **Scrap Asset** on the same unapproved asset (Journal Entry) | **Blocked** by the same approval guard |  |
| TS-FA-12 | FR-FA-55 | Tick **Disposal Approved** on the asset; confirm `Disposal Approved By` stamps the user | Stamp recorded; remarks saved |  |
| TS-FA-13 | FR-FA-52/53/54 | Now Sell the approved `TEST-FA PC 02` | Sales Invoice posts; gain/loss to **Other Income** disposal account |  |

## 4. Reports (FR-FA-65)

| ID | BRD | Steps | Expected | P/F |
|---|---|---|---|---|
| TS-FA-14 | FR-FA-65 | Run **Fixed Asset Register** | Seeded assets listed with gross / accumulated dep / net |  |
| TS-FA-15 | FR-FA-65 | Run **Depreciation Schedule** | Quarterly schedule per asset reconciles to GL |  |

---

## Notes
- **D-FA-1:** depreciation method defaults to **Straight Line** for both categories (FR-FA-22 says "varies by category" but §12.7 Q28 left blank). Change per category at CRP.
- **D-FA-2:** per-category GL accounts auto-created under the standard CoA parents (§12.7 Q10/Q11 blank) — AKD confirms/relocates at CRP.
- **D-FA-3:** ERPNext links the auto-created Asset to the Purchase Invoice; FR-FA-18 says "no link" — confirm acceptable or create assets manually.
- **FR-FA-26 salvage:** entered as a fixed amount per asset (`Expected Value After Useful Life`); category salvage % left 0.
- Migration of existing assets with opening accumulated depreciation (FR-FA-27/76/77) = Data Import at cut-over (CRP §12.7 Q101–104) — not seeded here.

## Out of scope (BRD "No" — do not test)
CWIP/construction (FR-FA-08/30–35) · Maintenance & Repairs (FR-FA-36–46) · Movements/Custodian/Location (FR-FA-10–14/47–50) · Revaluation/Impairment (FR-FA-57–60) · Insurance (FR-FA-61–64) · Barcode/RFID/verification (FR-FA-67/68/81/82) · bulk acquisition (FR-FA-19) · sub-categories (FR-FA-05) · multi-book (FR-FA-28) · shift depreciation (FR-FA-29).
