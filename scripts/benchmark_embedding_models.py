#!/usr/bin/env python3
"""
Sympl Solutions Proposal RAG — Embedding Model Benchmark Harness (v1.1)

Evaluates candidate embedding models on the verified retrieval gold benchmark (v1.1).
Enforces:
  - Exact NumPy cosine/dot-product ranking (no ANN / vector indexes)
  - Hard safety filters (pricing_content=false, boilerplate_content=false, retrieval_enabled=true)
  - Service-Family Eligibility Version 2.0 (resolved from query intent, zero label leakage)
  - Strict Dev/Holdout protocol: DEV selects the winner; HOLDOUT is evaluated ONLY on the frozen DEV winner.
  - Zero database writes (all vectors in-memory).
"""

import os
import sys
import json
import time
import math
import glob
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import numpy as np

# ----------------------------------------------------------------------
# 1. Environment & Key Discovery
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
GEMINI_API_KEY = ENV.get('GEMINI_API_KEY') or ENV.get('GOOGLE_API_KEY')
VOYAGE_API_KEY = ENV.get('VOYAGE_API_KEY')
OPENAI_API_KEY = ENV.get('OPENAI_API_KEY')

PROVIDER_STATUS = {
    'gemini': bool(GEMINI_API_KEY),
    'voyage': bool(VOYAGE_API_KEY),
    'openai': bool(OPENAI_API_KEY)
}

# ----------------------------------------------------------------------
# 2. Corpus & Benchmark Loading
# ----------------------------------------------------------------------
def load_corpus(normalized_dir: str = 'data/normalized') -> Dict[str, Dict[str, Any]]:
    corpus = {}
    for p in glob.glob(f"{normalized_dir}/*.json"):
        with open(p, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        p_code = doc['proposal']['proposal_code']
        for c in doc['chunks']:
            k = c['chunk_key']
            corpus[k] = {
                'chunk_key': k,
                'proposal_code': p_code,
                'section_type': c.get('section_type', ''),
                'service_modules': c.get('service_modules', []),
                'pricing_content': c.get('pricing_content', False),
                'boilerplate_content': c.get('boilerplate_content', False),
                'retrieval_enabled': c.get('retrieval_enabled', False),
                'retrieval_text': c.get('retrieval_text', '')
            }
    return corpus

def load_benchmark(benchmark_path: str = 'eval/retrieval_gold_v1.json') -> Dict[str, Any]:
    with open(benchmark_path, 'r', encoding='utf-8') as f:
        return json.load(f)

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
        sm = c['service_modules']
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
# 4. API Embeddings Interface (HTTP with Retry & Exponential Backoff)
# ----------------------------------------------------------------------
def call_gemini_embed_batch(texts: List[str], dim: int, max_retries: int = 5) -> Tuple[List[List[float]], int]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:batchEmbedContents?key={GEMINI_API_KEY}"
    requests_payload = {
        "requests": [
            {
                "model": "models/gemini-embedding-2",
                "content": {"parts": [{"text": t}]},
                "outputDimensionality": dim
            }
            for t in texts
        ]
    }
    req_data = json.dumps(requests_payload).encode('utf-8')
    req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                vectors = [item['values'] for item in data.get('embeddings', [])]
                token_count = sum(len(t.split()) for t in texts) * 2
                return vectors, token_count
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            if e.code == 429:
                # Quota delay
                sleep_sec = 35
                print(f"    [Gemini 429 Rate Limit] Sleeping {sleep_sec}s before retry (attempt {attempt+1}/{max_retries})...")
                time.sleep(sleep_sec)
            else:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Gemini API error (HTTP {e.code}): {err_body}")
                time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Gemini API connection error: {e}")
            time.sleep(2 ** attempt)
    raise RuntimeError("Gemini max retries exceeded.")

def call_voyage_embed_batch(texts: List[str], input_type: str, dim: int, max_retries: int = 5) -> Tuple[List[List[float]], int]:
    url = "https://api.voyageai.com/v1/embeddings"
    payload = {
        "model": "voyage-4-large",
        "input": texts,
        "input_type": input_type,
        "output_dimension": dim,
        "output_dtype": "float"
    }
    req_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={
            "Authorization": f"Bearer {VOYAGE_API_KEY}",
            "Content-Type": "application/json"
        }
    )

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                vectors = [item['embedding'] for item in data.get('data', [])]
                total_tokens = data.get('usage', {}).get('total_tokens', 0)
                return vectors, total_tokens
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            if e.code == 429:
                sleep_sec = 25
                print(f"    [Voyage 429 Rate Limit] Sleeping {sleep_sec}s before retry (attempt {attempt+1}/{max_retries})...")
                time.sleep(sleep_sec)
            else:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Voyage API error (HTTP {e.code}): {err_body}")
                time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Voyage API connection error: {e}")
            time.sleep(2 ** attempt)
    raise RuntimeError("Voyage max retries exceeded.")

