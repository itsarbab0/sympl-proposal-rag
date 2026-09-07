"""
Sympl Solutions Proposal RAG — API Routes

Defines REST endpoints for health checks, isolated stage runs (Plan, Write, Render),
and full end-to-end proposal generation.
"""

from fastapi import APIRouter, Depends, status, Request, HTTPException, Response
from typing import Dict, Any

from sympl_api.schemas import (
    HealthResponse,
    ProposalGenerateResponse,
    AsyncGenerateResponse,
    JobStatusResponse
)
from sympl_api.auth import verify_api_key
from sympl_api.services import service
from sympl_api.logging import get_current_request_id, logger
from sympl_observability.executor import default_executor
from sympl_observability.job_tracker import default_tracker
from sympl_storage.store import default_store

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    tags=["Health"]
)
async def health_check():
    """
    Returns service liveness, PostgreSQL database connectivity, and engine availability.
    Public endpoint: Does not require authentication.
    """
    health_data = service.check_health()
    return health_data


@router.post(
    "/proposal/generate",
    response_model=ProposalGenerateResponse,
    summary="End-to-End Proposal Generation Pipeline",
    dependencies=[Depends(verify_api_key)],
    tags=["Proposal Pipeline"]
)
async def generate_proposal(payload: Dict[str, Any]):
    """
    Executes the complete proposal generation pipeline:
      Client Intake -> Proposal Planner -> Proposal Writer -> Proposal Renderer
    Returns the generated proposal_id, request_id, plan, draft, rendered document, and stage execution timings.
    """
    req_id = get_current_request_id()
    logger.info("Executing full proposal generation pipeline")
    result = service.execute_full_pipeline(payload, request_id=req_id)
    return result


@router.post(
    "/proposal/plan",
    summary="Execute Proposal Planner Only",
    dependencies=[Depends(verify_api_key)],
    tags=["Individual Stages"]
)
async def plan_proposal(payload: Dict[str, Any]):
    """
    Executes only the Proposal Planner layer.
    Input: Client Intake JSON.
    Returns: Bounded, writer-sanitized proposal_plan.json structure.
    """
    logger.info("Executing Proposal Planner endpoint")
    plan = service.execute_planner(payload)
    return plan


@router.post(
    "/proposal/write",
    summary="Execute Proposal Writer Only",
    dependencies=[Depends(verify_api_key)],
    tags=["Individual Stages"]
)
async def write_proposal(payload: Dict[str, Any]):
    """
    Executes only the Proposal Writer layer.
    Input: proposal_plan.json structure.
    Returns: Validated proposal_draft.json structure.
    """
    logger.info("Executing Proposal Writer endpoint")
    draft = service.execute_writer(payload)
    return draft


@router.post(
    "/proposal/render",
    summary="Execute Proposal Renderer Only",
    dependencies=[Depends(verify_api_key)],
    tags=["Individual Stages"]
)
async def render_proposal(payload: Dict[str, Any]):
    """
    Executes only the Proposal Renderer layer.
    Input: proposal_draft.json structure.
    Returns: Presentation-ready rendered_proposal.json structure.
    """
    logger.info("Executing Proposal Renderer endpoint")
    rendered = service.execute_renderer(payload)
    return rendered


@router.post(
    "/proposal/generate/async",
    response_model=AsyncGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Asynchronous Proposal Generation Pipeline",
    dependencies=[Depends(verify_api_key)],
    tags=["Proposal Pipeline"]
)
async def generate_proposal_async(payload: Dict[str, Any]):
    """
    Submits client intake for asynchronous proposal generation.
    Validates input schema and approved_scope immediately, creates a proposal_jobs record,
    submits execution to LocalBackgroundExecutor, and returns job_id immediately.
    """
    req_id = get_current_request_id()
    logger.info(f"Received async proposal generation request [{req_id}]")

    # 1. Immediate validation before queuing
    service.parse_client_intake(payload)

    # 2. Create job in proposal_jobs and persist intake
    job_id = default_tracker.create_job(payload)
    default_store.save_intake(job_id, payload)

    # 3. Submit to background executor
    default_executor.submit_job(job_id=job_id, payload=payload, request_id=req_id, orchestrator=service)

    return {
        "job_id": job_id,
        "status": "CREATED",
        "request_id": req_id,
        "message": "Proposal generation job queued successfully."
    }


@router.get(
    "/proposal/status/{job_id}",
    response_model=JobStatusResponse,
    summary="Check Asynchronous Proposal Job Status",
    dependencies=[Depends(verify_api_key)],
    tags=["Proposal Pipeline"]
)
async def get_proposal_job_status(job_id: str):
    """
    Returns current status, active stage, completion progress, and proposal_id
    for an asynchronous proposal generation job. Requires authentication.
    """
    job_info = default_tracker.get_job_status(job_id)
    if not job_info:
        req_id = get_current_request_id()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "JOB_NOT_FOUND",
                "message": f"Proposal job '{job_id}' not found.",
                "request_id": req_id
            }
        )
    return job_info


@router.get(
    "/proposal/{proposal_id}/pdf",
    summary="Download Proposal PDF Document",
    tags=["Proposal Artifacts"]
)
async def get_proposal_pdf(proposal_id: str):
    """
    Returns the binary vector PDF file for a generated proposal.
    """
    pdf_bytes = default_store.load_pdf(proposal_id)
    if not pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "PDF_NOT_FOUND",
                "message": f"PDF artifact for proposal '{proposal_id}' was not found."
            }
        )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="proposal_{proposal_id}.pdf"'}
    )


@router.get(
    "/proposal/{proposal_id}/manifest",
    summary="Get Proposal Artifact Manifest",
    tags=["Proposal Artifacts"]
)
async def get_proposal_manifest(proposal_id: str):
    """
    Returns manifest.json listing all 5 proposal artifacts with metadata and hashes.
    """
    manifest = default_store.load_manifest(proposal_id)
    if not manifest:
        # Attempt to compile if directory exists
        manifest = default_store.compile_manifest(proposal_id)
    if not manifest or manifest.get("artifact_count", 0) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "MANIFEST_NOT_FOUND",
                "message": f"Manifest for proposal '{proposal_id}' was not found."
            }
        )
    return manifest


@router.get(
    "/proposal/{proposal_id}/artifacts",
    summary="List Proposal Artifacts",
    tags=["Proposal Artifacts"]
)
async def list_proposal_artifacts(proposal_id: str):
    """
    Returns artifact availability and file details for a given proposal.
    """
    manifest = default_store.load_manifest(proposal_id)
    if not manifest:
        manifest = default_store.compile_manifest(proposal_id)
    return {
        "proposal_id": proposal_id,
        "artifact_count": manifest.get("artifact_count", 0),
        "expected_count": 5,
        "all_artifacts_present": manifest.get("all_artifacts_present", False),
        "artifacts": manifest.get("artifacts", {})
    }

