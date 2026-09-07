"""
Sympl Solutions Proposal RAG — Long Proposal PDF Pagination & Overflow Regression Test Suite

Verifies:
  Test 1: 24 bullets in a single service section splits into two distinct pages with continuation headings,
          passes strict RenderValidator (<= 12 bullets per page), and produces a valid vector PDF.
  Test 2: Multiple large service sections (Bookkeeping 18 bullets, Payroll 14 bullets, Reporting 10 bullets)
          paginate cleanly with no layout overflow violations.
  Test 3: Single high-density subsection (20 bullets) cleanly splits into a 12 + 8 bullet distribution
          with continuation titles.
  Test 4: Direct PdfGenerationService draft dictionary rendering with oversized sections compiles
          safely with automatic pagination and no overflow exceptions.
"""

import io
from pathlib import Path
import pytest
import pypdf

from sympl_renderer.template_mapper import TemplateMapper
from sympl_renderer.renderer import ProposalRenderer
from sympl_renderer.validator import RenderValidator
from sympl_renderer.pdf_generator import PdfGenerationService
from sympl_renderer.schema import PageType


class TestPdfLongProposalPagination:
    """Regression test suite validating intelligent pagination and layout overflow prevention."""

    # --------------------------------------------------------------------------
    # Test 1: 24 Bullets in One Service Section
    # --------------------------------------------------------------------------
    def test_01_single_section_24_bullets_splits_and_validates(self):
        """
        Validates that a proposal draft containing 24 bullets in one section:
        1. Generates 2 service detail pages in TemplateMapper.
        2. Assigns continuation title '{Section Title} (continued)' to the second page.
        3. Maintains <= 12 bullets on each page, strictly satisfying RenderValidator.
        4. Compiles successfully via PdfGenerationService with correct running headers and footers.
        """
        draft = {
            "title": "Operational Accounting Services Proposal",
            "executive_summary": "Comprehensive financial management and bookkeeping support for community operations.",
            "sections": [
                {
                    "section_title": "Bookkeeping Services",
                    "opening_text": "Sympl Solutions will deliver end-to-end bookkeeping and general ledger operations.",
                    "subsections": [
                        {
                            "heading": "Accounts Payable & Receivable Operations",
                            "bullets": [f"AP/AR deliverable detail bullet point {i}" for i in range(1, 13)]  # 12 bullets
                        },
                        {
                            "heading": "Bank Reconciliations & Month-End Close",
                            "bullets": [f"Reconciliation operational procedure bullet {i}" for i in range(1, 13)]  # 12 bullets
                        }
                    ]
                }
            ],
            "why_us": [
                "Dedicated non-profit accounting practice lead.",
                "Cloud accounting platform expertise (QBO, Xero)."
            ],
            "pricing": {
                "fee_items": [
                    {"category": "Bookkeeping", "amount": 2800.0, "billing_frequency": "monthly"}
                ],
                "currency": "CAD",
                "billing_schedule": "Monthly retainer invoiced on the 1st of each service month."
            },
            "exclusions": ["Exclusion: Year-end external financial audit representation."],
            "validation_metadata": {"version": "1.0", "generator": "sympl_writer"}
        }

        # Step 1: Render and validate via full ProposalRenderer pipeline (raise_on_error=True)
        renderer = ProposalRenderer()
        rendered = renderer.render(draft)

        assert rendered is not None
        assert rendered.page_count >= 8

        # Step 2: Verify service detail pages are properly paginated
        service_pages = [p for p in rendered.pages if p.page_type == PageType.SERVICE_DETAIL]
        assert len(service_pages) == 2, f"Expected exactly 2 service detail pages, got {len(service_pages)}"

        page_1 = service_pages[0]
        page_2 = service_pages[1]

        # Verify page titles and subtitles
        assert page_1.page_title == "Bookkeeping Services"
        assert page_1.page_subtitle == "Deliverables & Procedures"
        assert page_2.page_title == "Bookkeeping Services (continued)"
        assert page_2.page_subtitle == "Deliverables & Procedures (continued)"

        # Verify bullet capacity on both pages (strictly <= 12)
        b1_count = page_1.capacity_metrics.get("bullet_count", 0)
        b2_count = page_2.capacity_metrics.get("bullet_count", 0)
        assert b1_count == 12, f"Expected 12 bullets on page 1, got {b1_count}"
        assert b2_count == 12, f"Expected 12 bullets on page 2, got {b2_count}"
        assert b1_count <= 12 and b2_count <= 12

        # Step 3: Validate with strict RenderValidator
        validator = RenderValidator(strict_mode=True)
        val_result = validator.validate(rendered, draft, raise_on_error=True)
        assert val_result.passed is True
        assert len(val_result.errors) == 0

        # Step 4: Compile PDF and verify physical pages & decorations
        pdf_service = PdfGenerationService()
        pdf_bytes = pdf_service.generate_pdf(rendered)

        assert len(pdf_bytes) > 2000
        assert pdf_bytes.startswith(b"%PDF-")

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == rendered.page_count

        # Check running headers and footers on both service pages
        p3_text = reader.pages[2].extract_text()
        p4_text = reader.pages[3].extract_text()

        assert "Bookkeeping Services" in p3_text
        assert "Bookkeeping Services (continued)" in p4_text
        assert f"Page 3 of {len(reader.pages)}" in p3_text
        assert f"Page 4 of {len(reader.pages)}" in p4_text

    # --------------------------------------------------------------------------
    # Test 2: Multiple Large Sections (18 + 14 + 10 Bullets)
    # --------------------------------------------------------------------------
    def test_02_multiple_large_sections_pagination(self):
        """
        Validates handling of multiple high-density service sections:
        - Bookkeeping: 18 bullets (splits into 12 + 6)
        - Payroll: 14 bullets (splits into 12 + 2)
        - Financial Reporting: 10 bullets (fits on 1 page <= 12)
        Total service detail pages: 2 + 2 + 1 = 5 pages.
        All pages must maintain <= 12 bullets with zero overflow errors.
        """
        draft = {
            "title": "Comprehensive Non-Profit Financial Services Proposal",
            "executive_summary": "Full spectrum accounting, payroll, and board financial reporting.",
            "sections": [
                {
                    "section_title": "Bookkeeping Services",
                    "opening_text": "Daily general ledger maintenance and accounts management.",
                    "subsections": [
                        {"heading": "Payables", "bullets": [f"Payable task {i}" for i in range(1, 10)]},
                        {"heading": "Receivables", "bullets": [f"Receivable task {i}" for i in range(1, 10)]}
                    ]  # Total 18 bullets
                },
                {
                    "section_title": "Payroll Services",
                    "opening_text": "Bi-weekly salaried and hourly payroll administration.",
                    "subsections": [
                        {"heading": "Payroll Processing", "bullets": [f"Payroll run task {i}" for i in range(1, 8)]},
                        {"heading": "Statutory Remittances", "bullets": [f"Tax remittance item {i}" for i in range(1, 8)]}
                    ]  # Total 14 bullets
                },
                {
                    "section_title": "Financial Reporting",
                    "opening_text": "Monthly and quarterly management package preparation.",
                    "subsections": [
                        {"heading": "Reporting Package", "bullets": [f"Report component {i}" for i in range(1, 11)]}
                    ]  # Total 10 bullets
                }
            ],
            "why_us": ["Over 10 years experience serving British Columbia non-profit organizations."],
            "pricing": {
                "fee_items": [
                    {"category": "Bookkeeping", "amount": 2500.0, "billing_frequency": "monthly"},
                    {"category": "Payroll", "amount": 800.0, "billing_frequency": "monthly"},
                    {"category": "Financial Reporting", "amount": 1200.0, "billing_frequency": "monthly"}
                ],
                "currency": "CAD"
            },
            "exclusions": ["Year-end audit preparation unless separately contracted."],
            "validation_metadata": {"version": "1.0", "generator": "sympl_writer"}
        }

        renderer = ProposalRenderer()
        rendered = renderer.render(draft)

        service_pages = [p for p in rendered.pages if p.page_type == PageType.SERVICE_DETAIL]
        # Bookkeeping (18 -> 2 pages), Payroll (14 -> 2 pages), Reporting (10 -> 1 page) = 5 pages
        assert len(service_pages) == 5

        # Verify no single page exceeds 12 bullets
        for sp in service_pages:
            b_count = sp.capacity_metrics.get("bullet_count", 0)
            assert b_count <= 12, f"Page {sp.page_number} has {b_count} bullets, exceeding 12 limit"

        # Verify titles include continuations for Bookkeeping and Payroll
        titles = [sp.page_title for sp in service_pages]
        assert "Bookkeeping Services" in titles
        assert "Bookkeeping Services (continued)" in titles
        assert "Payroll Services" in titles
        assert "Payroll Services (continued)" in titles
        assert "Financial Reporting" in titles

        # Verify PDF compiles cleanly
        pdf_service = PdfGenerationService()
        pdf_bytes = pdf_service.generate_pdf(rendered)
        assert len(pdf_bytes) > 2000

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == rendered.page_count

    # --------------------------------------------------------------------------
    # Test 3: Single Subsection with 20 Bullets (12 + 8 Split)
    # --------------------------------------------------------------------------
    def test_03_single_subsection_20_bullets_split(self):
        """
        Validates that an individual subsection containing 20 bullets (exceeding page capacity alone)
        is split cleanly into 12 bullets on page 1 and 8 bullets on page 2,
        with subsection continuation title '{Heading} (continued)'.
        """
        draft = {
            "title": "Deep Operational Scope Proposal",
            "executive_summary": "In-depth functional bookkeeping scope.",
            "sections": [
                {
                    "section_title": "Full Ledger Operations",
                    "opening_text": "Detailed operational accounting procedures.",
                    "subsections": [
                        {
                            "heading": "General Ledger Maintenance",
                            "bullets": [f"Operational activity number {i:02d} for ledger reconciliation" for i in range(1, 21)]
                        }
                    ]  # 20 bullets in single subsection
                }
            ],
            "why_us": ["Expertise in operational workflow design."],
            "pricing": {
                "fee_items": [{"category": "Ledger Maintenance", "amount": 3200.0, "billing_frequency": "monthly"}],
                "currency": "CAD"
            },
            "exclusions": ["Exclusion: Legal entity restructuring."],
            "validation_metadata": {"version": "1.0", "generator": "sympl_writer"}
        }

        renderer = ProposalRenderer()
        rendered = renderer.render(draft)

        service_pages = [p for p in rendered.pages if p.page_type == PageType.SERVICE_DETAIL]
        assert len(service_pages) == 2

        p1, p2 = service_pages[0], service_pages[1]
        assert p1.capacity_metrics["bullet_count"] == 12
        assert p2.capacity_metrics["bullet_count"] == 8

        # Verify component titles and items
        p1_list_comp = [c for c in p1.components if c.component_type == "bullet_list"][0]
        p2_list_comp = [c for c in p2.components if c.component_type == "bullet_list"][0]

        assert p1_list_comp.title == "General Ledger Maintenance"
        assert len(p1_list_comp.items) == 12
        assert p2_list_comp.title == "General Ledger Maintenance (continued)"
        assert len(p2_list_comp.items) == 8

        # Compile PDF and verify physical output
        pdf_bytes = PdfGenerationService().generate_pdf(rendered)
        assert len(pdf_bytes) > 2000

    # --------------------------------------------------------------------------
    # Test 4: Direct PdfGenerationService Draft Dictionary Rendering
    # --------------------------------------------------------------------------
    def test_04_direct_pdf_service_draft_rendering(self):
        """
        Validates that when a raw draft dictionary (without a pre-mapped pages array)
        is passed directly to PdfGenerationService.generate_pdf(draft_dict),
        the internal fallback engine paginates bullets in groups of <= 12 and generates a valid PDF.
        """
        draft_dict = {
            "title": "Direct PDF Generation Test",
            "client_name": "Direct Client Corp",
            "executive_summary": "Direct executive summary statement.",
            "sections": [
                {
                    "section_title": "Direct Bookkeeping",
                    "opening_text": "Direct section description.",
                    "subsections": [
                        {
                            "heading": "Direct Sub 1",
                            "bullets": [f"Direct bullet point {i}" for i in range(1, 26)]  # 25 bullets
                        }
                    ]
                }
            ],
            "why_us": ["Direct service approach."],
            "pricing": {
                "fee_items": [{"category": "Direct Fee", "amount": 1500.0, "billing_frequency": "monthly"}],
                "currency": "CAD"
            },
            "exclusions": ["Direct exclusion."],
            "validation_metadata": {"version": "1.0"}
        }

        pdf_service = PdfGenerationService()
        pdf_bytes = pdf_service.generate_pdf(draft_dict)

        assert len(pdf_bytes) > 2000
        assert pdf_bytes.startswith(b"%PDF-")

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 5

        # Verify continuation header appears in PDF stream
        full_text = " ".join(page.extract_text() for page in reader.pages)
        assert "Direct Bookkeeping (continued)" in full_text
        assert "Direct bullet point 25" in full_text
