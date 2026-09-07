# Retrieval Evaluation Dataset Design Specification (v1.1)
**Project:** Sympl Solutions Proposal RAG System  
**Corpus Scope:** 7 Curated Historical Proposals | 71 Total Chunks | 47 Retrieval-Enabled Chunks  
**Benchmark Artifact:** [`eval/retrieval_gold_v1.json`](file:///D:/Sympl/sympl-proposal-rag/eval/retrieval_gold_v1.json)  
**Status:** Version 1.1 Complete, Hardened, and Verified (Zero Family Filter Violations)  

---

## 1. Executive Summary & Purpose

The **Sympl Retrieval Evaluation Dataset v1.1** establishes a hardened, human-reviewed gold benchmark designed to evaluate, compare, and select embedding models, retrieval strategies, metadata boost weights, and top-$K$ cutoff thresholds for the Sympl Proposal RAG pipeline.

### Version 1.1 Integrity Hardening Updates:
- **Zero Relevance-Filter Contradictions:** Enforces strict adherence to Service-Family Eligibility Version 2.0 across all 80 queries. All 295 relevance-tier assignments (80 Primary, 147 Acceptable, 68 Optional) point exclusively to chunks that are production-eligible under the target service family filter.
- **Explicit Confuser Separation:** Ineligible cross-family near-neighbors that previously leaked into acceptable/optional tiers have been removed from relevance and documented in `confuser_notes` as true Grade 0 distractors.
- **Source-Fingerprint De-Identification:** Eliminated exact historical client numbers and scale fingerprints (e.g. removed `$1.4M` and `19 employees` from `Q079`, and removed `19 employees` from `Q017`), preventing vector embeddings from exploiting memorized client facts.
- **Holdout Divergence:** Rewrote `Q074` to ensure the Holdout interim staffing scenario is distinct and does not repeat the Sage 50 / Telpay phrasing of Dev `Q070`.
- **Accurate Ground-Truth Statistics:** All metrics, chunk keys, and counts are computed directly from the saved JSON artifact, eliminating all stale or hallucinated report references.

### Core Guiding Principles:
1. **Model & Provider Independence:** The benchmark is constructed completely independent of any vector embedding provider (OpenAI, Gemini, Voyage, Cohere, etc.). No vector embeddings, dimensions, or similarity SQL functions are committed in this phase.
2. **Realistic Intake Formulation:** Queries represent authentic client discovery text—originating from sales notes, client emails, discovery interviews, RFP extracts, and proposal intake forms. No queries copy literal phrases from `retrieval_text` or `cleaned_text`.
3. **Strict De-Identification:** All queries are strictly de-identified. Historical client names (Care/of, Cahoots, RPFF, Young People's Theatre, Good Foot, TACT, PIRS) are 100% absent.
4. **Three-Tier Graded Relevance:** Recognizes that multiple historical exemplars may be legitimate drafting references, categorizing relevance into Primary (Grade 3), Acceptable (Grade 2), and Optional (Grade 1). All grades 1–3 are guaranteed production-eligible chunks.
5. **Absolute Separation of Text Roles:** Evaluates candidate chunk retrieval against `proposal_chunks.retrieval_text`. It does not evaluate prose generation or writing style.
6. **Safety Firewalls:** Strictly enforces that historical pricing (`pricing_content = true`) and boilerplate clauses (`boilerplate_content = true`) are NEVER retrieved for writer drafting.

---

## 2. Runtime Text Separation Architecture

The Sympl Proposal RAG architecture enforces a three-layer textual separation across every chunk:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          1. RETRIEVAL TEXT                                   │
│  - Normalized, keyword-dense, semantic representation                       │
│  - Target for future embedding vectors & lexical search queries             │
│  - Stripped of pricing numbers, dates, and non-generalizable noise          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Retrieval Engine)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          2. CLEANED TEXT                                     │
│  - Authentic, human-written historical Sympl proposal prose                 │
│  - Supplied to the section-writer prompt AFTER retrieval                    │
│  - Injected strictly as STYLE_EXAMPLE_ONLY (syntax, cadence, tone)         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Auditing / Provenance)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          3. RAW TEXT                                         │
│  - Verbatim OCR / layout stream extracted from historical PDF source        │
│  - Preserved exclusively for lineage auditability and proof of provenance   │
└─────────────────────────────────────────────────────────────────────────────┘
```

The benchmark specifically tests whether a query finds the correct chunks via their **`retrieval_text`** representation.

---

## 3. Service-Family Eligibility Version 2.0

In Version 2.0, section and retrieval intent are the dominant signals. Service module overlaps create explicit exceptions only where the chunk genuinely acts as an operational writing exemplar for that service family.

### A. Eligibility Rules by Service Family

| Service Family | Base Rule | Conditional / Cross-Type Exceptions | Eligible Chunk Count |
| :--- | :--- | :--- | :---: |
| **`bookkeeping`** | `section_type IN ('bookkeeping', 'service_module')` where module overlaps `bookkeeping`, `reconciliations`, `accounts_payable`, `accounts_receivable` | `PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT` (explicit cross-type exception for bookkeeping oversight) | 14 |
| **`payroll`** | `section_type = 'payroll'` | `TACT_2026_TRANSFORMATION_PAYROLL_MIGRATION` (ONLY when query explicitly concerns payroll migration, platform transition, or parallel runs) | 7 |
| **`financial_reporting`** | `section_type = 'financial_reporting'` | `RPFF_2025_FUNDING_FUND_TRACKING` (conditional on funder/grant reporting); `PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT` (conditional on management/variance reporting) | 7 |
| **`financial_management`**| `section_type = 'financial_management'` | None (reporting and context chunks are confusers, not relevant) | 2 |
| **`compliance`** | `section_type = 'compliance'` | None (payroll compliance is confined to payroll) | 5 |
| **`audit`** | `section_type = 'audit'` | `section_type = 'compliance'` AND `'audit' = ANY(service_modules)` (hybrid audit-support chunks) | 5 |
| **`digital_transformation`**| `section_type = 'digital_transformation'` | None (operational bookkeeping modules are confusers, not transformation) | 8 |
| **`training`** | `'training' = ANY(service_modules)` | `'process_documentation' = ANY(service_modules)` ONLY IF query explicitly requests SOPs, process documentation, or workflow manuals | 7 |
| **`transition`** | `section_type IN ('transition', 'onboarding')` | None (recurring bookkeeping chunks are confusers, not transition) | 4 |
| **`context`** | `section_type = 'context_objectives'` | None (service modules are confusers, not context framing) | 2 |

### B. Eligibility Chunk Table (Complete Mapping for All 47 Chunks)

Every retrieval-enabled chunk is mapped below to its legitimate service families:

```
1. BOOKKEEPING (14 chunks):
   - CAHOOTS_2026_BIWEEKLY_BOOKKEEPING
   - CAHOOTS_2026_EXPENSE_AR
   - CAHOOTS_2026_MONTHLY_RECONCILIATIONS
   - CAREOF_2025_EXPENSE_MANAGEMENT
   - CAREOF_2025_MONTHLY_RECONCILIATIONS
   - CAREOF_2025_WEEKLY_BOOKKEEPING
   - GOODFOOT_2026_BOOKKEEPING
   - PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT
   - RPFF_2025_AP_AR
   - RPFF_2025_BOOKKEEPING_RECONCILIATIONS
   - RPFF_2025_FUNDING_FUND_TRACKING
   - TACT_2026_BOOKKEEPING
   - YPT_2026_AP_EXPENDITURES
   - YPT_2026_AR_REVENUES

