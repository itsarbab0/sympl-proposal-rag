"""
Sympl Solutions Proposal RAG — Section Sequencing & Scope Firewall

Resolves ordered document sections based on selected archetype and approved scope.
Enforces:
  1. Scope Firewall: Archetype never adds unapproved scope.
  2. Separation of requested vs approved scope: detects discrepancies and logs excluded_sections.
  3. Ordered section sequencing tailored to the selected archetype.
"""

from typing import List, Dict, Any, Tuple
from .schema import ClientInput, PlanSection, ExcludedSection, ScopeContainer


class SectionSelector:
    """
    Selects, orders, and validates proposal sections, generating excluded section audits.
    """

    @classmethod
    def select_sections(
        cls,
        client_input: ClientInput,
        selected_archetype: str,
        include_why_us: bool
    ) -> Tuple[List[PlanSection], List[ExcludedSection], List[Dict[str, Any]]]:
        """
        Determines the ordered sections and logs excluded sections with explicit reasons.
        Returns (sections, excluded_sections, unapproved_requested_scope).
        """
        app_scope = client_input.approved_scope
        req_scope = client_input.requested_scope
        org = client_input.organization
        eng = client_input.engagement

        sections: List[PlanSection] = []
        excluded: List[ExcludedSection] = []
        unapproved_requested: List[Dict[str, Any]] = []

        # --------------------------------------------------------------
        # 1. Audit Scope Firewall: Compare Requested vs Approved Scope
        # --------------------------------------------------------------
        all_possible_families = [
            ("digital_transformation", "Digital Transformation & Systems Migration"),
            ("bookkeeping", "Bookkeeping & General Ledger Operations"),
            ("payroll", "Payroll Accounting & Processing"),
            ("financial_reporting", "Financial Reporting & Funder Tracking"),
            ("compliance", "Statutory Compliance & Audit Support"),
            ("training", "Staff Training & SOP Documentation"),
            ("transition", "Transition, Onboarding & Continuity")
        ]

        for fam_key, fam_name in all_possible_families:
            req_item = getattr(req_scope, fam_key, None)
            app_item = getattr(app_scope, fam_key, None)

            if req_item is not None and app_item is None:
                # Requested by client/RFP, but NOT approved by Sympl leadership
                reason = "SCOPE_NOT_APPROVED_BY_LEADERSHIP"
                details = f"Client requested {fam_name} in intake, but this service was not approved for inclusion in this proposal."
                excluded.append(ExcludedSection(section_type=fam_key, reason=reason, details=details))
                unapproved_requested.append({
                    "service_family": fam_key,
                    "service_name": fam_name,
                    "reason": reason,
                    "requested_details": str(req_item)
                })
            elif req_item is None and app_item is None:
                # Neither requested nor approved
                details = f"{fam_name} is outside the approved scope for this engagement."
                excluded.append(ExcludedSection(section_type=fam_key, reason="NOT_IN_APPROVED_SCOPE", details=details))

        # --------------------------------------------------------------
        # 2. Sequence Sections by Archetype
        # --------------------------------------------------------------
        order = 1

        if selected_archetype == "ARCH_COMPACT_BOOKKEEPING":
            # Direct operational schedule
            sections.append(PlanSection(
                section_id="sec_header",
                section_title="Schedule of Bookkeeping Services",
                section_type="operational_schedule",
                service_family="bookkeeping",
                section_order=order,
                structural_role="operational_schedule",
                section_instructions=[
                    "Present operational bookkeeping tasks organized directly by cadence (Weekly/Biweekly/Monthly).",
                    "Maintain high conciseness with direct bullet points.",
                    "Exclude diagnostic narrative and organizational background."
                ]
            ))
            order += 1

            if app_scope.payroll is not None:
                sections.append(PlanSection(
                    section_id="sec_payroll",
                    section_title="Payroll Administration",
                    section_type="payroll",
                    service_family="payroll",
                    section_order=order,
                    structural_role="modular_service",
                    section_instructions=[
                        "Detail payroll processing cadence, employee/contractor administration, and tax filings.",
                        "Enforce manager data submission boundary."
                    ]
                ))
                order += 1

        elif selected_archetype == "ARCH_STANDARD_NONPROFIT":
            # Context & Objectives -> Modular Services
            sections.append(PlanSection(
                section_id="sec_context",
                section_title="Context & Objectives",
                section_type="context_objectives",
                service_family="context",
                section_order=order,
                structural_role="narrative_context",
                section_instructions=[
                    f"Frame {org.name}'s mission and operational context concisely.",
                    "Outline key engagement objectives tailored to nonprofit financial health."
                ]
            ))
            order += 1

            if app_scope.bookkeeping is not None:
                sections.append(PlanSection(
                    section_id="sec_bookkeeping",
                    section_title="Accounting & Bookkeeping Services",
                    section_type="bookkeeping",
                    service_family="bookkeeping",
                    section_order=order,
                    structural_role="modular_service",
                    section_instructions=[
                        "Detail full-cycle bookkeeping, AP/AR processing, and account reconciliations.",
                        "Align with nonprofit fund accounting best practices."
                    ]
                ))
                order += 1

            if app_scope.payroll is not None:
                sections.append(PlanSection(
                    section_id="sec_payroll",
                    section_title="Payroll Accounting & Administration",
                    section_type="payroll",
                    service_family="payroll",
                    section_order=order,
                    structural_role="modular_service",
                    section_instructions=[
                        "Specify payroll processing frequency, ROEs, T4 filings, and remittance verification."
                    ]
                ))
                order += 1

            if app_scope.financial_reporting is not None:
                sections.append(PlanSection(
                    section_id="sec_reporting",
                    section_title="Financial Reporting & Governance Support",
                    section_type="financial_reporting",
                    service_family="financial_reporting",
                    section_order=order,
                    structural_role="modular_service",
                    section_instructions=[
                        "Describe monthly/quarterly financial packages, budget vs actual comparisons, and funder/grant reporting."
                    ]
                ))
                order += 1

            if app_scope.compliance is not None:
                sections.append(PlanSection(
                    section_id="sec_compliance",
                    section_title="Statutory Compliance & Filings",
                    section_type="compliance",
                    service_family="compliance",
                    section_order=order,
                    structural_role="modular_service",
                    section_instructions=[
                        "Detail GST/HST public service body rebate/filing and annual charity return (T3010) support."
                    ]
                ))
                order += 1

        elif selected_archetype == "ARCH_TRANSITION_INTERIM":
            # Summary of Engagement -> Transition -> Recurring Operations
            sections.append(PlanSection(
                section_id="sec_summary",
                section_title="Summary of Engagement",
                section_type="context_objectives",
                service_family="context",
                section_order=order,
                structural_role="narrative_context",
                section_instructions=[
                    f"Frame the interim engagement duration ({eng.fixed_term_duration or 'fixed term'}) and organizational continuity priorities.",
                    "Highlight stability, legacy system preservation, and knowledge handover."
                ]
            ))
            order += 1

            if app_scope.transition is not None:
                sections.append(PlanSection(
                    section_id="sec_transition",
                    section_title="Transition, Onboarding & Handover Plan",
                    section_type="transition",
                    service_family="transition",
                    section_order=order,
                    structural_role="modular_service",
                    section_instructions=[
                        f"Outline chronological onboarding timeline ({app_scope.transition.onboarding_duration_weeks} weeks).",
                        "Detail historical data access, shadow period, and smooth handover milestones."
                    ]
                ))
                order += 1

            if app_scope.bookkeeping is not None:
                sections.append(PlanSection(
                    section_id="sec_recurring",
                    section_title="Ongoing Operational Accounting",
                    section_type="bookkeeping",
                    service_family="bookkeeping",
                    section_order=order,
                    structural_role="modular_service",
                    section_instructions=[
                        "Maintain operational continuity across accounts payable, reconciliations, and routine ledger maintenance."
                    ]
                ))
                order += 1

            if app_scope.payroll is not None:
                sections.append(PlanSection(
                    section_id="sec_payroll",
                    section_title="Payroll Management",
                    section_type="payroll",
                    service_family="payroll",
                    section_order=order,
                    structural_role="modular_service",
                    section_instructions=[
                        "Ensure uninterrupted payroll cycles and source deduction remittances during interim period."
                    ]
                ))
                order += 1

        elif selected_archetype == "ARCH_COMPREHENSIVE_TRANSFORMATION":
            # Formal Context & Objectives -> Part A -> Part B -> Part C
            sections.append(PlanSection(
                section_id="sec_context",
                section_title="Context & Objectives",
                section_type="context_objectives",
                service_family="context",
                section_order=order,
                structural_role="narrative_context",
                section_instructions=[
                    "Provide formal diagnostic overview of current organizational growth and financial workflow challenges.",
                    "Define transformation and capacity-building objectives."
                ]
            ))
            order += 1

            if app_scope.digital_transformation is not None:
                sections.append(PlanSection(
                    section_id="sec_transformation",
                    section_title="Part A: Digital Financial Systems & Workflow Transformation",
                    section_type="digital_transformation",
                    service_family="digital_transformation",
                    section_order=order,
                    structural_role="modular_service",
                    section_instructions=[
                        "Detail target software migrations (e.g. QBO, Wagepoint, Dext) and workflow automation.",
                        "Specify implementation phases, cutover dates, and parallel testing."
                    ]
                ))
                order += 1

            if app_scope.bookkeeping is not None or app_scope.payroll is not None:
                sections.append(PlanSection(
                    section_id="sec_accounting_ops",
                    section_title="Part B: Ongoing Accounting & Bookkeeping Operations",
                    section_type="bookkeeping",
                    service_family="bookkeeping",
                    section_order=order,
                    structural_role="modular_service",
                    section_instructions=[
                        "Outline steady-state day-to-day accounting, payroll cycles, and financial management following system migration."
                    ]
                ))
                order += 1

            if app_scope.training is not None:
                sections.append(PlanSection(
                    section_id="sec_training",
                    section_title="Part C: Training, Process Documentation & Change Management",
                    section_type="training",
                    service_family="training",
                    section_order=order,
                    structural_role="modular_service",
                    section_instructions=[
                        "Detail staff training sessions, standard operating procedure (SOP) manuals, and post-go-live support duration."
                    ]
                ))
                order += 1

        elif selected_archetype == "ARCH_AUDIT_OVERSIGHT_TRANSFORMATION":
            # Diagnostic Context -> Diagnostic Reconciliations -> Oversight
            sections.append(PlanSection(
                section_id="sec_context_diag",
                section_title="Context & Financial Diagnostic",
                section_type="context_objectives",
                service_family="context",
                section_order=order,
                structural_role="narrative_context",
                section_instructions=[
                    "Analyze internal controls, audit readiness gaps, and historical reconciliation backlogs.",
                    "Establish clear responsibility matrix between internal leadership and Sympl."
                ]
            ))
            order += 1

            sections.append(PlanSection(
                section_id="sec_audit_reconciliations",
                section_title="Diagnostic Reconciliation & Cleanup Tasks",
                section_type="financial_management",
                service_family="financial_management",
                section_order=order,
                structural_role="modular_service",
                section_instructions=[
                    "Structure tasks into granular Objective, Scope, and Timeline blocks.",
                    "Focus on balance sheet reconciliations, audit trail restoration, and transaction verification."
                ]
            ))
            order += 1

            if app_scope.financial_reporting is not None or (app_scope.compliance and app_scope.compliance.audit_support):
                sections.append(PlanSection(
                    section_id="sec_audit_readiness",
                    section_title="Audit Readiness & Oversight Support",
                    section_type="compliance",
                    service_family="compliance",
                    section_order=order,
                    structural_role="modular_service",
                    section_instructions=[
                        "Detail auditor package preparation, lead sheet generation, and direct auditor liaison."
                    ]
                ))
                order += 1

        # --------------------------------------------------------------
        # 3. Why Us Section (Optional by dynamic planner decision)
        # --------------------------------------------------------------
        if include_why_us:
            sections.append(PlanSection(
                section_id="sec_why_us",
                section_title="Why Sympl Solutions",
                section_type="why_us",
                service_family="why_us",
                section_order=order,
                structural_role="credentials",
                section_instructions=[
                    "Assemble canonical reference blocks in exact historical order.",
                    "Apply approved sector and organization identity credentials."
                ]
            ))
            order += 1
        else:
            excluded.append(ExcludedSection(
                section_type="why_us",
                reason="EXCLUDED_BY_PLANNER_DECISION",
                details="Why Us section omitted based on intake context (operational focus / direct client request / trusted continuity)."
            ))

        # --------------------------------------------------------------
        # 4. Commercial & Terms Sections (Always Present)
        # --------------------------------------------------------------
        sections.append(PlanSection(
            section_id="sec_pricing",
            section_title="Investment & Fee Schedule",
            section_type="pricing",
            service_family="pricing",
            section_order=order,
            structural_role="commercial_schedule",
            section_instructions=[
                "Present ONLY approved commercial fee categories or structured placeholders.",
                "Never invent fee amounts, categories, or payment structures."
            ]
        ))
        order += 1

        # Terms & Exclusions section (attached if backlog, software, or HR boundaries apply)
        comm = client_input.commercial_terms
        has_exclusions = comm.include_backlog_exclusion or comm.software_fees_excluded or (app_scope.payroll and app_scope.payroll.hr_functions_excluded)
        if has_exclusions:
            sections.append(PlanSection(
                section_id="sec_terms_exclusions",
                section_title="Engagement Terms & Exclusions",
                section_type="exclusions",
                service_family="exclusions",
                section_order=order,
                structural_role="terms_exclusions",
                section_instructions=[
                    "Include approved condition-triggered exclusion and boundary reference blocks."
                ]
            ))
            order += 1

        return sections, excluded, unapproved_requested
