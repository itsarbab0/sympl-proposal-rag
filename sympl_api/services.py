"""
Sympl Solutions Proposal RAG — API Service Layer

Orchestration services that wrap the frozen Proposal Planner, Proposal Writer,
and Proposal Renderer components without modifying any underlying logic or data assets.
"""

import time
import uuid
import json
from typing import Dict, Any, Optional

import psycopg
from sympl_planner.schema import (
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
    Preferences
)
from sympl_planner.engine import ProposalPlanner
from sympl_planner.retrieval import DATABASE_URL
from sympl_writer import ProposalWriter
from sympl_renderer import ProposalRenderer
from sympl_api.config import settings
from sympl_api.logging import logger
from sympl_api.exceptions import (
    InvalidIntakeException,
    ApprovalRequiredException,
    EmptyApprovedScopeException
)
from sympl_observability.environment import validate_environment
from sympl_observability.telemetry import PipelineTelemetry
from sympl_storage.store import default_store


class OrchestrationService:
    """Orchestrates proposal generation across Planner, Writer, and Renderer layers."""

    def __init__(self):
        self._planner: Optional[ProposalPlanner] = None
        self._writer: Optional[ProposalWriter] = None
        self._renderer: Optional[ProposalRenderer] = None

    @property
    def planner(self) -> ProposalPlanner:
        if self._planner is None:
            self._planner = ProposalPlanner()
        return self._planner

    @property
    def writer(self) -> ProposalWriter:
        if self._writer is None:
            self._writer = ProposalWriter()
        return self._writer

    @property
    def renderer(self) -> ProposalRenderer:
        if self._renderer is None:
            self._renderer = ProposalRenderer()
        return self._renderer

    def check_health(self) -> Dict[str, Any]:
        """Performs non-mutating liveness, database, and engine diagnostics."""
        report = validate_environment(strict=False)
        return {
            "status": report.status,
            "version": settings.API_VERSION,
            "database": report.database_status,
            "embedding": report.embedding_status,
            "planner": "available",
            "writer": "available",
            "renderer": "available",
            "llm_provider": report.llm_provider,
            "worker": report.worker_status
        }

    def parse_client_intake(self, intake_dict: Dict[str, Any]) -> ClientInput:
        """Parses and validates raw intake payload into strongly-typed ClientInput."""
        if not intake_dict or not isinstance(intake_dict, dict):
            raise InvalidIntakeException("Client intake payload must be a non-empty JSON object.")

        # Require organization name
        org_data = intake_dict.get("organization") or {}
        client_name = org_data.get("name") or intake_dict.get("client_name") or intake_dict.get("name")
        if not client_name:
            raise InvalidIntakeException(
                "Missing required client name. Supply either 'organization.name' or 'client_name'."
            )

        client_id = intake_dict.get("client_id") or f"client_{uuid.uuid4().hex[:8]}"

        org_info = OrganizationInfo(
            name=client_name,
            organization_type=org_data.get("organization_type") or intake_dict.get("organization_type", "nonprofit"),
            sector=org_data.get("sector") or intake_dict.get("sector", "community_services"),
            description=org_data.get("description") or intake_dict.get("description", ""),
            current_systems=org_data.get("current_systems") or intake_dict.get("current_systems", []),
            target_systems=org_data.get("target_systems") or intake_dict.get("target_systems", []),
            evaluation_systems=org_data.get("evaluation_systems", [])
        )

        eng_data = intake_dict.get("engagement") or {}
        engagement = EngagementContext(
            engagement_type=eng_data.get("engagement_type") or intake_dict.get("engagement_type", "recurring"),
            complexity=eng_data.get("complexity") or intake_dict.get("complexity", "standard"),
            fixed_term_duration=eng_data.get("fixed_term_duration") or intake_dict.get("fixed_term_duration"),
            diagnostic_focus=eng_data.get("diagnostic_focus", [])
        )

        # Scope validation: approved_scope is strictly required before proposal generation
        if "approved_scope" not in intake_dict or intake_dict.get("approved_scope") is None:
            raise ApprovalRequiredException(
                message="approved_scope is required before proposal generation",
                details={}
            )

        app_scope_raw = intake_dict.get("approved_scope")
        if not isinstance(app_scope_raw, dict) or len(app_scope_raw) == 0:
            raise EmptyApprovedScopeException(
                message="approved_scope cannot be empty",
                details={}
            )

        # Scopes: strictly isolate approved_scope, NEVER fallback to requested_scope
        req_scope_raw = intake_dict.get("requested_scope") or {}
        requested_scope = self._build_scope_container(req_scope_raw)
        approved_scope = self._build_scope_container(app_scope_raw)

        # Ensure approved_scope contains at least one active service family
        if not approved_scope.active_families():
            raise EmptyApprovedScopeException(
                message="approved_scope cannot be empty",
                details={}
            )

        # Preserve requested_scope strictly for audit and exclusion logging
        if req_scope_raw:
            req_families = set(requested_scope.active_families())
            app_families = set(approved_scope.active_families())
            unapproved_families = req_families - app_families
            if unapproved_families:
                logger.info(
                    f"Audit: Excluded requested scope families not approved: {list(unapproved_families)}"
                )

        # Commercial inputs
        comm_raw = intake_dict.get("commercial_terms") or {}
        commercial_terms = ApprovedCommercialInputs(
            pricing_model=comm_raw.get("pricing_model") or intake_dict.get("pricing_model", "fixed_retainer"),
            currency=comm_raw.get("currency", "CAD"),
            monthly_retainer=comm_raw.get("monthly_retainer"),
            setup_fee=comm_raw.get("setup_fee"),
            hourly_rate=comm_raw.get("hourly_rate"),
            billing_schedule=comm_raw.get("billing_schedule"),
            include_backlog_exclusion=comm_raw.get("include_backlog_exclusion", True),
            software_fees_excluded=comm_raw.get("software_fees_excluded", True)
        )

        # Preferences
        pref_raw = intake_dict.get("preferences") or {}
        preferences = Preferences(
            include_why_us=pref_raw.get("include_why_us"),
            is_competitive_pitch=pref_raw.get("is_competitive_pitch", False),
            is_trusted_continuity=pref_raw.get("is_trusted_continuity", False),
            identity_credential_preference=pref_raw.get("identity_credential_preference")
        )

        return ClientInput(
            client_id=client_id,
            organization=org_info,
            engagement=engagement,
            requested_scope=requested_scope,
            approved_scope=approved_scope,
            commercial_terms=commercial_terms,
            preferences=preferences
        )

    def _build_scope_container(self, scope_dict: Dict[str, Any]) -> ScopeContainer:
        """Maps nested scope dictionary into ScopeContainer."""
        if not isinstance(scope_dict, dict):
            return ScopeContainer()

        bk = None
        if "bookkeeping" in scope_dict and scope_dict["bookkeeping"]:
            bk_data = scope_dict["bookkeeping"] if isinstance(scope_dict["bookkeeping"], dict) else {}
            bk = BookkeepingScope(**{k: v for k, v in bk_data.items() if hasattr(BookkeepingScope, k)})

        py = None
        if "payroll" in scope_dict and scope_dict["payroll"]:
            py_data = scope_dict["payroll"] if isinstance(scope_dict["payroll"], dict) else {}
            py = PayrollScope(**{k: v for k, v in py_data.items() if hasattr(PayrollScope, k)})

        rep = None
        if "financial_reporting" in scope_dict and scope_dict["financial_reporting"]:
            rep_data = scope_dict["financial_reporting"] if isinstance(scope_dict["financial_reporting"], dict) else {}
            rep = ReportingScope(**{k: v for k, v in rep_data.items() if hasattr(ReportingScope, k)})

        comp = None
        if "compliance" in scope_dict and scope_dict["compliance"]:
            comp_data = scope_dict["compliance"] if isinstance(scope_dict["compliance"], dict) else {}
            comp = ComplianceScope(**{k: v for k, v in comp_data.items() if hasattr(ComplianceScope, k)})

        trans = None
        if "digital_transformation" in scope_dict and scope_dict["digital_transformation"]:
            trans_data = scope_dict["digital_transformation"] if isinstance(scope_dict["digital_transformation"], dict) else {}
            trans = TransformationScope(**{k: v for k, v in trans_data.items() if hasattr(TransformationScope, k)})

        train = None
        if "training" in scope_dict and scope_dict["training"]:
            train_data = scope_dict["training"] if isinstance(scope_dict["training"], dict) else {}
            train = TrainingScope(**{k: v for k, v in train_data.items() if hasattr(TrainingScope, k)})

        trans_svc = None
        if "transition" in scope_dict and scope_dict["transition"]:
            ts_data = scope_dict["transition"] if isinstance(scope_dict["transition"], dict) else {}
            trans_svc = TransitionScope(**{k: v for k, v in ts_data.items() if hasattr(TransitionScope, k)})

        return ScopeContainer(
            bookkeeping=bk,
            payroll=py,
            financial_reporting=rep,
            compliance=comp,
            digital_transformation=trans,
            training=train,
            transition=trans_svc
        )

    def execute_planner(self, intake_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the Proposal Planner and returns writer-sanitized proposal_plan."""
        client_input = self.parse_client_intake(intake_data)
        plan = self.planner.plan(client_input)
        return json.loads(plan.to_json(for_writer=True))

    def execute_writer(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the Proposal Writer on a proposal_plan and returns proposal_draft."""
        draft = self.writer.write(plan_data)
        return draft.to_dict()

    def execute_renderer(self, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the Proposal Renderer on proposal_draft and returns rendered_proposal."""
        rendered = self.renderer.render(draft_data)
        return rendered.to_dict()

    def execute_full_pipeline(self, intake_data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Orchestrates end-to-end execution: Planner -> Writer -> Renderer with telemetry and artifact persistence."""
        proposal_id = f"prop_{uuid.uuid4().hex[:12]}"
        telemetry = PipelineTelemetry(proposal_id=proposal_id, request_id=request_id)
        logger.info(f"Starting proposal generation pipeline: {proposal_id}")

        try:
            # Stage 1: Planner
            t0 = time.perf_counter()
            plan_dict = self.execute_planner(intake_data)
            t1 = time.perf_counter()
            planner_ms = round((t1 - t0) * 1000.0, 2)
            telemetry.record_planner(planner_ms)
            default_store.save_plan(proposal_id, plan_dict)
            logger.info(f"Planner stage completed in {planner_ms}ms")

            # Stage 2: Writer
            t2 = time.perf_counter()
            draft_dict = self.execute_writer(plan_dict)
            t3 = time.perf_counter()
            writer_ms = round((t3 - t2) * 1000.0, 2)
            telemetry.record_writer(writer_ms)
            default_store.save_draft(proposal_id, draft_dict)
            logger.info(f"Writer stage completed in {writer_ms}ms")

            # Stage 3: Renderer
            t4 = time.perf_counter()
            rendered_dict = self.execute_renderer(draft_dict)
            t5 = time.perf_counter()
            renderer_ms = round((t5 - t4) * 1000.0, 2)
            telemetry.record_renderer(renderer_ms)
            default_store.save_render(proposal_id, rendered_dict)
            logger.info(f"Renderer stage completed in {renderer_ms}ms")

            # Stage 4: PDF Generation & Manifest
            from sympl_renderer.pdf_generator import PdfGenerationService
            pdf_service = PdfGenerationService()
            pdf_bytes = pdf_service.generate_pdf(rendered_dict)
            default_store.save_pdf(proposal_id, pdf_bytes)

            client_label = (
                intake_data.get("organization", {}).get("name")
                or intake_data.get("client_name")
                or "Client Organization"
            )
            manifest = default_store.compile_manifest(
                proposal_id=proposal_id,
                client_name=client_label,
                title=draft_dict.get("title", "Services Proposal")
            )
            logger.info(f"Generated PDF and compiled artifact manifest for {proposal_id}")

            telemetry_result = telemetry.complete()
            total_ms = telemetry_result["stages"]["total_ms"]

            return {
                "proposal_id": proposal_id,
                "request_id": request_id,
                "status": "COMPLETED",
                "plan": plan_dict,
                "draft": draft_dict,
                "rendered_output": rendered_dict,
                "pdf_url": f"/proposal/{proposal_id}/pdf",
                "manifest": manifest,
                "execution_metadata": {
                    "planner_time_ms": planner_ms,
                    "writer_time_ms": writer_ms,
                    "renderer_time_ms": renderer_ms,
                    "total_time_ms": total_ms
                }
            }
        except Exception as e:
            telemetry.fail(str(e))
            raise


service = OrchestrationService()