2. PAYROLL (7 chunks):
   - CAHOOTS_2026_PAYROLL
   - CAREOF_2025_PAYROLL
   - GOODFOOT_2026_PAYROLL
   - PIRS_2025_PAYROLL
   - RPFF_2025_PAYROLL
   - TACT_2026_PAYROLL
   - TACT_2026_TRANSFORMATION_PAYROLL_MIGRATION (conditional: payroll migration)

3. FINANCIAL_REPORTING (7 chunks):
   - CAHOOTS_2026_FINANCIAL_REPORTING
   - CAREOF_2025_FINANCIAL_REPORTING
   - GOODFOOT_2026_FINANCIAL_REPORTING
   - PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT (conditional: management reporting)
   - RPFF_2025_FINANCIAL_REPORTING
   - RPFF_2025_FUNDING_FUND_TRACKING (conditional: funder tracking)
   - TACT_2026_FINANCIAL_REPORTING

4. FINANCIAL_MANAGEMENT (2 chunks):
   - GOODFOOT_2026_FINANCIAL_MANAGEMENT
   - PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT

5. COMPLIANCE (5 chunks):
   - CAHOOTS_2026_COMPLIANCE_YEAR_END
   - CAREOF_2025_COMPLIANCE_YEAR_END
   - GOODFOOT_2026_COMPLIANCE_AUDIT
   - RPFF_2025_COMPLIANCE_YEAR_END
   - TACT_2026_COMPLIANCE

