# Sympl Solutions Proposal RAG — Production Deployment Guide (Phase 6C)

This guide documents the procedures for deploying the **Sympl Proposal RAG System** in local development, staging, and containerized production environments.

---

## 1. Architectural Architecture & Services

The production deployment consists of three decoupled container services running against PostgreSQL with `pgvector`:

```
                           Incoming HTTPS Traffic
                                     │
                                     ▼
                     ┌──────────────────────────────┐
                     │         Nginx Proxy          │
                     │  - Enforces 1MB body limit   │
                     │  - 60s proxy timeouts        │
                     │  - Security headers          │
                     └──────────────┬───────────────┘
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │                FastAPI API Service (Gunicorn)           │
       │  - 4 Uvicorn worker processes                           │
       │  - Authentication via API_KEYS rotation                 │
       │  - Serves synchronous /plan, /write, /render, /generate │
       │  - Enqueues async jobs to PostgreSQL & shared artifacts │
       └────────────────────────────┬────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
       ┌────────────────────────┐      ┌─────────────────────────┐
       │  PostgreSQL Database   │      │  Dedicated Worker Pod   │
       │  - Frozen RAG Tables   │◄─────┤  - Atomic job claiming  │
       │  - Operational Tables  │      │  - Planner -> Writer -> │
       │    (proposal_jobs,     │      │    Renderer pipeline    │
       │     proposal_runs)     │      │  - Emits telemetry      │
       └────────────────────────┘      └─────────────────────────┘
                    ▲                               ▲
                    │                               │
                    └──────── Shared Volume ────────┘
                             /app/data/proposals
                             (Intakes & Artifacts)
```

---

## 2. Database Layers & Migration Order

The database architecture is strictly divided into two distinct layers:

### Layer A: Frozen RAG Business Intelligence Layer
Contains pre-computed vector embeddings, reference blocks, and historical proposal corpora. **NEVER MUTATE OR RUN MIGRATIONS ON THESE TABLES**:

| Table | Invariant Target | Description |
| :--- | :--- | :--- |
| `proposal_documents` | **7 records** | Ingested source proposal documents. |
| `proposal_chunks` | **71 records** | Document chunks with section metadata. |
| `embeddings` | **47 chunks** | BGE-M3 1024-dimensional dense embeddings (`embedding IS NOT NULL`). |
| `sympl_style_rules` | **21 rules** | Authoritative tone and structural rules. |
| `sympl_reference_blocks` | **13 blocks** | Reusable boilerplate, compliance, and scope modules. |
| `dataset_imports` | **7 imports** | Ingestion lineage and audit tracking. |

### Layer B: Operational Tracking Layer
Manages asynchronous job scheduling, status polling, and stage execution latencies:

| Table | Migration Script | Description |
| :--- | :--- | :--- |
| `proposal_jobs` | `scripts/init_operational_tables.py` | Top-level job metadata, statuses (`CREATED`, `RUNNING`, `COMPLETED`, `FAILED`), and SHA-256 payload hashes. |
| `proposal_runs` | `scripts/init_operational_tables.py` | Fine-grained stage execution latencies for `PLANNER`, `WRITER`, and `RENDERER`. |

> [!IMPORTANT]
> **Migration Execution Rule**: Application startup never runs DDL automatically. You must run `python scripts/init_operational_tables.py` once prior to starting API and Worker containers.

---

## 3. Local Docker Deployment

For rapid local testing and development using Docker:

```bash
# 1. Start all services locally
docker compose up --build

# 2. Verify health
curl -f http://localhost:8000/health
```

---

## 4. Production Deployment Step-by-Step

### Step 1: Clone Repository
```bash
git clone https://github.com/sympl-solutions/sympl-proposal-rag.git /opt/sympl-proposal-rag
cd /opt/sympl-proposal-rag
```

