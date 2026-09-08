"""
Sympl Solutions Proposal RAG — Proposal Writer Prompt Builder

Constructs strictly bounded, structured prompts for the Proposal Writer LLM.
Enforces:
  1. System instructions and persona: "You are the Sympl Solutions proposal writer."
  2. Client context and approved scope ingestion (never requested scope).
  3. Historical style exemplars isolated as STYLE & OPERATIONAL DEPTH GUIDANCE ONLY.
  4. Style rules, forbidden buzzword suppression, and executive summary constraints (<= 120 words).
  5. Minimum service depth: heading, cadence, operational activities, deliverables, boundaries.
  6. Deterministic reference block injection without rewriting.
  7. Strict JSON output schema enforcement matching proposal_draft.json.
"""

import json
from typing import Dict, Any, List, Optional, Tuple


class PromptBuilder:
    """
    Constructs the system prompt and user prompt for the proposal writer LLM.
    """

    FORBIDDEN_PHRASES = [
        "leverage",
        "cutting-edge",
        "game-changing",
        "holistic ecosystem",
        "unlock value",
        "bespoke transformation journey",
        "strategic synergies",
        "comprehensive suite",
        "continued success",
        "core mission",
        "strategic partnership",
        "world-class",
        "paradigm shift",
        "revolutionary",
        "unparalleled"
    ]

    SYSTEM_PROMPT = """You are the Sympl Solutions proposal writer.

Your objective is to convert an approved proposal plan into a professional, highly operational, and client-tailored proposal draft for Sympl Solutions.

CORE OPERATIONAL INVARIANTS:
1. Write operational financial service proposals with low-hype, high-clarity phrasing.
2. NEVER invent services, deliverables, systems, or compliance duties not present in the approved scope.
3. NEVER invent pricing amounts, fee structures, or billing terms. Use [PRICING_PLACEHOLDER] if fees are pending.
4. NEVER copy historical client names, historical dates, dollar figures, or headcounts from style exemplars.
5. Historical exemplars provide operational context and workflow terminology. Preserve the depth of operational activities (e.g. bill entry, payment processing, reconciliations, journal entries, compliance filings) WITHOUT copying historical names or numbers.
6. Reference blocks (Why Us, Backlog, Software, HR Boundary) MUST be inserted EXACTLY as provided. Do not rewrite, summarize, or alter them.
7. Executive Summary Requirements:
   - Must be under 120 words (1-2 concise paragraphs).
   - Start with a client-specific opening naming the organization.
   - Explicitly reference the approved service families.
   - Articulate concrete operational value (accuracy, audit-readiness, financial visibility).
   - Strictly avoid generic AI platitudes ("comprehensive suite", "continued success", "core mission", "strategic partnership").
8. Minimum Service Depth Requirements:
   For every approved service family, maintain historical proposal depth and include:
   - Service Heading: Clear, professional title.
   - Cadence: Stated operational frequency (e.g. weekly, semi-monthly, monthly, quarterly).
   - Operational Activities: Direct operational duties (3-5 specific bullet points).
   - Deliverables: Tangible recurring outputs (e.g. aged payables, reconciled ledgers, reporting packages).
   - Boundaries & Prerequisites: Clear boundaries (e.g. client manager approvals, timely receipts).
9. Service bullets must:
   - Target 6 to 20 words.
   - Start with active verbs (e.g. Manage, Reconcile, Prepare, Ingest, Review, Configure, Deliver, Process).
   - Use operational, direct language.
   - Avoid passive voice (e.g. NEVER write "will be managed by Sympl"; write "Manage ...").
   - Have NO trailing periods on bullet points.
10. Forbidden Buzzwords — NEVER use:
   - leverage, cutting-edge, game-changing, holistic ecosystem, unlock value
   - bespoke transformation journey, strategic synergies, comprehensive suite
   - continued success, core mission, strategic partnership, world-class
11. Output STRICTLY well-formed JSON matching the specified JSON schema. Do NOT output markdown code fences (```json) or conversational preamble."""

    @classmethod
    def build_prompt(cls, plan_data: Dict[str, Any], feedback_errors: Optional[List[str]] = None) -> Tuple[str, str]:
        """
        Builds (system_prompt, user_prompt) from the approved proposal plan.
        If feedback_errors is supplied (regeneration loop), includes error correction instructions.
        """
        # 1. Client Context
        client_ctx = plan_data.get("client_context") or {}
        client_name = plan_data.get("client_name") or client_ctx.get("name", "Client Organization")
        org_type = client_ctx.get("organization_type", "nonprofit")
        sector = client_ctx.get("sector", "community_services")
        current_systems = client_ctx.get("current_systems", [])
        target_systems = client_ctx.get("target_systems", [])
        eng_type = client_ctx.get("engagement_type", "recurring")
        complexity = client_ctx.get("complexity", "standard")
        fixed_term = client_ctx.get("fixed_term_duration")

        # 2. Approved Scope
        approved_scope = plan_data.get("approved_scope") or {}

        # 3. Sections & Exemplars
        sections_data = plan_data.get("sections") or []

        prompt_sections = []
        for sec in sections_data:
            sec_info = {
                "section_id": sec.get("section_id"),
                "section_title": sec.get("section_title"),
                "section_type": sec.get("section_type"),
                "service_family": sec.get("service_family"),
                "structural_role": sec.get("structural_role"),
                "instructions": sec.get("section_instructions", []),
                "style_rules": sec.get("style_rules_applied", [])
            }

            # If reference blocks are attached (e.g. Why Us or Exclusions)
            if sec.get("reference_blocks"):
                sec_info["exact_reference_blocks"] = [
                    b.get("content") for b in sec.get("reference_blocks", []) if b.get("content")
                ]

            # If retrieval exemplars are attached
            ret_ctx = sec.get("retrieval_context")
            if ret_ctx and ret_ctx.get("exemplars"):
                sec_info["historical_style_exemplars"] = [
                    {
                        "role": ex.get("role"),
                        "proposal_code": ex.get("proposal_code"),
                        "similarity_score": ex.get("similarity_score"),
                        "cleaned_text_guidance": ex.get("cleaned_text")
                    }
                    for ex in ret_ctx.get("exemplars", [])
                ]

            prompt_sections.append(sec_info)

        # 4. Pricing Structure
        pricing_data = plan_data.get("pricing") or plan_data.get("commercial_summary") or {}

        # 5. Assemble User Prompt
        parts = [
            "==================================================",
            "PROPOSAL GENERATION TASK FOR SYMPL SOLUTIONS",
            "==================================================",
            f"Client Name:       {client_name}",
            f"Organization Type: {org_type}",
            f"Sector:            {sector}",
            f"Current Systems:   {', '.join(current_systems) if current_systems else 'None specified'}",
            f"Target Systems:    {', '.join(target_systems) if target_systems else 'None specified'}",
            f"Engagement Type:   {eng_type} ({complexity})" + (f", Duration: {fixed_term}" if fixed_term else ""),
        ]

        # Enriched Client Narrative Context (appended when provided)
        if client_ctx.get("organization_description"):
            parts.append(f"Org Description:   {client_ctx['organization_description']}")
        if client_ctx.get("client_situation_summary"):
            parts.append(f"Client Situation:  {client_ctx['client_situation_summary']}")
        if client_ctx.get("client_challenges_summary"):
            parts.append(f"Client Challenges: {client_ctx['client_challenges_summary']}")
        if client_ctx.get("current_finance_challenges"):
            fc = client_ctx["current_finance_challenges"]
            fc_str = ", ".join(fc) if isinstance(fc, list) else str(fc)
            parts.append(f"Finance Challenges:{fc_str}")
        if client_ctx.get("current_finance_process"):
            parts.append(f"Finance Process:   {client_ctx['current_finance_process']}")
        if client_ctx.get("current_finance_team_structure"):
            parts.append(f"Finance Team:      {client_ctx['current_finance_team_structure']}")
        if client_ctx.get("reason_for_engagement"):
            parts.append(f"Engagement Reason: {client_ctx['reason_for_engagement']}")
        if client_ctx.get("desired_outcomes"):
            do = client_ctx["desired_outcomes"]
            do_str = ", ".join(do) if isinstance(do, list) else str(do)
            parts.append(f"Desired Outcomes:  {do_str}")
        if client_ctx.get("client_priorities"):
            cp = client_ctx["client_priorities"]
            cp_str = ", ".join(cp) if isinstance(cp, list) else str(cp)
            parts.append(f"Client Priorities: {cp_str}")

        parts.extend([
            "",
            "--- APPROVED SERVICE SCOPE (AUTHORITATIVE & COMPLETE) ---",
            "Every generated service MUST belong to this approved scope:",
            json.dumps(approved_scope, indent=2),
            "",
            "--- TARGET PROPOSAL SECTIONS & HISTORICAL EXEMPLARS ---",
            json.dumps(prompt_sections, indent=2),
            "",
            "--- COMMERCIAL SCHEDULE & TERMS ---",
            json.dumps(pricing_data, indent=2),
            ""
        ])

        # 6. If feedback errors present (Regeneration Loop)
        if feedback_errors:
            parts.extend([
                "==================================================",
                "CRITICAL: PREVIOUS ATTEMPT FAILED VALIDATION",
                "==================================================",
                "The previous output failed validation with the following errors. You MUST correct these in your new output:",
                "\n".join(f"  * {err}" for err in feedback_errors),
                ""
            ])

        # 7. Output Format Specification
        parts.extend([
            "==================================================",
            "REQUIRED JSON OUTPUT STRUCTURE",
            "==================================================",
            "Output a single JSON object with EXACTLY this schema:",
            "{",
            '  "title": "Accounting & Bookkeeping Services Proposal for ' + client_name + '",',
            '  "executive_summary": "Under 120 words. Client-specific opening stating Sympl will provide [approved services] to maintain accurate records, streamline workflows, and ensure financial clarity.",',
            '  "sections": [',
            '    {',
            '      "section_title": "Section Title as designated above",',
            '      "opening_text": "Brief 1-2 sentence framing text introducing the section scope and operating cadence.",',
            '      "subsections": [',
            '        {',
            '          "heading": "Operational Sub-heading (e.g. Accounts Payable & Vendor Disbursement Processing)",',
            '          "bullets": [',
            '            "Action verb starting bullet (6-20 words) describing specific operational activity",',
            '            "Action verb starting bullet (6-20 words) describing specific operational deliverable"',
            '          ]',
            '        }',
            '      ]',
            '    }',
            '  ],',
            '  "why_us": [',
            '    "Exact reference block string 1",',
            '    "Exact reference block string 2"',
            '  ],',
            '  "pricing": {',
            '    "pricing_model": "...",',
            '    "currency": "...",',
            '    "billing_schedule": "...",',
            '    "fee_items": [...],',
            '    "has_placeholders": boolean',
            '  },',
            '  "exclusions": [',
            '    "Exact conditional disclaimer string 1"',
            '  ],',
            '  "validation_metadata": {}',
            "}",
            "",
            "Generate ONLY the raw JSON object. No explanations, no markdown ticks."
        ])

        return cls.SYSTEM_PROMPT, "\n".join(parts)
