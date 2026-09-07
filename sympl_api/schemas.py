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