6. AUDIT (5 chunks):
   - GOODFOOT_2026_COMPLIANCE_AUDIT
   - PIRS_2025_AUDIT_PREPARATION
   - RPFF_2025_COMPLIANCE_YEAR_END
   - TACT_2026_AUDIT_SUPPORT
   - TACT_2026_COMPLIANCE

7. DIGITAL_TRANSFORMATION (8 chunks):
   - GOODFOOT_2026_DIGITAL_TRANSFORMATION
   - PIRS_2025_TRAINING_CHANGE_MANAGEMENT
   - PIRS_2025_TRANSFORMATION_IMPLEMENTATION
   - PIRS_2025_TRANSFORMATION_STRATEGY
   - RPFF_2025_PROCESS_TECHNOLOGY
   - TACT_2026_TRANSFORMATION_AP_PLOOTO
   - TACT_2026_TRANSFORMATION_AR_AUTOMATION
   - TACT_2026_TRANSFORMATION_PAYROLL_MIGRATION

8. TRAINING (7 chunks):
   - PIRS_2025_TRAINING_CHANGE_MANAGEMENT (primary: training)
   - TACT_2026_TRANSFORMATION_PAYROLL_MIGRATION (primary: training)
   - GOODFOOT_2026_DIGITAL_TRANSFORMATION (conditional: process documentation)
   - GOODFOOT_2026_SETUP_TRANSITION_SCOPE (conditional: process documentation)
   - PIRS_2025_TRANSFORMATION_STRATEGY (conditional: process documentation)
   - TACT_2026_TRANSFORMATION_AR_AUTOMATION (conditional: process documentation)
   - YPT_2026_ONBOARDING_SETUP (conditional: process documentation)

9. TRANSITION (4 chunks):
   - GOODFOOT_2026_SETUP_TRANSITION_SCOPE
   - YPT_2026_CONTEXT_TRANSITION
   - YPT_2026_ONBOARDING_SETUP
   - YPT_2026_SYSTEMS_CONTINUITY

10. CONTEXT (2 chunks):
   - GOODFOOT_2026_CONTEXT_OBJECTIVES
   - TACT_2026_CONTEXT_OBJECTIVES
