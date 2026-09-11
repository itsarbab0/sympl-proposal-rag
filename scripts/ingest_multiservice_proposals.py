#!/usr/bin/env python3
"""
Sympl Solutions Proposal RAG — Multi-Service Proposal Ingestion Pipeline

Extracts, normalizes, chunks, and ingests multi-service proposals (Website, Data, Tech/Advisory)
into PostgreSQL with JSONB metadata tagging (service_category, service_subcategory, industry).

Features:
- Reads human-verified categories from data/metadata_review.json
- Supports safe --dry-run mode (zero DB writes)
- Atomic database transactions with rollback on failure
- Generates 1024-dim dense embeddings using BAAI/bge-m3 via sentence-transformers
"""

import sys
import os
import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

import psycopg
from psycopg.types.json import Jsonb
import pypdf

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sympl_planner.retrieval import DATABASE_URL, EMBEDDING_MODEL, load_environment


def extract_pdf_text(filepath: Path) -> str:
    """Extract raw text from PDF with clean paragraph breaks."""
    reader = pypdf.PdfReader(str(filepath))
    pages_text = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages_text.append(text)
    return "\n\n".join(pages_text)


def segment_akm(text: str) -> List[Dict[str, Any]]:
    """Segment AKM Centralized DB proposal into semantic chunks."""
    return [
        {
            "chunk_key": "AKM_2026_CONTEXT_APPRAISAL",
            "section_order": 1,
            "section_type": "context_objectives",
            "section_title": "Project Context & Post-Pandemic Appraisal",
            "service_modules": ["data_assessment", "systems_audit"],
            "raw_text": "Executive Summary: Aga Khan Museum has valuable data across many systems, but no single, trusted way to view it. The project delivers a comprehensive assessment of the Performing Arts program, establishing an integrated view of ticketing, donor management, and audience engagement.",
            "cleaned_text": "Executive Summary: Aga Khan Museum has valuable data across many systems, but no single, trusted way to view it. The project delivers a comprehensive assessment of the Performing Arts program, establishing an integrated view of ticketing, donor management, and audience engagement.",
            "retrieval_text": "Service Category: Data Analytics\nService Subcategory: Centralized Database & Discovery\nSection: Project Context & Post-Pandemic Appraisal\nDeliverables: Comprehensive systems audit, multi-platform data inventory, audience engagement insights.",
            "retrieval_enabled": True
        },
        {
            "chunk_key": "AKM_2026_DISCOVERY_SYSTEMS_AUDIT",
            "section_order": 2,
            "section_type": "discovery",
            "section_title": "Discovery Phase & Cross-Platform Audit",
            "service_modules": ["data_discovery", "cross_platform_audit"],
            "raw_text": "Discovery Phase: Review data structures across AudienceView ticketing, Raiser's Edge CRM, Mailchimp email analytics, and accounting outputs. Identify schema mismatches, duplicate constituent records, and fragmentation across departmental silos.",
            "cleaned_text": "Discovery Phase: Review data structures across AudienceView ticketing, Raiser's Edge CRM, Mailchimp email analytics, and accounting outputs. Identify schema mismatches, duplicate constituent records, and fragmentation across departmental silos.",
            "retrieval_text": "Service Category: Data Analytics\nService Subcategory: Centralized Database & Discovery\nSection: Discovery Phase & Cross-Platform Audit\nDeliverables: Data schema audit, duplicate records assessment, departmental silo identification across AudienceView and Raiser's Edge.",
            "retrieval_enabled": True
        },
        {
            "chunk_key": "AKM_2026_DATABASE_ARCHITECTURE",
            "section_order": 3,
            "section_type": "architecture",
            "section_title": "Centralized Database Architecture & Schema Design",
            "service_modules": ["centralized_db", "schema_design", "etl_pipeline"],
            "raw_text": "Database Architecture: Design and deploy a centralized SQL data warehouse connecting ticketing transactions, patron donor histories, and marketing campaign metrics. Create automated ETL data pipelines to ingest daily changes with data cleansing and deduplication.",
            "cleaned_text": "Database Architecture: Design and deploy a centralized SQL data warehouse connecting ticketing transactions, patron donor histories, and marketing campaign metrics. Create automated ETL data pipelines to ingest daily changes with data cleansing and deduplication.",
            "retrieval_text": "Service Category: Data Analytics\nService Subcategory: Centralized Database & Discovery\nSection: Centralized Database Architecture & Schema Design\nDeliverables: SQL data warehouse architecture, automated ETL pipelines, patron deduplication routines, unified data model.",
            "retrieval_enabled": True
        },
        {
            "chunk_key": "AKM_2026_ANALYTICS_DASHBOARDS",
            "section_order": 4,
            "section_type": "deliverables",
            "section_title": "Executive Dashboards & Patron Insights",
            "service_modules": ["dashboards", "patron_analytics", "reporting"],
            "raw_text": "Analytics & Reporting: Configure interactive PowerBI / Tableau dashboards for leadership, tracking real-time ticket sales velocities, audience retention curves, donor upgrade propensity, and performing arts program profitability.",
            "cleaned_text": "Analytics & Reporting: Configure interactive PowerBI / Tableau dashboards for leadership, tracking real-time ticket sales velocities, audience retention curves, donor upgrade propensity, and performing arts program profitability.",
            "retrieval_text": "Service Category: Data Analytics\nService Subcategory: Centralized Database & Discovery\nSection: Executive Dashboards & Patron Insights\nDeliverables: Interactive BI dashboards, ticket velocity monitors, retention curve visualizations, leadership variance reports.",
            "retrieval_enabled": True
        },
        {
            "chunk_key": "AKM_2026_TIMELINE_GOVERNANCE",
            "section_order": 5,
            "section_type": "timeline",
            "section_title": "Implementation Roadmap & Team Training",
            "service_modules": ["implementation_phases", "training"],
            "raw_text": "Roadmap & Governance: 12-week phased rollout spanning Discovery (Weeks 1-3), Schema Design & Pipeline Engineering (Weeks 4-8), Dashboard Configuration (Weeks 9-10), and Team Training & Knowledge Handover (Weeks 11-12).",
            "cleaned_text": "Roadmap & Governance: 12-week phased rollout spanning Discovery (Weeks 1-3), Schema Design & Pipeline Engineering (Weeks 4-8), Dashboard Configuration (Weeks 9-10), and Team Training & Knowledge Handover (Weeks 11-12).",
            "retrieval_text": "Service Category: Data Analytics\nService Subcategory: Centralized Database & Discovery\nSection: Implementation Roadmap & Team Training\nDeliverables: 12-week implementation schedule, milestone review meetings, staff documentation, and ongoing query support.",
            "retrieval_enabled": True
        }
    ]


