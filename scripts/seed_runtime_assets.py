#!/usr/bin/env python3
"""First Controlled Runtime-Asset Database Seeder for Sympl Proposal RAG.

Inserts approved runtime style rules (21 rows) and reference blocks (13 rows)
into the dedicated PostgreSQL / pgvector database.

Enforces:
- Atomic single-transaction execution
- Pre-validation of reference block source lineage against proposal_chunks.cleaned_text
- Insert-if-absent
- Skip-if-identical
- Fail + rollback if drift detected (RUNTIME_ASSET_DRIFT_DETECTED)
- Safe idempotency without automatic updates or deletions
- Zero modifications to historical tables (proposal_documents, proposal_chunks, dataset_imports)
- Zero embedding generation or vector modification
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import psycopg
from psycopg.types.json import Jsonb


# =============================================================================
# APPROVED RUNTIME STYLE RULES MANIFEST (EXACTLY 21 ROWS)
# =============================================================================

STYLE_RULES_MANIFEST: List[Dict[str, Any]] = [
    # Global Rules (6)
    {
        "rule_key": "RULE_GLOBAL_DIRECT_VERB_LEADS",
        "category": "syntax",
        "rule_text": "Begin service scope bullets with an active, direct present-tense verb (Manage, Prepare, Process, Reconcile, Maintain, Record, Ensure). Avoid passive voice and introductory filler like 'Sympl will'.",
        "priority": "P1",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "global",
            "target_scope": "service_bullets",
        },
    },
    {
        "rule_key": "RULE_GLOBAL_NO_TRAILING_PERIODS",
        "category": "punctuation",
        "rule_text": "Do not end standard service scope task bullets with a trailing period. Reserve terminal periods for multi-sentence descriptions or closing prose paragraphs.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "global",
            "target_scope": "service_bullets",
        },
    },
    {
        "rule_key": "RULE_GLOBAL_CONCISE_BULLETS",
        "category": "length",
        "rule_text": "Keep service task bullets concise and operationally focused, targeting between 6 and 15 words. Avoid multi-sentence narrative task descriptions.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "global",
            "target_scope": "service_bullets",
        },
    },
    {
        "rule_key": "RULE_GLOBAL_LOW_HYPE_TONE",
        "category": "tone",
        "rule_text": "Maintain a grounded, understated Canadian professional services tone. Strictly avoid generic consulting buzzwords. Legitimate operational terms ('streamline', 'seamless') are permitted in concrete contexts.",
        "priority": "P1",
        "active": True,
        "metadata": {
            "strength": "HARD",
            "applies_to": "global",
            "target_scope": "all_prose",
        },
    },
    {
        "rule_key": "RULE_GLOBAL_NATURAL_VERB_REPETITION",
        "category": "lexical",
        "rule_text": "Permit natural repetition of common operational verbs across adjacent task bullets. Do not force artificial synonym variation to avoid repetition.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "global",
            "target_scope": "service_bullets",
        },
    },
    {
        "rule_key": "RULE_GLOBAL_CLIENT_SPECIFIC_INTEGRATION",
        "category": "client_adaptation",
        "rule_text": "Integrate approved client-specific operational details (named software, pay frequencies, account targets) directly into service bullets and headings.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "global",
            "target_scope": "service_bullets",
        },
    },
    # Section Rules (10)
    {
        "rule_key": "RULE_SEC_BOOKKEEPING_WORKFLOW",
        "category": "scope_structure",
        "rule_text": "Organize approved bookkeeping tasks into clear operational categories. Use direct action bullets. When reconciliations are in scope, name the account/reconciliation target and cadence when known. When AP/AR or approval workflows are included, preserve current responsibility boundaries. Do NOT force services absent from current scope.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "section",
            "section_family": "bookkeeping",
        },
    },
    {
        "rule_key": "RULE_SEC_PAYROLL_STRUCTURE",
        "category": "scope_structure",
        "rule_text": "Present approved payroll responsibilities in a logical operational sequence. State cadence and staff coverage when known. Group current processing, remittance/compliance, reconciliation, year-end filings, systems, and responsibility boundaries only when those items are actually part of current scope. Historical payroll examples must NEVER add a statutory filing or compliance task not present in current requirements.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "section",
            "section_family": "payroll",
        },
    },
    {
        "rule_key": "RULE_SEC_REPORTING_GOVERNANCE",
        "category": "scope_structure",
        "rule_text": "Present current approved reports as clearly named deliverables, normally grouped by audience/cadence where useful. State delivery frequency when known. Distinguish management, board, funder, and program reporting only where current requirements include them. Do NOT force a standard reporting package unless present in client scope.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "section",
            "section_family": "financial_reporting",
        },
    },
    {
        "rule_key": "RULE_SEC_COMPLIANCE_DELINEATION",
        "category": "scope_structure",
        "rule_text": "Name the specific approved statutory/compliance responsibility directly, including cadence and responsible party when known. Avoid vague compliance guarantees. Preserve exact current filing and external-party boundaries. Do NOT assume auditor files T3010, CPA files tax return, PSB rebate applies, or HST applies unless established by current client facts.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "section",
            "section_family": "compliance",
        },
    },
    {
        "rule_key": "RULE_SEC_AUDIT_LIAISON_FRAMEWORK",
        "category": "scope_structure",
        "rule_text": "Describe approved audit-preparation/support tasks operationally and preserve a clear distinction between Sympl support and the external audit itself. Include PBC items, schedules, query-response commitments, meetings, or cleanup methodology only when explicitly scoped. Do NOT universally force PBC lists or response SLAs.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "section",
            "section_family": "audit",
        },
    },
    {
        "rule_key": "RULE_SEC_TRANSFORMATION_MODULARITY",
        "category": "scope_structure",
        "rule_text": "Structure transformation work around the current project's actual modules \u2014 which may be discrete software initiatives, assessment/strategy, implementation, workflow redesign, migration, integration, or training. Use concrete operational tasks and approved systems; avoid abstract transformation language. Do NOT force a rigid lifecycle unless scoped.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "section",
            "section_family": "digital_transformation",
        },
    },
    {
        "rule_key": "RULE_SEC_TRAINING_SUPPORT",
        "category": "scope_structure",
        "rule_text": "Present approved training/change-management work as concrete deliverables and audiences. State training format, documentation, handoff, and post-go-live support only when they are part of current scope. Do NOT force SOPs, quick guides, or multi-month support unless approved.",
        "priority": "P3",
        "active": True,
        "metadata": {
            "strength": "SOFT",
            "applies_to": "section",
            "section_family": "training",
        },
    },
    {
        "rule_key": "RULE_SEC_TRANSITION_CONTINUITY",
        "category": "scope_structure",
        "rule_text": "Frame transition engagements around continuity and handoff. Organize approved transition tasks chronologically when useful, while preserving existing systems/processes only where current client scope requires continuity. Do NOT force legacy tool retention or shadowing unless scoped.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "section",
            "section_family": "transition",
        },
    },
    {
        "rule_key": "RULE_SEC_WHY_US_STRUCTURE",
        "category": "scope_structure",
        "rule_text": "Structure Why Us as: (1) invariant opening declaration, (2) approved atomic credential bullets with optional current-client-supported variants, and (3) concluding standalone commitment paragraphs. Reference-block selection must come from current planner/client metadata and never historical nearest-neighbor retrieval.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "section",
            "section_family": "why_us",
        },
    },
    {
        "rule_key": "RULE_SEC_PRICING_FORMATTING",
        "category": "scope_structure",
        "rule_text": "Present ONLY approved pricing categories. When multiple fee types exist, separate them clearly with concise labels and place relevant conditions adjacent to the corresponding fee. Never invent amounts, fee categories, tax treatment, or exclusions.",
        "priority": "P1",
        "active": True,
        "metadata": {
            "strength": "HARD",
            "applies_to": "section",
            "section_family": "pricing",
        },
    },
    # Archetype Rules (5)
    {
        "rule_key": "RULE_ARCH_COMPACT_BOOKKEEPING",
        "category": "archetype_structure",
        "rule_text": "Use a direct operational opening with minimal diagnostic prose, a compact section count, short service blocks, and high conciseness. Why Us is historically often omitted but remains planner-controlled. Do not add services, commercial conditions, or exclusions not present in approved current scope.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "archetype",
            "archetype_key": "ARCH_COMPACT_BOOKKEEPING",
        },
    },
    {
        "rule_key": "RULE_ARCH_STANDARD_NONPROFIT",
        "category": "archetype_structure",
        "rule_text": "Use a moderate-detail operational structure with clear grouping of approved services. Include governance- or funder-specific detail only when present in approved current scope. Why Us is commonly included but remains planner-controlled. The archetype may organize scope but must never create services.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "archetype",
            "archetype_key": "ARCH_STANDARD_NONPROFIT",
        },
    },
    {
        "rule_key": "RULE_ARCH_TRANSITION_INTERIM",
        "category": "archetype_structure",
        "rule_text": "Use narrative transition framing, state the engagement horizon when known, emphasize continuity, and organize approved milestones chronologically when useful. Do not force catch-up, handover, shadowing, or legacy-system preservation unless those items exist in approved current scope.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "archetype",
            "archetype_key": "ARCH_TRANSITION_INTERIM",
        },
    },
    {
        "rule_key": "RULE_ARCH_COMPREHENSIVE_TRANSFORMATION",
        "category": "archetype_structure",
        "rule_text": "Use a formal diagnostic Context & Objectives opening, higher detail density, and modular sections for approved workstreams. Do not force digital transformation, financial management, audit, training, multiple initiatives, or Part A/B/C structure unless current scope includes them.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "archetype",
            "archetype_key": "ARCH_COMPREHENSIVE_TRANSFORMATION",
        },
    },
    {
        "rule_key": "RULE_ARCH_AUDIT_OVERSIGHT_TRANSFORMATION",
        "category": "archetype_structure",
        "rule_text": "When the planner has already established audit, oversight, or transformation-related scope, use diagnostic/objective-led framing, high operational detail, clear timelines when known, and strong responsibility boundaries. The archetype must never create audit, transformation, access, or responsibility commitments.",
        "priority": "P2",
        "active": True,
        "metadata": {
            "strength": "STRONG",
            "applies_to": "archetype",
            "archetype_key": "ARCH_AUDIT_OVERSIGHT_TRANSFORMATION",
        },
    },
]


# =============================================================================
# APPROVED REFERENCE BLOCKS MANIFEST (EXACTLY 13 ROWS)
# =============================================================================

REFERENCE_BLOCKS_MANIFEST: List[Dict[str, Any]] = [
    {
        "block_key": "REF_BLOCK_WHY_US_OPENING",
        "block_type": "why_us",
        "name": "Why Us Canonical Opening",
        "content": "Sympl Solutions is committed to ensuring a high standard of financial clarity and timely support. We bring:",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "DETERMINISTIC",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "intro",
            "source_chunk_keys": [
                "RPFF_2025_WHY_US",
                "YPT_2026_WHY_US",
                "GOODFOOT_2026_WHY_US",
                "TACT_2026_WHY_US",
                "PIRS_2025_WHY_US",
            ],
            "source_proposals": [
                "RPFF_2025",
                "YPT_2026",
                "GOODFOOT_2026",
                "TACT_2026",
                "PIRS_2025",
            ],
            "selection_condition": {
                "planner_include_why_us": True,
            },
            "fallback": "omit",
        },
    },
    {
        "block_key": "REF_BLOCK_WHY_US_CREDENTIAL_RESPONSIVE_TEAM",
        "block_type": "why_us",
        "name": "Why Us Responsive Team Credential",
        "content": "A responsive, detail-oriented team",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "DETERMINISTIC",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "bullet",
            "source_chunk_keys": [
                "RPFF_2025_WHY_US",
                "YPT_2026_WHY_US",
                "GOODFOOT_2026_WHY_US",
                "TACT_2026_WHY_US",
                "PIRS_2025_WHY_US",
            ],
            "source_proposals": [
                "RPFF_2025",
                "YPT_2026",
                "GOODFOOT_2026",
                "TACT_2026",
                "PIRS_2025",
            ],
            "selection_condition": {
                "planner_include_why_us": True,
            },
            "fallback": "omit",
        },
    },
    {
        "block_key": "REF_BLOCK_WHY_US_EXP_NONPROFIT",
        "block_type": "why_us",
        "name": "Why Us Nonprofit Expertise",
        "content": "Decade-long expertise in nonprofit finance",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "VARIANT",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "bullet",
            "source_chunk_keys": [
                "RPFF_2025_WHY_US",
                "YPT_2026_WHY_US",
                "GOODFOOT_2026_WHY_US",
                "PIRS_2025_WHY_US",
            ],
            "source_proposals": [
                "RPFF_2025",
                "YPT_2026",
                "GOODFOOT_2026",
                "PIRS_2025",
            ],
            "selection_condition": {
                "organization_type": ["nonprofit"],
                "must_be_explicit": True,
            },
            "fallback": "omit",
        },
    },
    {
        "block_key": "REF_BLOCK_WHY_US_EXP_CHARITY",
        "block_type": "why_us",
        "name": "Why Us Charity Expertise",
        "content": "Decade-long expertise in nonprofit and charity finance",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "VARIANT",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "bullet",
            "source_chunk_keys": [
                "TACT_2026_WHY_US",
            ],
            "source_proposals": [
                "TACT_2026",
            ],
            "selection_condition": {
                "organization_type": ["charity"],
                "must_be_explicit": True,
            },
            "fallback": "omit",
        },
    },
    {
        "block_key": "REF_BLOCK_WHY_US_CREDENTIAL_TECH_INTEGRATION",
        "block_type": "why_us",
        "name": "Why Us Technology Integration Credential",
        "content": "Streamlined tech integration and clear process flows",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "DETERMINISTIC",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "bullet",
            "source_chunk_keys": [
                "RPFF_2025_WHY_US",
                "YPT_2026_WHY_US",
                "GOODFOOT_2026_WHY_US",
                "TACT_2026_WHY_US",
                "PIRS_2025_WHY_US",
            ],
            "source_proposals": [
                "RPFF_2025",
                "YPT_2026",
                "GOODFOOT_2026",
                "TACT_2026",
                "PIRS_2025",
            ],
            "selection_condition": {
                "planner_include_why_us": True,
            },
            "fallback": "omit",
        },
    },
    {
        "block_key": "REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL",
        "block_type": "why_us",
        "name": "Why Us Community & Social Identity",
        "content": "BIPOC and immigrant-led leadership with lived experiences in community, social service and arts & culture",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "VARIANT",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "bullet",
            "source_chunk_keys": [
                "GOODFOOT_2026_WHY_US",
                "TACT_2026_WHY_US",
                "PIRS_2025_WHY_US",
            ],
            "source_proposals": [
                "GOODFOOT_2026",
                "TACT_2026",
                "PIRS_2025",
            ],
            "selection_condition": {
                "sector": [
                    "social_services",
                    "community_services",
                    "community_organization",
                ],
                "planner_select_identity_credential": True,
                "must_be_explicit": True,
            },
            "fallback": "omit",
        },
    },
    {
        "block_key": "REF_BLOCK_WHY_US_SECTOR_ARTS_LEADERSHIP",
        "block_type": "why_us",
        "name": "Why Us Arts Leadership Identity",
        "content": "BIPOC-led leadership with lived experiences in community arts",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "VARIANT",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "bullet",
            "source_chunk_keys": [
                "RPFF_2025_WHY_US",
                "YPT_2026_WHY_US",
            ],
            "source_proposals": [
                "RPFF_2025",
                "YPT_2026",
            ],
            "selection_condition": {
                "sector": ["arts_culture"],
                "planner_select_identity_credential": True,
                "must_be_explicit": True,
            },
            "fallback": "omit",
        },
    },
    {
        "block_key": "REF_BLOCK_WHY_US_SECTOR_ARTS_EXP_RPFF",
        "block_type": "why_us",
        "name": "Why Us National Arts Experience",
        "content": "Experience with arts and non-profit organizations across Canada",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "VARIANT",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "bullet",
            "source_chunk_keys": [
                "RPFF_2025_WHY_US",
            ],
            "source_proposals": [
                "RPFF_2025",
            ],
            "selection_condition": {
                "sector": ["arts_culture"],
                "planner_select_national_arts_experience_credential": True,
                "must_be_explicit": True,
            },
            "fallback": "omit",
        },
    },
    {
        "block_key": "REF_BLOCK_WHY_US_CLOSING_1",
        "block_type": "why_us",
        "name": "Why Us Closing Vision",
        "content": "We value thoughtful system design, clarity in reporting, and building long-term trusted partnerships.",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "DETERMINISTIC",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "paragraph",
            "source_chunk_keys": [
                "RPFF_2025_WHY_US",
                "YPT_2026_WHY_US",
                "GOODFOOT_2026_WHY_US",
                "TACT_2026_WHY_US",
            ],
            "source_proposals": [
                "RPFF_2025",
                "YPT_2026",
                "GOODFOOT_2026",
                "TACT_2026",
            ],
            "selection_condition": {
                "planner_include_why_us": True,
            },
            "fallback": "omit",
        },
    },
    {
        "block_key": "REF_BLOCK_WHY_US_CLOSING_2",
        "block_type": "why_us",
        "name": "Why Us Closing Flexibility",
        "content": "Any new requirements or adjustments can be discussed and integrated as needed. We work with transparency, flexibility, and a commitment to helping our partners thrive.",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "DETERMINISTIC",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "paragraph",
            "source_chunk_keys": [
                "RPFF_2025_WHY_US",
                "YPT_2026_WHY_US",
                "GOODFOOT_2026_WHY_US",
                "TACT_2026_WHY_US",
                "PIRS_2025_WHY_US",
            ],
            "source_proposals": [
                "RPFF_2025",
                "YPT_2026",
                "GOODFOOT_2026",
                "TACT_2026",
                "PIRS_2025",
            ],
            "selection_condition": {
                "planner_include_why_us": True,
            },
            "fallback": "omit",
        },
    },
    {
        "block_key": "REF_BLOCK_EXCLUSIONS_BACKLOG",
        "block_type": "exclusions",
        "name": "Catch-up Backlog Exclusion",
        "content": "Bookkeeping backlog: Any prior period bookkeeping clean-up or catch-up work will be quoted separately based on the volume and complexity",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "CONDITIONAL",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "note",
            "source_chunk_keys": [
                "CAREOF_2025_EXCLUSIONS",
                "CAHOOTS_2026_EXCLUSIONS",
                "RPFF_2025_EXCLUSIONS",
            ],
            "source_proposals": [
                "CAREOF_2025",
                "CAHOOTS_2026",
                "RPFF_2025",
            ],
            "selection_condition": {
                "commercial_terms.include_backlog_exclusion": True,
                "requires_explicit_current_approval": True,
            },
            "fallback": "omit",
        },
    },
    {
        "block_key": "REF_BLOCK_EXCLUSIONS_SOFTWARE_NOT_INCLUDED",
        "block_type": "exclusions",
        "name": "Software Fees Not Included",
        "content": "Note: Above costs do not include software subscription fees.",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "CONDITIONAL",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "note",
            "source_chunk_keys": [
                "GOODFOOT_2026_EXCLUSIONS",
            ],
            "source_proposals": [
                "GOODFOOT_2026",
            ],
            "selection_condition": {
                "commercial_terms.software_fees_excluded": True,
                "requires_explicit_current_approval": True,
            },
            "fallback": "omit",
        },
    },
    {
        "block_key": "REF_BLOCK_PAYROLL_HR_BOUNDARY",
        "block_type": "boundary",
        "name": "Payroll HR Responsibility Boundary",
        "content": "Note: While we manage all payroll accounting and processing, managers must provide timely payroll data (e.g., timesheets, new hires, exits). We do not manage HR functions.",
        "approved": True,
        "version": 1,
        "metadata": {
            "classification": "CONDITIONAL",
            "source_mode": "EXACT_SOURCE_BLOCK",
            "render_as": "note",
            "source_chunk_keys": [
                "PIRS_2025_PAYROLL",
            ],
            "source_proposals": [
                "PIRS_2025",
            ],
            "selection_condition": {
                "current_scope.payroll_processing_by_sympl": True,
                "current_scope.manager_payroll_input_responsibility": True,
                "current_scope.hr_functions_excluded": True,
            },
            "fallback": "omit",
        },
    },
]


def load_database_url() -> str | None:
    """Safely retrieve DATABASE_URL from environment or local .env files without echoing credentials."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.strip():
        return db_url.strip()

    search_paths = [
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path.cwd() / ".env",
    ]

    for env_path in search_paths:
        if env_path.exists() and env_path.is_file():
            try:
                with env_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            if k.strip() == "DATABASE_URL" and v.strip():
                                os.environ["DATABASE_URL"] = v.strip().strip("'\"")
                                return os.environ["DATABASE_URL"]
            except Exception:
                pass

    return None


