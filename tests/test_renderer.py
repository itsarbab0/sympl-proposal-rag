"""
Sympl Solutions Proposal RAG — Proposal Renderer Test Suite (Phase 5)

Covers all 10 required test scenarios:
  Test 1:  Compact bookkeeping rendering (dynamic compact page count)
  Test 2:  Nonprofit rendering (with dynamic Why Us page)
  Test 3:  Transformation rendering (with dynamic timeline roadmap page)
  Test 4:  Pricing preservation (fee amounts and placeholders intact)
  Test 5:  Reference preservation (Why Us and exclusions intact verbatim)
  Test 6:  Invalid draft rejection (enforces input contract)
  Test 7:  Mock Canva rendering (design creation, population, export)
  Test 8:  Database invariant verification (0 DB modifications)
  Test 9:  Output adapter verification (JSON, Canva, HTML, Markdown)
  Test 10: Layout overflow handling (capacity checks, empty page detection)
"""

import os
import sys
import json
import copy
import pytest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sympl_renderer import (
    ProposalRenderer,
    RenderedProposal,
    RenderPage,
    RenderComponent,
    ComponentType,
    PageType,
    MockCanvaClient,
    TemplateMapper,
    RenderValidator,
    ContentIntegrityValidator,
    PricingIntegrityValidator,
    ReferenceIntegrityValidator,
    LayoutOverflowValidator,
    JsonOutputAdapter,
    CanvaPayloadAdapter,
    HtmlPdfAdapter,
    MarkdownAdapter,
    InvalidDraftError,
    ContentIntegrityError,
    PricingIntegrityError,
    ReferenceIntegrityError,
    LayoutOverflowError
)