```

---

## 4. Benchmark Dataset Structure & Schema

The gold dataset is serialized to [`eval/retrieval_gold_v1.json`](file:///D:/Sympl/sympl-proposal-rag/eval/retrieval_gold_v1.json).

### Top-Level Benchmark Envelope
```json
{
  "benchmark_name": "sympl_retrieval_gold",
  "version": "1.1",
  "service_family_eligibility_version": "2.0",
  "revision_notes": "v1.1 = family-filter-aligned and source-fingerprint-hardened revision...",
  "created_from_corpus": {
    "proposal_count": 7,
    "total_chunks": 71,
    "retrieval_enabled_chunks": 47,
    "pricing_chunks_suppressed": 14,
    "boilerplate_chunks_suppressed": 10
  },
  "split_policy": {
    "dev": 60,
    "holdout": 20,
    "policy_description": "DEV split (60 queries) is designated for tuning retrieval parameters, prompt query augmentation, and metadata boost weights. HOLDOUT split (20 queries) is strictly reserved for unbiased evaluation of candidate embedding models and configurations."
  },
  "graded_relevance": {
    "primary": 3,
    "acceptable": 2,
    "optional": 1,
    "unrelated": 0
  },
  "queries": [ ... 80 query records ... ],
  "safety_filter_tests": [ ... 8 safety records (P001-P005, B001-B003) ... ]
}
```

---

## 5. Dataset Statistics & Balance (Recomputed from JSON v1.1)

### A. Core Metrics Summary
- **Total Semantic Evaluation Queries:** 80
  - **DEV Split (Tuning):** 60 (75.0%)
  - **HOLDOUT Split (Final Benchmark):** 20 (25.0%)
- **Safety Filter Tests:** 8 (5 pricing suppression: `P001`–`P005`, 3 boilerplate suppression: `B001`–`B003`)
- **Total Chunks in Corpus:** 71
- **Retrieval-Enabled Chunks:** 47
- **Retrieval-Enabled Chunk Coverage (Any Tier):** **47 / 47 (100.0%)**
- **Unique Chunks Used as Primary:** **45 / 47 (95.7%)**
- **Maximum Primary Frequency:** **4** (no chunk dominates; well below threshold of 7)
- **Total Relevance Occurrences:** **295** (80 Primary, 147 Acceptable, 68 Optional)
- **Final Family Filter Violations:** **0** (Primary: 0, Acceptable: 0, Optional: 0)
- **De-Identification Leaks:** **0**
- **Historical Numeric Fingerprints Remaining:** **0**
- **Invalid / Hallucinated Chunk Keys:** **0**

### B. Query Class Distribution
| Query Class | Count | Percentage | Description |
| :--- | :---: | :---: | :--- |
| **`direct_intent`** | 31 | 38.75% | Clear, structured description of a specific service requirement. |
| **`natural_discovery`**| 23 | 28.75% | Realistic intake language, discovery notes, and informal pain point descriptions. |
| **`confuser`** | 26 | 32.50% | Near-neighbor scenarios requiring precise scope discrimination. |
| **Total** | **80** | **100.0%** | |

### C. Difficulty Level Distribution
| Difficulty | Count | Target | Actual % | Description |
| :--- | :---: | :---: | :---: | :--- |
| **`easy`** | 20 | 20 | 25.0% | Direct match to a single service family with standard terminology. |
| **`medium`** | 35 | 35 | 43.75% | Natural language paraphrase with multiple metadata constraints (cadence, software). |
| **`hard`** | 25 | 25 | 31.25% | Cross-family confusers, responsibility boundaries, or system-state distinctions. |
| **Total** | **80** | **80** | **100.0%** | |

### D. Service Family Distribution
| Target Service Family | Query Count | Dev Count | Holdout Count | Unique Primaries | Eligible Chunks in Family |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`bookkeeping`** | 12 | 9 | 3 | 7 | 14 |
| **`payroll`** | 10 | 8 | 2 | 6 | 7 |
| **`financial_reporting`**| 9 | 7 | 2 | 7 | 7 |
| **`financial_management`**| 6 | 4 | 2 | 2 | 2 |
| **`compliance`** | 6 | 4 | 2 | 4 | 5 |
| **`audit`** | 8 | 6 | 2 | 3 | 5 |
| **`digital_transformation`**| 12 | 9 | 3 | 7 | 8 |
| **`training`** | 5 | 4 | 1 | 3 | 7 |
| **`transition`** | 7 | 5 | 2 | 4 | 4 |
| **`context`** | 5 | 4 | 1 | 2 | 2 |
| **Total** | **80** | **60** | **20** | **45** | **47 (100%)** |

### E. Proposal Representation Balance
The dataset prevents single-proposal dominance, ensuring compact non-profit proposals (Care/of, Cahoots, RPFF) are represented alongside comprehensive proposals (TACT, Good Foot, PIRS):

| Proposal Code | Historical Context | Primary Count | Any-Relevance Label Occurrences | Any-Relevance Queries Containing |
| :--- | :--- | :---: | :---: | :---: |
| **`CAREOF_2025`** | Compact non-profit bookkeeping & expense management | 5 | 25 | 23 |
| **`CAHOOTS_2026`** | Cultural charity bi-weekly bookkeeping & Wagepoint payroll | 7 | 33 | 32 |
| **`RPFF_2025`** | Arts festival restricted fund tracking & CADAC reporting | 8 | 43 | 39 |
| **`YPT_2026`** | 3-month transition, Sage 50 / Telpay continuity | 7 | 27 | 13 |
| **`GOODFOOT_2026`**| Social enterprise financial management & onboarding | 14 | 63 | 63 |
| **`TACT_2026`** | Comprehensive charity bookkeeping, AP/AR automation | 23 | 69 | 57 |
| **`PIRS_2025`** | Supervisory oversight, audit preparation, training | 16 | 35 | 31 |
| **Total** | | **80** | **295** | — |

---

## 6. Discrimination & Confuser Design

The 26 confuser queries explicitly test whether semantic retrieval can distinguish subtle scope boundaries without collapsing into keyword overlap.

### A. Explicit Hard Case Matrix (All 12 Mandatory Cases Verified)

| Hard Case | Query IDs | Primary Chunk Key | Family Filter Lineage | Main Ineligible Confusers (Documented in Notes) |
| :--- | :--- | :--- | :--- | :--- |
| **Case 1: PIRS Bookkeeping Oversight** | `Q006` | `PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT` | Explicit cross-type exception for `bookkeeping` | `GOODFOOT_2026_FINANCIAL_MANAGEMENT` (financial management), `TACT_2026_BOOKKEEPING` (full outsource) |
| **Case 2: PIRS Historical Audit Prep** | `Q045`, `Q047`, `Q051` | `PIRS_2025_AUDIT_PREPARATION` | `section_type = 'audit'` | `TACT_2026_AUDIT_SUPPORT` (routine PBC support), `YPT_2026_CONTEXT_TRANSITION` (transition) |
| **Case 3: TACT AP Automation** | `Q052`, `Q056`, `Q058` | `TACT_2026_TRANSFORMATION_AP_PLOOTO` | `section_type = 'digital_transformation'` | `TACT_2026_BOOKKEEPING`, `CAREOF_2025_EXPENSE_MANAGEMENT` (recurring bill entry) |
| **Case 4: TACT Payroll Migration** | `Q017` | `TACT_2026_TRANSFORMATION_PAYROLL_MIGRATION` | Conditional payroll exception (migration / parallel run) | `TACT_2026_PAYROLL`, `GOODFOOT_2026_PAYROLL` (recurring processing) |
| **Case 5: TACT AR Automation** | `Q053`, `Q057`, `Q059` | `TACT_2026_TRANSFORMATION_AR_AUTOMATION` | `section_type = 'digital_transformation'` | `CAHOOTS_2026_EXPENSE_AR`, `TACT_2026_BOOKKEEPING` (recurring manual invoicing) |
| **Case 6A: PIRS Strategy** | `Q054`, `Q060` | `PIRS_2025_TRANSFORMATION_STRATEGY` | `section_type = 'digital_transformation'` | `PIRS_2025_TRANSFORMATION_IMPLEMENTATION` (tactical setup vs diagnostic roadmap) |
| **Case 6B: PIRS Implementation** | `Q055`, `Q062` | `PIRS_2025_TRANSFORMATION_IMPLEMENTATION` | `section_type = 'digital_transformation'` | `PIRS_2025_TRANSFORMATION_STRATEGY` (strategic planning vs opening balance testing) |
| **Case 7: PIRS Training** | `Q064`, `Q065`, `Q068` | `PIRS_2025_TRAINING_CHANGE_MANAGEMENT` | `'training' = ANY(service_modules)` | `TACT_2026_TRANSFORMATION_AP_PLOOTO` (tool setup without coaching) |
| **Case 8: Process Documentation Only** | `Q066` | `GOODFOOT_2026_SETUP_TRANSITION_SCOPE` | Conditional training exception (`process_documentation`) | `PIRS_2025_TRAINING_CHANGE_MANAGEMENT` (live coaching sessions) |
| **Case 9: YPT Transition** | `Q069`, `Q072` | `YPT_2026_CONTEXT_TRANSITION` | `section_type = 'transition'` | `CAREOF_2025_WEEKLY_BOOKKEEPING`, `GOODFOOT_2026_BOOKKEEPING` (indefinite operational scope) |
| **Case 10: Compact Bookkeeping** | `Q001`, `Q002`, `Q003`, `Q007` | `CAREOF_2025_EXPENSE_MANAGEMENT`, `CAHOOTS_2026_BIWEEKLY_BOOKKEEPING`, etc. | `section_type IN ('bookkeeping', 'service_module')` | `TACT_2026_BOOKKEEPING` (5-program comprehensive charity module) |
| **Case 11: Audit vs Compliance** | `Q038`, `Q041`, `Q043` (Compliance) vs `Q044`, `Q048`, `Q049` (Audit) | Compliance chunks vs Audit Support chunks | Distinct section types (`compliance` vs `audit`) | Cross-family confusion between tax filing and CPA auditor PBC coordination |
| **Case 12: Financial Management vs Reporting** | `Q032`, `Q034` | `GOODFOOT_2026_FINANCIAL_MANAGEMENT` | `section_type = 'financial_management'` | `GOODFOOT_2026_FINANCIAL_REPORTING`, `TACT_2026_FINANCIAL_REPORTING` (historical statements) |

### B. System-State Testing (Current vs Proposed vs Under-Evaluation)
Eight queries explicitly test whether retrieval understands system lifecycle states:
- **`Q008` (Current Sage 50 + Telpay):** Operational AP bill payments within existing desktop tools.
- **`Q017` (Current ADP -> Proposed QBO Payroll):** Explicit migration initiative with parallel cycle testing (headcount de-identified to ~14 staff).
- **`Q018` (Current PayWorks Under Evaluation):** Stable payroll operation while evaluating potential software changes.
- **`Q020` (Current QBO Payroll Stability):** Maintaining payroll inside QBO while evaluating standalone platforms.
- **`Q022` (Immediate Execution vs Platform Evaluation):** Running regular payroll without disruption while evaluating future systems.
- **`Q054` (Current Spreadsheets -> Proposed Cloud Architecture):** Diagnostic review of legacy tools.
- **`Q055` (Proposed QBO Chart of Accounts Setup):** Active migration and chart of accounts restructuring.
- **`Q070` (Legacy System Continuity):** Explicit guarantee to preserve existing desktop environments without migration.
- **`Q074` (Interim Operational Finance Bridge):** Operational finance bridge without software modifications.

### C. Responsibility-Boundary Testing
Six queries test exact responsibility limits between Sympl and the client:
- **`Q006` (Supervisory Oversight Boundary):** In-house junior bookkeeper handles transaction entry; Sympl performs supervisory review.
- **`Q011` (Payment Release Authority):** Sympl enters vendor bills; Executive Director retains exclusive final payment release authority.
- **`Q019` (Manager Payroll Input Boundary):** Program managers must submit approved timesheets; Sympl does not handle HR administration.
- **`Q035` (Governance & Budget Boundary):** Board and Executive Director retain sole budget approval authority; Sympl provides financial modeling templates.
- **`Q044` (Auditor Attestation Boundary):** Sympl compiles PBC working papers; external CPA firm conducts independent audit and issues audit opinion.
- **`Q058` (AP Approval Tier Boundary):** Sympl implements Plooto workflows; client board/officers execute final bank authorization.

---

## 7. Safety Filter Testing Framework

Historical pricing chunks (14 chunks) and boilerplate chunks (10 chunks) are strictly retrieval-disabled (`retrieval_enabled = false`) for section-writer semantic retrieval.

To verify that future retrieval engines never leak commercial rates or boilerplate text when user queries contain financial keywords or company questions, eight dedicated safety tests are defined:

```
[User Query containing "$2,500 budget" or "hourly rates"]
                         │
                         ▼
             [RETRIEVAL ENGINE FILTER]
      Hard Constraint: pricing_content = false
      Hard Constraint: retrieval_enabled = true
                         │
                         ▼
     [Returns ONLY Operational Service Exemplars]
     Historical Pricing Chunks Returned: EXACTLY 0
