"""
Sympl Solutions Proposal RAG — Proposal Planner Engine

Main entry point for generating structural proposal plans from client intake.
Coordinates:
  1. Archetype selection via precedence priority system.
  2. Dynamic Why Us inclusion and reference block assembly.
  3. Section sequencing and scope firewall audit (requested vs approved scope).
  4. pgvector exemplar retrieval (1-3 exemplars per section, cleaned_text strictly in exemplars).
  5. Commercial schedule and pricing placeholder handling.
  6. Confidence metadata calculation and validation flags.
"""

import time
import uuid
from typing import Optional, Dict, Any, List
import psycopg

from .schema import (
    ClientInput,
    ProposalPlan,
    ConfidenceMetadata,
    PlanSection
)
from .archetype import ArchetypeSelector
from .section_selector import SectionSelector
from .why_us import WhyUsSelector
from .pricing import PricingHandler
from .retrieval import ExemplarRetriever, DATABASE_URL


class ProposalPlanner:
    """
    Coordinates the end-to-end planning process to produce a validated ProposalPlan.
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or DATABASE_URL
        if not self.db_url:
            raise RuntimeError("DATABASE_URL is required to run the ProposalPlanner.")

    def plan(self, client_input: ClientInput) -> ProposalPlan:
        """
        Executes the planning pipeline and returns a structured ProposalPlan.
        """
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        created_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        # --------------------------------------------------------------
        # 1. Archetype Selection (Precedence Priority System)
        # --------------------------------------------------------------
        selected_archetype, precedence_audit = ArchetypeSelector.evaluate(client_input)

        # --------------------------------------------------------------
        # 2. Why Us Dynamic Evaluation & Block Assembly
        # --------------------------------------------------------------
        include_why_us, why_us_rationale = WhyUsSelector.evaluate_inclusion(
            client_input, selected_archetype
        )
        why_us_blocks = WhyUsSelector.assemble_why_us(client_input) if include_why_us else []

        # --------------------------------------------------------------
        # 3. Section Selection & Scope Firewall Audit
        # --------------------------------------------------------------
        sections, excluded_sections, unapproved_requested = SectionSelector.select_sections(
            client_input, selected_archetype, include_why_us
        )

        # --------------------------------------------------------------
        # 4. Commercial Schedule & Pricing Placeholders
        # --------------------------------------------------------------
        commercial_summary = PricingHandler.compile_commercial_schedule(client_input)

        # --------------------------------------------------------------
        # 5. Attach Reference Blocks, Exemplars, & Style Rules to Sections
        # --------------------------------------------------------------
        ref_block_manifest: List[str] = []
        retrieval_scores: List[float] = []

        with psycopg.connect(self.db_url) as conn:
            for sec in sections:
                # Apply style rules for this section family
                if sec.service_family in ExemplarRetriever.STYLE_RULES_BY_FAMILY:
                    sec.style_rules_applied = ExemplarRetriever.STYLE_RULES_BY_FAMILY[sec.service_family]

                # If Why Us section, attach reference blocks
                if sec.section_type == "why_us":
                    sec.reference_blocks = why_us_blocks
                    for b in why_us_blocks:
                        ref_block_manifest.append(b["block_key"])

                # If Terms & Exclusions section, attach conditional disclaimers
                elif sec.section_type == "exclusions":
                    sec.reference_blocks = commercial_summary.get("disclaimers", [])
                    for d in sec.reference_blocks:
                        ref_block_manifest.append(d["block_key"])

                # For retrieval-driven service sections, attach 1-3 exemplars
                else:
                    retrieval_ctx = ExemplarRetriever.attach_exemplars_to_section(
                        conn=conn,
                        service_family=sec.service_family or "",
                        section_type=sec.section_type,
                        target_archetype=selected_archetype,
                        client_input=client_input
                    )
                    if retrieval_ctx:
                        sec.retrieval_context = retrieval_ctx
                        if retrieval_ctx.exemplars:
                            retrieval_scores.append(retrieval_ctx.exemplars[0].similarity_score)

        # --------------------------------------------------------------
        # 6. Calculate Confidence Metadata & Quality Flags
        # --------------------------------------------------------------
        flags: List[str] = []

        # Archetype confidence
        arch_score = precedence_audit.get("selection_score", 50.0)
        arch_conf = min(1.0, max(0.6, arch_score / 120.0))

        # Scope alignment score (penalized if client requested unapproved services)
        if unapproved_requested:
            scope_alignment = max(0.5, 1.0 - (len(unapproved_requested) * 0.15))
            flags.append("UNAPPROVED_REQUESTED_ITEMS_PRESENT")
        else:
            scope_alignment = 1.0

        # Commercial placeholder flag
        if commercial_summary.get("has_placeholders", False):
            flags.append("PRICING_PLACEHOLDERS_ACTIVE")

        # Exclusions active
        if commercial_summary.get("disclaimers"):
            flags.append("CONDITIONAL_DISCLAIMERS_ACTIVE")

        # Why Us rationale flag
        flags.append(f"WHY_US_{'INCLUDED' if include_why_us else 'OMITTED'}: {why_us_rationale}")

        # Average retrieval confidence
        avg_retrieval_conf = float(sum(retrieval_scores) / len(retrieval_scores)) if retrieval_scores else 0.85

        # Overall weighted confidence
        overall_conf = round(
            0.40 * arch_conf +
            0.35 * scope_alignment +
            0.25 * avg_retrieval_conf,
            4
        )

        confidence_meta = ConfidenceMetadata(
            overall_confidence=overall_conf,
            archetype_confidence=round(arch_conf, 4),
            archetype_rationale=precedence_audit.get("selection_rationale", ""),
            scope_alignment_score=round(scope_alignment, 4),
            retrieval_confidence=round(avg_retrieval_conf, 4),
            flags=flags
        )

        # Collect all active style rules
        all_style_rules = []
        for sec in sections:
            for r in sec.style_rules_applied:
                if r not in all_style_rules:
                    all_style_rules.append(r)

        client_context = {
            "name": client_input.organization.name,
            "organization_type": client_input.organization.organization_type,
            "sector": client_input.organization.sector,
            "description": client_input.organization.description,
            "current_systems": client_input.organization.current_systems,
            "target_systems": client_input.organization.target_systems,
            "evaluation_systems": client_input.organization.evaluation_systems,
            "engagement_type": client_input.engagement.engagement_type,
            "complexity": client_input.engagement.complexity,
            "fixed_term_duration": client_input.engagement.fixed_term_duration,
            "diagnostic_focus": client_input.engagement.diagnostic_focus
        }

        # Merge narrative and contextual intelligence if provided
        if getattr(client_input, "narrative_context", None):
            from dataclasses import asdict
            narrative_dict = asdict(client_input.narrative_context)
            for k, v in narrative_dict.items():
                if v is not None and (k not in client_context or not client_context[k]):
                    client_context[k] = v

        if getattr(client_input, "enriched_context", None):
            for k, v in client_input.enriched_context.items():
                if v is not None and (k not in client_context or not client_context[k]):
                    client_context[k] = v

        if getattr(client_input, "service_context", None):
            client_context["service_context"] = client_input.service_context

        client_context["context_quality"] = getattr(client_input, "context_quality", "LOW")
        client_context["context_score"] = getattr(client_input, "context_score", 0)

        approved_scope_dict = {}
        for fam in client_input.approved_scope.active_families():
            item = getattr(client_input.approved_scope, fam, None)
            if item is not None:
                from dataclasses import asdict
                approved_scope_dict[fam] = asdict(item)

        return ProposalPlan(
            plan_id=plan_id,
            client_id=client_input.client_id,
            client_name=client_input.organization.name,
            selected_archetype=selected_archetype,
            precedence_applied=precedence_audit,
            confidence_metadata=confidence_meta,
            sections=sections,
            excluded_sections=excluded_sections,
            unapproved_requested_scope=unapproved_requested,
            commercial_summary=commercial_summary,
            reference_block_manifest=sorted(list(set(ref_block_manifest))),
            created_at=created_at,
            client_context=client_context,
            approved_scope=approved_scope_dict,
            archetype=selected_archetype,
            pricing=commercial_summary,
            style_rules=all_style_rules,
            reference_blocks=sorted(list(set(ref_block_manifest))),
            metadata={
                "plan_id": plan_id,
                "created_at": created_at,
                "overall_confidence": overall_conf,
                "flags": flags,
                "context_quality": getattr(client_input, "context_quality", "LOW"),
                "context_score": getattr(client_input, "context_score", 0)
            }
        )