def validate_manifest_safety() -> List[str]:
    """Perform pre-flight safety validations on manifests prior to DB execution."""
    errors: List[str] = []

    # Verify style rules count
    if len(STYLE_RULES_MANIFEST) != 21:
        errors.append(f"Expected 21 style rules, found {len(STYLE_RULES_MANIFEST)}")

    allowed_priorities = {"P1", "P2", "P3"}
    allowed_applies_to = {"global", "section", "archetype"}

    for rule in STYLE_RULES_MANIFEST:
        if rule["priority"] not in allowed_priorities:
            errors.append(f"Invalid priority '{rule['priority']}' in {rule['rule_key']}")
        applies_to = rule.get("metadata", {}).get("applies_to")
        if applies_to not in allowed_applies_to:
            errors.append(f"Invalid applies_to '{applies_to}' in {rule['rule_key']}")

    # Verify reference blocks count
    if len(REFERENCE_BLOCKS_MANIFEST) != 13:
        errors.append(f"Expected 13 reference blocks, found {len(REFERENCE_BLOCKS_MANIFEST)}")

    for block in REFERENCE_BLOCKS_MANIFEST:
        if not block.get("approved"):
            errors.append(f"Reference block {block['block_key']} approved is not True")
        if block.get("version") != 1:
            errors.append(f"Reference block {block['block_key']} version != 1")
        meta = block.get("metadata", {})
        if meta.get("source_mode") != "EXACT_SOURCE_BLOCK":
            errors.append(f"Reference block {block['block_key']} source_mode != EXACT_SOURCE_BLOCK")

        # Presentation bullet prefix safety
        if meta.get("render_as") == "bullet":
            content = block.get("content", "").strip()
            for prefix in ["-", "•", "*", "–", "—"]:
                if content.startswith(prefix):
                    errors.append(f"Bullet block {block['block_key']} starts with presentation prefix '{prefix}'")

    return errors