class TestProposalRenderer:
    """Test suite for Phase 5 Sympl Proposal Renderer layer."""

    @classmethod
    def setup_class(cls):
        cls.renderer = ProposalRenderer(canva_client=MockCanvaClient())
        cls.validator = RenderValidator()
        cls.template_mapper = TemplateMapper()

    # --------------------------------------------------------------------------
    # Test 1: Compact bookkeeping rendering
    # --------------------------------------------------------------------------
    def test_01_compact_bookkeeping_rendering(self):
        """Validates that a compact proposal produces a scaled, lean document without unnecessary pages."""
        compact_draft = {
            "title": "Accounting & Bookkeeping Services Proposal for Meadowvale Hub",
            "executive_summary": "Sympl Solutions delivers reliable, full-cycle operational bookkeeping support.",
            "sections": [
                {
                    "section_title": "Accounting & Bookkeeping Services",
                    "opening_text": "We manage day-to-day accounts payable, reconciliations, and financial records.",
                    "subsections": [
                        {
                            "heading": "Operational Ledger Management",
                            "bullets": [
                                "Process vendor invoices and coordinate disbursement runs",
                                "Reconcile operating bank accounts and credit cards monthly"
                            ]
                        }
                    ]
                }
            ],
            "why_us": [],  # Intentionally empty for lean proposal
            "pricing": {
                "pricing_model": "fixed_retainer",
                "currency": "CAD",
                "billing_schedule": "Monthly retainer invoiced on the 1st of each service month.",
                "fee_items": [
                    {
                        "category": "Monthly Recurring Retainer",
                        "amount": 1850.0,
                        "currency": "CAD",
                        "billing_frequency": "monthly",
                        "description": "Full-cycle bookkeeping and monthly reconciliations.",
                        "is_placeholder": False
                    }
                ],
                "has_placeholders": False
            },
            "exclusions": [
                "Bookkeeping backlog: Any prior period bookkeeping clean-up will be quoted separately"
            ],
            "validation_metadata": {"passed": True}
        }

        rendered = self.renderer.render(compact_draft)

        # Dynamic page count: Cover, Exec Summary, Bookkeeping Detail, Pricing, Exclusions, Closing (6 pages)
        # MUST NOT include Why Us page or Timeline page
        page_types = [p.page_type for p in rendered.pages]
        assert PageType.WHY_US not in page_types, "Compact proposal must not include Why Us page when omitted from draft"
        assert PageType.TIMELINE not in page_types, "Compact proposal must not include Timeline page without transformation"
        assert PageType.COVER in page_types
        assert PageType.EXECUTIVE_SUMMARY in page_types
        assert PageType.PRICING in page_types
        assert PageType.EXCLUSIONS in page_types
        assert PageType.CLOSING in page_types
        assert rendered.page_count <= 7
        assert rendered.render_metadata["validation_results"]["passed"] is True

    # --------------------------------------------------------------------------
    # Test 2: Nonprofit rendering
    # --------------------------------------------------------------------------
    def test_02_nonprofit_rendering(self):
        """Validates nonprofit proposal rendering including dynamic Why Us credentials card."""
        nonprofit_draft = {
            "title": "Accounting & Financial Reporting Proposal for Evergreen Community Care",
            "executive_summary": "We provide funder-aligned financial reporting and operational bookkeeping.",
            "sections": [
                {
                    "section_title": "Accounting & Bookkeeping Services",
                    "opening_text": "We maintain daily ledger entries and monthly account reconciliations.",
                    "subsections": [
                        {
                            "heading": "Ledger Maintenance",
                            "bullets": ["Record accounts payable entries and reconcile bank statements"]
                        }
                    ]
                },
                {
                    "section_title": "Financial Reporting & Governance",
                    "opening_text": "We deliver monthly financial packages for board oversight.",
                    "subsections": [
                        {
                            "heading": "Funder & Board Reporting",
                            "bullets": ["Compile quarterly grant budget variance reports"]
                        }
                    ]
                }
            ],
            "why_us": [
                "Why Sympl?",
                "Non-profit and charity experience: We specialize in supporting organizations with mission-focused fund accounting.",
                "Dedicated, responsive team: Direct access to senior financial professionals."
            ],
            "pricing": {
                "pricing_model": "fixed_retainer",
                "currency": "CAD",
                "billing_schedule": "Monthly retainer invoiced on the 1st.",
                "fee_items": [
                    {
                        "category": "Monthly Retainer",
                        "amount": 2800.0,
                        "currency": "CAD",
                        "billing_frequency": "monthly",
                        "description": "Bookkeeping and fund reporting.",
                        "is_placeholder": False
                    }
                ],
                "has_placeholders": False
            },
            "exclusions": ["Note: Above costs do not include software subscription fees."],
            "validation_metadata": {"passed": True}
        }

        rendered = self.renderer.render(nonprofit_draft)

        page_types = [p.page_type for p in rendered.pages]
        assert PageType.WHY_US in page_types, "Nonprofit proposal with Why Us must generate Why Us page"
        why_page = next(p for p in rendered.pages if p.page_type == PageType.WHY_US)
        assert len(why_page.components) >= 2
        assert rendered.render_metadata["validation_results"]["passed"] is True

    # --------------------------------------------------------------------------
    # Test 3: Transformation rendering
    # --------------------------------------------------------------------------
    def test_03_transformation_rendering(self):
        """Validates systems transformation proposal generates implementation timeline roadmap."""
        transform_draft = {
            "title": "Digital Financial Transformation Proposal for Toronto Arts",
            "executive_summary": "Sympl Solutions leads modern cloud accounting migrations and workflow transformation.",
            "sections": [
                {
                    "section_title": "Part A: Digital Financial Systems Transformation",
                    "opening_text": "We migrate manual processes into automated cloud accounting software.",
                    "subsections": [
                        {
                            "heading": "Cloud Architecture & Integration",
                            "bullets": [
                                "Configure QuickBooks Online chart of accounts and vendor mapping",
                                "Integrate Dext expense ingestion and Wagepoint digital payroll"
                            ]
                        }
                    ]
                }
            ],
            "why_us": ["Technology and integration: Modern cloud tools create automated auditable workflows."],
            "pricing": {
                "pricing_model": "fixed_retainer",
                "currency": "CAD",
                "billing_schedule": "Retainer billed monthly; setup fee billed on kickoff.",
                "fee_items": [
                    {
                        "category": "System Setup Fee",
                        "amount": 1500.0,
                        "currency": "CAD",
                        "billing_frequency": "one_time",
                        "description": "Cloud onboarding and workflow configuration.",
                        "is_placeholder": False
                    }
                ],
                "has_placeholders": False
            },
            "exclusions": ["Note: Software fees not included."],
            "validation_metadata": {"passed": True}
        }

        rendered = self.renderer.render(transform_draft)

        page_types = [p.page_type for p in rendered.pages]
        assert PageType.TIMELINE in page_types, "Transformation proposal must dynamically generate Timeline Roadmap page"
        timeline_page = next(p for p in rendered.pages if p.page_type == PageType.TIMELINE)
        assert any("Phase 1" in item for comp in timeline_page.components for item in comp.items)
        assert rendered.render_metadata["validation_results"]["passed"] is True

    # --------------------------------------------------------------------------
    # Test 4: Pricing preservation
    # --------------------------------------------------------------------------
    def test_04_pricing_preservation(self):
        """Validates that fee values, categories, and placeholders are preserved with zero mutation."""
        pricing_draft = {
            "title": "Proposal for Client with Placeholder Pricing",
            "executive_summary": "Commercial schedule pending finalization.",
            "sections": [
                {
                    "section_title": "Bookkeeping Services",
                    "opening_text": "Core bookkeeping services.",
                    "subsections": [{"heading": "Services", "bullets": ["Manage general ledger"]}]
                }
            ],
            "why_us": [],
            "pricing": {
                "pricing_model": "placeholder",
                "currency": "CAD",
                "billing_schedule": "To be finalized upon agreement.",
                "fee_items": [
                    {
                        "category": "Monthly Bookkeeping Retainer",
                        "amount": None,
                        "currency": "CAD",
                        "placeholder_token": "[PRICING_PLACEHOLDER: Monthly Retainer Fee (CAD)]",
                        "billing_frequency": "monthly",
                        "description": "Fee schedule pending board confirmation.",
                        "is_placeholder": True
                    }
                ],
                "has_placeholders": True
            },
            "exclusions": [],
            "validation_metadata": {"passed": True}
        }

        rendered = self.renderer.render(pricing_draft)

        # Check pricing integrity
        errs = PricingIntegrityValidator.validate(rendered, pricing_draft)
        assert len(errs) == 0

        # Verify placeholder token is in table
        pricing_page = next(p for p in rendered.pages if p.page_type == PageType.PRICING)
        table_comp = next(c for c in pricing_page.components if c.component_type == ComponentType.TABLE)
        table_rows = table_comp.table_data.get("rows", [])
        assert any("[PRICING_PLACEHOLDER" in cell for row in table_rows for cell in row)

        # Test failure case: tamper with fee category
        tampered_draft = copy.deepcopy(pricing_draft)
        tampered_draft["pricing"]["fee_items"][0]["category"] = "Invented Advisory Surcharge"
        tampered_errs = PricingIntegrityValidator.validate(rendered, tampered_draft)
        assert len(tampered_errs) > 0

    # --------------------------------------------------------------------------
    # Test 5: Reference preservation
    # --------------------------------------------------------------------------
    def test_05_reference_preservation(self):
        """Validates that Why Us credentials and exclusions remain verbatim without alterations."""
        sample_why_block = "BIPOC and immigrant-led leadership with lived experiences in community, social service and arts & culture"
        sample_exclusion = "Bookkeeping backlog: Any prior period bookkeeping clean-up or catch-up work will be quoted separately based on the volume and complexity"

        draft = {
            "title": "Proposal with Reference Blocks",
            "executive_summary": "Executive summary text.",
            "sections": [
                {
                    "section_title": "Accounting Services",
                    "opening_text": "Operational accounting.",
                    "subsections": [{"heading": "Ledger", "bullets": ["Process bills"]}]
                }
            ],
            "why_us": [sample_why_block],
            "pricing": {"pricing_model": "fixed_retainer", "fee_items": []},
            "exclusions": [sample_exclusion],
            "validation_metadata": {"passed": True}
        }

        rendered = self.renderer.render(draft)

        ref_errs = ReferenceIntegrityValidator.validate(rendered, draft)
        assert len(ref_errs) == 0

        # Verify exact substring match
        rendered_text = ContentIntegrityValidator._extract_all_rendered_text(rendered)
        assert sample_why_block in rendered_text
        assert sample_exclusion in rendered_text

    # --------------------------------------------------------------------------
    # Test 6: Invalid draft rejection
    # --------------------------------------------------------------------------
    def test_06_invalid_draft_rejection(self):
        """Validates that malformed or incomplete proposal drafts are rejected immediately."""
        # Missing sections
        with pytest.raises(InvalidDraftError):
            self.renderer.render({
                "title": "Bad Draft",
                "executive_summary": "Missing sections key"
            })

        # Missing executive summary
        with pytest.raises(InvalidDraftError):
            self.renderer.render({
                "title": "Bad Draft",
                "sections": [],
                "pricing": {}
            })

        # Missing title
        with pytest.raises(InvalidDraftError):
            self.renderer.render({
                "executive_summary": "Valid summary",
                "sections": [],
                "why_us": [],
                "pricing": {},
                "exclusions": [],
                "validation_metadata": {}
            })

    # --------------------------------------------------------------------------
    # Test 7: Mock Canva rendering
    # --------------------------------------------------------------------------
    def test_07_mock_canva_rendering(self):
        """Validates MockCanvaClient creates design, populates pages, and returns simulated PDF URL."""
        mock_client = MockCanvaClient(template_id="custom_test_template")
        assert mock_client.is_mock is True

        design_resp = mock_client.create_design(title="Test Design", template_id="custom_test_template")
        assert design_resp["design_id"].startswith("canva_des_mock_")
        assert design_resp["template_id"] == "custom_test_template"

        pop_resp = mock_client.populate_design(
            design_id=design_resp["design_id"],
            pages_data=[{"page_number": 1, "title": "Page 1"}]
        )
        assert pop_resp["status"] == "populated"
        assert pop_resp["page_count"] == 1

        pdf_url = mock_client.export_pdf(design_id=design_resp["design_id"])
        assert pdf_url.endswith(".pdf")
        assert design_resp["design_id"] in pdf_url

    # --------------------------------------------------------------------------
    # Test 8: Database invariant verification
    # --------------------------------------------------------------------------
    def test_08_database_invariants_post_renderer(self):
        """
        Verifies that running the renderer layer made ZERO modifications to:
          - proposal_documents (7)
          - proposal_chunks (71)
          - dataset_imports (7)
          - sympl_style_rules (21)
          - sympl_reference_blocks (13)
          - embeddings (47)
        """
        import psycopg
        from sympl_planner.retrieval import DATABASE_URL

        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM proposal_documents;")
                docs_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM proposal_chunks;")
                chunks_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM dataset_imports;")
                imports_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM sympl_style_rules;")
                rules_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM sympl_reference_blocks;")
                refs_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM proposal_chunks WHERE embedding IS NOT NULL;")
                embedded_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM proposal_chunks WHERE retrieval_enabled = false AND embedding IS NOT NULL;")
                unsafe_embedded = cur.fetchone()[0]

        assert docs_count == 7, "proposal_documents must remain 7"
        assert chunks_count == 71, "proposal_chunks must remain 71"
        assert imports_count == 7, "dataset_imports must remain 7"
        assert rules_count == 21, "sympl_style_rules must remain 21"
        assert refs_count == 13, "sympl_reference_blocks must remain 13"
        assert embedded_count == 47, "embedded chunks must remain exactly 47"
        assert unsafe_embedded == 0, "unsafe embedded must remain 0"

    # --------------------------------------------------------------------------
    # Test 9: Output adapter verification
    # --------------------------------------------------------------------------
    def test_09_output_adapter_verification(self):
        """Validates JSON, Canva Payload, HTML/PDF, and Markdown adapters."""
        with open("proposal_draft.json", "r", encoding="utf-8") as f:
            draft_data = json.load(f)

        rendered = self.renderer.render(draft_data)

        # 1. JSON Adapter
        json_adapter = JsonOutputAdapter()
        json_str = json_adapter.adapt(rendered)
        parsed = json.loads(json_str)
        assert parsed["design_id"] == rendered.design_id
        assert parsed["page_count"] == rendered.page_count

        # 2. Canva Payload Adapter
        canva_adapter = CanvaPayloadAdapter()
        canva_payload = canva_adapter.adapt(rendered)
        assert "design_id" in canva_payload
        assert "pages" in canva_payload
        assert len(canva_payload["pages"]) == rendered.page_count

        # 3. HTML/PDF Adapter
        html_adapter = HtmlPdfAdapter()
        html_str = html_adapter.adapt(rendered)
        assert "<!DOCTYPE html>" in html_str
        assert rendered.title in html_str
        assert "page_1" in html_str

        # 4. Markdown Adapter
        md_adapter = MarkdownAdapter()
        md_str = md_adapter.adapt(rendered)
        assert f"# {rendered.title}" in md_str
        assert "## Page 1" in md_str

    # --------------------------------------------------------------------------
    # Test 10: Layout overflow handling
    # --------------------------------------------------------------------------
    def test_10_layout_overflow_handling(self):
        """Validates detection of layout overflow warnings and empty page errors."""
        # 1. Page with empty components
        empty_page = RenderPage(
            page_number=1,
            page_type="cover",
            page_title="Empty Page",
            components=[]
        )
        empty_proposal = RenderedProposal(
            design_id="test",
            title="Empty Doc",
            client_name="Client",
            page_count=1,
            pages=[empty_page]
        )
        errors, warnings = LayoutOverflowValidator.validate(empty_proposal)
        assert any("completely empty" in err for err in errors)

        # 2. Page with missing title
        untitled_page = RenderPage(
            page_number=1,
            page_type="cover",
            page_title="",  # Missing title!
            components=[RenderComponent(component_id="c1", component_type=ComponentType.PARAGRAPH, content="text")]
        )
        untitled_proposal = RenderedProposal(
            design_id="test",
            title="Untitled Page Doc",
            client_name="Client",
            page_count=1,
            pages=[untitled_page]
        )
        errors, warnings = LayoutOverflowValidator.validate(untitled_proposal)
        assert any("missing a page title" in err for err in errors)

        # 3. High bullet count capacity warning
        overflow_page = RenderPage(
            page_number=1,
            page_type="service_detail",
            page_title="High Density Page",
            components=[
                RenderComponent(
                    component_id="dense_list",
                    component_type=ComponentType.BULLET_LIST,
                    items=[f"Bullet point {i}" for i in range(15)]  # 15 bullets!
                )
            ],
            overflow_detected=True,
            capacity_metrics={"bullet_count": 15}
        )
        overflow_proposal = RenderedProposal(
            design_id="test",
            title="Dense Doc",
            client_name="Client",
            page_count=1,
            pages=[overflow_page]
        )
        errors, warnings = LayoutOverflowValidator.validate(overflow_proposal)
        assert any("exceeds maximum recommended bullet capacity" in err for err in errors)
        assert any("flagged for high content density" in warn for warn in warnings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
