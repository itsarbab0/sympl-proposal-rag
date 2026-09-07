#!/usr/bin/env python3
"""
Sympl Solutions Proposal RAG — pgvector Retrieval Benchmark

Evaluates database pgvector retrieval against eval/retrieval_gold_v1.json.
Enforces:
  - Exact pgvector cosine distance (<=> operator) retrieval directly against PostgreSQL.
  - Environment-based model configuration (EMBEDDING_MODEL, EMBEDDING_DIMENSION).
  - Candidate Pool Resolution via Service-Family Eligibility v2.0.
  - Evaluation of DEV split (60 queries), HOLDOUT split (20 queries), and Safety Tests (8 cases).
  - Computation of standard ranking metrics: Hit@1, Hit@3, Recall@3, MRR, nDCG@3.
"""

import os
import sys
import json
import time
import math
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
import psycopg
from psycopg.rows import dict_row
from sentence_transformers import SentenceTransformer


# ----------------------------------------------------------------------
# 1. Environment & Configuration
# ----------------------------------------------------------------------
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
EMBEDDING_MODEL = ENV.get('EMBEDDING_MODEL', 'BAAI/bge-m3')
EMBEDDING_DIMENSION = int(ENV.get('EMBEDDING_DIMENSION', '1024'))

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required in environment.")


# ----------------------------------------------------------------------
# 2. Database Helpers & Corpus Metadata
# ----------------------------------------------------------------------
def get_db_connection():
    return psycopg.connect(DATABASE_URL)


