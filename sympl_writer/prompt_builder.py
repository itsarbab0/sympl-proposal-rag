"""
Sympl Solutions Proposal RAG — Proposal Writer Prompt Builder

Constructs strictly bounded, structured prompts for the Proposal Writer LLM.
Enforces:
  1. System instructions and persona: "You are the Sympl Solutions proposal writer."
  2. Dynamic playbook resolution based on service_category, generic_services, and approved_scope.
  3. Client context and approved scope ingestion (never requested scope).
  4. Historical style exemplars isolated as STYLE & OPERATIONAL DEPTH GUIDANCE ONLY.
  5. Style rules, forbidden buzzword suppression, and executive summary narrative constraints.
  6. Minimum service depth: heading, cadence, operational activities, deliverables, boundaries.
  7. Deterministic reference block injection without rewriting.
  8. Strict JSON output schema enforcement matching proposal_draft.json.
  9. Internal playbook selection audit log generation.
"""

import json
from typing import Dict, Any, List, Optional, Tuple

from sympl_writer.playbooks import (
    BASE_STYLE_SYSTEM_PERSONA,
    BASE_STYLE_SYSTEM_RULES,
    BASE_STYLE_USER_HEADER,
    BASE_STYLE_USER_INSTRUCTIONS_LINES,
    BASE_STYLE_DOMAIN_NEUTRAL_PERSONA_TEMPLATE,
    BASE_STYLE_DOMAIN_NEUTRAL_RULES,
    BASE_STYLE_DOMAIN_NEUTRAL_USER_HEADER_TEMPLATE,
    BASE_STYLE_DOMAIN_NEUTRAL_USER_INSTRUCTIONS_LINES,
    FORBIDDEN_PHRASES,
    ACCOUNTING_OPERATIONAL_PLAYBOOK_SYSTEM,
    ACCOUNTING_OPERATIONAL_PLAYBOOK_USER_LINES,
    PlaybookRegistry,
    PlaybookAuditLog,
)