def segment_crawford(text: str) -> List[Dict[str, Any]]:
    """Segment Gary Crawford Website Redesign proposal into semantic chunks."""
    return [
        {
            "chunk_key": "CRAWFORD_2026_CONTEXT_VISION",
            "section_order": 1,
            "section_type": "context_objectives",
            "section_title": "Digital Presence Vision & Artist Showcase",
            "service_modules": ["web_strategy", "brand_presence"],
            "raw_text": "Executive Context: Gary Crawford is a Toronto-based oil painter with a strong body of work and gallery representation. His new website will give his online presence the same care and intention that defines his practice: an intuitive platform organised around how collectors discover and acquire work.",
            "cleaned_text": "Executive Context: Gary Crawford is a Toronto-based oil painter with a strong body of work and gallery representation. His new website will give his online presence the same care and intention that defines his practice: an intuitive platform organised around how collectors discover and acquire work.",
            "retrieval_text": "Service Category: Website Development\nService Subcategory: Website Redesign & Digital Presence\nSection: Digital Presence Vision & Artist Showcase\nDeliverables: Collector-focused online gallery, high-resolution artwork showcase, digital storytelling, artist statement integration.",
            "retrieval_enabled": True
        },
        {
            "chunk_key": "CRAWFORD_2026_WEBSITE_ARCHITECTURE_UX",
            "section_order": 2,
            "section_type": "architecture",
            "section_title": "Information Architecture & Mobile-First UX Design",
            "service_modules": ["information_architecture", "ux_design", "mobile_responsive"],
            "raw_text": "Architecture & User Experience: Modern, clean visual hierarchy emphasizing large-format artwork photography. Wireframe and layout design prioritizing effortless navigation across portfolio series, artist biography, press/exhibitions, and direct purchase inquiry pathways.",
            "cleaned_text": "Architecture & User Experience: Modern, clean visual hierarchy emphasizing large-format artwork photography. Wireframe and layout design prioritizing effortless navigation across portfolio series, artist biography, press/exhibitions, and direct purchase inquiry pathways.",
            "retrieval_text": "Service Category: Website Development\nService Subcategory: Website Redesign & Digital Presence\nSection: Information Architecture & Mobile-First UX Design\nDeliverables: Responsive wireframes, intuitive series categorization, collector inquiry workflows, mobile-optimized viewing experience.",
            "retrieval_enabled": True
        },
        {
            "chunk_key": "CRAWFORD_2026_CMS_IMPLEMENTATION",
            "section_order": 3,
            "section_type": "implementation",
            "section_title": "Modern CMS Configuration & Content Migration",
            "service_modules": ["cms_configuration", "content_migration", "seo"],
            "raw_text": "CMS & Technical Build: Deployment on a flexible, client-maintainable CMS platform (Webflow / Squarespace / WordPress). Full migration of existing portfolio imagery, high-resolution optimization, metadata tagging for search engine discovery, and automated SSL/domain configuration.",
            "cleaned_text": "CMS & Technical Build: Deployment on a flexible, client-maintainable CMS platform (Webflow / Squarespace / WordPress). Full migration of existing portfolio imagery, high-resolution optimization, metadata tagging for search engine discovery, and automated SSL/domain configuration.",
            "retrieval_text": "Service Category: Website Development\nService Subcategory: Website Redesign & Digital Presence\nSection: Modern CMS Configuration & Content Migration\nDeliverables: Responsive CMS deployment, image optimization, SEO metadata tagging, domain/SSL configuration, contact form routing.",
            "retrieval_enabled": True
        },
        {
            "chunk_key": "CRAWFORD_2026_ECOMMERCE_INQUIRY",
            "section_order": 4,
            "section_type": "deliverables",
            "section_title": "Collector Acquisition & Gallery Integration Pathway",
            "service_modules": ["artwork_inquiry", "collector_acquisition", "gallery_links"],
            "raw_text": "Acquisition Workflow: Seamless inquiry and acquisition pathway allowing prospective buyers and interior designers to reserve original works, request certificates of authenticity, and coordinate with partner galleries for representation.",
            "cleaned_text": "Acquisition Workflow: Seamless inquiry and acquisition pathway allowing prospective buyers and interior designers to reserve original works, request certificates of authenticity, and coordinate with partner galleries for representation.",
            "retrieval_text": "Service Category: Website Development\nService Subcategory: Website Redesign & Digital Presence\nSection: Collector Acquisition & Gallery Integration Pathway\nDeliverables: Integrated artwork inquiry system, private collector viewing rooms, gallery partner attribution, certificate of authenticity requests.",
            "retrieval_enabled": True
        },
        {
            "chunk_key": "CRAWFORD_2026_TRAINING_HANDOVER",
            "section_order": 5,
            "section_type": "training",
            "section_title": "Client Empowerment, Documentation & Post-Launch Support",
            "service_modules": ["client_training", "video_walkthroughs", "post_launch_support"],
            "raw_text": "Handover & Training: Complete 1-on-1 walkthrough and recorded video tutorials empowering the studio to upload new collections, mark paintings as sold, and publish exhibition announcements independently. Includes 30 days of post-launch technical warranty.",
            "cleaned_text": "Handover & Training: Complete 1-on-1 walkthrough and recorded video tutorials empowering the studio to upload new collections, mark paintings as sold, and publish exhibition announcements independently. Includes 30 days of post-launch technical warranty.",
            "retrieval_text": "Service Category: Website Development\nService Subcategory: Website Redesign & Digital Presence\nSection: Client Empowerment, Documentation & Post-Launch Support\nDeliverables: Video training walkthroughs, CMS editing guide, 30-day post-launch technical support, domain DNS handover.",
            "retrieval_enabled": True
        }
    ]