### Step 2: Configure Production Environment
Copy `.env.production.example` to `.env.production` and populate production credentials:
```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Key configuration parameters to verify:
- `ENVIRONMENT=production`
- `DATABASE_URL`: Production PostgreSQL URI with SSL mode
- `API_KEYS`: Comma-separated list of cryptographically secure tokens
- `LLM_PROVIDER`: `openrouter` or `gemini`
- `DOCS_ENABLED=false`: Disables public Swagger/Redoc endpoints
- `STORAGE_DIR=/app/data/proposals`: Location of persistent shared volume

### Step 3: Run Operational Migrations
Execute the standalone operational migration script:
```bash
python scripts/init_operational_tables.py
```
Expected output:
```
[OK] Operational tables verified/created: proposal_jobs, proposal_runs.
[VERIFIED] Frozen RAG assets remain untouched: docs=7, chunks=71, embeddings=47, rules=21, refs=13, imports=7.
```

### Step 4: Build & Start Containers
Launch the production stack using Docker Compose:
```bash
# Build and run API, Worker, and Nginx containers in background
docker compose -f docker-compose.production.yml up -d --build
```

Container startup order:
1. `api`: Starts Gunicorn with 4 Uvicorn workers and validates environment.
2. `worker`: Starts the dedicated worker daemon after `api` passes health checks.
3. `nginx`: Binds ports 80 and 443, reverse proxying incoming traffic to `api:8000`.

### Step 5: Verify Deployment Health
Execute the automated health verification script:
```bash
python scripts/production_health_check.py
```
Or query the health endpoint through Nginx:
```bash
curl -i http://localhost/health
```
Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "embedding": "ready (BGE-M3 1024d)",
  "llm_provider": "openrouter",
  "worker": "ready (ThreadPoolExecutor)",
  "engines": {
    "planner": "available",
    "writer": "available",
    "renderer": "available"
  }
}
```

---

## 5. Worker Architecture & Scaling

The asynchronous execution architecture is designed to be **brokerless** and provider-agnostic, using PostgreSQL for coordination:

1. **Job Queuing**:
   - Upstream client calls `POST /proposal/generate/async`.
   - The API validates the intake schema and approved scope firewall.
   - A `proposal_jobs` record is created with `status = 'CREATED'`.
   - The intake payload is persisted to `/app/data/proposals/jobs/<job_id>/intake.json`.
   - `job_id` is immediately returned with HTTP 202.
2. **Safe Atomic Claiming**:
   - The `ProposalWorker` polls for `status = 'CREATED'`.
   - It claims the job using atomic SQL:
     ```sql
     UPDATE proposal_jobs 
     SET status = 'RUNNING', proposal_id = %s 
     WHERE id = %s AND status = 'CREATED' 
     RETURNING id;
     ```
   - If another worker claims the row first, the update returns empty and duplicate execution is prevented.
3. **Execution & Persistence**:
   - Worker loads intake payload from shared volume.
   - Reuses `sympl_observability.executor` to run:
     - `PLANNER` -> records run in `proposal_runs`, saves `proposal_plan.json`.
     - `WRITER`  -> records run in `proposal_runs`, saves `proposal_draft.json`.
     - `RENDERER`-> records run in `proposal_runs`, saves `rendered_proposal.json`.
   - Updates `proposal_jobs` status to `COMPLETED` (or `FAILED` with sanitized error message).
4. **Horizontal Scaling**:
   - Multiple worker containers can run concurrently against the same PostgreSQL database and shared volume.
   - To scale workers:
     ```bash
     docker compose -f docker-compose.production.yml up -d --scale worker=3
     ```

---

## 6. FastAPI Production Documentation Security

Interactive documentation endpoints (`/docs`, `/redoc`, and `/openapi.json`) can expose API structure and schemas. In production:

- Controlled via environment variable: `DOCS_ENABLED` (default: `false` in production).
- When `DOCS_ENABLED=false`:
  - `GET /docs` -> 404 Not Found
  - `GET /redoc` -> 404 Not Found
  - `GET /openapi.json` -> 404 Not Found
- To enable internal documentation behind a secure VPN or in staging:
  ```bash
  DOCS_ENABLED=true
  ```

---

## 7. Operational Monitoring & Logging

### Structured JSON Logs
All container logs are formatted as single-line JSON records:
```json
{
  "timestamp": "2026-09-07T02:14:31.291042+00:00",
  "level": "INFO",
  "request_id": "req_a1b2c3d4e5f6",
  "logger": "sympl_observability",
  "message": "Proposal pipeline finished with status: COMPLETED",
  "module": "telemetry",
  "line": 108,
  "telemetry": {
    "request_id": "req_a1b2c3d4e5f6",
    "proposal_id": "prop_998877665544",
    "stages": {
      "planner_ms": 312.4,
      "writer_ms": 450.8,
      "renderer_ms": 12.1,
      "total_ms": 775.3
    },
    "status": "COMPLETED"
  }
}
```

### Inspecting Container Logs
```bash
# View API service logs
docker compose -f docker-compose.production.yml logs -f api

# View Worker service logs
docker compose -f docker-compose.production.yml logs -f worker

# View Nginx access and error logs
docker compose -f docker-compose.production.yml logs -f nginx
```