```

### Safety Tests Summary (`P001` - `P005`, `B001` - `B003`)
- **`P001` (Bookkeeping Budget):** Query mentions "$2,500 per month budget" -> Returns operational bookkeeping; 0 pricing chunks.
- **`P002` (Payroll Fee Quote):** Query asks for "fee quote and hourly rate for 15 staff" -> Returns operational payroll; 0 pricing chunks.
- **`P003` (Audit Billing Rate):** Query asks for "hourly rate for year-end audit support" -> Returns audit coordination scope; 0 pricing chunks.
- **`P004` (Fixed-Fee Implementation Quote):** Query asks for "fixed-fee quote for QBO migration" -> Returns digital transformation scope; 0 pricing chunks.
- **`P005` (Fractional CFO Retainer):** Query asks for "monthly retainer fees for fractional CFO" -> Returns financial management scope; 0 pricing chunks.
- **`B001` (Why Us Credentials):** Query asks "Why should we choose Sympl? Tell us about team values" -> Handled via `sympl_reference_blocks`; 0 boilerplate chunks.
- **`B002` (Software Fee Exclusions):** Query asks "What exclusions apply to software fees?" -> Handled via canonical reference block; 0 boilerplate chunks.
- **`B003` (Backlog Disclaimers):** Query asks for "standard terms regarding catch-up backlog" -> Handled via canonical reference block; 0 boilerplate chunks.

---

## 8. Benchmark Evaluation Metrics (Specification for Next Phase)

When embedding models and retrieval configurations are evaluated in the next phase, the evaluation harness must calculate and report the following standard information-retrieval metrics across DEV and HOLDOUT splits:

### 1. Graded Relevance Scoring
- **Primary Relevant:** Relevance score = **3** (Production-eligible, best historical match)
- **Acceptable Relevant:** Relevance score = **2** (Production-eligible, substantial matching intent)
- **Optional Relevant:** Relevance score = **1** (Production-eligible, supporting example)
- **Unrelated / Ineligible Confusers:** Relevance score = **0**

### 2. Binary vs Graded Evaluation Thresholds
- **Binary Metrics (Hit@1, Hit@3, Recall@3, MRR):** Chunks with relevance grade $\ge 2$ (Primary and Acceptable) are treated as relevant hits. Optional chunks (grade 1) provide graded supporting context in nDCG@3 but do not count as primary binary targets.
- **Graded Metric (nDCG@3):** Uses the full graded scale ($3, 2, 1, 0$) to reward models that rank the Primary match ahead of Acceptable and Optional chunks:
  $$\text{DCG}@K = \sum_{i=1}^K \frac{2^{rel_i} - 1}{\log_2(i + 1)}$$

### 3. Required Performance Metrics
1. **Hit@1:** Proportion of queries where the top-1 retrieved chunk has relevance $\ge 2$.
2. **Hit@3:** Proportion of queries where at least one chunk in top-3 has relevance $\ge 2$.
3. **Recall@3:** Proportion of total relevant items (Primary + Acceptable) retrieved in the top-3 results.
4. **Mean Reciprocal Rank (MRR):** Reciprocal rank of the first relevant chunk ($\text{grade} \ge 2$).
5. **nDCG@3:** Normalized Discounted Cumulative Gain across the top-3 retrieved items.
6. **Family Eligibility Accuracy:** Percentage of retrieved chunks that satisfy the target service family's hard eligibility filter.
7. **Unsafe Retrieval Count:** Total count of pricing, boilerplate, or retrieval-disabled chunks returned. **Must be strictly 0.**

---

## 9. Model Selection & Indexing Protocol (Phase Guidelines)

### A. Model Selection Criteria
The upcoming benchmark phase will evaluate candidate embedding models (e.g. OpenAI `text-embedding-3-large`, `text-embedding-3-small`, Google Gemini embeddings, Voyage AI, etc.) under identical conditions:
1. **Holdout Generalization:** Superior performance on the 20 unseen holdout queries.
2. **Hard-Case Discrimination:** Accuracy on the 26 confuser queries and 12 special hard cases.
3. **Zero Safety Leakage:** Zero instances of pricing or boilerplate retrieval across all tests.
4. **Operational Simplicity & Stability:** Consistent vector normalization, stable cosine distances, and straightforward deployment.
5. **Latency & Cost:** Efficient inference latency and predictable token costs.

### B. Vector Indexing Policy
- **No Approximate Nearest Neighbor (ANN) Indexing:** With only 47 retrieval-enabled chunks, exhaustive flat cosine distance search (`ORDER BY embedding <=> query_vector LIMIT K`) executes in sub-millisecond time.
- Creating HNSW or IVFFlat indexes on a 47-row corpus introduces unnecessary indexing overhead and approximate recall degradation without any performance benefit. ANN indexing will be revisited only after the corpus expands significantly.

### C. Embedding Dimension Policy
- Dimension testing will evaluate whether reduced dimensions (e.g. 512 or 768 via Matryoshka representations) maintain retrieval accuracy compared to full-width embeddings (1536 or 3072).
- Zero embeddings are generated or committed during this evaluation dataset phase.

---
*End of Retrieval Evaluation Dataset Design Specification v1.1.*
