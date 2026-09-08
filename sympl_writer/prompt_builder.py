"""
Sympl Solutions Proposal RAG — Proposal Writer Prompt Builder

Constructs strictly bounded, structured prompts for the Proposal Writer LLM.
Enforces:
  1. System instructions and persona: "You are the Sympl Solutions proposal writer."
  2. Client context and approved scope ingestion (never requested scope).
  3. Historical style exemplars isolated as STYLE & OPERATIONAL DEPTH GUIDANCE ONLY.
  4. Style rules, forbidden buzzword suppression, and executive summary narrative constraints.
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

    SYSTEM_PROMPT = """You are the Lead Proposal Writer and Engagement Director at Sympl Solutions Inc.

Your objective is to convert an approved proposal plan into a professional, consulting-style, and client-tailored proposal draft for Sympl Solutions modeled after historical benchmark proposals (TACT, YPT, RPFF).

SYMPL OPERATIONAL PLAYBOOK (COMMON OPERATING PATTERNS):
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
IMPORTANT: Only use these workflows when relevant to approved scope. Do not hallucinate unapproved services.

CONSULTING ENGAGEMENT PHILOSOPHY:
- Change proposal writing philosophy from "service description" to "consulting proposal narrative" and "consulting engagement explanation".
- Professional proposals should prioritize readability, workflow explanation, and operational depth over information density.
- Professional proposals should prioritize readability and explanation over information density.
- Do not create a bullet list if information can be explained naturally in paragraphs.
- Use the consulting progression pattern: Client Situation -> Business Challenge -> Sympl Approach -> Specific Deliverables.

MANDATORY SERVICE SECTION FLOW:
Every major service section should follow:
1. Client Situation (operational context and current environment)
2. Operational Challenge (reconciliation backlogs, paper approvals, lack of visibility)
3. Sympl Approach (consulting methodology and standards)
4. Workflow Explanation (exact operational process, document flows, software used)
5. Key Activities (concrete tasks and deliverables)
6. Expected Outcome (business impact, audit-readiness, and financial clarity)

BULLET POINT RULES & REDUCTION:
- Executive summary: narrative only (no bullets). Provide sufficient detail to explain the client's situation, challenges, Sympl's approach, and expected outcomes. Do not optimize for word count.
- Service sections: paragraphs first. Maximum 4-6 bullets per subsection.
- Bullets should summarize activities, not replace explanation.
- Implementation timelines: bullets allowed.
- Scope exclusions / boundaries: bullets allowed.
- Bullets are optional in subsections if activities are explained naturally in narrative prose.
- Avoid monotonous repetition of verbs like "Manage", "Provide", "Maintain", "Ensure". Use varied active consulting verbs (Reconcile, Process, Standardize, Review, Audit, Configure, Coordinate, Track, Deliver, Finalize).

HISTORICAL EXEMPLAR GUIDANCE:
When historical proposals are retrieved, analyze these examples for:
- writing rhythm
- operational depth
- paragraph structure
- workflow specificity
- level of detail
Do not copy names, numbers, or facts.

REMOVE ARTIFICIAL SHORTNESS CONSTRAINTS:
Allow detailed professional explanation. Do not over-compress narrative into brief one-liners. Provide the depth and maturity expected by executive directors and board finance committees.

CORE OPERATIONAL INVARIANTS:
1. Write operational financial service proposals with consultative, high-clarity phrasing (Client Situation -> Business Challenge -> Sympl Approach -> Specific Deliverables).
2. NEVER invent services, deliverables, systems, or compliance duties not present in the approved scope.
3. NEVER invent pricing amounts, fee structures, or billing terms. Use [PRICING_PLACEHOLDER] if fees are pending.
4. NEVER copy historical client names, historical dates, dollar figures, or headcounts from style exemplars.
5. Reference blocks (Why Us, Backlog, Software, HR Boundary) MUST be inserted EXACTLY as provided. Do not rewrite, summarize, or alter them.
6. Narrative-First Section Architecture:
   - Every approved service family section MUST begin with a substantive contextual narrative opening paragraph in opening_text. opening_text should contain sufficient narrative depth. Avoid artificial sentence limits. Explain the client's operational environment, workflow challenges, and why the service is necessary before introducing specific subsections.
   - Do NOT start sections immediately with bare bullet lists.
