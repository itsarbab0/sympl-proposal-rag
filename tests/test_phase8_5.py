"""
Sympl Solutions Proposal RAG — Phase 8.5 Quality Optimization Test Suite

Covers all 8 key verification scenarios for Phase 8.5:
  1. Minimum service depth preservation (service heading, cadence, operational subsections, deliverables, boundaries)
  2. Executive summary constraints (<= 120 words, client-specific, zero buzzwords)
  3. Why Us reference block classification and sector isolation (arts vs non-arts)
  4. Branding system customization (logo URL/path, company metadata, colors, typography, footer)
  5. PDF generation service (ReportLab Platypus, NumberedCanvas, vector layout)
  6. Artifact manifest completeness (all 5 files: plan, draft, render, pdf, manifest)
  7. API artifact delivery endpoints (GET /pdf, GET /manifest, GET /artifacts)
  8. Database invariants verification (Zero changes to the 6 frozen DB tables)
"""

import os
import sys
import json
import pytest
from pathlib import Path
from starlette.testclient import TestClient
import psycopg

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

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
    ApprovedCommercialInputs,
    Preferences
)
from sympl_planner.engine import ProposalPlanner
from sympl_planner.why_us import (
    GLOBAL_REFERENCE_BLOCK,
    SECTOR_SPECIFIC_REFERENCE_BLOCK,
    CONDITIONAL_REFERENCE_BLOCK,
    REFERENCE_BLOCKS,
    WhyUsSelector
)
from sympl_writer import (
    ProposalWriter,
    ProposalDraft,
    ProposalValidator,
    MockLLMClient
)
from sympl_renderer.branding import SymplBranding, ColorPalette, Typography
from sympl_renderer.pdf_generator import PdfGenerationService
from sympl_renderer.renderer import ProposalRenderer
from sympl_storage.store import default_store
from sympl_api.main import app
from sympl_api.config import settings


