"""
Sympl Solutions Proposal RAG — Archetype Precedence Priority Engine

Implements the deterministic archetype selection and priority routing across the 5 approved archetypes:
  1. ARCH_TRANSITION_INTERIM (Priority 1)
  2. ARCH_AUDIT_OVERSIGHT_TRANSFORMATION (Priority 2)
  3. ARCH_COMPREHENSIVE_TRANSFORMATION (Priority 3)
  4. ARCH_STANDARD_NONPROFIT (Priority 4)
  5. ARCH_COMPACT_BOOKKEEPING (Priority 5 - Base Default)

Enforces the non-negotiable architectural invariant:
  PROPOSAL ARCHETYPE IS DERIVED FROM APPROVED CURRENT SCOPE.
  ARCHETYPE NEVER ADDS SCOPE.
"""

from typing import Dict, Any, Tuple, List
from .schema import ClientInput, ScopeContainer


class ArchetypeSelector:
    """
    Evaluates client intake against approved scope to deterministically select the proposal archetype.
    """

    # Precedence weights (higher number = higher evaluation precedence)
    PRECEDENCE_ORDER = [
        "ARCH_TRANSITION_INTERIM",
        "ARCH_AUDIT_OVERSIGHT_TRANSFORMATION",
        "ARCH_COMPREHENSIVE_TRANSFORMATION",
        "ARCH_STANDARD_NONPROFIT",
        "ARCH_COMPACT_BOOKKEEPING"
    ]

    ARCHETYPE_DESCRIPTIONS = {
        "ARCH_TRANSITION_INTERIM": "Fixed-term / interim handover framing with chronological transition milestones.",
        "ARCH_AUDIT_OVERSIGHT_TRANSFORMATION": "Diagnostic framing around internal controls, reconciliation cleanup, and audit readiness.",
        "ARCH_COMPREHENSIVE_TRANSFORMATION": "Modular multi-workstream structure with formal Context & Objectives and system migration phases.",
        "ARCH_STANDARD_NONPROFIT": "Moderate-detail operational structure adapted to nonprofit governance and funder reporting.",
        "ARCH_COMPACT_BOOKKEEPING": "Direct operational schedule with concise service blocks and minimal diagnostic narrative."
    }

    ARCHETYPE_HISTORICAL_EXEMPLARS = {
        "ARCH_TRANSITION_INTERIM": ["YPT_2026"],
        "ARCH_AUDIT_OVERSIGHT_TRANSFORMATION": ["PIRS_2025"],
        "ARCH_COMPREHENSIVE_TRANSFORMATION": ["TACT_2026", "GOODFOOT_2026"],
        "ARCH_STANDARD_NONPROFIT": ["RPFF_2025"],
        "ARCH_COMPACT_BOOKKEEPING": ["CAREOF_2025", "CAHOOTS_2026"]
    }

    @classmethod
    def evaluate(cls, client_input: ClientInput) -> Tuple[str, Dict[str, Any]]:
        """
        Evaluates the client input using the archetype precedence priority system.
        Returns (selected_archetype, precedence_audit_dict).
        """
        app_scope = client_input.approved_scope
        eng = client_input.engagement
        org = client_input.organization
        diagnostic_focus = [d.lower() for d in eng.diagnostic_focus]

        scores: Dict[str, float] = {}
        criteria_met: Dict[str, List[str]] = {}

        # --------------------------------------------------------------
        # Priority 1: ARCH_TRANSITION_INTERIM
        # --------------------------------------------------------------
        t_crit = []
        if eng.engagement_type == "interim":
            t_crit.append("engagement_type is interim")
        if eng.fixed_term_duration:
            t_crit.append(f"fixed_term_duration specified ({eng.fixed_term_duration})")
        if app_scope.transition and (app_scope.transition.handover_continuity or app_scope.transition.legacy_shadowing):
            t_crit.append("approved transition scope includes handover continuity or legacy shadowing")

        if "engagement_type is interim" in t_crit or (len(t_crit) >= 2 and app_scope.transition):
            scores["ARCH_TRANSITION_INTERIM"] = 100.0 + (len(t_crit) * 10.0)
        criteria_met["ARCH_TRANSITION_INTERIM"] = t_crit

        # --------------------------------------------------------------
        # Priority 2: ARCH_AUDIT_OVERSIGHT_TRANSFORMATION
        # --------------------------------------------------------------
        a_crit = []
        has_audit_diag = any(f in diagnostic_focus for f in ["internal_controls", "audit_readiness", "controls"])
        has_audit_comp = app_scope.compliance and app_scope.compliance.audit_support
        has_catchup = (app_scope.bookkeeping and app_scope.bookkeeping.catchup_cleanup)

        if has_audit_diag:
            a_crit.append("diagnostic_focus includes internal_controls or audit_readiness")
        if has_audit_comp:
            a_crit.append("approved compliance scope includes audit_support")
        if has_catchup:
            a_crit.append("approved bookkeeping scope includes catchup_cleanup")

        if (has_audit_diag and has_audit_comp) or (has_audit_diag and has_catchup):
            scores["ARCH_AUDIT_OVERSIGHT_TRANSFORMATION"] = 85.0 + (len(a_crit) * 5.0)
        criteria_met["ARCH_AUDIT_OVERSIGHT_TRANSFORMATION"] = a_crit

        # --------------------------------------------------------------
        # Priority 3: ARCH_COMPREHENSIVE_TRANSFORMATION
        # --------------------------------------------------------------
        c_crit = []
        has_transformation = (
            app_scope.digital_transformation is not None and
            (bool(app_scope.digital_transformation.system_migrations) or app_scope.digital_transformation.workflow_redesign)
        )
        has_training = app_scope.training is not None and app_scope.training.sop_documentation
        multi_workstream = (
            int(has_transformation) +
            int(app_scope.bookkeeping is not None) +
            int(app_scope.payroll is not None) +
            int(has_training)
        ) >= 3

        if has_transformation:
            c_crit.append("approved digital_transformation scope includes migrations or workflow redesign")
        if has_training:
            c_crit.append("approved training scope includes SOP documentation")
        if eng.complexity == "comprehensive":
            c_crit.append("engagement complexity is comprehensive")
        if multi_workstream:
            c_crit.append("engagement encompasses 3+ distinct active workstreams")

        if has_transformation or (multi_workstream and eng.complexity == "comprehensive"):
            scores["ARCH_COMPREHENSIVE_TRANSFORMATION"] = 70.0 + (len(c_crit) * 5.0)
        criteria_met["ARCH_COMPREHENSIVE_TRANSFORMATION"] = c_crit

        # --------------------------------------------------------------
        # Priority 4: ARCH_STANDARD_NONPROFIT
        # --------------------------------------------------------------
        s_crit = []
        is_nonprofit = org.organization_type in ("nonprofit", "charity")
        has_funder_tracking = app_scope.financial_reporting and app_scope.financial_reporting.funder_tracking
        has_board_pkg = app_scope.financial_reporting and app_scope.financial_reporting.board_package
        has_recurring_ops = app_scope.bookkeeping is not None

        if is_nonprofit:
            s_crit.append(f"organization_type is {org.organization_type}")
        if has_funder_tracking:
            s_crit.append("approved financial_reporting scope includes funder/grant tracking")
        if has_board_pkg:
            s_crit.append("approved financial_reporting scope includes board_package")
        if has_recurring_ops:
            s_crit.append("approved bookkeeping scope is active")

        if is_nonprofit and (has_funder_tracking or has_board_pkg or (has_recurring_ops and eng.complexity == "standard")):
            scores["ARCH_STANDARD_NONPROFIT"] = 55.0 + (len(s_crit) * 3.0)
        criteria_met["ARCH_STANDARD_NONPROFIT"] = s_crit

        # --------------------------------------------------------------
        # Priority 5: ARCH_COMPACT_BOOKKEEPING (Base Default)
        # --------------------------------------------------------------
        b_crit = []
        if app_scope.bookkeeping is not None:
            b_crit.append("approved bookkeeping scope is active")
        if eng.complexity == "compact" or (not has_transformation and not has_audit_diag and not has_funder_tracking):
            b_crit.append("scope is operational bookkeeping without heavy diagnostic or transformation overlays")
        scores["ARCH_COMPACT_BOOKKEEPING"] = 40.0 + (len(b_crit) * 2.0)
        criteria_met["ARCH_COMPACT_BOOKKEEPING"] = b_crit

        # --------------------------------------------------------------
        # Apply Precedence Selection
        # --------------------------------------------------------------
        selected_archetype = "ARCH_COMPACT_BOOKKEEPING"
        selection_rationale = "Defaulted to base operational schedule."
        highest_score = 0.0

        for arch in cls.PRECEDENCE_ORDER:
            if arch in scores and scores[arch] > highest_score:
                selected_archetype = arch
                highest_score = scores[arch]
                selection_rationale = f"Selected by precedence priority ({arch}) satisfying: {', '.join(criteria_met[arch])}"

        precedence_audit = {
            "precedence_hierarchy": cls.PRECEDENCE_ORDER,
            "selected_archetype": selected_archetype,
            "selection_score": highest_score,
            "selection_rationale": selection_rationale,
            "candidate_scores": scores,
            "criteria_evaluated": criteria_met,
            "exemplar_references": cls.ARCHETYPE_HISTORICAL_EXEMPLARS[selected_archetype]
        }

        return selected_archetype, precedence_audit
