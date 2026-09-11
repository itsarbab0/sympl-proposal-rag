"""
Sympl Solutions Proposal RAG — Multi-Service Retrieval Test Suite (unittest)

Validates Phase 1 Multi-Service Upgrades:
  1. Test 1: Bookkeeping proposal for nonprofit theatre -> 100% accounting chunks, zero web/data.
  2. Test 2: Website redesign proposal -> 100% website chunks (CRAWFORD), zero accounting.
  3. Test 3: Data analytics proposal -> 100% data chunks (AKM), zero accounting.
  4. Test 4: Technology / transformation proposal -> 100% transformation chunks (COMPASS), zero bookkeeping.
  5. Test 5: Bookkeeping regression verification against tests/fixtures/bookkeeping_regression_snapshot.json.
"""

import os
os.environ["HF_HUB_OFFLINE"] = "1"
import sys
import json
import unittest
from pathlib import Path
import psycopg

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sympl_planner.schema import (
    ClientInput,
    OrganizationInfo,
    EngagementContext,
    ScopeContainer,
    BookkeepingScope,
    PayrollScope,
    ReportingScope,
    ComplianceScope,
    GenericServiceScope,
    ApprovedCommercialInputs,
    Preferences
)
from sympl_planner.retrieval import ExemplarRetriever, DATABASE_URL
from sympl_planner.engine import ProposalPlanner


import time