class TestPhase85QualityOptimization:
    """Test suite for Phase 8.5 quality optimizations and delivery layer."""

    @classmethod
    def setup_class(cls):
        cls.planner = ProposalPlanner()
        cls.validator = ProposalValidator()
        cls.writer = ProposalWriter(llm_client=MockLLMClient())
        cls.renderer = ProposalRenderer()
        cls.pdf_service = PdfGenerationService()
        cls.client = TestClient(app)
        cls.api_headers = {"X-API-Key": settings.API_KEY}

    # --------------------------------------------------------------------------
    # Test 1: Minimum Service Depth Preservation
    # --------------------------------------------------------------------------
    def test_01_minimum_service_depth_preservation(self):
        """Validates that service sections contain heading, cadence, operational subsections, deliverables, and boundaries."""
        client_input = ClientInput(
            client_id="TEST_85_DEPTH",
            organization=OrganizationInfo(
                name="Northstar Community Clinic",
                organization_type="nonprofit",
                sector="community_services"
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="standard"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="semi_monthly", sympl_processes_payroll=True)
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="semi_monthly", sympl_processes_payroll=True)
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=3100.0
            )
        )

        plan = self.planner.plan(client_input)
        plan_dict = json.loads(plan.to_json(for_writer=True))
        draft = self.writer.write(plan_dict)

        # Check section structure
        assert len(draft.sections) >= 2
        for sec in draft.sections:
            assert sec.section_title is not None
            assert len(sec.opening_text) > 20
            # Cadence mentioned in opening or headings
            assert any(word in sec.opening_text.lower() or any(word in sub.heading.lower() for sub in sec.subsections)
                       for word in ["cycle", "weekly", "monthly", "cadence", "schedule"])
            # Operational subsections, deliverables, boundaries
            headings = [sub.heading.lower() for sub in sec.subsections]
            assert any("deliverable" in h for h in headings), f"Missing deliverables in {sec.section_title}"
            assert any("boundar" in h or "prerequisite" in h for h in headings), f"Missing boundaries in {sec.section_title}"

    # --------------------------------------------------------------------------
    # Test 2: Executive Summary Word Count and Style
    # --------------------------------------------------------------------------
    def test_02_executive_summary_constraints(self):
        """Validates that executive summary is <= 120 words, client-specific, and free of buzzwords."""
        client_input = ClientInput(
            client_id="TEST_85_EXEC",
            organization=OrganizationInfo(
                name="Hope Valley Community Care",
                organization_type="charity",
                sector="community_services"
            ),
            engagement=EngagementContext(engagement_type="recurring", complexity="compact"),
            requested_scope=ScopeContainer(bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)),
            approved_scope=ScopeContainer(bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)),
            commercial_terms=ApprovedCommercialInputs(pricing_model="fixed_retainer", monthly_retainer=1850.0)
        )

        plan = self.planner.plan(client_input)
        plan_dict = json.loads(plan.to_json(for_writer=True))
        draft = self.writer.write(plan_dict)

        exec_summary = draft.executive_summary
        words = exec_summary.split()
        assert len(words) <= 120, f"Executive summary exceeds 120 words ({len(words)} words)"
        assert "Hope Valley" in exec_summary, "Executive summary must reference client name"

        # Check for buzzwords
        for forbidden in ["comprehensive suite", "continued success", "core mission", "strategic partnership", "synergy", "cutting-edge"]:
            assert forbidden not in exec_summary.lower(), f"Forbidden buzzword found: {forbidden}"

    # --------------------------------------------------------------------------
    # Test 3: Why Us Reference Block Classification and Sector Isolation
    # --------------------------------------------------------------------------
    def test_03_why_us_reference_block_classification_and_isolation(self):
        """Validates reference block types and sector isolation between community services and arts."""
        # 1. Classification check
        for block_id, blk in REFERENCE_BLOCKS.items():
            assert "block_type" in blk
            assert blk["block_type"] in (GLOBAL_REFERENCE_BLOCK, SECTOR_SPECIFIC_REFERENCE_BLOCK, CONDITIONAL_REFERENCE_BLOCK)

        # 2. Sector Isolation: Community Services Nonprofit
        comm_input = ClientInput(
            client_id="TEST_85_COMM",
            organization=OrganizationInfo(name="Community Food Network", organization_type="nonprofit", sector="community_services"),
            engagement=EngagementContext(engagement_type="recurring", complexity="standard"),
            requested_scope=ScopeContainer(bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)),
            approved_scope=ScopeContainer(bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)),
            commercial_terms=ApprovedCommercialInputs(pricing_model="fixed_retainer", monthly_retainer=2000.0),
            preferences=Preferences(include_why_us=True)
        )
        comm_blocks = WhyUsSelector.assemble_why_us(comm_input)
        comm_keys = [b.get("block_key") or b.get("block_id") for b in comm_blocks]
        assert "REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL" in comm_keys
        assert "REF_BLOCK_WHY_US_SECTOR_ARTS_LEADERSHIP" not in comm_keys
        assert "REF_BLOCK_WHY_US_SECTOR_ARTS_EXP_RPFF" not in comm_keys

        # 3. Sector Isolation: Arts Organization
        arts_input = ClientInput(
            client_id="TEST_85_ARTS",
            organization=OrganizationInfo(name="Lakeshore Youth Theatre", organization_type="nonprofit", sector="arts_culture"),
            engagement=EngagementContext(engagement_type="recurring", complexity="standard"),
            requested_scope=ScopeContainer(bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)),
            approved_scope=ScopeContainer(bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)),
            commercial_terms=ApprovedCommercialInputs(pricing_model="fixed_retainer", monthly_retainer=2000.0),
            preferences=Preferences(include_why_us=True)
        )
        arts_blocks = WhyUsSelector.assemble_why_us(arts_input)
        arts_keys = [b.get("block_key") or b.get("block_id") for b in arts_blocks]
        assert "REF_BLOCK_WHY_US_SECTOR_ARTS_LEADERSHIP" in arts_keys
        assert "REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL" not in arts_keys

    # --------------------------------------------------------------------------
    # Test 4: Branding System Customization
    # --------------------------------------------------------------------------
    def test_04_branding_system_customization(self):
        """Validates that custom branding (logo, company metadata, colors, typography, footer) applies cleanly."""
        custom_data = {
            "company_name": "Sympl Advisors LLP",
            "tagline": "Financial Architecture for Canadian Organizations",
            "website": "https://sympladvisors.ca",
            "logo_url": "https://sympladvisors.ca/assets/logo.png",
            "logo_path": "assets/test_logo.png",
            "footer_text": "Private & Confidential — Sympl Advisors LLP",
            "colors": {
                "primary": "#0F172A",
                "secondary": "#0D9488"
            },
            "typography": {
                "heading_font": "Roboto, sans-serif",
                "body_font": "Inter, sans-serif"
            }
        }
        branding = SymplBranding.from_dict(custom_data)
        assert branding.company_name == "Sympl Advisors LLP"
        assert branding.logo_url == "https://sympladvisors.ca/assets/logo.png"
        assert branding.logo_path == "assets/test_logo.png"
        assert branding.colors.primary == "#0F172A"
        assert branding.colors.secondary == "#0D9488"
        assert branding.footer_text == "Private & Confidential — Sympl Advisors LLP"

    # --------------------------------------------------------------------------
    # Test 5: ReportLab PDF Generation Service
    # --------------------------------------------------------------------------
    def test_05_pdf_generation_service(self):
        """Validates compiling RenderedProposal into a binary PDF using ReportLab Platypus."""
        client_input = ClientInput(
            client_id="TEST_85_PDF",
            organization=OrganizationInfo(name="Toronto Arts Coalition", organization_type="nonprofit", sector="arts_culture"),
            engagement=EngagementContext(engagement_type="recurring", complexity="compact"),
            requested_scope=ScopeContainer(bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)),
            approved_scope=ScopeContainer(bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)),
            commercial_terms=ApprovedCommercialInputs(pricing_model="fixed_retainer", monthly_retainer=2200.0)
        )

        plan = self.planner.plan(client_input)
        plan_dict = json.loads(plan.to_json(for_writer=True))
        draft = self.writer.write(plan_dict)
        rendered = self.renderer.render(draft)

        pdf_bytes = self.pdf_service.generate_pdf(rendered)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 2000
        assert pdf_bytes.startswith(b"%PDF-"), "Generated file must have valid PDF magic bytes"

    # --------------------------------------------------------------------------
    # Test 6: Proposal Artifact Manifest Structure
    # --------------------------------------------------------------------------
    def test_06_artifact_manifest_structure(self):
        """Validates that all 5 proposal artifacts are tracked with valid SHA256 checksums."""
        proposal_id = "test_prop_manifest_85"
        plan_data = {"test": "plan"}
        draft_data = {"test": "draft"}
        render_data = {"test": "render"}
        pdf_content = b"%PDF-1.4 test bytes content"

        default_store.save_plan(proposal_id, plan_data)
        default_store.save_draft(proposal_id, draft_data)
        default_store.save_render(proposal_id, render_data)
        default_store.save_pdf(proposal_id, pdf_content)

        manifest = default_store.compile_manifest(
            proposal_id=proposal_id,
            client_name="Test Client",
            title="Test Proposal"
        )

        assert manifest["proposal_id"] == proposal_id
        assert manifest["artifact_count"] == 5
        assert manifest["all_artifacts_present"] is True

        expected = ["proposal_plan.json", "proposal_draft.json", "rendered_proposal.json", "proposal.pdf", "manifest.json"]
        for f in expected:
            art = manifest["artifacts"][f]
            assert art["exists"] is True
            assert len(art["sha256"]) == 64
            assert art["size_bytes"] > 0

    # --------------------------------------------------------------------------
    # Test 7: API Artifact Delivery Endpoints
    # --------------------------------------------------------------------------
    def test_07_api_artifact_endpoints(self):
        """Validates GET /proposal/{id}/pdf, /manifest, and /artifacts endpoints."""
        payload = {
            "client_id": "TEST_85_API_ARTIFACTS",
            "organization": {
                "name": "Pacific Wildlife Trust",
                "organization_type": "nonprofit",
                "sector": "community_services"
            },
            "engagement": {
                "engagement_type": "recurring",
                "complexity": "compact"
            },
            "requested_scope": {
                "bookkeeping": {"cadence": "weekly", "ap_ar": True, "reconciliations": True}
            },
            "approved_scope": {
                "bookkeeping": {"cadence": "weekly", "ap_ar": True, "reconciliations": True}
            },
            "commercial_terms": {
                "pricing_model": "fixed_retainer",
                "monthly_retainer": 2500.0
            }
        }

        # Generate proposal
        resp = self.client.post("/proposal/generate", json=payload, headers=self.api_headers)
        assert resp.status_code == 200
        data = resp.json()
        proposal_id = data["proposal_id"]

        # 1. GET /proposal/{proposal_id}/pdf
        pdf_resp = self.client.get(f"/proposal/{proposal_id}/pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"] == "application/pdf"
        assert pdf_resp.content.startswith(b"%PDF-")

        # 2. GET /proposal/{proposal_id}/manifest
        m_resp = self.client.get(f"/proposal/{proposal_id}/manifest")
        assert m_resp.status_code == 200
        m_data = m_resp.json()
        assert m_data["artifact_count"] == 5
        assert m_data["all_artifacts_present"] is True

        # 3. GET /proposal/{proposal_id}/artifacts
        a_resp = self.client.get(f"/proposal/{proposal_id}/artifacts")
        assert a_resp.status_code == 200
        a_data = a_resp.json()
        assert a_data["artifact_count"] == 5

    # --------------------------------------------------------------------------
    # Test 8: Database Invariants Post Phase 8.5
    # --------------------------------------------------------------------------
    def test_08_database_invariants_post_phase8_5(self):
        """Confirms that all 6 frozen tables in PostgreSQL maintain exact invariant counts."""
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            from sympl_planner.retrieval import DATABASE_URL
            db_url = DATABASE_URL

        expected_counts = {
            "proposal_documents": 7,
            "proposal_chunks": 71,
            "sympl_style_rules": 21,
            "sympl_reference_blocks": 13,
            "dataset_imports": 7
        }

        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                for table, count in expected_counts.items():
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    actual = cur.fetchone()[0]
                    assert actual == count, f"Frozen table {table} count mismatch: expected {count}, got {actual}"

                # Embeddings count
                cur.execute("SELECT COUNT(*) FROM proposal_chunks WHERE embedding IS NOT NULL")
                emb_count = cur.fetchone()[0]
                assert emb_count == 47, f"Embeddings count altered: expected 47, got {emb_count}"
