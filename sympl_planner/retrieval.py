"""
Sympl Solutions Proposal RAG — pgvector Exemplar Retrieval & Attachment

Attaches 1-3 verified historical exemplars (primary, secondary, optional archetype)
to proposal sections using exact PostgreSQL pgvector cosine distance.
Enforces:
  1. Service-Family Eligibility Version 2.0 candidate pool resolution.
  2. Exactly 1-3 exemplars per retrieval-enabled section.
  3. cleaned_text is placed STRICTLY under retrieval_context.exemplars.
  4. Dynamic model loading via EMBEDDING_MODEL environment variable (default: BAAI/bge-m3).
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import psycopg
from psycopg.rows import dict_row
from sentence_transformers import SentenceTransformer
from .schema import RetrievalContext, ExemplarItem, ClientInput


def load_environment() -> Dict[str, str]:
    env_vars = {}
    candidates = [
        Path('d:/Sympl/.env'),
        Path('d:/Sympl/sympl-proposal-rag/.env'),
        Path('.env'),
        Path('../.env')
    ]
    for p in candidates:
        if p.exists():
            with open(p, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        env_vars[k.strip()] = v.strip().strip('"\'')
    for k, v in os.environ.items():
        if k not in env_vars:
            env_vars[k] = v
    return env_vars


ENV = load_environment()
DATABASE_URL = ENV.get('DATABASE_URL')
if DATABASE_URL and 'junction.proxy.rlwy.net' in DATABASE_URL and 'hostaddr' not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL + ('&' if '?' in DATABASE_URL else '?') + 'hostaddr=66.33.22.241'
EMBEDDING_MODEL = ENV.get('EMBEDDING_MODEL', 'BAAI/bge-m3')
EMBEDDING_DIMENSION = int(ENV.get('EMBEDDING_DIMENSION', '1024'))


class ExemplarRetriever:
    """
    Retrieves and attaches 1-3 historical chunk exemplars to proposal sections.
    """

    _model: Optional[SentenceTransformer] = None
    _corpus_cache: Optional[Dict[str, Dict[str, Any]]] = None

    STYLE_RULES_BY_FAMILY = {
        "bookkeeping": [
            "RULE_CADENCE_SERVICE_MAPPING",
            "RULE_SYSTEM_ACTION_LINKAGE",
            "RULE_MODULAR_DELIVERABLES"
        ],
        "payroll": [
            "RULE_PAYROLL_MIGRATION_PARALLEL",
            "RULE_SEC_PAYROLL_ADMIN_SEPARATION",
            "RULE_RESPONSIBILITY_BOUNDARY_EXPLICIT"
        ],
        "financial_reporting": [
            "RULE_FUNDER_GRANT_ACCOUNTING",
            "RULE_GOVERNANCE_BOARD_DELIVERY"
        ],
        "compliance": [
            "RULE_COMPLIANCE_REBATE_SEPARATION",
            "RULE_AUDIT_READINESS_COORDINATION"
        ],
        "digital_transformation": [
            "RULE_SEC_TRANSFORMATION_MODULARITY",
            "RULE_SYSTEM_MIGRATION_CHRONOLOGY"
        ],
        "training": [
            "RULE_SEC_TRAINING_SUPPORT"
        ],
        "transition": [
            "RULE_SEC_TRANSITION_CONTINUITY",
            "RULE_ONBOARDING_CHRONOLOGY"
        ],
        "context": [
            "RULE_DOC_NONPROFIT_POSITIONING",
            "RULE_DIAGNOSTIC_ORGANIZATION_FRAMING"
        ],
        "financial_management": [
            "RULE_DIAGNOSTIC_RECONCILIATION_TASKING"
        ],
        "why_us": [
            "RULE_SEC_WHY_US_STRUCTURE"
        ],
        "pricing": [
            "RULE_SEC_PRICING_FORMATTING"
        ]
    }

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            cls._model = SentenceTransformer(EMBEDDING_MODEL)
        return cls._model

    @classmethod
    def get_corpus(cls, conn: psycopg.Connection, force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
        if cls._corpus_cache is None or force_reload:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT 
                        pc.chunk_key,
                        pd.proposal_code,
                        pc.section_type,
                        pc.service_modules,
                        pc.pricing_content,
                        pc.boilerplate_content,
                        pc.retrieval_enabled,
                        pc.retrieval_text,
                        pc.cleaned_text,
                        pc.metadata,
                        pc.core_bookkeeping
                    FROM proposal_chunks pc
                    JOIN proposal_documents pd ON pc.proposal_id = pd.id
                    WHERE pc.retrieval_enabled = true;
                """)
                rows = cur.fetchall()
                cls._corpus_cache = {r['chunk_key']: dict(r) for r in rows}
        return cls._corpus_cache

    @classmethod
    def resolve_candidate_pool(
        cls,
        family: str,
        query_text: str,
        corpus: Dict[str, Dict[str, Any]],
        target_category: Optional[str] = None
    ) -> List[str]:
        """
        Applies Service-Family Eligibility & Category Isolation to resolve candidate keys.
        Guarantees that category filtering occurs strictly BEFORE vector search.
        """
        fam = family.lower()
        qt = query_text.lower()
        target_cat = (target_category or "").strip()

        # -------------------------------------------------------------
        # NON-ACCOUNTING CATEGORIES: Multi-Tier Isolation & Fallback
        # -------------------------------------------------------------
        if target_cat and target_cat.lower() != "accounting":
            tier1 = []
            tier2 = []
            tier3 = []

            for k, c in corpus.items():
                if not c['retrieval_enabled'] or c['pricing_content'] or c['boilerplate_content']:
                    continue

                meta = c.get('metadata') or {}
                chunk_cat = meta.get('service_category', 'Accounting')
                is_bookkeeping = c.get('core_bookkeeping', False) or (chunk_cat == 'Accounting')

                # STRICT HARD NEGATIVE FIREWALL: Never return accounting chunks for non-accounting requests
                if is_bookkeeping:
                    continue

                st = (c.get('section_type') or '').lower()

                # Tier 1: Exact category match
                if chunk_cat.lower() == target_cat.lower():
                    # If section type matches or is directly relevant
                    if st in (fam, 'deliverables', 'architecture', 'implementation', 'discovery', 'timeline', 'context_objectives'):
                        tier1.append(k)
                    else:
                        tier2.append(k)
                elif meta.get('proposal_style') == 'consulting_deliverables':
                    # Tier 3: General Sympl consulting fallback (non-accounting)
                    tier3.append(k)

            # Combine according to exact hierarchy:
            # Priority: Tier 1 -> Tier 2 -> Tier 3
            pool = list(tier1)
            for k in tier2:
                if k not in pool:
                    pool.append(k)
            if len(pool) < 3:
                for k in tier3:
                    if k not in pool:
                        pool.append(k)

            # Tier 4: Return whatever candidates exist (even if only 1 or 2 chunks)
            return pool

        # -------------------------------------------------------------
        # ACCOUNTING CATEGORY: Battle-tested bookkeeping candidate resolution
        # -------------------------------------------------------------
        pool = []
        for k, c in corpus.items():
            if not c['retrieval_enabled'] or c['pricing_content'] or c['boilerplate_content']:
                continue

            meta = c.get('metadata') or {}
            chunk_cat = meta.get('service_category', 'Accounting')

            # STRICT ISOLATION: Never include website or data chunks in accounting proposals
            if chunk_cat != 'Accounting':
                continue

            st = c['section_type']
            sm = c.get('service_modules') or []
            eligible = False

            if fam == 'bookkeeping':
                if st in ('bookkeeping', 'service_module'):
                    eligible = any(m in sm for m in ['bookkeeping', 'reconciliations', 'accounts_payable', 'accounts_receivable'])
                elif k == 'PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT':
                    eligible = True

            elif fam == 'payroll':
                if st == 'payroll':
                    eligible = True
                elif k == 'TACT_2026_TRANSFORMATION_PAYROLL_MIGRATION':
                    is_migration = any(w in qt for w in ['migrat', 'transition', 'move', 'switch', 'parallel', 'adp'])
                    if is_migration:
                        eligible = True

            elif fam == 'financial_reporting':
                if st == 'financial_reporting':
                    eligible = True
                elif k == 'RPFF_2025_FUNDING_FUND_TRACKING':
                    is_funder = any(w in qt for w in ['funder', 'grant', 'contribution', 'fund'])
                    if is_funder:
                        eligible = True
                elif k == 'PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT':
                    is_oversight = any(w in qt for w in ['management reporting', 'budget', 'visibility', 'oversight'])
                    if is_oversight:
                        eligible = True

            elif fam == 'financial_management':
                if st == 'financial_management':
                    eligible = True

            elif fam == 'compliance':
                if st == 'compliance':
                    eligible = True

            elif fam == 'audit':
                if st == 'audit':
                    eligible = True
                elif st == 'compliance' and 'audit' in sm:
                    eligible = True

            elif fam == 'digital_transformation':
                if st == 'digital_transformation':
                    eligible = True

            elif fam == 'training':
                if 'training' in sm:
                    eligible = True
                elif 'process_documentation' in sm:
                    is_doc_query = any(w in qt for w in ['sop', 'process documentation', 'workflow documentation', 'manual', 'guide'])
                    if is_doc_query:
                        eligible = True

            elif fam == 'transition':
                if st in ('transition', 'onboarding'):
                    eligible = True

            elif fam == 'context':
                if st == 'context_objectives':
                    eligible = True

            if eligible:
                pool.append(k)

        return pool

    @classmethod
    def attach_exemplars_to_section(
        cls,
        conn: psycopg.Connection,
        service_family: str,
        section_type: str,
        target_archetype: str,
        client_input: ClientInput
    ) -> Optional[RetrievalContext]:
        """
        Retrieves 1-3 exemplars for a section and compiles RetrievalContext.
        Category filtering is strictly enforced BEFORE pgvector search.
        """
        if not service_family or service_family in ("why_us", "pricing", "exclusions"):
            return None

        corpus = cls.get_corpus(conn)
        org = client_input.organization
        eng = client_input.engagement

        # Determine target service category
        target_category = None
        if hasattr(client_input, "service_category") and client_input.service_category:
            target_category = client_input.service_category
        elif hasattr(org, "service_category") and org.service_category:
            target_category = org.service_category
        elif client_input.approved_scope.generic_services:
            for gs in client_input.approved_scope.generic_services:
                cat_norm = gs.service_category.lower().replace(" ", "_").replace("/", "_")
                if cat_norm == service_family:
                    target_category = gs.service_category
                    break
            if not target_category and client_input.approved_scope.generic_services:
                target_category = client_input.approved_scope.generic_services[0].service_category

        if not target_category:
            if service_family in ("bookkeeping", "payroll", "financial_reporting", "compliance", "training", "transition", "context", "financial_management"):
                target_category = "Accounting"
            else:
                norm_fam = service_family.lower()
                if "web" in norm_fam:
                    target_category = "Website Development"
                elif "data" in norm_fam or "analytic" in norm_fam:
                    target_category = "Data Analytics"
                elif "tech" in norm_fam:
                    target_category = "Technology Consulting"
                elif "finance" in norm_fam or "forecast" in norm_fam:
                    target_category = "Finance Transformation"
                else:
                    target_category = "Accounting"

        # Formulate query text representing the client section intent
        query_parts = [
            f"Organization: {org.name} ({org.organization_type}, sector: {org.sector}).",
            f"Service Section: {section_type.replace('_', ' ').title()} ({service_family}).",
            f"Engagement: {eng.engagement_type} ({eng.complexity})."
        ]

        if org.current_systems:
            query_parts.append(f"Current systems: {', '.join(org.current_systems)}.")
        if org.target_systems:
            query_parts.append(f"Target systems: {', '.join(org.target_systems)}.")

        # Add scope details if applicable
        if service_family == "bookkeeping" and client_input.approved_scope.bookkeeping:
            bk = client_input.approved_scope.bookkeeping
            query_parts.append(f"Cadence: {bk.cadence}, AP/AR: {bk.ap_ar}, Reconciliations: {bk.reconciliations}.")
        elif service_family == "payroll" and client_input.approved_scope.payroll:
            py = client_input.approved_scope.payroll
            query_parts.append(f"Headcount: {py.headcount_employees} employees, {py.headcount_contractors} contractors, Cadence: {py.cadence}.")
        elif service_family == "digital_transformation" and client_input.approved_scope.digital_transformation:
            tr = client_input.approved_scope.digital_transformation
            query_parts.append(f"Migrations: {', '.join(tr.system_migrations)}, Workflow redesign: {tr.workflow_redesign}.")
        elif service_family == "transition" and client_input.approved_scope.transition:
            ts = client_input.approved_scope.transition
            query_parts.append(f"Onboarding: {ts.onboarding_duration_weeks} weeks, Handover continuity: {ts.handover_continuity}.")

        # For generic services, incorporate deliverables and scope details
        if client_input.approved_scope.generic_services:
            for gs in client_input.approved_scope.generic_services:
                if gs.deliverables:
                    query_parts.append(f"Deliverables: {', '.join(gs.deliverables)}.")
                if gs.requirements:
                    query_parts.append(f"Requirements: {', '.join(gs.requirements)}.")

        query_text = " ".join(query_parts)

        # -------------------------------------------------------------
        # 1. Resolve candidate pool with category filtering FIRST
        # -------------------------------------------------------------
        cand_pool = cls.resolve_candidate_pool(service_family, query_text, corpus, target_category=target_category)
        if not cand_pool:
            return None

        # -------------------------------------------------------------
        # 2. Encode query vector
        # -------------------------------------------------------------
        model = cls.get_model()
        vec = model.encode(query_text, normalize_embeddings=True)
        vec_str = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"

        # -------------------------------------------------------------
        # 3. Query pgvector for candidates within the pre-filtered pool
        # -------------------------------------------------------------
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    pc.chunk_key,
                    pd.proposal_code,
                    pc.section_type,
                    1 - (pc.embedding <=> %s::vector) AS cosine_similarity
                FROM proposal_chunks pc
                JOIN proposal_documents pd ON pc.proposal_id = pd.id
                WHERE pc.chunk_key = ANY(%s)
                  AND pc.embedding IS NOT NULL
                ORDER BY pc.embedding <=> %s::vector ASC
                LIMIT 5;
            """, (vec_str, cand_pool, vec_str))
            ranked = cur.fetchall()

        if not ranked:
            return None

        # -------------------------------------------------------------
        # 4. Assemble 1-3 exemplars (Primary, Secondary, Optional Archetype)
        # -------------------------------------------------------------
        exemplars: List[ExemplarItem] = []

        # 1. Primary (Top-1)
        top1 = ranked[0]
        top1_key = top1[0]
        top1_chunk = corpus[top1_key]
        top1_meta = top1_chunk.get('metadata') or {}
        exemplars.append(ExemplarItem(
            role="primary",
            chunk_key=top1_key,
            proposal_code=top1[1],
            section_type=top1[2],
            similarity_score=float(top1[3]),
            cleaned_text=top1_chunk['cleaned_text'],
            service_category=top1_meta.get('service_category', 'Accounting')
        ))

        # 2. Secondary (Top-2, if available)
        if len(ranked) > 1:
            top2 = ranked[1]
            top2_key = top2[0]
            top2_chunk = corpus[top2_key]
            top2_meta = top2_chunk.get('metadata') or {}
            exemplars.append(ExemplarItem(
                role="secondary",
                chunk_key=top2_key,
                proposal_code=top2[1],
                section_type=top2[2],
                similarity_score=float(top2[3]),
                cleaned_text=top2_chunk['cleaned_text'],
                service_category=top2_meta.get('service_category', 'Accounting')
            ))

        # 3. Optional Archetype (Exemplar matching selected archetype, or Top-3)
        archetype_proposals = {
            "ARCH_TRANSITION_INTERIM": ["YPT_2026"],
            "ARCH_AUDIT_OVERSIGHT_TRANSFORMATION": ["PIRS_2025"],
            "ARCH_COMPREHENSIVE_TRANSFORMATION": ["TACT_2026", "GOODFOOT_2026"],
            "ARCH_STANDARD_NONPROFIT": ["RPFF_2025"],
            "ARCH_COMPACT_BOOKKEEPING": ["CAREOF_2025", "CAHOOTS_2026"]
        }.get(target_archetype, [])

        archetype_candidate = None
        for r in ranked[1:]:
            if r[1] in archetype_proposals and r[0] != exemplars[-1].chunk_key:
                archetype_candidate = r
                break

        if archetype_candidate:
            arch_chunk = corpus[archetype_candidate[0]]
            arch_meta = arch_chunk.get('metadata') or {}
            exemplars.append(ExemplarItem(
                role="optional_archetype",
                chunk_key=archetype_candidate[0],
                proposal_code=archetype_candidate[1],
                section_type=archetype_candidate[2],
                similarity_score=float(archetype_candidate[3]),
                cleaned_text=arch_chunk['cleaned_text'],
                service_category=arch_meta.get('service_category', 'Accounting')
            ))
        elif len(ranked) > 2 and len(exemplars) < 3:
            top3 = ranked[2]
            top3_chunk = corpus[top3[0]]
            top3_meta = top3_chunk.get('metadata') or {}
            exemplars.append(ExemplarItem(
                role="optional_archetype",
                chunk_key=top3[0],
                proposal_code=top3[1],
                section_type=top3[2],
                similarity_score=float(top3[3]),
                cleaned_text=top3_chunk['cleaned_text'],
                service_category=top3_meta.get('service_category', 'Accounting')
            ))

        return RetrievalContext(
            query_text=query_text,
            target_service_family=service_family,
            candidate_pool_size=len(cand_pool),
            exemplars=exemplars
        )