class TestMultiServiceRetrieval(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.conn = None
        for attempt in range(5):
            try:
                cls.conn = psycopg.connect(DATABASE_URL, connect_timeout=10)
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(1.5)
        cls.planner = ProposalPlanner(conn=cls.conn)
        # Force reload corpus to guarantee newly ingested chunks and metadata are active
        ExemplarRetriever.get_corpus(cls.conn, force_reload=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn") and cls.conn:
            cls.conn.close()

    def test_1_bookkeeping_theatre_retrieval_isolation(self):
        """
        Test 1: Bookkeeping proposal for nonprofit theatre
        Must retrieve accounting proposals ONLY. Zero website or database chunks.
        """
        client_input = ClientInput(
            client_id="TEST_BK_THEATRE",
            organization=OrganizationInfo(
                name="Harbourfront Community Theatre",
                organization_type="nonprofit",
                sector="arts_culture",
                current_systems=["QuickBooks Online"]
            ),
            engagement=EngagementContext(engagement_type="recurring", complexity="standard"),
            requested_scope=ScopeContainer(),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="biweekly", ap_ar=True, reconciliations=True),
                financial_reporting=ReportingScope(cadence="monthly", board_package=True)
            ),
            commercial_terms=ApprovedCommercialInputs(pricing_model="fixed_retainer")
        )

        ctx_bk = ExemplarRetriever.attach_exemplars_to_section(
            conn=self.conn,
            service_family="bookkeeping",
            section_type="bookkeeping",
            target_archetype="ARCH_STANDARD_NONPROFIT",
            client_input=client_input
        )

        self.assertIsNotNone(ctx_bk)
        self.assertGreater(len(ctx_bk.exemplars), 0)

        for ex in ctx_bk.exemplars:
            # Must be strictly accounting proposals
            self.assertIn(
                ex.proposal_code,
                ["TACT_2026", "RPFF_2025", "CAHOOTS_2026", "YPT_2026", "PIRS_2025", "CAREOF_2025", "GOODFOOT_2026"],
                f"Unexpected proposal code in bookkeeping retrieval: {ex.proposal_code}"
            )
            self.assertNotIn("AKM", ex.proposal_code)
            self.assertNotIn("CRAWFORD", ex.proposal_code)
            self.assertNotIn("COMPASS", ex.proposal_code)

    def test_2_website_redesign_retrieval_isolation(self):
        """
        Test 2: Website redesign proposal
        Must retrieve website examples ONLY (CRAWFORD_2026). Zero bookkeeping chunks.
        """
        client_input = ClientInput(
            client_id="TEST_WEB_REDESIGN",
            organization=OrganizationInfo(
                name="Nexus Contemporary Gallery",
                organization_type="nonprofit",
                sector="arts_culture",
                service_category="Website Development"
            ),
            engagement=EngagementContext(engagement_type="fixed_term", complexity="standard"),
            requested_scope=ScopeContainer(),
            approved_scope=ScopeContainer(
                generic_services=[
                    GenericServiceScope(
                        service_category="Website Development",
                        service_name="Website Redesign & CMS Portfolio",
                        deliverables=["Mobile-responsive design", "CMS configuration", "Collector inquiry pathway"],
                        requirements=["Large format artwork photography", "SEO metadata tagging"]
                    )
                ]
            ),
            commercial_terms=ApprovedCommercialInputs(pricing_model="placeholder")
        )

        ctx_web = ExemplarRetriever.attach_exemplars_to_section(
            conn=self.conn,
            service_family="website_development",
            section_type="architecture",
            target_archetype="ARCH_STANDARD_NONPROFIT",
            client_input=client_input
        )

        self.assertIsNotNone(ctx_web)
        self.assertGreater(len(ctx_web.exemplars), 0)

        for ex in ctx_web.exemplars:
            self.assertEqual(
                ex.proposal_code,
                "CRAWFORD_2026",
                f"Website query retrieved non-website proposal: {ex.proposal_code}"
            )
            self.assertNotIn("TACT", ex.proposal_code)
            self.assertNotIn("PIRS", ex.proposal_code)
            self.assertNotIn("RPFF", ex.proposal_code)
            self.assertNotIn("CAHOOTS", ex.proposal_code)

    def test_3_data_analytics_discovery_retrieval_isolation(self):
        """
        Test 3: Data analytics discovery proposal
        Must retrieve data consulting examples ONLY (AKM_2026). Zero bookkeeping chunks.
        """
        client_input = ClientInput(
            client_id="TEST_DATA_ANALYTICS",
            organization=OrganizationInfo(
                name="Civic Heritage Foundation",
                organization_type="nonprofit",
                sector="museum",
                service_category="Data Analytics"
            ),
            engagement=EngagementContext(engagement_type="fixed_term", complexity="comprehensive"),
            requested_scope=ScopeContainer(),
            approved_scope=ScopeContainer(
                generic_services=[
                    GenericServiceScope(
                        service_category="Data Analytics",
                        service_name="Centralized Database & Cross-System Analytics",
                        deliverables=["SQL data warehouse architecture", "Automated ETL pipelines", "Executive BI dashboards"],
                        requirements=["AudienceView and Raiser's Edge data unification"]
                    )
                ]
            ),
            commercial_terms=ApprovedCommercialInputs(pricing_model="placeholder")
        )

        ctx_data = ExemplarRetriever.attach_exemplars_to_section(
            conn=self.conn,
            service_family="data_analytics",
            section_type="architecture",
            target_archetype="ARCH_COMPREHENSIVE_TRANSFORMATION",
            client_input=client_input
        )

        self.assertIsNotNone(ctx_data)
        self.assertGreater(len(ctx_data.exemplars), 0)

        for ex in ctx_data.exemplars:
            self.assertEqual(
                ex.proposal_code,
                "AKM_2026",
                f"Data analytics query retrieved non-data proposal: {ex.proposal_code}"
            )
            self.assertNotIn("TACT", ex.proposal_code)
            self.assertNotIn("RPFF", ex.proposal_code)

    def test_4_finance_transformation_retrieval_isolation(self):
        """
        Test 4: Finance transformation & forecasting proposal
        Must retrieve transformation consulting (COMPASS_2026). Zero operational bookkeeping.
        """
        client_input = ClientInput(
            client_id="TEST_FIN_TRANSFORMATION",
            organization=OrganizationInfo(
                name="Northern Health Alliance",
                organization_type="nonprofit",
                sector="health",
                service_category="Finance Transformation"
            ),
            engagement=EngagementContext(engagement_type="recurring", complexity="comprehensive"),
            requested_scope=ScopeContainer(),
            approved_scope=ScopeContainer(
                generic_services=[
                    GenericServiceScope(
                        service_category="Finance Transformation",
                        service_name="Multi-District Budget Process Revamp & Forecasting",
                        deliverables=["Dynamic financial forecasting model", "Rolling cash runways", "Board variance package"],
                        requirements=["Multi-funder grant allocation complexity"]
                    )
                ]
            ),
            commercial_terms=ApprovedCommercialInputs(pricing_model="placeholder")
        )

        ctx_trans = ExemplarRetriever.attach_exemplars_to_section(
            conn=self.conn,
            service_family="finance_transformation",
            section_type="architecture",
            target_archetype="ARCH_COMPREHENSIVE_TRANSFORMATION",
            client_input=client_input
        )

        self.assertIsNotNone(ctx_trans)
        self.assertGreater(len(ctx_trans.exemplars), 0)

        for ex in ctx_trans.exemplars:
            self.assertEqual(
                ex.proposal_code,
                "COMPASS_2026",
                f"Finance transformation retrieved non-transformation proposal: {ex.proposal_code}"
            )
            self.assertNotIn("TACT", ex.proposal_code)
            self.assertNotIn("CAHOOTS", ex.proposal_code)

    def test_5_bookkeeping_regression_against_snapshot(self):
        """
        Test 5: Verify that existing bookkeeping retrieval matches 100% of the regression snapshot.
        Candidate pool size, primary proposal codes, and section assignments must match.
        """
        snapshot_file = ROOT_DIR / "tests" / "fixtures" / "bookkeeping_regression_snapshot.json"
        self.assertTrue(snapshot_file.exists(), "Snapshot file missing!")

        with open(snapshot_file, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

        from scripts.create_bookkeeping_snapshot import BENCHMARK_PROFILES

        for profile in BENCHMARK_PROFILES:
            pid = profile["id"]
            arch = profile["archetype"]
            c_input = profile["client_input"]
            expected_sections = snapshot[pid]["sections"]

            for fam, sec_type in profile["families"]:
                exp_data = expected_sections.get(fam)
                if not exp_data:
                    continue

                ctx = ExemplarRetriever.attach_exemplars_to_section(
                    conn=self.conn,
                    service_family=fam,
                    section_type=sec_type,
                    target_archetype=arch,
                    client_input=c_input
                )

                self.assertIsNotNone(ctx, f"Retrieval returned None for {pid} - {fam}")
                self.assertEqual(
                    ctx.candidate_pool_size,
                    exp_data["candidate_pool_size"],
                    f"Candidate pool size mismatch for {pid} - {fam}"
                )

                actual_codes = [ex.proposal_code for ex in ctx.exemplars]
                expected_codes = [ex["proposal_code"] for ex in exp_data["exemplars"]]

                self.assertEqual(
                    actual_codes,
                    expected_codes,
                    f"Retrieved codes mismatch for {pid} - {fam}: actual {actual_codes} != expected {expected_codes}"
                )


if __name__ == "__main__":
    unittest.main()