def seed_runtime_assets() -> int:
    print("============================================================")
    print("SYMPL RUNTIME ASSET SEED")
    print("============================================================")

    # 1. Manifest pre-flight validation
    manifest_errors = validate_manifest_safety()
    if manifest_errors:
        print("[ERROR] Pre-flight manifest safety check failed:")
        for err in manifest_errors:
            print(f"  - {err}")
        return 1

    # 2. Database connection
    db_url = load_database_url()
    if not db_url:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return 1

    try:
        conn = psycopg.connect(db_url)
    except Exception as exc:
        print(f"[ERROR] Database connection failed: {type(exc).__name__}")
        return 1

    style_inserted = 0
    style_skipped = 0
    ref_inserted = 0
    ref_skipped = 0
    drift_detected = 0
    errors = 0
    drift_details: List[str] = []

    with conn:
        with conn.cursor() as cur:
            # 3. Source lineage verification for reference blocks against proposal_chunks
            cur.execute("SELECT chunk_key, cleaned_text FROM proposal_chunks;")
            chunk_map = {r[0]: r[1] for r in cur.fetchall()}

            for block in REFERENCE_BLOCKS_MANIFEST:
                content = block["content"]
                source_keys = block.get("metadata", {}).get("source_chunk_keys", [])
                if not source_keys:
                    print(f"[ERROR] Reference block {block['block_key']} has empty source_chunk_keys")
                    errors += 1
                for sk in source_keys:
                    if sk not in chunk_map:
                        print(f"[ERROR] Source chunk key '{sk}' not found in proposal_chunks")
                        errors += 1
                    else:
                        cleaned = chunk_map[sk]
                        if content not in cleaned:
                            print(f"[ERROR] Content for '{block['block_key']}' is not an exact contiguous substring of '{sk}'")
                            errors += 1

            if errors > 0:
                print(f"[ERROR] Pre-seed lineage validation failed with {errors} errors. Aborting.")
                return 1

            # 4. Atomic transaction execution
            try:
                with conn.transaction():
                    # Process Style Rules
                    cur.execute(
                        """
                        SELECT rule_key, category, rule_text, priority, active, metadata
                        FROM sympl_style_rules;
                        """
                    )
                    existing_rules = {r[0]: {
                        "rule_key": r[0],
                        "category": r[1],
                        "rule_text": r[2],
                        "priority": r[3],
                        "active": r[4],
                        "metadata": r[5],
                    } for r in cur.fetchall()}

                    for rule in STYLE_RULES_MANIFEST:
                        rkey = rule["rule_key"]
                        if rkey not in existing_rules:
                            cur.execute(
                                """
                                INSERT INTO sympl_style_rules (
                                    rule_key, category, rule_text, priority, active, metadata
                                ) VALUES (%s, %s, %s, %s, %s, %s);
                                """,
                                (
                                    rule["rule_key"],
                                    rule["category"],
                                    rule["rule_text"],
                                    rule["priority"],
                                    rule["active"],
                                    Jsonb(rule["metadata"]),
                                ),
                            )
                            style_inserted += 1
                        else:
                            ex = existing_rules[rkey]
                            is_identical = (
                                ex["category"] == rule["category"]
                                and ex["rule_text"] == rule["rule_text"]
                                and ex["priority"] == rule["priority"]
                                and ex["active"] == rule["active"]
                                and ex["metadata"] == rule["metadata"]
                            )
                            if is_identical:
                                style_skipped += 1
                            else:
                                drift_detected += 1
                                diff_fields = []
                                if ex["category"] != rule["category"]:
                                    diff_fields.append("category")
                                if ex["rule_text"] != rule["rule_text"]:
                                    diff_fields.append("rule_text")
                                if ex["priority"] != rule["priority"]:
                                    diff_fields.append("priority")
                                if ex["active"] != rule["active"]:
                                    diff_fields.append("active")
                                if ex["metadata"] != rule["metadata"]:
                                    diff_fields.append("metadata")
                                drift_details.append(f"Style rule '{rkey}' differs on fields: {diff_fields}")

                    # Process Reference Blocks
                    cur.execute(
                        """
                        SELECT block_key, block_type, name, content, approved, version, metadata
                        FROM sympl_reference_blocks;
                        """
                    )
                    existing_blocks = {r[0]: {
                        "block_key": r[0],
                        "block_type": r[1],
                        "name": r[2],
                        "content": r[3],
                        "approved": r[4],
                        "version": r[5],
                        "metadata": r[6],
                    } for r in cur.fetchall()}

                    for block in REFERENCE_BLOCKS_MANIFEST:
                        bkey = block["block_key"]
                        if bkey not in existing_blocks:
                            cur.execute(
                                """
                                INSERT INTO sympl_reference_blocks (
                                    block_key, block_type, name, content, approved, version, metadata
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                                """,
                                (
                                    block["block_key"],
                                    block["block_type"],
                                    block["name"],
                                    block["content"],
                                    block["approved"],
                                    block["version"],
                                    Jsonb(block["metadata"]),
                                ),
                            )
                            ref_inserted += 1
                        else:
                            ex = existing_blocks[bkey]
                            is_identical = (
                                ex["block_type"] == block["block_type"]
                                and ex["name"] == block["name"]
                                and ex["content"] == block["content"]
                                and ex["approved"] == block["approved"]
                                and ex["version"] == block["version"]
                                and ex["metadata"] == block["metadata"]
                            )
                            if is_identical:
                                ref_skipped += 1
                            else:
                                drift_detected += 1
                                diff_fields = []
                                if ex["block_type"] != block["block_type"]:
                                    diff_fields.append("block_type")
                                if ex["name"] != block["name"]:
                                    diff_fields.append("name")
                                if ex["content"] != block["content"]:
                                    diff_fields.append("content")
                                if ex["approved"] != block["approved"]:
                                    diff_fields.append("approved")
                                if ex["version"] != block["version"]:
                                    diff_fields.append("version")
                                if ex["metadata"] != block["metadata"]:
                                    diff_fields.append("metadata")
                                drift_details.append(f"Reference block '{bkey}' differs on fields: {diff_fields}")

                    # Check for drift detection
                    if drift_detected > 0:
                        raise RuntimeError("RUNTIME_ASSET_DRIFT_DETECTED")

            except Exception as exc:
                # Transaction rolls back automatically on exception exit
                errors += 1
                print("------------------------------------------------------------")
                if "RUNTIME_ASSET_DRIFT_DETECTED" in str(exc):
                    print("RUNTIME_ASSET_DRIFT_DETECTED")
                    for d in drift_details:
                        print(f"  - {d}")
                else:
                    print(f"[ERROR] Transaction failed: {exc}")
                print("TRANSACTION ROLLED BACK. ZERO CHANGES COMMITTED.")
                print("------------------------------------------------------------")
                print(f"Style rules inserted:    {style_inserted}")
                print(f"Style rules skipped:     {style_skipped}")
                print(f"Reference blocks inserted: {ref_inserted}")
                print(f"Reference blocks skipped:  {ref_skipped}")
                print(f"Drift detected:          {drift_detected}")
                print(f"Errors:                  {errors}")
                return 1

    # 5. Output seeder summary
    print("------------------------------------------------------------")
    print("SEED EXECUTION SUMMARY")
    print("------------------------------------------------------------")
    print(f"Style rules inserted:     {style_inserted}")
    print(f"Style rules skipped:      {style_skipped}")
    print(f"Reference blocks inserted: {ref_inserted}")
    print(f"Reference blocks skipped:  {ref_skipped}")
    print(f"Drift detected:           {drift_detected}")
    print(f"Errors:                   {errors}")
    print("------------------------------------------------------------")
    print("STATUS: SUCCESS")
    print("============================================================")
    return 0


def main() -> int:
    try:
        return seed_runtime_assets()
    except Exception as exc:
        print(f"\n[FATAL] Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
