"""
Sympl Solutions Proposal RAG — Data Analytics Domain Playbook

Contains established operating methodologies for multi-system discovery, data audits,
centralized SQL data warehouse architecture, ETL pipelines, Power BI/Tableau dashboards,
and Canadian data sovereignty / PIPEDA compliance.
Extracted strictly from historical Sympl proposal: AKM_2026.
"""

from typing import List

DATA_OPERATIONAL_PLAYBOOK_SYSTEM = """SYMPL DATA ANALYTICS & DATABASE PLAYBOOK (COMMON OPERATING PATTERNS):
When relevant to approved scope, incorporate Sympl's established data analytics methodologies:
1. Stakeholder & KPI Alignment:
   - Conduct leadership and departmental discovery interviews to define decision needs and reporting gaps.
   - Run structured KPI alignment workshops to establish unified metrics across organizational functions.
2. Cross-Platform Systems Mapping & Data Audit:
   - Inventory disparate source platforms (ticketing/CRM, scheduling, retail/POS, finance systems, and spreadsheets).
   - Establish data ownership matrices, document schema mismatches, and identify constituent duplicate records.
3. Centralized Data Architecture, Security & Governance:
   - Design centralized SQL data layer / warehouse connecting transactional, constituent, and operational metrics.
   - Build automated ETL ingestion routines with automated data cleansing and deduplication rules.
   - Enforce rigorous data security: Role-Based Access Control (RBAC), encryption in transit and at rest, and audit logs.
   - Canadian data sovereignty: strict PIPEDA compliance and Canadian cloud residency (Azure, AWS, or GCP Canada regions).
4. Executive Dashboards & Business Intelligence:
   - Configure interactive Power BI or Tableau leadership dashboards with operational drill-downs.
   - Visualize core metrics (e.g. sales velocity, retention curves, constituent engagement, and program profitability).
   - Develop clickable dashboard prototypes for early stakeholder validation.
5. Implementation Roadmap & Governance Handover:
   - Phased delivery schedule with defined milestones, budget ranges, and risk mitigations.
   - Complete technical documentation, data dictionaries, and internal team query/dashboard training.
IMPORTANT: Only use these workflows when relevant to approved scope. Do not hallucinate unapproved services, features, or administrative workflows."""

DATA_OPERATIONAL_PLAYBOOK_USER_LINES: List[str] = [
    "1. SYMPL DATA ANALYTICS & DATABASE PLAYBOOK (COMMON OPERATING PATTERNS):",
    "   When relevant to approved scope, incorporate Sympl's proven data methodologies:",
    "   * Stakeholder & KPI Alignment:",
    "     - Leadership and departmental interviews to define operational decision needs",
    "     - Structured KPI workshops to align definitions across teams",
    "   * Cross-Platform Systems Mapping & Audit:",
    "     - Inventory of disparate source systems, spreadsheets, and data owners",
    "     - Audit of schema mismatches, fragmented records, and deduplication requirements",
    "   * Centralized Architecture & Security:",
    "     - Centralized SQL data model and automated ETL cleansing pipelines",
    "     - Role-based access controls, encryption, and audit logging",
    "     - Canadian data residency and PIPEDA-aligned data governance",
    "   * Executive BI Dashboards:",
    "     - Interactive Power BI / Tableau dashboards for executive and operational tracking",
    "     - Clickable mockups and visualizations of core retention, velocity, and revenue metrics",
    "   * Roadmap & Handover:",
    "     - Phased delivery roadmap with budget ranges and review milestones",
    "     - Technical documentation, data dictionary, and staff knowledge transfer",
    "   IMPORTANT: Only use these workflows when relevant to approved scope. Do not hallucinate unapproved services."
]

# -----------------------------------------------------------------------------
# Phase 2C Domain Decoupling Metadata
# -----------------------------------------------------------------------------
BENCHMARK_REFERENCES: List[str] = ["AKM_2026"]

JSON_EXAMPLE_SUBHEADING: str = "Data Warehouse / Dashboard Architecture"

EXECUTIVE_SUMMARY_GUIDANCE: str = """EXECUTIVE SUMMARY NARRATIVE GUIDANCE (DATA ANALYTICS & CENTRALIZED DATABASE):
Problem:
Client operates disconnected operational systems (ticketing, donor CRM, marketing email), resulting in fragmented constituent profiles, duplicate records, and lack of cross-departmental reporting for leadership.
Approach:
Sympl executes an exhaustive cross-platform systems audit (AudienceView, Raiser's Edge, Mailchimp), engineers a centralized SQL data warehouse on Azure Canada Central cloud infrastructure with automated Python ETL pipelines, and configures interactive Power BI dashboards.
Outcome:
Real-time ticket sales velocity curves, audience retention cohort analysis, single source of truth for leadership, and strict Canadian cloud data residency (PIPEDA) compliance."""

DOMAIN_VOCABULARY: List[str] = [
    "AudienceView", "Raiser's Edge", "Mailchimp", "SQL Data Warehouse", "Python ETL",
    "Power BI", "Tableau", "Ticket Sales Velocity", "Audience Retention", "Patron Deduplication",
    "Azure Canada Central", "Canadian Cloud Residency", "PIPEDA", "Data Dictionary", "ERD",
    "Role-Based Access Control", "Data Governance Framework"
]