def load_corpus_from_db(conn) -> Dict[str, Dict[str, Any]]:
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
                (pc.embedding IS NOT NULL) AS has_embedding
            FROM proposal_chunks pc
            JOIN proposal_documents pd ON pc.proposal_id = pd.id
            ORDER BY pc.id ASC;
        """)
        rows = cur.fetchall()
        return {r['chunk_key']: dict(r) for r in rows}


# ----------------------------------------------------------------------
# 3. Candidate Pool Resolver (Service-Family Eligibility v2.0)
# ----------------------------------------------------------------------
def resolve_candidate_pool(query: Dict[str, Any], corpus: Dict[str, Dict[str, Any]]) -> List[str]:
    fam = query['target_service_family']
    qt = query['query_text'].lower()
    intent_tags = [t.lower() for t in query.get('intent_tags', [])]
    pool = []

    for k, c in corpus.items():
        if not c['retrieval_enabled'] or c['pricing_content'] or c['boilerplate_content']:
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
                is_migration = (any(w in qt for w in ['migrat', 'transition', 'move', 'switch', 'parallel', 'adp']) or
                                any('migrat' in t or 'parallel' in t for t in intent_tags))
                if is_migration:
                    eligible = True

        elif fam == 'financial_reporting':
            if st == 'financial_reporting':
                eligible = True
            elif k == 'RPFF_2025_FUNDING_FUND_TRACKING':
                is_funder = (any(w in qt for w in ['funder', 'grant', 'contribution', 'fund']) or
                             any('funder' in t or 'grant' in t for t in intent_tags))
                if is_funder:
                    eligible = True
            elif k == 'PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT':
                is_oversight = (any(w in qt for w in ['management reporting', 'budget', 'visibility', 'oversight', 'monthly financial reporting']) or
                                any('management_reporting' in t or 'oversight' in t for t in intent_tags))
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
                is_doc_query = (any(w in qt for w in ['sop', 'process documentation', 'workflow documentation', 'procedural documentation', 'manual', 'guide']) or
                                any('sop' in t or 'documentation' in t for t in intent_tags))
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


# ----------------------------------------------------------------------
# 4. Metric Computation Functions
# ----------------------------------------------------------------------
def evaluate_query_ranking(
    retrieved_keys: List[str],
    query: Dict[str, Any],
    candidate_pool: List[str],
    corpus: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    prim = set(query.get('primary_relevant', []))
    acc = set(query.get('acceptable_relevant', []))
    opt = set(query.get('optional_relevant', []))

    def get_grade(k: str) -> int:
        if k in prim:
            return 3
        if k in acc:
            return 2
        if k in opt:
            return 1
        return 0

    top3_keys = retrieved_keys[:3]

    def is_rel(k: str) -> bool:
        return get_grade(k) >= 2

    hit1 = 1.0 if (len(top3_keys) > 0 and is_rel(top3_keys[0])) else 0.0
    hit3 = 1.0 if any(is_rel(k) for k in top3_keys) else 0.0

    total_rel = len([k for k in candidate_pool if is_rel(k)])
    retrieved_rel = len([k for k in top3_keys if is_rel(k)])
    recall3 = (retrieved_rel / total_rel) if total_rel > 0 else 1.0

    mrr = 0.0
    for idx, k in enumerate(retrieved_keys):
        if is_rel(k):
            mrr = 1.0 / (idx + 1)
            break

    dcg = 0.0
    for idx, k in enumerate(top3_keys):
        g = get_grade(k)
        dcg += (2.0 ** g - 1.0) / math.log2(idx + 2)

    all_grades = sorted([get_grade(k) for k in candidate_pool], reverse=True)
    idcg = 0.0
    for idx, g in enumerate(all_grades[:3]):
        idcg += (2.0 ** g - 1.0) / math.log2(idx + 2)

    ndcg3 = (dcg / idcg) if idcg > 0 else 0.0

    unsafe_count = 0
    family_violations = 0
    for k in top3_keys:
        c = corpus.get(k, {})
        if c.get('pricing_content', False) or c.get('boilerplate_content', False) or not c.get('retrieval_enabled', False):
            unsafe_count += 1
        if k not in candidate_pool:
            family_violations += 1

    fam_accuracy = 1.0 if family_violations == 0 else 0.0

    return {
        'hit1': hit1,
        'hit3': hit3,
        'recall3': recall3,
        'mrr': mrr,
        'ndcg3': ndcg3,
        'unsafe_count': unsafe_count,
        'fam_accuracy': fam_accuracy
    }


def aggregate_metrics(metrics_list: List[Dict[str, float]]) -> Dict[str, float]:
    n = len(metrics_list)
    if n == 0:
        return {}
    return {
        'Hit@1': float(np.mean([m['hit1'] for m in metrics_list])),
        'Hit@3': float(np.mean([m['hit3'] for m in metrics_list])),
        'Recall@3': float(np.mean([m['recall3'] for m in metrics_list])),
        'MRR': float(np.mean([m['mrr'] for m in metrics_list])),
        'nDCG@3': float(np.mean([m['ndcg3'] for m in metrics_list])),
        'Family Eligibility Accuracy': float(np.mean([m['fam_accuracy'] for m in metrics_list])),
        'Unsafe Retrieval Count': int(np.sum([m['unsafe_count'] for m in metrics_list]))
    }


def compute_dev_selection_score(m: Dict[str, float]) -> float:
    return float(
        0.35 * m['nDCG@3'] +
        0.25 * m['Hit@1'] +
        0.20 * m['MRR'] +
        0.10 * m['Hit@3'] +
        0.10 * m['Recall@3']
    )


# ----------------------------------------------------------------------
# 5. Benchmark Execution Function
# ----------------------------------------------------------------------
def run_pgvector_benchmark():
    print("=" * 60)
    print("SYMPL PGVECTOR RETRIEVAL BENCHMARK")
    print("=" * 60)
    print(f"Embedding Model:     {EMBEDDING_MODEL}")
    print(f"Embedding Dimension: {EMBEDDING_DIMENSION}")

    # Connect to PostgreSQL
    conn = get_db_connection()
    corpus = load_corpus_from_db(conn)
    print(f"Loaded {len(corpus)} chunks from database.")

    retrieval_chunks = [k for k, c in corpus.items() if c['retrieval_enabled']]
    embedded_chunks = [k for k, c in corpus.items() if c['retrieval_enabled'] and c['has_embedding']]
    print(f"Retrieval-enabled chunks: {len(retrieval_chunks)}")
    print(f"Embedded chunks in DB:    {len(embedded_chunks)}")

    if len(embedded_chunks) != len(retrieval_chunks):
        raise RuntimeError(
            f"Embedding check failed: {len(embedded_chunks)}/{len(retrieval_chunks)} retrieval-enabled chunks embedded."
        )

    # Load benchmark dataset
    benchmark_path = Path("eval/retrieval_gold_v1.json")
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_path}")

    with open(benchmark_path, 'r', encoding='utf-8') as f:
        benchmark_data = json.load(f)

    queries = benchmark_data['queries']
    dev_queries = [q for q in queries if q['split'] == 'dev']
    holdout_queries = [q for q in queries if q['split'] == 'holdout']
    safety_tests = benchmark_data.get('safety_filter_tests', [])

    print(f"Benchmark Version:        {benchmark_data.get('benchmark_version', '1.1')}")
    print(f"Total Queries:            {len(queries)} (DEV: {len(dev_queries)}, HOLDOUT: {len(holdout_queries)})")
    print(f"Safety Tests:             {len(safety_tests)}")

    # Load Model
    print(f"\n[1] Loading embedding model '{EMBEDDING_MODEL}'...")
    t0 = time.perf_counter()
    model = SentenceTransformer(EMBEDDING_MODEL)
    load_time = time.perf_counter() - t0
    print(f"Model loaded in {load_time:.2f}s")

    # Helper to execute pgvector search
    def retrieve_candidates(query_text: str, candidate_pool: List[str], top_k: int = 3) -> List[Tuple[str, float]]:
        vec = model.encode(query_text, normalize_embeddings=True)
        if len(vec) != EMBEDDING_DIMENSION:
            raise ValueError(f"Vector dim {len(vec)} does not match expected {EMBEDDING_DIMENSION}")
        vec_str = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"

        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    chunk_key,
                    1 - (embedding <=> %s::vector) AS cosine_similarity
                FROM proposal_chunks
                WHERE chunk_key = ANY(%s)
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector ASC
                LIMIT %s;
            """, (vec_str, candidate_pool, vec_str, top_k))
            return cur.fetchall()

    # ------------------------------------------------------------------
    # [2] Execute DEV Split (60 queries)
    # ------------------------------------------------------------------
    print(f"\n[2] Executing DEV Evaluations ({len(dev_queries)} queries)...")
    dev_metrics = []
    dev_detailed = []
    dev_latencies = []

    for q in dev_queries:
        cand_pool = resolve_candidate_pool(q, corpus)
        q_t0 = time.perf_counter()
        results = retrieve_candidates(q['query_text'], cand_pool, top_k=3)
        latency_ms = (time.perf_counter() - q_t0) * 1000.0
        dev_latencies.append(latency_ms)

        retrieved_keys = [r[0] for r in results]
        m = evaluate_query_ranking(retrieved_keys, q, cand_pool, corpus)
        dev_metrics.append(m)
        dev_detailed.append({
            'query_id': q['query_id'],
            'query_text': q['query_text'],
            'target_family': q['target_service_family'],
            'primary_relevant': q.get('primary_relevant', []),
            'acceptable_relevant': q.get('acceptable_relevant', []),
            'retrieved_keys': retrieved_keys,
            'similarities': [float(r[1]) for r in results],
            'latency_ms': latency_ms,
            'metrics': m
        })

    dev_agg = aggregate_metrics(dev_metrics)
    dev_score = compute_dev_selection_score(dev_agg)
    avg_dev_latency = float(np.mean(dev_latencies))

    print("  DEV Benchmark Results:")
    print(f"    Hit@1:                       {dev_agg['Hit@1']:.4f}")
    print(f"    Hit@3:                       {dev_agg['Hit@3']:.4f}")
    print(f"    Recall@3:                    {dev_agg['Recall@3']:.4f}")
    print(f"    MRR:                         {dev_agg['MRR']:.4f}")
    print(f"    nDCG@3:                      {dev_agg['nDCG@3']:.4f}")
    print(f"    Family Eligibility Accuracy: {dev_agg['Family Eligibility Accuracy']:.4f}")
    print(f"    Unsafe Retrieval Count:      {dev_agg['Unsafe Retrieval Count']}")
    print(f"    DEV Selection Score:         {dev_score:.4f}")
    print(f"    Avg Retrieval Latency:       {avg_dev_latency:.2f} ms/query")

    # ------------------------------------------------------------------
    # [3] Execute HOLDOUT Split (20 queries)
    # ------------------------------------------------------------------
    print(f"\n[3] Executing HOLDOUT Evaluations ({len(holdout_queries)} queries)...")
    holdout_metrics = []
    holdout_detailed = []
    holdout_latencies = []

    for q in holdout_queries:
        cand_pool = resolve_candidate_pool(q, corpus)
        q_t0 = time.perf_counter()
        results = retrieve_candidates(q['query_text'], cand_pool, top_k=3)
        latency_ms = (time.perf_counter() - q_t0) * 1000.0
        holdout_latencies.append(latency_ms)

        retrieved_keys = [r[0] for r in results]
        m = evaluate_query_ranking(retrieved_keys, q, cand_pool, corpus)
        holdout_metrics.append(m)
        holdout_detailed.append({
            'query_id': q['query_id'],
            'query_text': q['query_text'],
            'target_family': q['target_service_family'],
            'primary_relevant': q.get('primary_relevant', []),
            'acceptable_relevant': q.get('acceptable_relevant', []),
            'retrieved_keys': retrieved_keys,
            'similarities': [float(r[1]) for r in results],
            'latency_ms': latency_ms,
            'metrics': m
        })

    holdout_agg = aggregate_metrics(holdout_metrics)
    avg_holdout_latency = float(np.mean(holdout_latencies))

    print("  HOLDOUT Benchmark Results:")
    print(f"    Hit@1:                       {holdout_agg['Hit@1']:.4f}")
    print(f"    Hit@3:                       {holdout_agg['Hit@3']:.4f}")
    print(f"    Recall@3:                    {holdout_agg['Recall@3']:.4f}")
    print(f"    MRR:                         {holdout_agg['MRR']:.4f}")
    print(f"    nDCG@3:                      {holdout_agg['nDCG@3']:.4f}")
    print(f"    Family Eligibility Accuracy: {holdout_agg['Family Eligibility Accuracy']:.4f}")
    print(f"    Unsafe Retrieval Count:      {holdout_agg['Unsafe Retrieval Count']}")
    print(f"    Avg Retrieval Latency:       {avg_holdout_latency:.2f} ms/query")

    # ------------------------------------------------------------------
    # [4] Execute Safety Filter Tests (8 cases)
    # ------------------------------------------------------------------
    print(f"\n[4] Executing Safety Filter Tests ({len(safety_tests)} tests)...")
    safety_violations = 0
    safety_results = []

    for st in safety_tests:
        test_query = st['query_text']
        # For safety tests, search across ALL retrieval-enabled chunks in DB
        all_retrieval_keys = [k for k, c in corpus.items() if c['retrieval_enabled']]
        results = retrieve_candidates(test_query, all_retrieval_keys, top_k=3)
        retrieved_keys = [r[0] for r in results]

        # Check if any retrieved chunk violates safety constraints
        violated = False
        prohibited = set(st.get('prohibited_chunk_types', []))
        for k in retrieved_keys:
            c = corpus[k]
            if c['pricing_content'] and 'pricing_content' in prohibited:
                violated = True
                safety_violations += 1
            if c['boilerplate_content'] and 'boilerplate_content' in prohibited:
                violated = True
                safety_violations += 1
            if not c['retrieval_enabled']:
                violated = True
                safety_violations += 1

        safety_results.append({
            'test_id': st['test_id'],
            'query_text': test_query,
            'prohibited_types': list(prohibited),
            'retrieved_keys': retrieved_keys,
            'violation': violated
        })

    print(f"  Safety Filter Violations: {safety_violations}/{len(safety_tests)}")

    # ------------------------------------------------------------------
    # [5] Save Benchmark Results
    # ------------------------------------------------------------------
    results_dir = Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    model_slug = EMBEDDING_MODEL.replace('/', '_').replace('-', '_').lower()
    output_path = results_dir / f"{model_slug}_pgvector_baseline.json"

    result_payload = {
        'benchmark_name': 'sympl_pgvector_retrieval_benchmark',
        'benchmark_version': benchmark_data.get('benchmark_version', '1.1'),
        'embedding_model': EMBEDDING_MODEL,
        'embedding_dimension': EMBEDDING_DIMENSION,
        'retrieval_engine': 'PostgreSQL pgvector (<=> cosine distance)',
        'corpus_chunks_total': len(corpus),
        'retrieval_enabled_chunks': len(retrieval_chunks),
        'execution_timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'dev_summary': {
            'query_count': len(dev_queries),
            'metrics': dev_agg,
            'dev_selection_score': dev_score,
            'avg_latency_ms': avg_dev_latency
        },
        'holdout_summary': {
            'query_count': len(holdout_queries),
            'metrics': holdout_agg,
            'avg_latency_ms': avg_holdout_latency
        },
        'safety_summary': {
            'test_count': len(safety_tests),
            'violations': safety_violations
        },
        'dev_detailed_results': dev_detailed,
        'holdout_detailed_results': holdout_detailed,
        'safety_detailed_results': safety_results
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_payload, f, indent=2)

    print(f"\n[5] Benchmark results saved to: {output_path}")
    print("=" * 60)
    print("BENCHMARK COMPLETED SUCCESSFULLY")
    print("=" * 60)
    conn.close()


if __name__ == '__main__':
    run_pgvector_benchmark()
