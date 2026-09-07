"""
Sympl Solutions Proposal RAG — Proposal Writer Prompt Builder

Constructs strictly bounded, structured prompts for the Proposal Writer LLM.
Enforces:
  1. System instructions and persona: "You are the Sympl Solutions proposal writer."
  2. Client context and approved scope ingestion (never requested scope).
  3. Historical style exemplars isolated as STYLE GUIDANCE ONLY — DO NOT COPY FACTS.
  4. Style rules and forbidden buzzword suppression.
  5. Deterministic reference block injection without rewriting.
  6. Strict JSON output schema enforcement matching proposal_draft.json.
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
        "strategic synergies"
    ]

    SYSTEM_PROMPT = """You are the Sympl Solutions proposal writer.

Your objective is to convert an approved proposal plan into a professional, operational, and client-tailored proposal draft for Sympl Solutions.

CORE OPERATIONAL INVARIANTS:
1. Write operational financial service proposals with low-hype, high-clarity phrasing.
2. NEVER invent services, deliverables, systems, or compliance duties not present in the approved scope.
3. NEVER invent pricing amounts, fee structures, or billing terms. Use [PRICING_PLACEHOLDER] if fees are pending.
4. NEVER copy historical client names, historical dates, dollar figures, or headcounts from style exemplars.
5. Historical exemplars are provided for STYLE, TONE, AND RHYTHM GUIDANCE ONLY. DO NOT copy historical text.
6. Reference blocks (Why Us, Backlog, Software, HR Boundary) MUST be inserted EXACTLY as provided. Do not rewrite, summarize, or alter them.
7. Service bullets must:
   - Target 6 to 15 words.
   - Start with active verbs (e.g. Manage, Reconcile, Prepare, Ingest, Review, Configure, Deliver, Process).
   - Use operational, direct language.
   - Avoid passive voice (e.g. NEVER write "will be managed by Sympl"; write "Manage ...").
   - Have NO trailing periods on bullet points.
8. Forbidden Buzzwords — NEVER use:
   - leverage
   - cutting-edge
   - game-changing
   - holistic ecosystem
   - unlock value
   - bespoke transformation journey
   - strategic synergies
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
        ]

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
            '  "executive_summary": "1-2 concise paragraphs framing the engagement objectives, operational continuity, and partnership value.",',
            '  "sections": [',
            '    {',
            '      "section_title": "Section Title as designated above",',
            '      "opening_text": "Brief 1-2 sentence framing text introducing the section scope.",',
            '      "subsections": [',
            '        {',
            '          "heading": "Clear operational heading (e.g. Vendor Management & Accounts Payable)",',
            '          "bullets": [',
            '            "Action verb starting bullet (6-15 words) describing specific deliverable",',
            '            "Action verb starting bullet (6-15 words) describing specific deliverable"',
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
