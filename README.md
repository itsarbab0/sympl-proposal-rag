# Sympl Solutions — Proposal RAG Database Foundation

Production-quality data and database foundation for automated proposal generation at **Sympl Solutions**.

---

## 1. Purpose & Architecture

Sympl Solutions serves non-profits, charities, and early-stage organisations with bookkeeping, payroll, compliance, and financial management. This repository implements **Phase 1B: Database & Dataset Foundation** of the proposal generation pipeline.

### End-to-End Pipeline Overview

```
Historical Sympl Proposals (data/raw/)
               ↓
Structured Proposal Knowledge Base (data/normalized/)
               ↓
Embeddings (pgvector)
               ↓
PostgreSQL 18 + pgvector 0.8.6 (Railway Pro)
               ↓
Section-Aware RAG Retrieval
               ↓
LLM Proposal Generation (with Style Rules & Reference Blocks)
               ↓
Human Review & Pricing Approval
               ↓
Canva Template Export
               ↓
Editable Final Proposal
```

*Note: Phase 1B establishes the database schema, data contract, validator, importer, and test harnesses. Embedding generation, LLM prompts, and orchestration are deferred to later phases.*

---

## 2. Core Architectural & Safety Invariants

- **Normal RAG Retrieval Rule**: `proposal_chunks` used for semantic content retrieval must normally have `retrieval_enabled = TRUE`.
- **Historical Pricing Safety & Retention**: Historical pricing rows must have `pricing_content = TRUE`, `commercial_reference_only = TRUE`, and `retrieval_enabled = FALSE` (enforced by database check constraint `chk_pricing_safety`). Historical pricing is **NOT deleted**; it is retained strictly as commercial reference material for proposal structure and layout. It must **NEVER** drive, infer, or calculate new client pricing.
- **Historical Boilerplate Safety**: Historical boilerplate rows must have `boilerplate_content = TRUE` and `retrieval_enabled = FALSE` (enforced by check constraint `chk_boilerplate_retrieval`). Approved reusable boilerplate belongs in `sympl_reference_blocks` and is inserted deterministically, not through semantic similarity.
- **Reference Blocks**: Approved, version-controlled standard Sympl content (disclaimers, standard exclusions, why us, client responsibilities) is maintained in `sympl_reference_blocks`.
- **Style Rules**: Firm-wide tone, terminology, and syntax directives reside in `sympl_style_rules` for direct prompt injection.
- **Unconstrained Vector Dimension**: The `embedding` column in `proposal_chunks` uses the unconstrained `VECTOR` type until the embedding model is benchmarked and finalized.
- **Import Idempotency**: Enforced at the database level with a partial unique index on `dataset_imports(source_name, source_hash)` for completed imports.
- **No ORM**: Uses direct parameterized PostgreSQL SQL and `psycopg 3` for maximum performance, predictability, and auditability.

---

## 3. Environment Setup

### 3.1. Prerequisites
- Python 3.12+
- PostgreSQL 18 with pgvector 0.8.6+

### 3.2. Virtual Environment Setup

**Create environment:**
```bash
python -m venv .venv
```

**Activate environment:**
- **Windows (Command Prompt / PowerShell):**
  ```powershell
  .venv\Scripts\activate
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

### 3.3. Database Configuration

Set your connection string via the `DATABASE_URL` environment variable. Never hardcode or commit credentials into source control.

- **PowerShell:**
  ```powershell
  $env:DATABASE_URL="postgresql://username:password@host:port/database"
  ```
- **Bash / Zsh:**
  ```bash
  export DATABASE_URL="postgresql://username:password@host:port/database"
  ```
- **Local Development (.env file):**
  Copy `.env.example` to `.env` and populate your connection string:
  ```bash
  cp .env.example .env
  ```
  *(Note: `.env` is ignored by `.gitignore` to prevent credential exposure).*

---

## 4. Operational Workflows

### 4.1. Manual Migration Execution
To apply the initial schema migration against your PostgreSQL database:

Using `psql`:
```bash
psql "$DATABASE_URL" -f db/migrations/001_initial_schema.sql
```

Using Python / psycopg (one-liner):
```bash
python -c "import os, psycopg; conn = psycopg.connect(os.environ['DATABASE_URL']); cur = conn.cursor(); cur.execute(open('db/migrations/001_initial_schema.sql', encoding='utf-8').read()); conn.commit(); print('Migration successfully applied.')"
```

### 4.2. Verify Database Status
Run the non-destructive diagnostic test utility to check connection, server version, pgvector status, table existence, and transaction isolation:

```bash
python scripts/test_database.py
```

### 4.3. Validate Normalized Datasets
Before ingestion, validate all normalized JSON proposal documents in `data/normalized/`:

```bash
python scripts/validate_dataset.py
```
This utility:
- Verifies JSON structure and data types.
- Enforces pricing safety constraints (`pricing_content` -> `commercial_reference_only`).
- Detects duplicate `proposal_code` or `chunk_key` values.
- Issues warnings for unknown service modules or section types.
- Exits with code `0` on success and `1` on hard errors. Never alters source files.

### 4.4. Ingest Normalized Proposals
To import or update verified JSON proposals into the database:

```bash
python scripts/import_dataset.py
```
This utility:
- Automatically runs pre-import validation.
- Computes SHA-256 hashes of each file to prevent duplicate imports.
- Upserts documents and chunks transactionally.
- Audits import activity in `dataset_imports`.
- Ensures embeddings remain `NULL` until Phase 2.

---

## 5. Directory Structure

```
sympl-proposal-rag/
│
├── db/
│   └── migrations/
│       └── 001_initial_schema.sql      # PostgreSQL 18 + pgvector DDL
│
├── data/
│   ├── raw/
│   │   └── README.md                   # Immutable source proposals guideline
│   │
│   └── normalized/
│       └── README.md                   # Curated JSON proposal repository
│
├── scripts/
│   ├── validate_dataset.py             # Pre-ingestion validation utility
│   ├── import_dataset.py               # psycopg 3 transactional ingestion utility
│   └── test_database.py                # Read/safe database verification test
│
├── docs/
│   ├── DATA_CONTRACT.md                # Comprehensive JSON schema specification
│   └── DATABASE_SCHEMA.md              # Schema architecture & invariant documentation
│
├── .env.example                        # Template for environment configuration
├── .gitignore                          # Version control exclusions
├── requirements.txt                    # Minimal dependencies (psycopg[binary]>=3.2)
└── README.md                           # Setup and operations guide
```
