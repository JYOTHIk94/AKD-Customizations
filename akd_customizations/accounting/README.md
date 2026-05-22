# Accounting Module — AKD Customizations

Customizations for AKD Consulting LLC's ERPNext v16 Accounting setup.

Scope: BRD Section 4 (FR-ACC-01 → FR-ACC-100).

## Contents
- `../fixtures/` — Payment Terms, Modes of Payment, Tax Templates, Cost Centres, Notifications, Auto Email Reports.
- `../print_format/akd_sales_invoice/` — A4 Sales Invoice print format with TRN, logo, bank details.
- `../tasks/supplier_payment_reminders.py` — daily overdue PI scan (FR-ACC-34).
- `../utils/opening_balance.py` — Odoo → ERPNext opening-balance importer (FR-ACC-75/76).
- `../overrides/sales_invoice.py` — credit-limit validation hook (FR-SELL-09).

See `../../../AKD/AKD_Implementation_BRD_v4 (1).docx.md` for source requirements.