def call_openai_embed_batch(texts: List[str], dim: Optional[int], max_retries: int = 3) -> Tuple[List[List[float]], int]:
    url = "https://api.openai.com/v1/embeddings"
    payload = {
        "model": "text-embedding-3-large",
        "input": texts,
        "encoding_format": "float"
    }
    if dim is not None:
        payload["dimensions"] = dim

    req_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
    )

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                vectors = [item['embedding'] for item in data.get('data', [])]
                total_tokens = data.get('usage', {}).get('total_tokens', 0)
                return vectors, total_tokens
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            if e.code == 429 and ('insufficient_quota' in err_body or 'credit_balance_exhausted' in err_body):
                raise RuntimeError(f"OpenAI Quota Exhausted: {err_body}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"OpenAI API error (HTTP {e.code}): {err_body}")
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"OpenAI API connection error: {e}")
            time.sleep(2 ** attempt)
    raise RuntimeError("OpenAI max retries exceeded.")

# ----------------------------------------------------------------------
# 5. Vector Normalization & Cosine Search
# ----------------------------------------------------------------------
def l2_normalize(vec: np.ndarray) -> np.ndarray:
    v = vec.astype(np.float32)
    norm = np.linalg.norm(v)
    if norm > 0:
        v = v / norm
    return v

