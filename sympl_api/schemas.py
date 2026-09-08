"""
Sympl Solutions Proposal RAG — API Schemas

Pydantic data models for request validation and response formatting across
all Proposal RAG API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field("healthy", description="Overall service status")
    version: str = Field("1.0.0", description="API version")
    database: str = Field("connected", description="PostgreSQL database connectivity status")
    embedding: str = Field("available", description="Embedding model availability status")
    planner: str = Field("available", description="Proposal Planner engine status")
    writer: str = Field("available", description="Proposal Writer engine status")
    renderer: str = Field("available", description="Proposal Renderer engine status")
    llm_provider: str = Field("mock", description="Active LLM provider")
    worker: str = Field("ready", description="Background job worker status")


class AsyncGenerateResponse(BaseModel):
    """Asynchronous proposal generation initiation response schema."""
    job_id: str = Field(..., description="Unique asynchronous job identifier")
    status: str = Field("CREATED", description="Job initial status")
    request_id: str = Field(..., description="Request correlation tracking ID")
    message: str = Field("Proposal generation job queued successfully.", description="Status message")


class JobStatusResponse(BaseModel):
    """Asynchronous job progress and status response schema."""
    job_id: str = Field(..., description="Unique asynchronous job identifier")
    status: str = Field(..., description="Job status: CREATED, RUNNING, COMPLETED, FAILED")
    current_stage: str = Field(..., description="Active stage: QUEUED, PLANNER, WRITER, RENDERER, COMPLETED, FAILED")
    progress: float = Field(..., description="Estimated completion progress between 0.0 and 1.0")
    proposal_id: Optional[str] = Field(None, description="Allocated proposal identifier once created")
    error_message: Optional[str] = Field(None, description="Error reason if job failed")


class ExecutionMetadata(BaseModel):
    """Timing and operational metadata for proposal pipeline execution."""
    planner_time_ms: float = Field(..., description="Planner execution duration in milliseconds")
    writer_time_ms: float = Field(..., description="Writer execution duration in milliseconds")
    renderer_time_ms: float = Field(..., description="Renderer execution duration in milliseconds")
    total_time_ms: float = Field(..., description="Total pipeline execution duration in milliseconds")


class ProposalGenerateResponse(BaseModel):
    """Full end-to-end proposal generation response schema."""
    proposal_id: str = Field(..., description="Unique generated proposal identifier")
    request_id: str = Field(..., description="Request correlation tracking ID")
    status: str = Field(..., description="Overall completion status (e.g. COMPLETED)")
    plan: Dict[str, Any] = Field(..., description="Compiled proposal_plan.json structure")
    draft: Dict[str, Any] = Field(..., description="Validated proposal_draft.json structure")
    rendered_output: Dict[str, Any] = Field(..., description="Compiled rendered_proposal.json structure")
    pdf_url: Optional[str] = Field(None, description="Direct download URL for generated proposal.pdf")
    manifest: Optional[Dict[str, Any]] = Field(None, description="5-artifact package manifest")
    execution_metadata: ExecutionMetadata = Field(..., description="Pipeline execution metrics")



class ErrorResponse(BaseModel):
    """Uniform error response schema."""
    error: str = Field(..., description="Machine-readable error classification code")
    message: str = Field(..., description="Human-readable description of the error")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed diagnostic context")
    request_id: str = Field(..., description="Request correlation tracking ID")


class WebhookCallbackPayload(BaseModel):
    """Schema for automated webhook callback payload sent to external orchestrators (n8n)."""
    job_id: str = Field(..., description="Unique asynchronous job identifier")
    proposal_id: str = Field(..., description="Unique generated proposal identifier")
    status: str = Field("COMPLETED", description="Job completion status")
    pdf_url: str = Field(..., description="URL endpoint to download the generated proposal.pdf")
    manifest_url: str = Field(..., description="URL endpoint to retrieve the artifact manifest.json")
    error_message: Optional[str] = Field(None, description="Error message if generation failed")


class ClientNarrativeSchema(BaseModel):
    """Optional narrative context capturing client operational situation, challenges, and goals."""
    client_situation_summary: Optional[str] = Field(None, description="Operational posture and current situation")
    client_challenges_summary: Optional[str] = Field(None, description="Core challenges and pain points")
    organization_description: Optional[str] = Field(None, description="Organizational overview and mission")
    industry_context: Optional[str] = Field(None, description="Sector context and regulatory environment")
    employee_count: Optional[Any] = Field(None, description="Approximate employee / staff count")
    organization_size: Optional[str] = Field(None, description="Size category (compact, small, medium, large)")
    annual_budget_or_revenue_range: Optional[str] = Field(None, description="Budget or annual revenue range")
    current_accounting_system: Optional[str] = Field(None, description="Primary accounting software (e.g. Sage, QBO)")
    current_finance_process: Optional[str] = Field(None, description="Current invoicing, payables, and reporting workflow")
    current_finance_team_structure: Optional[str] = Field(None, description="Internal team composition and departing roles")
    current_finance_challenges: Optional[Any] = Field(None, description="Specific finance obstacles or backlog")
    reason_for_engagement: Optional[str] = Field(None, description="Primary catalyst for seeking outsourced services")
    desired_outcomes: Optional[Any] = Field(None, description="Target outcomes and success criteria")
    client_priorities: Optional[Any] = Field(None, description="Top operational priorities")


class BookkeepingContextSchema(BaseModel):
    """Specific operational context for bookkeeping service."""
    bookkeeping_volume: Optional[str] = None
    bookkeeping_frequency: Optional[str] = None
    ap_ar_requirements: Optional[str] = None
    reconciliation_requirements: Optional[str] = None
    cleanup_requirements: Optional[str] = None


class PayrollContextSchema(BaseModel):
    """Specific operational context for payroll service."""
    employee_count_for_payroll: Optional[Any] = None
    payroll_frequency: Optional[str] = None
    current_payroll_system: Optional[str] = None
    payroll_transition_requirements: Optional[str] = None


class ReportingContextSchema(BaseModel):
    """Specific operational context for reporting service."""
    reporting_requirements: Optional[str] = None
    board_reporting_requirements: Optional[str] = None
    budgeting_requirements: Optional[str] = None


class ComplianceContextSchema(BaseModel):
    """Specific operational context for compliance service."""
    compliance_requirements: Optional[str] = None
    regulatory_requirements: Optional[str] = None


class ServiceContextSchema(BaseModel):
    """Container for service-specific operational requirements."""
    bookkeeping: Optional[BookkeepingContextSchema] = None
    payroll: Optional[PayrollContextSchema] = None
    reporting: Optional[ReportingContextSchema] = None
    compliance: Optional[ComplianceContextSchema] = None


class ProposalIntakeRequest(BaseModel):
    """
    Intake schema for proposal generation.
    Maintains 100% backward compatibility with legacy minimal payloads
    while allowing rich client context and narrative story fields.
    """
    client_name: Optional[str] = Field(None, description="Client or organization name")
    organization: Optional[Dict[str, Any]] = Field(None, description="Organization details (name, type, sector)")
    engagement: Optional[Dict[str, Any]] = Field(None, description="Engagement context (type, complexity)")
    requested_scope: Optional[Dict[str, Any]] = Field(None, description="Client requested service scope")
    approved_scope: Dict[str, Any] = Field(..., description="Authoritative approved service scope")
    commercial_terms: Dict[str, Any] = Field(..., description="Pricing structure and commercial terms")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Optional presentation preferences")

    # High-value narrative fields (top-level or nested)
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
    current_finance_challenges: Optional[Any] = None
    reason_for_engagement: Optional[str] = None
    desired_outcomes: Optional[Any] = None
    client_priorities: Optional[Any] = None

    # Grouped structures (optional alternatives)
    client_background: Optional[ClientNarrativeSchema] = None
    finance_context: Optional[Dict[str, Any]] = None
    objectives: Optional[Dict[str, Any]] = None
    service_context: Optional[ServiceContextSchema] = None
    callback_url: Optional[str] = None


