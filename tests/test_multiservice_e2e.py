"""
Sympl Solutions Proposal RAG — Multi-Service End-to-End Pipeline Test Suite

Validates complete lifecycle across all three new service categories:
  1. Website Development Proposal (API Intake -> Planner -> Retrieval -> Writer Input -> PDF Generation)
  2. Data Analytics Proposal     (API Intake -> Planner -> Retrieval -> Writer Input -> PDF Generation)
  3. Finance Transformation      (API Intake -> Planner -> Retrieval -> Writer Input -> PDF Generation)
  4. Ingestion Metadata Safety   (Strict rejection of unverified or incomplete metadata)

Proves:
  - Exact category-filtered retrieval isolation before pgvector search (zero cross-contamination).
  - Scope Firewall and Writer Input Contract integrity (zero unapproved scope leakage).
  - Clean ReportLab Platypus PDF compilation and page count verification.
"""

import os
os.environ["HF_HUB_OFFLINE"] = "1"
import sys
import io
import json
import time
import unittest
from pathlib import Path
import pypdf
import psycopg

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sympl_planner.schema import (
    ClientInput,
    OrganizationInfo,
    EngagementContext,
    ScopeContainer,
    GenericServiceScope,
    ApprovedCommercialInputs,
    Preferences
)
from sympl_planner.retrieval import DATABASE_URL, ExemplarRetriever
from sympl_planner.engine import ProposalPlanner
from sympl_api.services import OrchestrationService
from sympl_writer.schema import ProposalDraft, DraftSection, DraftSubsection
from sympl_renderer import ProposalRenderer
from sympl_renderer.pdf_generator import PdfGenerationService
from scripts.ingest_multiservice_proposals import validate_metadata_catalog