class PromptBuilder:
    """
    Constructs the system prompt and user prompt for the proposal writer LLM.
    """

    FORBIDDEN_PHRASES = FORBIDDEN_PHRASES

    # Baseline default static system prompt for backwards-compatibility checks
    SYSTEM_PROMPT = f"{BASE_STYLE_SYSTEM_PERSONA}\n\n{ACCOUNTING_OPERATIONAL_PLAYBOOK_SYSTEM}\n\n{BASE_STYLE_SYSTEM_RULES}"
    
    # Internal audit log from most recent resolution
    last_audit_log: Optional[PlaybookAuditLog] = None

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

        # 2. Approved Scope & Generic Services
        approved_scope = plan_data.get("approved_scope") or {}
        generic_services = plan_data.get("generic_services") or approved_scope.get("generic_services")
        service_category = (
            plan_data.get("service_category")
            or client_ctx.get("service_category")
            or plan_data.get("metadata", {}).get("service_category")
        )

        # 3. Dynamic Playbook Resolution
        resolution = PlaybookRegistry.resolve_playbook(
            service_category=service_category,
            approved_scope=approved_scope,
            generic_services=generic_services,
            client_context=client_ctx,
            plan_data=plan_data
        )
        cls.last_audit_log = resolution.audit_log

        is_accounting = (resolution.audit_log.playbook_selected == "accounting_playbook")

        if is_accounting:
            system_prompt = f"{BASE_STYLE_SYSTEM_PERSONA}\n\n{resolution.system_prompt}\n\n{BASE_STYLE_SYSTEM_RULES}"
        else:
            benchmarks_str = ", ".join(resolution.benchmark_references)
            persona = BASE_STYLE_DOMAIN_NEUTRAL_PERSONA_TEMPLATE.format(BENCHMARKS=benchmarks_str)
            system_prompt = f"{persona}\n\n{resolution.system_prompt}\n\n{BASE_STYLE_DOMAIN_NEUTRAL_RULES}"

        # 4. Sections & Exemplars
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

        # 5. Pricing Structure
        pricing_data = plan_data.get("pricing") or plan_data.get("commercial_summary") or {}

        # 6. Assemble User Prompt with Domain Playbook Lines & Guidance
        if is_accounting:
            parts = [
                *BASE_STYLE_USER_HEADER,
                *resolution.user_lines,
                "",
                *BASE_STYLE_USER_INSTRUCTIONS_LINES,
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
        else:
            benchmarks_str = ", ".join(resolution.benchmark_references)
            domain_user_header = [
                line.format(BENCHMARKS=benchmarks_str) if "{BENCHMARKS}" in line else line
                for line in BASE_STYLE_DOMAIN_NEUTRAL_USER_HEADER_TEMPLATE
            ]
            parts = [
                *domain_user_header,
                *resolution.user_lines,
                "",
            ]
            if resolution.executive_summary_guidance:
                parts.extend([
                    resolution.executive_summary_guidance,
                    "",
                ])
            parts.extend([
                *BASE_STYLE_DOMAIN_NEUTRAL_USER_INSTRUCTIONS_LINES,
                "==================================================",
                "PROPOSAL GENERATION TASK FOR SYMPL SOLUTIONS",
                "==================================================",
                f"Client Name:       {client_name}",
                f"Organization Type: {org_type}",
                f"Sector:            {sector}",
                f"Current Systems:   {', '.join(current_systems) if current_systems else 'None specified'}",
                f"Target Systems:    {', '.join(target_systems) if target_systems else 'None specified'}",
                f"Engagement Type:   {eng_type} ({complexity})" + (f", Duration: {fixed_term}" if fixed_term else ""),
            ])

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

        # 7. If feedback errors present (Regeneration Loop)
        if feedback_errors:
            parts.extend([
                "==================================================",
                "CRITICAL: PREVIOUS ATTEMPT FAILED VALIDATION",
                "==================================================",
                "The previous output failed validation with the following errors. You MUST correct these in your new output:",
                "\n".join(f"  * {err}" for err in feedback_errors),
                ""
            ])

        # 8. Output Format Specification with Context-Aware Title
        playbook_name = resolution.audit_log.playbook_selected
        if playbook_name == "website_playbook":
            sample_title = f"Website Development Proposal for {client_name}"
        elif playbook_name == "data_playbook":
            sample_title = f"Data Analytics & Centralized Database Proposal for {client_name}"
        elif playbook_name == "finance_transformation_playbook":
            sample_title = f"Budget Revamp & Financial Forecasting Proposal for {client_name}"
        elif playbook_name == "general_consulting_playbook":
            sample_title = f"Consulting Services Proposal for {client_name}"
        else:
            sample_title = "Accounting & Bookkeeping Services Proposal for " + client_name

        subheading_example = (
            "Accounts Payable & Vendor Disbursement Workflow"
            if is_accounting
            else resolution.json_example_subheading
        )

        parts.extend([
            "==================================================",
            "REQUIRED JSON OUTPUT STRUCTURE",
            "==================================================",
            "Output a single JSON object with EXACTLY this schema:",
            "{",
            f'  "title": "{sample_title}",',
            '  "executive_summary": "Pure narrative paragraphs (no bullet points). Provide sufficient detail to explain the client\'s situation, challenges, Sympl\'s approach, and expected outcomes. Do not optimize for word count.",',
            '  "sections": [',
            '    {',
            '      "section_title": "Section Title as designated above",',
            '      "opening_text": "Substantive contextual narrative containing sufficient narrative depth, integrating Client Situation, Operational Challenge, and Sympl Approach (methodology & cloud workflows).",',
            '      "subsections": [',
            '        {',
            f'          "heading": "Operational Sub-heading (e.g. {subheading_example})",',
            '          "context": "Context paragraph explaining why this function matters for this specific client.",',
            '          "approach": "Sympl Approach paragraph detailing methodology, standards, and execution framework.",',
            '          "workflow": "Operational Workflow paragraph explaining the step-by-step process and tooling (when relevant).",',
            '          "bullets": [',
            '            "Action verb starting bullet for key activities or deliverables (maximum 4-6 bullets)"',
            '          ],',
            '          "outcome": "Expected Outcome paragraph explaining business impact, clarity, audit-readiness, or governance.",',
            '          "narrative": "Unified narrative fallback (if discrete context/approach/workflow/outcome are not used separately)"',
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

        return system_prompt, "\n".join(parts)