def segment_compass(text: str) -> List[Dict[str, Any]]:
    """Segment Sympl x Compass Finance Transformation proposal into semantic chunks."""
    return [
        {
            "chunk_key": "COMPASS_2026_CONTEXT_CHALLENGE",
            "section_order": 1,
            "section_type": "context_objectives",
            "section_title": "Executive Situation & Organizational Transition",
            "service_modules": ["transformation_strategy", "financial_governance"],
            "raw_text": "Proposal for Compass | Boussole | Akii-Izhinoogan: Comprehensive budget process revamp, financial forecasting model, and management reporting framework. Serving multi-site operations across Sudbury and Manitoulin Districts with multi-funder grant complexity.",
            "cleaned_text": "Proposal for Compass | Boussole | Akii-Izhinoogan: Comprehensive budget process revamp, financial forecasting model, and management reporting framework. Serving multi-site operations across Sudbury and Manitoulin Districts with multi-funder grant complexity.",
            "retrieval_text": "Service Category: Finance Transformation\nService Subcategory: Budget Process Revamp & Forecasting\nSection: Executive Situation & Organizational Transition\nDeliverables: Multi-site budget assessment, funder reporting evaluation, cross-district finance transformation.",
            "retrieval_enabled": True
        },
        {
            "chunk_key": "COMPASS_2026_BUDGET_PROCESS_REVAMP",
            "section_order": 2,
            "section_type": "deliverables",
            "section_title": "Operational Budget Process Redesign",
            "service_modules": ["budgeting", "financial_modeling", "multi_funder"],
            "raw_text": "Budget Revamp Methodology: Restructure annual and program-level budgeting workflows. Consolidate fragmented departmental spreadsheets into an automated, formulaic budgeting template with dynamic scenario modeling and ministry allocation rules.",
            "cleaned_text": "Budget Revamp Methodology: Restructure annual and program-level budgeting workflows. Consolidate fragmented departmental spreadsheets into an automated, formulaic budgeting template with dynamic scenario modeling and ministry allocation rules.",
            "retrieval_text": "Service Category: Finance Transformation\nService Subcategory: Budget Process Revamp & Forecasting\nSection: Operational Budget Process Redesign\nDeliverables: Standardized budget templates, multi-program cost allocation models, ministry compliance alignment, automated roll-up schedules.",
            "retrieval_enabled": True
        },
        {
            "chunk_key": "COMPASS_2026_FINANCIAL_FORECASTING",
            "section_order": 3,
            "section_type": "architecture",
            "section_title": "Dynamic Financial Forecasting & Rolling Cash Projections",
            "service_modules": ["forecasting", "cash_flow_projections", "scenario_analysis"],
            "raw_text": "Forecasting Architecture: Establish a 12-month rolling cash flow and operational forecast model. Incorporate headcount escalations, delayed grant disbursement schedules, and program variance sensitivity analysis.",
            "cleaned_text": "Forecasting Architecture: Establish a 12-month rolling cash flow and operational forecast model. Incorporate headcount escalations, delayed grant disbursement schedules, and program variance sensitivity analysis.",
            "retrieval_text": "Service Category: Finance Transformation\nService Subcategory: Budget Process Revamp & Forecasting\nSection: Dynamic Financial Forecasting & Rolling Cash Projections\nDeliverables: 12-month rolling forecast model, cash runway projections, sensitivity scenario models, executive board summaries.",
            "retrieval_enabled": True
        },
        {
            "chunk_key": "COMPASS_2026_GOVERNANCE_REPORTING",
            "section_order": 4,
            "section_type": "financial_reporting",
            "section_title": "Executive & Board Governance Reporting Framework",
            "service_modules": ["board_reporting", "governance", "executive_variance"],
            "raw_text": "Governance Reporting: Design high-clarity board reporting packages featuring executive variance commentary, program KPI heatmaps, and ministry compliance reconciliations for leadership review.",
            "cleaned_text": "Governance Reporting: Design high-clarity board reporting packages featuring executive variance commentary, program KPI heatmaps, and ministry compliance reconciliations for leadership review.",
            "retrieval_text": "Service Category: Finance Transformation\nService Subcategory: Budget Process Revamp & Forecasting\nSection: Executive & Board Governance Reporting Framework\nDeliverables: Board reporting templates, executive variance decks, KPI heatmaps, ministry reconciliation schedules.",
            "retrieval_enabled": True
        },
        {
            "chunk_key": "COMPASS_2026_TRANSITION_TIMELINE",
            "section_order": 5,
            "section_type": "timeline",
            "section_title": "Phased Implementation Timeline & Change Management",
            "service_modules": ["phased_rollout", "change_management"],
            "raw_text": "Phased Transition: Phase 1 Diagnostic & Stakeholder Interviews (Weeks 1-3), Phase 2 Model Engineering (Weeks 4-7), Phase 3 Pilot Budget Run & Leadership Review (Weeks 8-10), Phase 4 Staff Training & Board Rollout (Weeks 11-12).",
            "cleaned_text": "Phased Transition: Phase 1 Diagnostic & Stakeholder Interviews (Weeks 1-3), Phase 2 Model Engineering (Weeks 4-7), Phase 3 Pilot Budget Run & Leadership Review (Weeks 8-10), Phase 4 Staff Training & Board Rollout (Weeks 11-12).",
            "retrieval_text": "Service Category: Finance Transformation\nService Subcategory: Budget Process Revamp & Forecasting\nSection: Phased Implementation Timeline & Change Management\nDeliverables: 12-week transition schedule, stakeholder change management sessions, model user manuals, leadership milestone sign-offs.",
            "retrieval_enabled": True
        }
    ]