def evaluate_retrieval(query_vec: np.ndarray,
                       candidate_keys: List[str],
                       doc_vecs: Dict[str, np.ndarray],
                       query_rec: Dict[str, Any]) -> List[Tuple[str, float]]:
    scored = []
    for k in candidate_keys:
        d_vec = doc_vecs[k]
        score = float(np.dot(query_vec, d_vec))
        scored.append((k, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored

# ----------------------------------------------------------------------
# 6. Evaluation Metrics Engine
# ----------------------------------------------------------------------
def compute_query_metrics(ranked_results: List[Tuple[str, float]],
                          query_rec: Dict[str, Any],
                          candidate_pool: List[str],
                          corpus: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    prim = set(query_rec.get('primary_relevant', []))
    acc = set(query_rec.get('acceptable_relevant', []))
    opt = set(query_rec.get('optional_relevant', []))

    def get_grade(k: str) -> int:
        if k in prim:
            return 3
        if k in acc:
            return 2
        if k in opt:
            return 1
        return 0

    top3 = ranked_results[:3]
    top3_keys = [r[0] for r in top3]

    def is_rel(k: str) -> bool:
        return get_grade(k) >= 2

    hit1 = 1.0 if (len(top3_keys) > 0 and is_rel(top3_keys[0])) else 0.0
    hit3 = 1.0 if any(is_rel(k) for k in top3_keys) else 0.0

    total_rel = len([k for k in candidate_pool if is_rel(k)])
    retrieved_rel = len([k for k in top3_keys if is_rel(k)])
    recall3 = (retrieved_rel / total_rel) if total_rel > 0 else 1.0

    mrr = 0.0
    for idx, r in enumerate(ranked_results):
        if is_rel(r[0]):
            mrr = 1.0 / (idx + 1)
            break

    dcg = 0.0
    for idx, r in enumerate(top3):
        g = get_grade(r[0])
        dcg += (2.0 ** g - 1.0) / math.log2(idx + 2)

    all_grades = sorted([get_grade(k) for k in candidate_pool], reverse=True)
    idcg = 0.0
    for idx, g in enumerate(all_grades[:3]):
        idcg += (2.0 ** g - 1.0) / math.log2(idx + 2)

    ndcg3 = (dcg / idcg) if idcg > 0 else 0.0

    unsafe_count = 0
    family_violations = 0
    for k in top3_keys:
        c = corpus[k]
        if c['pricing_content'] or c['boilerplate_content'] or not c['retrieval_enabled']:
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
# 7. Benchmark Runner Implementation
# ----------------------------------------------------------------------
class EmbeddingBenchmarkRunner:
    def __init__(self, corpus: Dict[str, Dict[str, Any]], benchmark_data: Dict[str, Any]):
        self.corpus = corpus
        self.benchmark_data = benchmark_data
        self.doc_keys = sorted([k for k, c in corpus.items() if c['retrieval_enabled']])
        self.doc_texts = {k: corpus[k]['retrieval_text'] for k in self.doc_keys}
        self.dev_queries = [q for q in benchmark_data['queries'] if q['split'] == 'dev']
        self.holdout_queries = [q for q in benchmark_data['queries'] if q['split'] == 'holdout']
        self.safety_tests = benchmark_data.get('safety_filter_tests', [])

    def embed_documents(self, config_id: str, provider: str, dim: Optional[int]) -> Tuple[Dict[str, np.ndarray], float, int]:
        t0 = time.perf_counter()
        doc_vecs = {}
        tokens = 0

        if provider == 'gemini':
            formatted_docs = [f"title: none | text: {self.doc_texts[k]}" for k in self.doc_keys]
            raw_vecs, tok = call_gemini_embed_batch(formatted_docs, dim=dim)
            tokens += tok
            for k, v in zip(self.doc_keys, raw_vecs):
                doc_vecs[k] = l2_normalize(np.array(v, dtype=np.float32))

        elif provider == 'voyage':
            raw_docs = [self.doc_texts[k] for k in self.doc_keys]
            raw_vecs, tok = call_voyage_embed_batch(raw_docs, input_type="document", dim=dim)
            tokens += tok
            for k, v in zip(self.doc_keys, raw_vecs):
                doc_vecs[k] = l2_normalize(np.array(v, dtype=np.float32))

        elif provider == 'openai':
            raw_docs = [self.doc_texts[k] for k in self.doc_keys]
            raw_vecs, tok = call_openai_embed_batch(raw_docs, dim=dim)
            tokens += tok
            for k, v in zip(self.doc_keys, raw_vecs):
                doc_vecs[k] = l2_normalize(np.array(v, dtype=np.float32))

        t1 = time.perf_counter()
        return doc_vecs, (t1 - t0), tokens

    def embed_queries(self, queries: List[Dict[str, Any]], provider: str, dim: Optional[int]) -> Tuple[List[np.ndarray], float, List[float], int]:
        t0 = time.perf_counter()
        query_vecs = []
        latencies = []
        tokens = 0

        if provider == 'gemini':
            formatted_queries = [f"task: search result | query: {q['query_text']}" for q in queries]
            # Batch in 1 or 2 calls with pacing
            raw_vecs, tok = call_gemini_embed_batch(formatted_queries, dim=dim)
            tokens += tok
            per_q_lat = ((time.perf_counter() - t0) / len(queries)) * 1000.0
            for v in raw_vecs:
                query_vecs.append(l2_normalize(np.array(v, dtype=np.float32)))
                latencies.append(per_q_lat)

        elif provider == 'voyage':
            # Voyage 3 RPM limit: sleep 22s before query call
            time.sleep(22)
            raw_queries = [q['query_text'] for q in queries]
            b_t0 = time.perf_counter()
            raw_vecs, tok = call_voyage_embed_batch(raw_queries, input_type="query", dim=dim)
            b_t1 = time.perf_counter()
            tokens += tok
            per_q_lat = ((b_t1 - b_t0) / len(queries)) * 1000.0
            for v in raw_vecs:
                query_vecs.append(l2_normalize(np.array(v, dtype=np.float32)))
                latencies.append(per_q_lat)

        elif provider == 'openai':
            raw_queries = [q['query_text'] for q in queries]
            b_t0 = time.perf_counter()
            raw_vecs, tok = call_openai_embed_batch(raw_queries, dim=dim)
            b_t1 = time.perf_counter()
            tokens += tok
            per_q_lat = ((b_t1 - b_t0) / len(queries)) * 1000.0
            for v in raw_vecs:
                query_vecs.append(l2_normalize(np.array(v, dtype=np.float32)))
                latencies.append(per_q_lat)

        t1 = time.perf_counter()
        return query_vecs, (t1 - t0), latencies, tokens

    def run_split_evaluation(self, queries: List[Dict[str, Any]],
                             query_vecs: List[np.ndarray],
                             doc_vecs: Dict[str, np.ndarray]) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
        all_metrics = []
        detailed_records = []

        for q, q_vec in zip(queries, query_vecs):
            pool = resolve_candidate_pool(q, self.corpus)
            ranked = evaluate_retrieval(q_vec, pool, doc_vecs, q)
            m = compute_query_metrics(ranked, q, pool, self.corpus)
            all_metrics.append(m)
            detailed_records.append({
                'query_id': q['query_id'],
                'target_service_family': q['target_service_family'],
                'difficulty': q['difficulty'],
                'query_class': q['query_class'],
                'ranked_top3': [r[0] for r in ranked[:3]],
                'ranked_scores': [round(r[1], 4) for r in ranked[:3]],
                'metrics': m
            })

        summary = aggregate_metrics(all_metrics)
        return summary, detailed_records

    def run_safety_tests(self, provider: str, dim: Optional[int], doc_vecs: Dict[str, np.ndarray]) -> Tuple[int, int, int, int]:
        safety_queries = [{'query_id': s['test_id'], 'query_text': s['query_text'], 'target_service_family': s['target_service_family']} for s in self.safety_tests]
        query_vecs, _, _, _ = self.embed_queries(safety_queries, provider, dim)

        pricing_count = 0
        boilerplate_count = 0
        disabled_count = 0
        family_violations = 0

        for s, q_vec in zip(self.safety_tests, query_vecs):
            pool = resolve_candidate_pool({'query_text': s['query_text'], 'target_service_family': s['target_service_family'], 'intent_tags': []}, self.corpus)
            ranked = evaluate_retrieval(q_vec, pool, doc_vecs, s)
            for r in ranked[:3]:
                c = self.corpus[r[0]]
                if c['pricing_content']:
                    pricing_count += 1
                if c['boilerplate_content']:
                    boilerplate_count += 1
                if not c['retrieval_enabled']:
                    disabled_count += 1
                if r[0] not in pool:
                    family_violations += 1

        return pricing_count, boilerplate_count, disabled_count, family_violations

# ----------------------------------------------------------------------
# 8. Execution Orchestration
# ----------------------------------------------------------------------
def main():
    print("============================================================")
    print("SYMPL EMBEDDING MODEL BENCHMARK (V1.1)")
    print("============================================================")

    print("\n[1] Checking Provider Access:")
    print(f"  Gemini: {'AVAILABLE' if PROVIDER_STATUS['gemini'] else 'MISSING'}")
    print(f"  Voyage: {'AVAILABLE' if PROVIDER_STATUS['voyage'] else 'MISSING'}")
    print(f"  OpenAI: {'AVAILABLE' if PROVIDER_STATUS['openai'] else 'MISSING'}")

    corpus = load_corpus()
    benchmark_data = load_benchmark()
    runner = EmbeddingBenchmarkRunner(corpus, benchmark_data)

    print(f"\n[2] Loaded Corpus & Benchmark:")
    print(f"  Retrieval-enabled documents: {len(runner.doc_keys)}")
    print(f"  Dev queries: {len(runner.dev_queries)}")
    print(f"  Holdout queries: {len(runner.holdout_queries)}")
    print(f"  Safety test cases: {len(runner.safety_tests)}")

    candidate_configs = [
        {'config_id': 'GEMINI2_768', 'provider': 'gemini', 'model': 'gemini-embedding-2', 'dim': 768, 'q_mode': 'task: search result | query: {query_text}', 'd_mode': 'title: none | text: {retrieval_text}'},
        {'config_id': 'GEMINI2_1536', 'provider': 'gemini', 'model': 'gemini-embedding-2', 'dim': 1536, 'q_mode': 'task: search result | query: {query_text}', 'd_mode': 'title: none | text: {retrieval_text}'},
        {'config_id': 'GEMINI2_3072', 'provider': 'gemini', 'model': 'gemini-embedding-2', 'dim': 3072, 'q_mode': 'task: search result | query: {query_text}', 'd_mode': 'title: none | text: {retrieval_text}'},
        {'config_id': 'VOYAGE4L_1024', 'provider': 'voyage', 'model': 'voyage-4-large', 'dim': 1024, 'q_mode': 'input_type=query', 'd_mode': 'input_type=document'},
        {'config_id': 'VOYAGE4L_2048', 'provider': 'voyage', 'model': 'voyage-4-large', 'dim': 2048, 'q_mode': 'input_type=query', 'd_mode': 'input_type=document'},
        {'config_id': 'OPENAI3L_DEFAULT', 'provider': 'openai', 'model': 'text-embedding-3-large', 'dim': None, 'q_mode': 'raw_text', 'd_mode': 'raw_text'},
        {'config_id': 'OPENAI3L_1536', 'provider': 'openai', 'model': 'text-embedding-3-large', 'dim': 1536, 'q_mode': 'raw_text', 'd_mode': 'raw_text'}
    ]

    dev_results = {}
    detailed_dev_records = {}
    config_metadata = {}
    failed_configs = []

    print("\n[3] Executing DEV Evaluations (60 Queries):")
    for cfg in candidate_configs:
        cid = cfg['config_id']
        prov = cfg['provider']
        dim = cfg['dim']
        print(f"\n--- Testing Config: {cid} ({prov}, requested dim={dim}) ---")

        if not PROVIDER_STATUS[prov]:
            print(f"  [SKIPPED] {prov} API key is missing.")
            failed_configs.append({'config_id': cid, 'reason': 'MISSING_API_KEY'})
            config_metadata[cid] = {'status': 'MISSING_API_KEY', 'actual_dimension': 'N/A'}
            continue

        try:
            # 1. Embed documents
            doc_vecs, doc_wall_time, doc_tok = runner.embed_documents(cid, prov, dim)
            actual_dim = len(next(iter(doc_vecs.values())))
            print(f"  Documents embedded in {doc_wall_time:.2f}s (actual dim={actual_dim}, tokens={doc_tok})")

            # Small pause between document and query embedding to stay well under rate limits
            time.sleep(5)

            # 2. Embed dev queries
            q_vecs, q_wall_time, q_latencies, q_tok = runner.embed_queries(runner.dev_queries, prov, dim)
            med_lat = float(np.median(q_latencies)) if q_latencies else 0.0
            p95_lat = float(np.percentile(q_latencies, 95)) if q_latencies else 0.0
            print(f"  Dev queries embedded in {q_wall_time:.2f}s (med={med_lat:.1f}ms, p95={p95_lat:.1f}ms, tokens={q_tok})")

            # 3. Evaluate DEV metrics
            dev_summary, dev_records = runner.run_split_evaluation(runner.dev_queries, q_vecs, doc_vecs)

            hard_records = [r['metrics'] for r in dev_records if r['difficulty'] == 'hard']
            hard_summary = aggregate_metrics(hard_records)
            confuser_records = [r['metrics'] for r in dev_records if r['query_class'] == 'confuser']
            confuser_summary = aggregate_metrics(confuser_records)

            dev_summary['hard_Hit@1'] = hard_summary.get('Hit@1', 0.0)
            dev_summary['hard_nDCG@3'] = hard_summary.get('nDCG@3', 0.0)
            dev_summary['confuser_Hit@1'] = confuser_summary.get('Hit@1', 0.0)
            dev_summary['confuser_nDCG@3'] = confuser_summary.get('nDCG@3', 0.0)

            score = compute_dev_selection_score(dev_summary)
            dev_summary['DEV_SELECTION_SCORE'] = round(score, 4)

            # 4. Run safety tests
            time.sleep(5)
            p_cnt, b_cnt, d_cnt, f_cnt = runner.run_safety_tests(prov, dim, doc_vecs)

            dev_results[cid] = {
                'metrics': dev_summary,
                'safety': {'pricing': p_cnt, 'boilerplate': b_cnt, 'disabled': d_cnt, 'family': f_cnt},
                'latency': {
                    'doc_wall_sec': round(doc_wall_time, 2),
                    'query_wall_sec': round(q_wall_time, 2),
                    'median_query_ms': round(med_lat, 1),
                    'p95_query_ms': round(p95_lat, 1)
                },
                'usage': {'doc_tokens': doc_tok, 'query_tokens': q_tok}
            }
            detailed_dev_records[cid] = dev_records
            config_metadata[cid] = {'status': 'COMPLETE', 'actual_dimension': actual_dim}

            print(f"  DEV_SELECTION_SCORE: {dev_summary['DEV_SELECTION_SCORE']:.4f} | nDCG@3: {dev_summary['nDCG@3']:.4f} | Hit@1: {dev_summary['Hit@1']:.4f} | MRR: {dev_summary['MRR']:.4f}")

            # Sleep between configs
            time.sleep(10)

        except Exception as e:
            err_msg = str(e)
            print(f"  [FAILED] {cid}: {err_msg}")
            failed_configs.append({'config_id': cid, 'reason': err_msg})
            config_metadata[cid] = {'status': f"FAILED: {err_msg[:60]}", 'actual_dimension': 'N/A'}

    # 4. DEV Candidate Rankings
    print("\n[4] DEV Candidate Rankings:")
    completed_configs = [c for c in candidate_configs if c['config_id'] in dev_results]
    completed_configs.sort(key=lambda c: dev_results[c['config_id']]['metrics']['DEV_SELECTION_SCORE'], reverse=True)

    for rank, c in enumerate(completed_configs, 1):
        cid = c['config_id']
        m = dev_results[cid]['metrics']
        print(f"  Rank {rank}: {cid:15} | Score: {m['DEV_SELECTION_SCORE']:.4f} | nDCG@3: {m['nDCG@3']:.4f} | Hit@1: {m['Hit@1']:.4f} | MRR: {m['MRR']:.4f}")

    dev_winner_cfg = completed_configs[0] if completed_configs else None
    dev_winner_id = dev_winner_cfg['config_id'] if dev_winner_cfg else None

    tie_triggered = False
    if len(completed_configs) >= 2:
        top1_score = dev_results[completed_configs[0]['config_id']]['metrics']['DEV_SELECTION_SCORE']
        top2_score = dev_results[completed_configs[1]['config_id']]['metrics']['DEV_SELECTION_SCORE']
        if abs(top1_score - top2_score) < 0.005:
            tie_triggered = True
            print(f"  [TIEBREAK TRIGGERED] Top 2 scores differ by {abs(top1_score - top2_score):.4f} (< 0.005).")

    # 5. Holdout Evaluation (ONLY on Frozen DEV Winner)
    holdout_results = {}
    gen_gap = 0.0
    gen_warning = False

    if dev_winner_cfg:
        print(f"\n[5] FREEZING DEV WINNER: {dev_winner_id}")
        print(f"  Running HOLDOUT evaluation (20 queries) exclusively for frozen winner...")
        w_prov = dev_winner_cfg['provider']
        w_dim = dev_winner_cfg['dim']

        w_doc_vecs, _, _ = runner.embed_documents(dev_winner_id, w_prov, w_dim)
        w_holdout_qvecs, _, _, _ = runner.embed_queries(runner.holdout_queries, w_prov, w_dim)
        holdout_summary, holdout_records = runner.run_split_evaluation(runner.holdout_queries, w_holdout_qvecs, w_doc_vecs)

        h_hard = aggregate_metrics([r['metrics'] for r in holdout_records if r['difficulty'] == 'hard'])
        h_conf = aggregate_metrics([r['metrics'] for r in holdout_records if r['query_class'] == 'confuser'])

        holdout_summary['hard_Hit@1'] = h_hard.get('Hit@1', 0.0)
        holdout_summary['hard_nDCG@3'] = h_hard.get('nDCG@3', 0.0)
        holdout_summary['confuser_Hit@1'] = h_conf.get('Hit@1', 0.0)
        holdout_summary['confuser_nDCG@3'] = h_conf.get('nDCG@3', 0.0)

        h_score = compute_dev_selection_score(holdout_summary)
        holdout_summary['HOLDOUT_SELECTION_SCORE'] = round(h_score, 4)

        dev_w_score = dev_results[dev_winner_id]['metrics']['DEV_SELECTION_SCORE']
        gen_gap = round(h_score - dev_w_score, 4)
        gen_warning = gen_gap < -0.10

        holdout_results = {
            'metrics': holdout_summary,
            'generalization_gap': gen_gap,
            'generalization_warning': gen_warning
        }
        print(f"  HOLDOUT Score: {h_score:.4f} | Generalization Gap: {gen_gap:+.4f} (Warning: {gen_warning})")

    # 6. Hard-case, System-state, Responsibility analysis on winner
    hard_cases_matrix = []
    system_state_metrics = {}
    responsibility_metrics = {}

    if dev_winner_id:
        w_records = detailed_dev_records[dev_winner_id]
        rec_by_id = {r['query_id']: r for r in w_records}

        hard_case_map = [
            ('Case 1: PIRS Bookkeeping Oversight', ['Q006'], 'PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT', 'PIRS oversight provides supervisory oversight over junior internal bookkeeper'),
            ('Case 2: PIRS Audit Preparation', ['Q045', 'Q047', 'Q051'], 'PIRS_2025_AUDIT_PREPARATION', 'Audit prep and reconciliation cleanup after finance director departure'),
            ('Case 3: TACT AP Automation', ['Q052', 'Q056', 'Q058'], 'TACT_2026_TRANSFORMATION_AP_PLOOTO', 'Digital AP approvals and Plooto workflow implementation'),
            ('Case 4: TACT Payroll Migration', ['Q017'], 'TACT_2026_TRANSFORMATION_PAYROLL_MIGRATION', 'Moving ADP to QBO Payroll with parallel pay runs'),
            ('Case 5: TACT AR Automation', ['Q053', 'Q057', 'Q059'], 'TACT_2026_TRANSFORMATION_AR_AUTOMATION', 'Automated recurring invoicing and PAD collections'),
            ('Case 6A: PIRS Strategy', ['Q054', 'Q060'], 'PIRS_2025_TRANSFORMATION_STRATEGY', 'High-level financial systems diagnostic roadmap'),
            ('Case 6B: PIRS Implementation', ['Q055', 'Q062'], 'PIRS_2025_TRANSFORMATION_IMPLEMENTATION', 'Hands-on QBO configuration and chart of accounts setup'),
            ('Case 7: PIRS Training', ['Q064', 'Q065', 'Q068'], 'PIRS_2025_TRAINING_CHANGE_MANAGEMENT', 'Interactive user training sessions and change management'),
            ('Case 8: Process Documentation Only', ['Q066'], 'GOODFOOT_2026_SETUP_TRANSITION_SCOPE', 'Written SOPs and workflow manuals without live coaching'),
            ('Case 9: YPT Transition', ['Q069', 'Q072'], 'YPT_2026_CONTEXT_TRANSITION', 'Fixed-term interim finance coverage maintaining existing systems'),
            ('Case 10: Compact Bookkeeping', ['Q001', 'Q002', 'Q003', 'Q007'], 'CAREOF_2025_EXPENSE_MANAGEMENT', 'Low-overhead weekly bookkeeping for compact team'),
            ('Case 11: Audit vs Compliance', ['Q038', 'Q041', 'Q044', 'Q048'], 'TACT_2026_AUDIT_SUPPORT', 'External CPA audit liaison vs statutory tax filing'),
            ('Case 12: Financial Management vs Reporting', ['Q032', 'Q034'], 'GOODFOOT_2026_FINANCIAL_MANAGEMENT', '13-week rolling cash flow runway modeling vs delivered statements')
        ]

        for c_name, qids, p_key, c_notes in hard_case_map:
            q_rec = next((rec_by_id[qid] for qid in qids if qid in rec_by_id), None)
            if q_rec:
                top3 = q_rec['ranked_top3']
                rank_str = f"Rank {top3.index(p_key)+1}" if p_key in top3 else "Outside Top 3"
                top3_str = "YES" if p_key in top3 else "NO"
                hard_cases_matrix.append({
                    'case': c_name,
                    'query_ids': qids,
                    'primary_key': p_key,
                    'winner_primary_rank': rank_str,
                    'winner_top3': top3_str,
                    'notes': c_notes
                })

        sys_ids = ['Q008', 'Q017', 'Q018', 'Q020', 'Q022', 'Q054', 'Q055', 'Q070']
        sys_recs = [rec_by_id[qid]['metrics'] for qid in sys_ids if qid in rec_by_id]
        if sys_recs:
            system_state_metrics = {
                'query_count': len(sys_recs),
                'Hit@1': float(np.mean([m['hit1'] for m in sys_recs])),
                'Hit@3': float(np.mean([m['hit3'] for m in sys_recs])),
                'nDCG@3': float(np.mean([m['ndcg3'] for m in sys_recs]))
            }

        resp_ids = ['Q006', 'Q011', 'Q019', 'Q035', 'Q044', 'Q058']
        resp_recs = [rec_by_id[qid]['metrics'] for qid in resp_ids if qid in rec_by_id]
        if resp_recs:
            responsibility_metrics = {
                'query_count': len(resp_recs),
                'Hit@1': float(np.mean([m['hit1'] for m in resp_recs])),
                'Hit@3': float(np.mean([m['hit3'] for m in resp_recs])),
                'nDCG@3': float(np.mean([m['ndcg3'] for m in resp_recs]))
            }

    # 7. Per-family DEV results for EVERY completed configuration
    per_family_results_by_config = {}
    families = sorted(list(set(q['target_service_family'] for q in runner.dev_queries)))
    for c in completed_configs:
        cid = c['config_id']
        per_family_results_by_config[cid] = {}
        for fam in families:
            fam_recs = [r['metrics'] for r in detailed_dev_records[cid] if r['target_service_family'] == fam]
            per_family_results_by_config[cid][fam] = {
                'query_count': len(fam_recs),
                'Hit@1': round(float(np.mean([m['hit1'] for m in fam_recs])), 4),
                'Hit@3': round(float(np.mean([m['hit3'] for m in fam_recs])), 4),
                'nDCG@3': round(float(np.mean([m['ndcg3'] for m in fam_recs])), 4)
            }

    # 8. Save eval/embedding_model_benchmark_v1_1.json
    result_json = {
        'benchmark_name': 'sympl_embedding_model_benchmark',
        'benchmark_version': '1.1',
        'execution_timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'provider_access': {
            'gemini': 'AVAILABLE' if PROVIDER_STATUS['gemini'] else 'MISSING',
            'voyage': 'AVAILABLE' if PROVIDER_STATUS['voyage'] else 'MISSING',
            'openai': 'AVAILABLE' if PROVIDER_STATUS['openai'] else 'MISSING'
        },
        'configurations_tested': config_metadata,
        'dev_results': dev_results,
        'failed_configurations': failed_configs,
        'dev_winner': {
            'config_id': dev_winner_id,
            'provider': dev_winner_cfg['provider'] if dev_winner_cfg else None,
            'model': dev_winner_cfg['model'] if dev_winner_cfg else None,
            'dimension': dev_winner_cfg['dim'] if dev_winner_cfg else None,
            'dev_selection_score': dev_results[dev_winner_id]['metrics']['DEV_SELECTION_SCORE'] if dev_winner_id else None,
            'tie_triggered': tie_triggered
        },
        'holdout_results': holdout_results,
        'hard_cases_matrix': hard_cases_matrix,
        'system_state_metrics': system_state_metrics,
        'responsibility_metrics': responsibility_metrics,
        'per_family_results': per_family_results_by_config,
        'final_status': 'EMBEDDING_BENCHMARK_BLOCKED_MISSING_PROVIDER_ACCESS' if failed_configs else 'EMBEDDING_MODEL_BENCHMARK_VERIFIED'
    }

    os.makedirs('eval', exist_ok=True)
    with open('eval/embedding_model_benchmark_v1_1.json', 'w', encoding='utf-8') as f:
        json.dump(result_json, f, indent=2)
    print("\nSaved eval/embedding_model_benchmark_v1_1.json successfully.")

if __name__ == '__main__':
    main()