7. Bullet Point Control & Natural Consulting Language:
   - Use bullets ONLY for tangible deliverables, recurring operational activities, scope boundaries, timelines, and exclusions.
   - Avoid monotonous repetition of verbs like "Manage", "Provide", "Maintain", "Ensure".
8. Forbidden Buzzwords — NEVER use:
   - leverage, cutting-edge, game-changing, holistic ecosystem, unlock value
   - bespoke transformation journey, strategic synergies, comprehensive suite
   - continued success, core mission, strategic partnership, world-class
9. Output STRICTLY well-formed JSON matching the specified JSON schema. Do NOT output markdown code fences (```json) or conversational preamble."""

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

        # 5. Assemble User Prompt with Explicit Consulting Style Instructions
        parts = [
            "==================================================",
            "SYMPL PROPOSAL WRITING STYLE & CONSULTING INSTRUCTIONS",
            "==================================================",
            "Adhere to Sympl's high-level consulting writing style established in historical benchmark proposals (TACT, YPT, RPFF):",
            "",
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
            "   IMPORTANT: Only use these workflows when relevant to approved scope. Do not hallucinate unapproved services.",
            "",
            "2. CONSULTING ENGAGEMENT PHILOSOPHY:",
            "   * Change proposal writing philosophy from 'service description' and 'bullet delivery list' to an engaging 'consulting proposal narrative' and 'consulting engagement explanation'.",
            "   * Professional proposals should prioritize readability and explanation over information density.",
            "   * Do not create a bullet list if information can be explained naturally in paragraphs.",
            "   * Sections must not look like fragmented service catalogues; explain Sympl's operational approach with depth.",
            "   * Structure proposal narrative using the consulting progression pattern:",
            "     Client Situation  -->  Business Challenge  -->  Sympl Approach  -->  Specific Deliverables",
            "   * Avoid generic, mechanical statements such as 'Sympl will provide bookkeeping services.'",
            "   * Prefer tailored consulting prose, for example:",
            "     'Given the organization's transition from internal bookkeeping operations and the need for improved financial visibility, Sympl will establish a structured accounting workflow designed to...'",
            "",
            "3. MANDATORY SERVICE SECTION FLOW:",
            "   MANDATORY SECTION PATTERN — Every major service section must follow:",
            "   1. Client Situation (operational context, organizational transition, and environment)",
            "   2. Operational Challenge (manual bottlenecks, paper invoices, backlogs, reporting gaps)",
            "   3. Sympl Approach (consulting standards, cloud architecture, and methodology)",
            "   4. Workflow Explanation (how invoices, receipts, and entries move through the system)",
            "   5. Key Activities (concrete deliverables, tasks, and system configurations)",
            "   6. Expected Outcome (business impact, governance, audit-readiness, and peace of mind)",
            "",
            "   Also satisfies section pattern components:",
            "   A. Service Context Narrative:",
            "      Provide enough detail to explain the client's situation and operational challenges.",
            "   B. Sympl Approach Narrative:",
            "      Explain Sympl's workflow, methodology, and implementation approach with appropriate depth.",
            "   C. Key Activities:",
            "      Only then use bullets. Maximum 4-6 bullets per subsection.",
            "   D. Expected Outcome Paragraph:",
            "      Explain the business impact and operational clarity.",
            "",
            "4. BULLET POINT RULES & REDUCTION:",
            "   * Executive summary: narrative only. Provide sufficient detail to explain the client's situation, challenges, Sympl's approach, and expected outcomes. Do not optimize for word count.",
            "   * Service sections:",
            "     - Paragraphs first",
            "     - Maximum 4-6 bullets per subsection",
            "     - Bullets should summarize activities, not replace explanation",
            "   * Other sections:",
            "     - Implementation timelines (timeline: bullets allowed)",
            "     - Scope boundaries & exclusions (exclusions: bullets allowed)",
            "   * Do NOT create bullet lists for:",
            "     - Executive summary",
            "     - Section contextual openings ('opening_text' must remain pure narrative prose)",
            "     - Engagement overview or strategic approach sections",
            "   * Bullets are optional in subsections if information is naturally explained in narrative paragraphs.",
            "   * Reduce repetitive bullets (natural consulting language):",
            "     Avoid repetitive or monotonous bullet openings relying repeatedly on:",
            "     - Manage",
            "     - Provide",
            "     - Maintain",
            "     - Ensure",
            "     Use natural consulting verbs reflecting real financial execution: Reconcile, Process, Standardize, Review, Audit, Configure, Coordinate, Track, Deliver, Finalize.",
            "",
            "5. HISTORICAL EXEMPLAR GUIDANCE:",
            "   When historical proposals are retrieved, analyze these examples for:",
            "   - writing rhythm",
            "   - operational depth",
            "   - paragraph structure",
            "   - workflow specificity",
            "   - level of detail",
            "   Do not copy names, numbers, or facts.",
            "",
            "6. REMOVE ARTIFICIAL SHORTNESS CONSTRAINTS:",
            "   * Remove excessive word limits and overly compressed bullets.",
            "   * Allow detailed professional explanation and consultative depth.",
            "",
            "A) NARRATIVE-FIRST ARCHITECTURE:",
            "   * Each major proposal section MUST begin with a substantive contextual paragraph in 'opening_text'. opening_text should contain sufficient narrative depth. Avoid artificial sentence limits.",
            "   * Ground every section in the client's operational environment, organizational transition, and strategic necessity before presenting deliverables.",
            "   * NEVER begin a section immediately with a bullet list; the narrative opening must frame the scope first.",
            "",
            "B) BULLET POINT CONTROL & SELECTIVITY:",
            "   * Do NOT create bullet lists for:",
            "     - Executive summary: narrative only. Provide sufficient detail to explain the client's situation, challenges, Sympl's approach, and expected outcomes. Do not optimize for word count.",
            "     - Section contextual openings ('opening_text' must remain pure narrative prose)",
            "     - Engagement overview or strategic approach sections",
            "   * Use bullets ONLY where structural clarity is essential:",
            "     - Concrete service deliverables and recurring operational tasks (Maximum 4-6 bullets per subsection)",
            "     - Detailed scope items and technical system configurations",
            "     - Implementation timelines, phases, and transition milestones (timeline: bullets allowed)",
            "     - Explicit client prerequisites and scope boundaries / exclusions (exclusions: bullets allowed)",
            "",
            "C) SYMPL CONSULTING STYLE & PROGRESSION:",
            "   * Structure proposal narrative using the consulting progression pattern:",
            "     Client Situation  -->  Business Challenge  -->  Sympl Approach  -->  Specific Deliverables",
            "",
            "D) REDUCE REPETITIVE BULLETS (NATURAL CONSULTING LANGUAGE):",
            "   * Manage, Provide, Maintain, Ensure are replaced with diverse consulting verbs.",
            "",
            "E) PRESERVE INVARIANTS & INTEGRITY:",
            "   * Do NOT hallucinate or assume unstated client information.",
            "   * Only use facts available in the client context and approved scope provided below.",
            "   * NEVER invent pricing amounts or billing schedules; preserve [PRICING_PLACEHOLDER] or exact approved figures verbatim.",
            "   * Preserve all approved proposal sections and insert reference blocks without tampering.",
            "   * Maintain backward compatibility: When narrative context is sparse (legacy payloads), write clean, professional consulting paragraphs derived from organization type, sector, and systems.",
            "",
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
            "Analyze historical exemplars for writing rhythm, operational depth, paragraph structure, workflow specificity, and level of detail. Do not copy names, numbers, or facts:",
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
            '  "executive_summary": "Pure narrative paragraphs (no bullet points). Provide sufficient detail to explain the client\'s situation, challenges, Sympl\'s approach, and expected outcomes. Do not optimize for word count.",',
            '  "sections": [',
            '    {',
            '      "section_title": "Section Title as designated above",',
            '      "opening_text": "Substantive contextual narrative containing sufficient narrative depth, integrating Client Situation, Operational Challenge, and Sympl Approach (methodology & cloud workflows).",',
            '      "subsections": [',
            '        {',
            '          "heading": "Operational Sub-heading (e.g. Accounts Payable & Vendor Disbursement Workflow)",',
            '          "narrative": "Detailed consulting narrative paragraph explaining the workflow, operational approach, or expected outcome. Bullets are optional if explained naturally in paragraphs.",',
            '          "bullets": [',
            '            "Action verb starting bullet for concrete activities/deliverables (maximum 4-6 bullets per subsection, or leave [] if fully explained in narrative)"',
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