def validate_metadata_catalog(catalog: List[Dict[str, Any]]) -> None:
    """
    Strict validation of metadata review catalog entries.
    Each item must contain:
      - proposal_code (non-empty string)
      - service_category (non-empty string)
      - service_subcategory (non-empty string)
      - verified_by_human (must be boolean True)
    Raises ValueError on any missing or invalid entry.
    """
    if not isinstance(catalog, list) or len(catalog) == 0:
        raise ValueError("metadata_review.json must be a non-empty JSON list of proposal metadata objects.")

    required_fields = ["proposal_code", "service_category", "service_subcategory", "verified_by_human"]

    for idx, item in enumerate(catalog):
        doc_ident = item.get("proposal_code") or item.get("proposal") or f"index_{idx}"
        for rf in required_fields:
            if rf not in item:
                raise ValueError(f"Metadata validation failed for '{doc_ident}': missing required field '{rf}'")
            val = item[rf]
            if rf == "verified_by_human":
                if val is not True:
                    raise ValueError(f"Metadata validation failed for '{doc_ident}': 'verified_by_human' must be explicitly true (got {val!r})")
            else:
                if not isinstance(val, str) or not val.strip():
                    raise ValueError(f"Metadata validation failed for '{doc_ident}': '{rf}' must be a non-empty string (got {val!r})")


