"""
Sympl Solutions Proposal RAG — Proposal Planner Package
"""

from .schema import (
    ClientInput,
    OrganizationInfo,
    EngagementContext,
    ScopeContainer,
    BookkeepingScope,
    PayrollScope,
    ReportingScope,
    ComplianceScope,
    TransformationScope,
    TrainingScope,
    TransitionScope,
    ApprovedCommercialInputs,
    Preferences,
    ProposalPlan,
    PlanSection,
    ExcludedSection,
    ConfidenceMetadata,
    RetrievalContext,
    ExemplarItem
)
from .engine import ProposalPlanner

__all__ = [
    "ClientInput",
    "OrganizationInfo",
    "EngagementContext",
    "ScopeContainer",
    "BookkeepingScope",
    "PayrollScope",
    "ReportingScope",
    "ComplianceScope",
    "TransformationScope",
    "TrainingScope",
    "TransitionScope",
    "ApprovedCommercialInputs",
    "Preferences",
    "ProposalPlan",
    "PlanSection",
    "ExcludedSection",
    "ConfidenceMetadata",
    "RetrievalContext",
    "ExemplarItem",
    "ProposalPlanner"
]
