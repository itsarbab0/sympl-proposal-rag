"""
Sympl Solutions Proposal RAG — Proposal Planner Schemas

Defines type-safe data structures for client intake, requested vs approved scope separation,
commercial terms, section sequencing, retrieval exemplar attachment, confidence metadata,
and the final proposal plan.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Literal, Union
import json
import time
import uuid


# ----------------------------------------------------------------------
# 1. Client Intake Components
# ----------------------------------------------------------------------
@dataclass
class OrganizationInfo:
    name: str
    organization_type: str = "nonprofit"  # nonprofit, charity, for_profit, social_enterprise, unspecified
    sector: str = "community_services"   # community_services, social_services, arts_culture, health, literacy, other
    description: Optional[str] = None
    current_systems: List[str] = field(default_factory=list)
    target_systems: List[str] = field(default_factory=list)
    evaluation_systems: List[str] = field(default_factory=list)
    service_category: Optional[str] = None


@dataclass
class BookkeepingScope:
    cadence: str = "monthly"             # weekly, biweekly, monthly, quarterly
    ap_ar: bool = True
    reconciliations: bool = True
    expense_management: bool = True
    catchup_cleanup: bool = False
    bookkeeping_volume: Optional[str] = None
    bookkeeping_frequency: Optional[str] = None
    ap_ar_requirements: Optional[str] = None
    reconciliation_requirements: Optional[str] = None
    cleanup_requirements: Optional[str] = None


@dataclass
class PayrollScope:
    cadence: str = "semi_monthly"        # weekly, biweekly, semi_monthly, monthly
    headcount_employees: int = 0
    headcount_contractors: int = 0
    migration_parallel_run: bool = False
    sympl_processes_payroll: bool = True
    manager_input_responsibility: bool = True
    hr_functions_excluded: bool = True
    employee_count_for_payroll: Optional[Any] = None
    payroll_frequency: Optional[str] = None
    current_payroll_system: Optional[str] = None
    payroll_transition_requirements: Optional[str] = None


@dataclass
class ReportingScope:
    cadence: str = "monthly"             # monthly, quarterly, annual
    funder_tracking: bool = False
    class_department_tracking: bool = False
    board_package: bool = False
    budget_vs_actual: bool = False
    reporting_requirements: Optional[str] = None
    board_reporting_requirements: Optional[str] = None
    budgeting_requirements: Optional[str] = None


@dataclass
class ComplianceScope:
    gst_hst_filing: bool = True
    t3010_support: bool = False
    audit_support: bool = False
    audit_response_sla: Optional[str] = None  # e.g., "1-2 business days" if explicitly approved
    compliance_requirements: Optional[str] = None
    regulatory_requirements: Optional[str] = None


@dataclass
class TransformationScope:
    system_migrations: List[str] = field(default_factory=list)
    workflow_redesign: bool = False
    integration_milestones: List[str] = field(default_factory=list)
    implementation_phases: List[str] = field(default_factory=list)


@dataclass
class TrainingScope:
    target_roles: List[str] = field(default_factory=list)
    format: str = "remote"               # remote, onsite, hybrid
    sop_documentation: bool = False
    post_golive_support_weeks: int = 0


@dataclass
class TransitionScope:
    onboarding_duration_weeks: int = 4
    historical_access: bool = True
    handover_continuity: bool = True
    legacy_shadowing: bool = False
    legacy_systems: List[str] = field(default_factory=list)



@dataclass
class GenericServiceScope:
    service_category: str                    # e.g., "Website Development", "Data Analytics"
    service_name: str                        # e.g., "Website Redesign & CMS Migration"
    description: Optional[str] = None
    deliverables: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    timeline: Optional[str] = None
    constraints: Optional[str] = None
    target_systems: List[str] = field(default_factory=list)


@dataclass
class ScopeContainer:
    bookkeeping: Optional[BookkeepingScope] = None
    payroll: Optional[PayrollScope] = None
    financial_reporting: Optional[ReportingScope] = None
    compliance: Optional[ComplianceScope] = None
    digital_transformation: Optional[TransformationScope] = None
    training: Optional[TrainingScope] = None
    transition: Optional[TransitionScope] = None
    generic_services: List[GenericServiceScope] = field(default_factory=list)

    def active_families(self) -> List[str]:
        active = []
        if self.bookkeeping is not None:
            active.append("bookkeeping")
        if self.payroll is not None:
            active.append("payroll")
        if self.financial_reporting is not None:
            active.append("financial_reporting")
        if self.compliance is not None:
            active.append("compliance")
        if self.digital_transformation is not None:
            active.append("digital_transformation")
        if self.training is not None:
            active.append("training")
        if self.transition is not None:
            active.append("transition")
        for gs in self.generic_services:
            cat_key = gs.service_category.lower().replace(" ", "_").replace("/", "_")
            if cat_key not in active:
                active.append(cat_key)
        return active


@dataclass
class ApprovedCommercialInputs:
    pricing_model: str = "placeholder"   # fixed_retainer, hourly, phased_milestone, placeholder
    currency: str = "CAD"
    monthly_retainer: Optional[float] = None
    setup_fee: Optional[float] = None
    hourly_rate: Optional[float] = None
    billing_schedule: Optional[str] = None
    approved_categories: List[str] = field(default_factory=list)  # e.g. ["monthly_retainer", "setup_fee"]
    include_backlog_exclusion: bool = False
    software_fees_excluded: bool = False


@dataclass
class Preferences:
    include_why_us: Optional[bool] = None  # None = dynamic planner decision
    is_competitive_pitch: bool = False
    is_trusted_continuity: bool = False
    identity_credential_preference: Optional[str] = None  # community_social, arts_leadership, none, auto


@dataclass
class EngagementContext:
    engagement_type: str = "recurring"   # recurring, interim, transformation, project, catchup
    complexity: str = "standard"         # standard, comprehensive, compact
    fixed_term_duration: Optional[str] = None
    diagnostic_focus: List[str] = field(default_factory=list)  # internal_controls, audit_readiness, workflow_efficiency


@dataclass
class ClientNarrativeContext:
    client_situation_summary: Optional[str] = None
    client_challenges_summary: Optional[str] = None
    organization_description: Optional[str] = None
    industry_context: Optional[str] = None
    employee_count: Optional[Any] = None
    organization_size: Optional[str] = None
    annual_budget_or_revenue_range: Optional[str] = None
    current_accounting_system: Optional[str] = None
    current_finance_process: Optional[str] = None
    current_finance_team_structure: Optional[str] = None
    current_finance_challenges: Optional[Union[str, List[str]]] = None
    reason_for_engagement: Optional[str] = None
    desired_outcomes: Optional[Union[str, List[str]]] = None
    client_priorities: Optional[Union[str, List[str]]] = None


@dataclass
class ClientInput:
    client_id: str
    organization: OrganizationInfo
    engagement: EngagementContext
    requested_scope: ScopeContainer
    approved_scope: ScopeContainer
    commercial_terms: ApprovedCommercialInputs
    preferences: Preferences = field(default_factory=Preferences)
    narrative_context: Optional[ClientNarrativeContext] = None
    service_context: Optional[Dict[str, Any]] = None
    context_quality: str = "LOW"
    context_score: int = 0
    enriched_context: Dict[str, Any] = field(default_factory=dict)
    service_category: Optional[str] = None



# ----------------------------------------------------------------------
# 2. Retrieval & Plan Output Structures
# ----------------------------------------------------------------------
@dataclass
class ExemplarItem:
    role: str                            # primary, secondary, optional_archetype
    chunk_key: str
    proposal_code: str
    section_type: str
    similarity_score: float
    cleaned_text: str                    # Strictly placed only here
    service_category: Optional[str] = None


@dataclass
class RetrievalContext:
    query_text: str
    target_service_family: str
    candidate_pool_size: int
    exemplars: List[ExemplarItem] = field(default_factory=list)


@dataclass
class PlanSection:
    section_id: str
    section_title: str
    section_type: str
    service_family: Optional[str]
    section_order: int
    structural_role: str                 # narrative_context, operational_schedule, modular_service, credentials, commercial_schedule, terms_exclusions
    reference_blocks: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_context: Optional[RetrievalContext] = None
    style_rules_applied: List[str] = field(default_factory=list)
    section_instructions: List[str] = field(default_factory=list)


@dataclass
class ExcludedSection:
    section_type: str
    reason: str                          # NOT_IN_APPROVED_SCOPE, NOT_APPLICABLE_TO_ENGAGEMENT, SUPERSEDED_BY_ARCHETYPE, OUT_OF_SCOPE_REQUESTED
    details: str


@dataclass
class ConfidenceMetadata:
    overall_confidence: float
    archetype_confidence: float
    archetype_rationale: str
    scope_alignment_score: float
    retrieval_confidence: float
    flags: List[str] = field(default_factory=list)


@dataclass
class ProposalPlan:
    plan_id: str
    client_id: str
    client_name: str
    selected_archetype: str
    precedence_applied: Dict[str, Any]
    confidence_metadata: ConfidenceMetadata
    sections: List[PlanSection]
    excluded_sections: List[ExcludedSection]
    commercial_summary: Dict[str, Any]
    reference_block_manifest: List[str]
    created_at: str
    client_context: Dict[str, Any] = field(default_factory=dict)
    approved_scope: Dict[str, Any] = field(default_factory=dict)
    archetype: str = ""
    pricing: Dict[str, Any] = field(default_factory=dict)
    style_rules: List[str] = field(default_factory=list)
    reference_blocks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    unapproved_requested_scope: List[Dict[str, Any]] = field(default_factory=list)
    service_category: Optional[str] = None
    generic_services: Optional[List[Dict[str, Any]]] = None

    def to_dict(self, for_writer: bool = False) -> Dict[str, Any]:
        d = asdict(self)
        if for_writer:
            d.pop("unapproved_requested_scope", None)
            d.pop("requested_scope", None)
        return d

    def to_json(self, indent: int = 2, for_writer: bool = False) -> str:
        return json.dumps(self.to_dict(for_writer=for_writer), indent=indent)