class TestMultiServiceEndToEnd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.conn = None
        for attempt in range(5):
            try:
                cls.conn = psycopg.connect(DATABASE_URL, sslmode="disable", connect_timeout=10)
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(1.5)

        cls.planner = ProposalPlanner(conn=cls.conn)
        cls.service = OrchestrationService()
        cls.renderer = ProposalRenderer()
        cls.pdf_service = PdfGenerationService()
        # Force reload corpus to guarantee newly ingested chunks and metadata are active
        ExemplarRetriever.get_corpus(cls.conn, force_reload=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn") and cls.conn and not cls.conn.closed:
            cls.conn.close()

    # -------------------------------------------------------------------------
    # Test 1: Website Development Proposal (End-to-End)
    # -------------------------------------------------------------------------
    def test_e2e_website_development_proposal(self):
        """
        API intake -> Planner -> Retrieval -> Writer input -> PDF generation
        Target: Website Development (Gary Crawford reference corpus)
        """
        intake_payload = {
            "client_name": "Gallery 44 Contemporary Visual Art",
            "organization_type": "nonprofit",
            "sector": "arts_culture",
            "service_category": "Website Development",
            "description": "Nonprofit contemporary visual arts centre with community gallery and artist facilities.",
            "approved_scope": {
                "generic_services": [
                    {
                        "service_category": "Website Development",
                        "service_name": "Website Redesign & CMS Architecture",
                        "deliverables": [
                            "Mobile-responsive portfolio showcase",
                            "Headless CMS setup for staff administration",
                            "Collector acquisition inquiry pathway"
                        ],
                        "requirements": ["High-res artwork photography", "SEO metadata tagging"],
                        "target_systems": ["Webflow", "Stripe", "Airtable"]
                    }
                ]
            },
            "commercial_terms": {
                "pricing_model": "fixed_retainer",
                "monthly_retainer": 3500.0,
                "setup_fee": 1200.0
            },
            "preferences": {
                "include_why_us": True
            }
        }

        # Step 1: API Intake
        client_input = self.service.parse_client_intake(intake_payload)
        self.assertEqual(client_input.organization.name, "Gallery 44 Contemporary Visual Art")
        self.assertEqual(len(client_input.approved_scope.generic_services), 1)
        self.assertEqual(client_input.approved_scope.generic_services[0].service_category, "Website Development")

        # Step 2: Planner & Retrieval
        plan = self.planner.plan(client_input)
        self.assertIsNotNone(plan)
        self.assertGreater(len(plan.sections), 0)

        # Verify Retrieval Isolation: strictly CRAWFORD_2026, zero accounting chunks
        arch_sec = next((s for s in plan.sections if s.section_type == "architecture"), None)
        self.assertIsNotNone(arch_sec, "Architecture section missing from Website plan")
        self.assertIsNotNone(arch_sec.retrieval_context)
        self.assertGreater(len(arch_sec.retrieval_context.exemplars), 0)

        for ex in arch_sec.retrieval_context.exemplars:
            self.assertEqual(ex.proposal_code, "CRAWFORD_2026")
            self.assertEqual(ex.service_category, "Website Development")
            self.assertNotIn("TACT", ex.proposal_code)
            self.assertNotIn("RPFF", ex.proposal_code)
            self.assertNotIn("CAHOOTS", ex.proposal_code)

        # Step 3: Writer Input Contract
        writer_input_str = plan.to_json(for_writer=True)
        writer_input = json.loads(writer_input_str)
        self.assertIn("client_context", writer_input)
        self.assertIn("sections", writer_input)
        self.assertNotIn("requested_scope", writer_input)
        self.assertNotIn("unapproved_requested_scope", writer_input)

        # Step 4: Draft Assembly
        draft_dict = {
            "title": f"Website Development Proposal for {client_input.organization.name}",
            "executive_summary": (
                f"Sympl Solutions is pleased to propose comprehensive website redesign services for {client_input.organization.name}. "
                "Our approach combines responsive mobile-first information architecture with intuitive content management workflows."
            ),
            "sections": [
                {
                    "section_title": s.section_title,
                    "opening_text": f"Sympl executes structured digital delivery tailored to {client_input.organization.name}'s mission.",
                    "subsections": [
                        {
                            "heading": "Technical Architecture & Design Strategy",
                            "bullets": [
                                "Develop clean mobile-first templates highlighting artist portfolios",
                                "Configure headless CMS architecture for autonomous administrative management",
                                "Implement streamlined inquiry pathways and visitor engagement analytics"
                            ]
                        },
                        {
                            "heading": "Deliverables & Verification",
                            "bullets": [
                                "Deliver fully responsive staging environment for stakeholder review",
                                "Provide staff user training guide and digital asset handover memo"
                            ]
                        }
                    ]
                }
                for s in plan.sections if s.structural_role in ("modular_service", "narrative_context")
            ],
            "why_us": [
                "Why Sympl?",
                "Extensive Arts & Nonprofit Digital Experience: Deep domain expertise designing responsive portfolio sites.",
                "Technology & Integration: Seamless configuration of modern CMS platforms and automated inquiry workflows.",
                "Dedicated Partnership: Direct communication and structured milestones throughout launch and cutover."
            ],
            "pricing": plan.commercial_summary,
            "exclusions": [
                "Domain renewal and third-party hosting subscription charges are billed directly to the client.",
                "Ongoing custom software engineering beyond the scoped deliverables will be quoted separately."
            ]
        }

        draft = ProposalDraft.from_dict(draft_dict)
        self.assertEqual(draft.title, "Website Development Proposal for Gallery 44 Contemporary Visual Art")

        # Step 5: Renderer & Vector PDF Generation
        rendered = self.renderer.render(draft.to_dict())
        self.assertIsNotNone(rendered)
        self.assertGreaterEqual(rendered.page_count, 4)

        pdf_bytes = self.pdf_service.generate_pdf(rendered)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Generated file is not a valid PDF")

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        self.assertEqual(len(reader.pages), rendered.page_count)
        self.assertGreater(len(reader.pages), 0)

    # -------------------------------------------------------------------------
    # Test 2: Data Analytics Proposal (End-to-End)
    # -------------------------------------------------------------------------
    def test_e2e_data_analytics_proposal(self):
        """
        API intake -> Planner -> Retrieval -> Writer input -> PDF generation
        Target: Data Analytics (Aga Khan Museum reference corpus)
        """
        intake_payload = {
            "client_name": "Metro Heritage Museum & Archive",
            "organization_type": "nonprofit",
            "sector": "museum",
            "service_category": "Data Analytics",
            "description": "Historical archive and cultural exhibition space integrating multi-system patron data.",
            "approved_scope": {
                "generic_services": [
                    {
                        "service_category": "Data Analytics",
                        "service_name": "Centralized Database & Cross-System Analytics",
                        "deliverables": [
                            "Centralized SQL data warehouse schema design",
                            "Automated ETL pipeline integrations across ticketing and donor CRM",
                            "Executive analytics dashboards and patron engagement insights"
                        ],
                        "requirements": ["AudienceView ticketing and Raiser's Edge CRM unification"],
                        "target_systems": ["PostgreSQL", "PowerBI", "Python ETL"]
                    }
                ]
            },
            "commercial_terms": {
                "pricing_model": "fixed_retainer",
                "monthly_retainer": 4200.0
            },
            "preferences": {
                "include_why_us": True
            }
        }

        # Step 1: API Intake
        client_input = self.service.parse_client_intake(intake_payload)
        self.assertEqual(client_input.organization.name, "Metro Heritage Museum & Archive")
        self.assertEqual(len(client_input.approved_scope.generic_services), 1)

        # Step 2: Planner & Retrieval
        plan = self.planner.plan(client_input)
        self.assertIsNotNone(plan)

        # Verify Retrieval Isolation: strictly AKM_2026, zero accounting chunks
        approach_sec = next((s for s in plan.sections if s.section_type == "architecture"), None)
        self.assertIsNotNone(approach_sec)
        self.assertIsNotNone(approach_sec.retrieval_context)
        self.assertGreater(len(approach_sec.retrieval_context.exemplars), 0)

        for ex in approach_sec.retrieval_context.exemplars:
            self.assertEqual(ex.proposal_code, "AKM_2026")
            self.assertEqual(ex.service_category, "Data Analytics")
            self.assertNotIn("TACT", ex.proposal_code)
            self.assertNotIn("PIRS", ex.proposal_code)

        # Step 3: Writer Input Contract
        writer_input = json.loads(plan.to_json(for_writer=True))
        self.assertNotIn("requested_scope", writer_input)

        # Step 4: Draft Assembly
        draft_dict = {
            "title": f"Data Analytics Discovery Proposal for {client_input.organization.name}",
            "executive_summary": (
                f"Sympl Solutions is pleased to propose centralized data architecture services for {client_input.organization.name}. "
                "We unify disparate ticketing, donor management, and exhibition databases into actionable leadership intelligence."
            ),
            "sections": [
                {
                    "section_title": s.section_title,
                    "opening_text": f"Sympl delivers structured data discovery and warehouse architecture for {client_input.organization.name}.",
                    "subsections": [
                        {
                            "heading": "Database Architecture & Systems Integration",
                            "bullets": [
                                "Design centralized relational warehouse schema linking patron interactions",
                                "Engineer automated data ingestion pipelines across ticketing and CRM platforms",
                                "Implement patron segmentation models and automated variance alerts"
                            ]
                        },
                        {
                            "heading": "Executive Dashboards & Reporting",
                            "bullets": [
                                "Deliver interactive executive intelligence dashboards for leadership oversight",
                                "Provide comprehensive data governance documentation and schema diagrams"
                            ]
                        }
                    ]
                }
                for s in plan.sections if s.structural_role in ("modular_service", "narrative_context")
            ],
            "why_us": [
                "Why Sympl?",
                "Museum and Cultural Sector Data Expertise: Track record architecting complex multi-platform analytics solutions.",
                "Disciplined Technical Governance: Scalable data schemas and automated pipelines built on open, robust platforms.",
                "Executive Intelligence: Translating raw operational records into actionable strategic insights."
            ],
            "pricing": plan.commercial_summary,
            "exclusions": [
                "External software database hosting fees are paid directly by the client.",
                "Direct API access to proprietary legacy systems is contingent upon vendor export access."
            ]
        }

        # Step 5: Renderer & PDF Generation
        draft = ProposalDraft.from_dict(draft_dict)
        rendered = self.renderer.render(draft.to_dict())
        self.assertGreaterEqual(rendered.page_count, 4)

        pdf_bytes = self.pdf_service.generate_pdf(rendered)
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        self.assertEqual(len(reader.pages), rendered.page_count)

    # -------------------------------------------------------------------------
    # Test 3: Finance Transformation Proposal (End-to-End)
    # -------------------------------------------------------------------------
    def test_e2e_finance_transformation_proposal(self):
        """
        API intake -> Planner -> Retrieval -> Writer input -> PDF generation
        Target: Finance Transformation (Compass reference corpus)
        """
        intake_payload = {
            "client_name": "Northern Health & Community Network",
            "organization_type": "nonprofit",
            "sector": "community_services",
            "service_category": "Finance Transformation",
            "description": "Multi-regional health service provider transitioning to strategic budgeting models.",
            "approved_scope": {
                "generic_services": [
                    {
                        "service_category": "Finance Transformation",
                        "service_name": "Multi-District Budget Process Revamp & Forecasting",
                        "deliverables": [
                            "Dynamic financial forecasting model with multi-district consolidation",
                            "Rolling 12-month cash runway projections",
                            "Executive variance reporting package for board governance"
                        ],
                        "requirements": ["Multi-funder grant tracking and ministry allocation matrix"],
                        "target_systems": ["Adaptive Insights", "Excel Financial Engine", "PowerBI"]
                    }
                ]
            },
            "commercial_terms": {
                "pricing_model": "fixed_retainer",
                "monthly_retainer": 5000.0
            },
            "preferences": {
                "include_why_us": True
            }
        }

        # Step 1: API Intake
        client_input = self.service.parse_client_intake(intake_payload)
        self.assertEqual(client_input.organization.name, "Northern Health & Community Network")

        # Step 2: Planner & Retrieval
        plan = self.planner.plan(client_input)
        self.assertIsNotNone(plan)

        # Verify Retrieval Isolation: strictly COMPASS_2026, zero operational bookkeeping chunks
        approach_sec = next((s for s in plan.sections if s.section_type == "architecture"), None)
        self.assertIsNotNone(approach_sec)
        self.assertIsNotNone(approach_sec.retrieval_context)
        self.assertGreater(len(approach_sec.retrieval_context.exemplars), 0)

        for ex in approach_sec.retrieval_context.exemplars:
            self.assertEqual(ex.proposal_code, "COMPASS_2026")
            self.assertEqual(ex.service_category, "Finance Transformation")
            self.assertNotIn("TACT", ex.proposal_code)
            self.assertNotIn("CAHOOTS", ex.proposal_code)

        # Step 3: Writer Input Contract
        writer_input = json.loads(plan.to_json(for_writer=True))
        self.assertNotIn("requested_scope", writer_input)

        # Step 4: Draft Assembly
        draft_dict = {
            "title": f"Finance Transformation Advisory Proposal for {client_input.organization.name}",
            "executive_summary": (
                f"Sympl Solutions is pleased to submit this proposal to support {client_input.organization.name} "
                "with modern financial forecasting models, structured budget process redesign, and board governance frameworks."
            ),
            "sections": [
                {
                    "section_title": s.section_title,
                    "opening_text": f"Sympl partners with leadership to engineer resilient financial models for {client_input.organization.name}.",
                    "subsections": [
                        {
                            "heading": "Budget Process Redesign & Dynamic Forecasting",
                            "bullets": [
                                "Engineer rolling 12-month dynamic financial forecasting models",
                                "Structure program-level variance analysis matrices for management oversight",
                                "Implement multi-district grant allocation formulas and funder tracking"
                            ]
                        },
                        {
                            "heading": "Board Governance & Advisory Reporting",
                            "bullets": [
                                "Establish standardized board financial presentation decks and key metrics",
                                "Conduct leadership walkthrough sessions and financial model training"
                            ]
                        }
                    ]
                }
                for s in plan.sections if s.structural_role in ("modular_service", "narrative_context")
            ],
            "why_us": [
                "Why Sympl?",
                "Complex Nonprofit Financial Transformation: Specialized experience guiding multi-program organizations through restructuring.",
                "Actionable Decision Modeling: Dynamic forecasting tools built for clarity and strategic planning.",
                "Governance Leadership: Trusted advisory support for finance committees and executive boards."
            ],
            "pricing": plan.commercial_summary,
            "exclusions": [
                "Internal payroll operations and day-to-day transaction processing are excluded from this advisory scope.",
                "External auditor attestation opinions must be issued by the designated auditing firm."
            ]
        }

        # Step 5: Renderer & PDF Generation
        draft = ProposalDraft.from_dict(draft_dict)
        rendered = self.renderer.render(draft.to_dict())
        self.assertGreaterEqual(rendered.page_count, 4)

        pdf_bytes = self.pdf_service.generate_pdf(rendered)
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        self.assertEqual(len(reader.pages), rendered.page_count)

    # -------------------------------------------------------------------------
    # Test 4: Ingestion Validation (Negative Testing)
    # -------------------------------------------------------------------------
    def test_ingestion_metadata_validation_negative_cases(self):
        """
        Validates that validate_metadata_catalog rejects invalid catalog entries:
          - Missing proposal_code
          - Missing service_category
          - Missing service_subcategory
          - verified_by_human is False or missing
        """
        # Case A: Missing proposal_code
        with self.assertRaises(ValueError) as cm:
            validate_metadata_catalog([{
                "proposal": "sample.pdf",
                "service_category": "Website Development",
                "service_subcategory": "CMS",
                "verified_by_human": True
            }])
        self.assertIn("missing required field 'proposal_code'", str(cm.exception))

        # Case B: Missing service_category
        with self.assertRaises(ValueError) as cm:
            validate_metadata_catalog([{
                "proposal_code": "TEST_001",
                "service_subcategory": "CMS",
                "verified_by_human": True
            }])
        self.assertIn("missing required field 'service_category'", str(cm.exception))

        # Case C: Missing service_subcategory
        with self.assertRaises(ValueError) as cm:
            validate_metadata_catalog([{
                "proposal_code": "TEST_001",
                "service_category": "Website Development",
                "verified_by_human": True
            }])
        self.assertIn("missing required field 'service_subcategory'", str(cm.exception))

        # Case D: verified_by_human is False
        with self.assertRaises(ValueError) as cm:
            validate_metadata_catalog([{
                "proposal_code": "TEST_001",
                "service_category": "Website Development",
                "service_subcategory": "CMS",
                "verified_by_human": False
            }])
        self.assertIn("'verified_by_human' must be explicitly true", str(cm.exception))

        # Case E: Empty string for service_category
        with self.assertRaises(ValueError) as cm:
            validate_metadata_catalog([{
                "proposal_code": "TEST_001",
                "service_category": "   ",
                "service_subcategory": "CMS",
                "verified_by_human": True
            }])
        self.assertIn("'service_category' must be a non-empty string", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
