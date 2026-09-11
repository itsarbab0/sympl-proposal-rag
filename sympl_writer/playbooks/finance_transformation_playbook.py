"""
Sympl Solutions Proposal RAG — Finance Transformation & Advisory Playbook

Contains established operating methodologies for multi-funder budget revamps, chart of accounts
realignment, standardized Excel + Power BI reporting, and dynamic multi-scenario financial forecasting.
Extracted strictly from historical Sympl proposal: COMPASS_2026.
"""

from typing import List

FINANCE_TRANSFORMATION_PLAYBOOK_SYSTEM = """SYMPL FINANCE TRANSFORMATION & ADVISORY PLAYBOOK (COMMON OPERATING PATTERNS):
When relevant to approved scope, incorporate Sympl's established financial transformation methodologies:
1. Operational Budget Process Revamp:
   - Consolidate fragmented departmental spreadsheets into a single unified annual budget model.
   - Build multi-funder revenue and expense allocation formulas (e.g. ministry grants, donor funds).
   - Back-test the new budgeting model against historical actual transactions to validate funding splits.
2. Chart of Accounts & GL Code Realignment:
   - Diagnostic review of existing GL accounts against funder reporting standards and operational needs.
   - Redesign class and department structures so transactions tag automatically to program and funder.
   - Implement realigned GL codes directly in the client's accounting platform (QBO, Xero, or ERP) so nothing runs in a parallel system.
3. Standardized Reporting Framework (Excel + Power BI):
   - Design operational Excel reports pulling directly from the realigned ledger.
   - Create high-clarity Power BI dashboards with executive variance commentary and KPI heatmaps for board review.
   - Execute one complete live reporting cycle during rollout to test templates and validate outputs.
4. Dynamic Financial Forecasting & Scenario Modeling:
   - Engineer a 12-month rolling cash flow and multi-year forecasting engine.
   - Centralize modeling inputs into a single Assumptions tab (wage rates, inflation, headcount) driving all outputs automatically without spreadsheet rebuilds.
   - Incorporate scenario layers: collective bargaining impact, multi-year operating cost escalation, and organizational restructuring.
5. Change Management & Governance Handover:
   - Conduct structured walkthroughs and provide practical user documentation on model logic.
   - Establish a dependable recurring monthly and quarterly reporting cadence.
IMPORTANT: Only use these workflows when relevant to approved scope. Do not hallucinate website redesign, CMS platforms, or non-financial data pipelines."""

FINANCE_TRANSFORMATION_PLAYBOOK_USER_LINES: List[str] = [
    "1. SYMPL FINANCE TRANSFORMATION PLAYBOOK (COMMON OPERATING PATTERNS):",
    "   When relevant to approved scope, incorporate Sympl's proven advisory methodologies:",
    "   * Budget Process Revamp:",
    "     - Single annual budget model consolidating fragmented departmental spreadsheets",
    "     - Multi-funder allocation logic and historical transaction back-testing",
    "   * GL Realignment & Class Tagging:",
    "     - Diagnostic review of chart of accounts against funder reporting standards",
    "     - Automated program and funder class tagging deployed directly in core ledger",
    "   * Reporting Framework (Excel + Power BI):",
    "     - Reconciled operational Excel schedules paired with Power BI board visualizations",
    "     - Live reporting cycle test prior to operational handover",
    "   * Dynamic Forecasting & Scenarios:",
    "     - Assumptions-driven rolling cash flow and multi-year forecasting model",
    "     - Scenario analysis (collective bargaining, cost inflation, organizational restructuring)",
    "   * Phased Rollout & Governance:",
    "     - Phased transition schedule, model user manuals, and finance committee sign-off",
    "   IMPORTANT: Only use these workflows when relevant to approved scope. Do not hallucinate unapproved services."
]

# -----------------------------------------------------------------------------
# Phase 2C Domain Decoupling Metadata
# -----------------------------------------------------------------------------
BENCHMARK_REFERENCES: List[str] = ["COMPASS_2026"]

JSON_EXAMPLE_SUBHEADING: str = "Forecast Model / Budget Framework"

EXECUTIVE_SUMMARY_GUIDANCE: str = """EXECUTIVE SUMMARY NARRATIVE GUIDANCE (FINANCE TRANSFORMATION & BUDGET REVAMP):
Problem:
Client operates complex multi-site facilities with multiple ministry funding allocations, relying on fragmented departmental spreadsheets prone to formula errors and delayed financial projections.
Approach:
Sympl consolidates budgeting into an automated, formulaic annual budget model, realigns the chart of accounts and general ledger codes to program cost centers, and engineers a 12-month rolling cash flow forecast driven by an Assumptions tab.
Outcome:
Dynamic scenario simulation (wage hikes, funding delays), 40%+ reduction in budget preparation cycles, ministry grant compliance, and executive board variance reporting decks."""

DOMAIN_VOCABULARY: List[str] = [
    "Budget Process Revamp", "Multi-Funder Allocations", "MCCSS Ministry Allocations",
    "12-Month Rolling Cash Flow Forecast", "Assumptions Tab", "Salary Grid Step Modeling",
    "Dynamic Scenario Analysis", "Class Code Tagging", "Chart of Accounts Realignment",
    "Sudbury/Manitoulin Consolidation", "Board Variance Reporting", "KPI Heatmaps"
]

