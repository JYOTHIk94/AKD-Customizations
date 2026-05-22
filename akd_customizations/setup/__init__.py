"""
AKD ERPNext v16 setup orchestrator.

Order of execution (see orchestrator.run):
  1. foundation.setup        — Company, Fiscal Year, currencies, Banks, Bank Accounts
  2. accounts_settings.apply — global Accounts Settings flags
  3. scaffold_accounts.add   — VAT Output/Input + FX gain/loss (placeholder
                               accounts that survive the Odoo CoA import only
                               if their names match the Odoo mapping)
  4. accounting.bootstrap    — cost centres + UAE VAT tax templates +
                               Mode of Payment wiring (existing module)

All steps are idempotent; re-running is safe.
"""