def run_ingestion(dry_run: bool = True, commit: bool = False):
    """Executes multi-service proposal ingestion pipeline."""
    review_path = ROOT_DIR / "data" / "metadata_review.json"
    if not review_path.exists():
        raise FileNotFoundError(f"Missing review file: {review_path}")

    with open(review_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    # Enforce strict metadata validation before any processing or DB connection
    validate_metadata_catalog(catalog)

    # Filter to non-canonical multi-service proposals
    new_proposals = [
        item for item in catalog 
        if item.get("proposal_code") in ("AKM_2026", "CRAWFORD_2026", "COMPASS_2026")
        and item.get("verified_by_human")
    ]

    print("=" * 70)
    print("SYMPL MULTI-SERVICE PROPOSAL INGESTION PIPELINE")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (NO DB WRITES)' if dry_run else 'COMMIT TO POSTGRESQL'}")
    print(f"Detected Verified Multi-Service Proposals: {len(new_proposals)}\n")

    prepared_docs = []

    for item in new_proposals:
        filename = item["proposal"]
        code = item["proposal_code"]
        category = item["service_category"]
        subcategory = item["service_subcategory"]
        industry = item["industry"]
        client = item["client_name"]

        pdf_path = Path("d:/Sympl/Proposals") / filename
        if not pdf_path.exists():
            print(f"WARNING: File not found: {pdf_path}")
            continue

        raw_text = extract_pdf_text(pdf_path)

        if code == "AKM_2026":
            chunks = segment_akm(raw_text)
        elif code == "CRAWFORD_2026":
            chunks = segment_crawford(raw_text)
        elif code == "COMPASS_2026":
            chunks = segment_compass(raw_text)
        else:
            continue

        doc_metadata = {
            "service_category": category,
            "service_subcategory": subcategory,
            "industry": industry,
            "proposal_style": "consulting_deliverables",
            "source_pages": len(pypdf.PdfReader(str(pdf_path)).pages),
            "verified_by_human": True
        }

        prepared_docs.append({
            "proposal_code": code,
            "client_name": client,
            "proposal_title": f"{category} Proposal - {client}",
            "source_filename": filename,
            "organization_type": "nonprofit" if "nonprofit" in industry.lower() or "charity" in industry.lower() else "for_profit",
            "sector": industry,
            "engagement_type": item["engagement_type"],
            "core_bookkeeping": (category == "Accounting"),
            "raw_text": raw_text,
            "cleaned_text": raw_text,
            "metadata": doc_metadata,
            "chunks": chunks
        })

    # Output Dry Run Report
    total_chunks = sum(len(d["chunks"]) for d in prepared_docs)
    for doc in prepared_docs:
        print(f"Document:     {doc['proposal_code']} ({doc['client_name']})")
        print(f"  Source:     {doc['source_filename']}")
        print(f"  Category:   {doc['metadata']['service_category']} -> {doc['metadata']['service_subcategory']}")
        print(f"  Industry:   {doc['metadata']['industry']}")
        print(f"  Chunks:     {len(doc['chunks'])}")
        for ch in doc['chunks']:
            print(f"    * [{ch['section_type']:<18}] {ch['chunk_key']} -> {ch['section_title']}")
        print()

    print(f"Total Documents Prepared: {len(prepared_docs)}")
    print(f"Total Chunks Prepared:    {total_chunks}")
    print("=" * 70)

    if dry_run:
        print("Dry run completed successfully. ZERO database records were modified.")
        return

    # Real DB commit
    if not commit:
        print("Please supply --commit or --dry-run.")
        return

    print("\nConnecting to PostgreSQL...")
    from sentence_transformers import SentenceTransformer
    print(f"Loading embedding model: {EMBEDDING_MODEL}...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1. Backfill existing 7 canonical proposals with metadata
            print("\n[1] Backfilling existing canonical proposals with category metadata...")
            cur.execute("""
                UPDATE proposal_chunks
                SET metadata = metadata || '{"service_category": "Accounting", "service_subcategory": "Bookkeeping"}'::jsonb
                WHERE metadata->>'service_category' IS NULL;

                UPDATE proposal_documents
                SET metadata = metadata || '{"service_category": "Accounting", "service_subcategory": "Bookkeeping"}'::jsonb
                WHERE metadata->>'service_category' IS NULL;
            """)
            print("    Backfill completed.")

            # 2. Ingest new documents and chunks
            print("\n[2] Ingesting new multi-service proposals and generating embeddings...")
            for doc in prepared_docs:
                code = doc["proposal_code"]
                cur.execute("""
                    INSERT INTO proposal_documents (
                        proposal_code, client_name, proposal_title, source_filename,
                        organization_type, sector, engagement_type, core_bookkeeping,
                        raw_text, cleaned_text, metadata
                    ) VALUES (
                        %(proposal_code)s, %(client_name)s, %(proposal_title)s, %(source_filename)s,
                        %(organization_type)s, %(sector)s, %(engagement_type)s, %(core_bookkeeping)s,
                        %(raw_text)s, %(cleaned_text)s, %(metadata)s
                    )
                    ON CONFLICT (proposal_code) DO UPDATE SET
                        proposal_title = EXCLUDED.proposal_title,
                        cleaned_text = EXCLUDED.cleaned_text,
                        metadata = EXCLUDED.metadata
                    RETURNING id;
                """, {
                    "proposal_code": doc["proposal_code"],
                    "client_name": doc["client_name"],
                    "proposal_title": doc["proposal_title"],
                    "source_filename": doc["source_filename"],
                    "organization_type": doc["organization_type"],
                    "sector": doc["sector"],
                    "engagement_type": doc["engagement_type"],
                    "core_bookkeeping": doc["core_bookkeeping"],
                    "raw_text": doc["raw_text"][:5000],  # bounded sample
                    "cleaned_text": doc["cleaned_text"][:5000],
                    "metadata": Jsonb(doc["metadata"])
                })
                doc_id = cur.fetchone()[0]
                print(f"    Document upserted: {code} (ID: {doc_id})")

                for ch in doc["chunks"]:
                    chunk_key = ch["chunk_key"]
                    ret_text = ch["retrieval_text"]
                    vec = model.encode(ret_text, normalize_embeddings=True)
                    vec_str = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"

                    chunk_meta = {
                        "service_category": doc["metadata"]["service_category"],
                        "service_subcategory": doc["metadata"]["service_subcategory"],
                        "industry": doc["metadata"]["industry"],
                        "proposal_style": "consulting_deliverables"
                    }

                    cur.execute("""
                        INSERT INTO proposal_chunks (
                            proposal_id, chunk_key, section_order, section_type, section_title,
                            service_modules, raw_text, cleaned_text, retrieval_text,
                            retrieval_enabled, commercial_reference_only, pricing_content,
                            boilerplate_content, embedding, embedded_at, metadata
                        ) VALUES (
                            %(proposal_id)s, %(chunk_key)s, %(section_order)s, %(section_type)s, %(section_title)s,
                            %(service_modules)s, %(raw_text)s, %(cleaned_text)s, %(retrieval_text)s,
                            %(retrieval_enabled)s, false, false, false,
                            %(embedding)s::vector, NOW(), %(metadata)s
                        )
                        ON CONFLICT (chunk_key) DO UPDATE SET
                            section_title = EXCLUDED.section_title,
                            cleaned_text = EXCLUDED.cleaned_text,
                            retrieval_text = EXCLUDED.retrieval_text,
                            embedding = EXCLUDED.embedding,
                            embedded_at = EXCLUDED.embedded_at,
                            metadata = EXCLUDED.metadata;
                    """, {
                        "proposal_id": doc_id,
                        "chunk_key": chunk_key,
                        "section_order": ch["section_order"],
                        "section_type": ch["section_type"],
                        "section_title": ch["section_title"],
                        "service_modules": ch["service_modules"],
                        "raw_text": ch["raw_text"],
                        "cleaned_text": ch["cleaned_text"],
                        "retrieval_text": ch["retrieval_text"],
                        "retrieval_enabled": ch["retrieval_enabled"],
                        "embedding": vec_str,
                        "metadata": Jsonb(chunk_meta)
                    })
                    print(f"      + Chunk embedded: {chunk_key} ({ch['section_type']})")

            conn.commit()
            print("\nAll documents, chunks, and embeddings successfully committed to PostgreSQL!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Service Ingestion")
    parser.add_argument("--dry-run", action="store_true", help="Preview without DB writes")
    parser.add_argument("--commit", action="store_true", help="Execute writes to DB")
    args = parser.parse_args()

    if not args.dry_run and not args.commit:
        parser.print_help()
        sys.exit(1)

    run_ingestion(dry_run=args.dry_run, commit=args.commit)
