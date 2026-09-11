"""
Sympl Solutions Proposal RAG — Accounting & Bookkeeping Domain Playbook

Contains established operating methodologies for accounting, bookkeeping,
payroll, and financial reporting engagements (QBO, Dext, Plooto, close workflows).
Extracted verbatim from Phase 1 prompt instructions without textual modifications.
"""

from typing import List

ACCOUNTING_OPERATIONAL_PLAYBOOK_SYSTEM = """SYMPL OPERATIONAL PLAYBOOK (COMMON OPERATING PATTERNS):
When relevant to approved scope, incorporate Sympl's established operating methodologies:
1. Bookkeeping & General Ledger:
   - QuickBooks Online migration and chart of accounts cleanup to establish program-level and fund-accounting visibility.
   - Dext receipt capture and mobile expense ingestion to eliminate paper receipts and manual tracking.
   - Structured month-end close workflow and disciplined reconciliation cadence (bank accounts, credit cards, payroll clearing).
2. Accounts Payable & Payments:
   - Systematic invoice review and GL coding against organizational budgets.
   - Transparent separation of duties and dual-control approval workflow.
   - Plooto payment approval process where Sympl queues batches and client leadership approves with one-touch email authorization.
3. Financial Reporting & Governance:
   - Monthly financial package: Statement of Operations (P&L with budget vs actual analysis), Balance Sheet, and Cash Flow schedules.
   - Board reporting packages with executive variance commentary tailored for board meetings and finance committees.
   - Clear reporting deadlines (e.g. financial packages delivered by the 15th business day following month-end close).
IMPORTANT: Only use these workflows when relevant to approved scope. Do not hallucinate unapproved services."""

ACCOUNTING_OPERATIONAL_PLAYBOOK_USER_LINES: List[str] = [
    "1. SYMPL OPERATIONAL PLAYBOOK (COMMON OPERATING PATTERNS):",
    "   When relevant to approved scope, incorporate Sympl's proven operating methodologies:",
    "   * Bookkeeping:",
    "     - QuickBooks Online migration and chart of accounts cleanup",
    "     - Dext receipt capture and electronic expense ingestion",
    "     - Month-end close workflow and disciplined reconciliation cadence",
    "   * Payments:",
    "     - Rigorous invoice review and budget verification",
    "     - Dual-control approval workflow",
    "     - Plooto/payment approval process with one-touch client executive sign-off",
    "   * Reporting:",
    "     - Comprehensive monthly financial package (P&L, Balance Sheet, Cash Flow)",
    "     - Board reporting with variance commentary for finance committees",
    "     - Budget vs actual analysis and dependable reporting deadlines (e.g. by 15th business day)",
    "   IMPORTANT: Only use these workflows when relevant to approved scope. Do not hallucinate unapproved services."
]

# -----------------------------------------------------------------------------
# Phase 2C Domain Decoupling Metadata
# -----------------------------------------------------------------------------
BENCHMARK_REFERENCES: List[str] = ["TACT", "YPT", "RPFF"]

JSON_EXAMPLE_SUBHEADING: str = "Accounts Payable & Vendor Disbursement Workflow"

EXECUTIVE_SUMMARY_GUIDANCE: str = """EXECUTIVE SUMMARY NARRATIVE GUIDANCE (ACCOUNTING & MANAGED BOOKKEEPING):
Problem:
Client relies on fragmented legacy desktop software, vulnerable solo in-house bookkeeping, and suffers from reconciliation backlogs, paper receipts, or delayed reporting.
Approach:
Sympl deploys a paperless cloud accounting infrastructure (QuickBooks Online, Dext, Plooto, WagePoint), structured weekly accounts payable/receivable cycles, and disciplined month-end close reconciliations.
Outcome:
Audit-ready financial records, predictable cash flow visibility, funder-compliant grant expenditure tracking, and executive board governance reporting."""

DOMAIN_VOCABULARY: List[str] = [
    "QuickBooks Online", "QBO", "Dext", "Plooto", "WagePoint", "Bank Reconciliations",
    "Accounts Payable", "Accounts Receivable", "CRA Payroll Remittances", "CPP/EI",
    "GST/HST", "PSB Rebate", "T3010", "General Ledger", "Chart of Accounts",
    "Trial Balance", "Lead Schedules", "Working Papers", "Month-End Close"
]

