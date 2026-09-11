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
    GenericServiceScope,
    ApprovedCommercialInputs,
    Preferences,
    ClientNarrativeContext
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


def calculate_context_quality(intake_dict: Dict[str, Any]) -> tuple:
    """
    Calculates weighted context quality score (0 to 100).
    High-value narrative fields carry 75% of weight.
    Structured and operational fields carry 25% of weight.

    Returns:
        (context_quality: str, score: int, breakdown: Dict[str, Any])
    """
    score = 0
    breakdown = {}

    org_data = intake_dict.get("organization") or {}
    bg_data = intake_dict.get("client_background") or {}
    fin_data = intake_dict.get("finance_context") or {}
    obj_data = intake_dict.get("objectives") or {}
    svc_data = intake_dict.get("service_context") or {}

    # High-value narrative fields (up to 75 points)
    # 1. Client Situation Summary (15 pts)
    sit = intake_dict.get("client_situation_summary") or bg_data.get("client_situation_summary") or fin_data.get("client_situation_summary")
    if sit and str(sit).strip():
        score += 15
        breakdown["client_situation_summary"] = 15

    # 2. Client Challenges Summary (15 pts)
    chal_sum = intake_dict.get("client_challenges_summary") or bg_data.get("client_challenges_summary") or fin_data.get("client_challenges_summary")
    if chal_sum and str(chal_sum).strip():
        score += 15
        breakdown["client_challenges_summary"] = 15

    # 3. Current Finance Challenges (15 pts)
    fin_chal = intake_dict.get("current_finance_challenges") or fin_data.get("current_finance_challenges") or fin_data.get("challenges")
    if fin_chal and (isinstance(fin_chal, list) and len(fin_chal) > 0 or str(fin_chal).strip()):
        score += 15
        breakdown["current_finance_challenges"] = 15

    # 4. Organization Description (10 pts)
    desc = intake_dict.get("organization_description") or bg_data.get("organization_description") or org_data.get("description") or intake_dict.get("description")
    if desc and str(desc).strip():
        score += 10
        breakdown["organization_description"] = 10

    # 5. Reason for Engagement (10 pts)
    reason = intake_dict.get("reason_for_engagement") or obj_data.get("reason_for_engagement")
    if reason and str(reason).strip():
        score += 10
        breakdown["reason_for_engagement"] = 10

    # 6. Desired Outcomes (10 pts)
    outcomes = intake_dict.get("desired_outcomes") or obj_data.get("desired_outcomes")
    if outcomes and (isinstance(outcomes, list) and len(outcomes) > 0 or str(outcomes).strip()):
        score += 10
        breakdown["desired_outcomes"] = 10

    # Structured context fields (up to 25 points)
    # 7. Current Accounting System (5 pts)
    sys_name = intake_dict.get("current_accounting_system") or fin_data.get("current_accounting_system") or fin_data.get("current_system") or (org_data.get("current_systems", [None])[0] if org_data.get("current_systems") else None)
    if sys_name and str(sys_name).strip():
        score += 5
        breakdown["current_accounting_system"] = 5

    # 8. Current Finance Process / Team (5 pts)
    proc = intake_dict.get("current_finance_process") or fin_data.get("current_finance_process") or intake_dict.get("current_finance_team_structure") or fin_data.get("current_finance_team_structure")
    if proc and str(proc).strip():
        score += 5
        breakdown["finance_process_or_team"] = 5

    # 9. Employee Count / Org Size / Revenue Range (5 pts)
    size = intake_dict.get("employee_count") or bg_data.get("employee_count") or intake_dict.get("organization_size") or bg_data.get("organization_size") or intake_dict.get("annual_budget_or_revenue_range") or bg_data.get("annual_budget_or_revenue_range")
    if size is not None and str(size).strip():
        score += 5
        breakdown["organization_scale"] = 5

    # 10. Service Specific Operational Context (10 pts)
    has_svc_ctx = False
    if svc_data and isinstance(svc_data, dict) and any(bool(v) for v in svc_data.values()):
        has_svc_ctx = True
    elif any(k.startswith("bookkeeping_") or k.startswith("payroll_") or k.startswith("reporting_") or k.startswith("compliance_") for k in intake_dict.keys()):
        has_svc_ctx = True

    if has_svc_ctx:
        score += 10
        breakdown["service_context"] = 10

    score = min(100, score)

    if score >= 70:
        quality = "HIGH"
    elif score >= 30:
        quality = "MEDIUM"
    else:
        quality = "LOW"

    return quality, score, breakdown


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

        # Context Quality Scoring (weighted importance: 75% narrative, 25% structured)
        context_quality, context_score, quality_breakdown = calculate_context_quality(intake_dict)
        if context_quality == "LOW":
            logger.warning(
                f"Intake context quality is LOW ({context_score}/100) for client '{client_name}'. "
                "Minimal business context provided; generating generic proposal."
            )

        # Extract enriched narrative context (support both top-level and nested structures)
        bg_data = intake_dict.get("client_background") or {}
        fin_data = intake_dict.get("finance_context") or {}
        obj_data = intake_dict.get("objectives") or {}
        svc_context_raw = intake_dict.get("service_context") or {}

        sit_summary = intake_dict.get("client_situation_summary") or bg_data.get("client_situation_summary") or fin_data.get("client_situation_summary")
        chal_summary = intake_dict.get("client_challenges_summary") or bg_data.get("client_challenges_summary") or fin_data.get("client_challenges_summary")
        org_desc = intake_dict.get("organization_description") or bg_data.get("organization_description") or org_data.get("description") or intake_dict.get("description")
        ind_ctx = intake_dict.get("industry_context") or bg_data.get("industry_context") or org_data.get("industry_context")
        emp_cnt = intake_dict.get("employee_count") or bg_data.get("employee_count") or org_data.get("employee_count")
        org_sz = intake_dict.get("organization_size") or bg_data.get("organization_size") or org_data.get("organization_size")
        rev_rng = intake_dict.get("annual_budget_or_revenue_range") or bg_data.get("annual_budget_or_revenue_range") or org_data.get("annual_budget_or_revenue_range")

        curr_acct = intake_dict.get("current_accounting_system") or fin_data.get("current_accounting_system") or fin_data.get("current_system")
        if not curr_acct and org_data.get("current_systems"):
            curr_acct = org_data.get("current_systems")[0]

        curr_proc = intake_dict.get("current_finance_process") or fin_data.get("current_finance_process")
        curr_team = intake_dict.get("current_finance_team_structure") or fin_data.get("current_finance_team_structure")
        curr_chal = intake_dict.get("current_finance_challenges") or fin_data.get("current_finance_challenges") or fin_data.get("challenges")

        reason_eng = intake_dict.get("reason_for_engagement") or obj_data.get("reason_for_engagement")
        des_outcomes = intake_dict.get("desired_outcomes") or obj_data.get("desired_outcomes")
        cl_prio = intake_dict.get("client_priorities") or obj_data.get("client_priorities")

        narrative_ctx = ClientNarrativeContext(
            client_situation_summary=sit_summary,
            client_challenges_summary=chal_summary,
            organization_description=org_desc,
            industry_context=ind_ctx,
            employee_count=emp_cnt,
            organization_size=org_sz,
            annual_budget_or_revenue_range=rev_rng,
            current_accounting_system=curr_acct,
            current_finance_process=curr_proc,
            current_finance_team_structure=curr_team,
            current_finance_challenges=curr_chal,
            reason_for_engagement=reason_eng,
            desired_outcomes=des_outcomes,
            client_priorities=cl_prio
        )

        enriched_dict = {
            "client_situation_summary": sit_summary,
            "client_challenges_summary": chal_summary,
            "organization_description": org_desc,
            "industry_context": ind_ctx,
            "employee_count": emp_cnt,
            "organization_size": org_sz,
            "annual_budget_or_revenue_range": rev_rng,
            "current_accounting_system": curr_acct,
            "current_finance_process": curr_proc,
            "current_finance_team_structure": curr_team,
            "current_finance_challenges": curr_chal,
            "reason_for_engagement": reason_eng,
            "desired_outcomes": des_outcomes,
            "client_priorities": cl_prio,
            "context_quality": context_quality,
            "context_score": context_score
        }

        # Scopes: strictly isolate approved_scope, NEVER fallback to requested_scope
        req_scope_raw = intake_dict.get("requested_scope") or {}
        requested_scope = self._build_scope_container(req_scope_raw, svc_context_raw)
        approved_scope = self._build_scope_container(app_scope_raw, svc_context_raw)

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
            preferences=preferences,
            narrative_context=narrative_ctx,
            service_context=svc_context_raw if svc_context_raw else None,
            context_quality=context_quality,
            context_score=context_score,
            enriched_context=enriched_dict
        )

    def _build_scope_container(
        self,
        scope_dict: Dict[str, Any],
        service_context: Optional[Dict[str, Any]] = None
    ) -> ScopeContainer:
        """Maps nested scope dictionary into ScopeContainer, integrating service context."""
        if not isinstance(scope_dict, dict):
            return ScopeContainer()

        svc_ctx = service_context or {}

        bk = None
        if "bookkeeping" in scope_dict and scope_dict["bookkeeping"]:
            bk_data = scope_dict["bookkeeping"] if isinstance(scope_dict["bookkeeping"], dict) else {}
            bk_extra = svc_ctx.get("bookkeeping") or {}
            combined_bk = {**bk_extra, **bk_data}
            bk = BookkeepingScope(**{k: v for k, v in combined_bk.items() if hasattr(BookkeepingScope, k)})

        py = None
        if "payroll" in scope_dict and scope_dict["payroll"]:
            py_data = scope_dict["payroll"] if isinstance(scope_dict["payroll"], dict) else {}
            py_extra = svc_ctx.get("payroll") or {}
            combined_py = {**py_extra, **py_data}
            py = PayrollScope(**{k: v for k, v in combined_py.items() if hasattr(PayrollScope, k)})

        rep = None
        if "financial_reporting" in scope_dict and scope_dict["financial_reporting"]:
            rep_data = scope_dict["financial_reporting"] if isinstance(scope_dict["financial_reporting"], dict) else {}
            rep_extra = svc_ctx.get("reporting") or svc_ctx.get("financial_reporting") or {}
            combined_rep = {**rep_extra, **rep_data}
            rep = ReportingScope(**{k: v for k, v in combined_rep.items() if hasattr(ReportingScope, k)})

        comp = None
        if "compliance" in scope_dict and scope_dict["compliance"]:
            comp_data = scope_dict["compliance"] if isinstance(scope_dict["compliance"], dict) else {}
            comp_extra = svc_ctx.get("compliance") or {}
            combined_comp = {**comp_extra, **comp_data}
            comp = ComplianceScope(**{k: v for k, v in combined_comp.items() if hasattr(ComplianceScope, k)})

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

        generic_list: List[GenericServiceScope] = []
        if "generic_services" in scope_dict and isinstance(scope_dict["generic_services"], list):
            valid_keys = getattr(GenericServiceScope, "__dataclass_fields__", {})
            for gs in scope_dict["generic_services"]:
                if isinstance(gs, dict):
                    filtered = {k: v for k, v in gs.items() if k in valid_keys}
                    generic_list.append(GenericServiceScope(**filtered))

        for k, v in scope_dict.items():
            if k in ("bookkeeping", "payroll", "financial_reporting", "compliance", "digital_transformation", "training", "transition", "generic_services"):
                continue
            if isinstance(v, dict):
                cat_name = v.get("service_category") or k.replace("_", " ").title()
                generic_list.append(GenericServiceScope(
                    service_category=cat_name,
                    service_name=v.get("service_name", cat_name),
                    description=v.get("description"),
                    deliverables=v.get("deliverables", []) if isinstance(v.get("deliverables"), list) else [],
                    requirements=v.get("requirements", []) if isinstance(v.get("requirements"), list) else [],
                    timeline=v.get("timeline"),
                    constraints=v.get("constraints"),
                    target_systems=v.get("target_systems", []) if isinstance(v.get("target_systems"), list) else []
                ))
            elif isinstance(v, bool) and v:
                cat_name = k.replace("_", " ").title()
                generic_list.append(GenericServiceScope(
                    service_category=cat_name,
                    service_name=cat_name
                ))

        return ScopeContainer(
            bookkeeping=bk,
            payroll=py,
            financial_reporting=rep,
            compliance=comp,
            digital_transformation=trans,
            training=train,
            transition=trans_svc,
            generic_services=generic_list
        )

    def execute_planner(self, intake_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the Proposal Planner and returns writer-sanitized proposal_plan."""
        client_input = self.parse_client_intake(intake_data)
        logger.info(
            f"[Planner Ingestion Validation] Client: '{client_input.organization.name}', "
            f"Context Quality: {client_input.context_quality} ({client_input.context_score}/100)."
        )
        plan = self.planner.plan(client_input)
        return json.loads(plan.to_json(for_writer=True))

    def execute_writer(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the Proposal Writer on a proposal_plan and returns proposal_draft."""
        client_ctx = plan_data.get("client_context") or {}
        meta = plan_data.get("metadata") or {}
        logger.info(
            f"[Writer Ingestion Validation] Client: '{plan_data.get('client_name')}', "
            f"Context Quality: {meta.get('context_quality', client_ctx.get('context_quality', 'UNKNOWN'))} "
            f"({meta.get('context_score', client_ctx.get('context_score', 0))}/100). "
            f"Situation Summary: {bool(client_ctx.get('client_situation_summary'))}, "
            f"Challenges Summary: {bool(client_ctx.get('client_challenges_summary'))}, "
            f"Finance Challenges: {bool(client_ctx.get('current_finance_challenges'))}, "
            f"Reason: {bool(client_ctx.get('reason_for_engagement'))}, "
            f"Outcomes: {bool(client_ctx.get('desired_outcomes'))}."
        )
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
