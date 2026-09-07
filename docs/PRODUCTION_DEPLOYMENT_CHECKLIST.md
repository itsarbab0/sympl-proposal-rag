# Sympl Solutions Proposal RAG — Production Deployment Checklist (Phase 7)

This checklist outlines the mandatory verification gates, deployment steps, operational migration order, and rollback procedures for deploying the **Sympl Proposal RAG System** to production environments.

---

## 1. Pre-Deployment Secrets & Configuration Inventory

Ensure the following secrets and environment variables are populated in your target platform (e.g. Railway, Kubernetes Secrets, or Docker Compose `.env.production`):

| Variable Name | Criticality | Purpose / Example Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | **Mandatory** | PostgreSQL URI with pgvector extension (`postgresql://user:pass@host:5432/dbname?sslmode=require`). |
| `ENVIRONMENT` | **Mandatory** | Set strictly to `production` to activate security controls. |
| `API_KEYS` | **Mandatory** | Comma-separated list of 32+ char secret keys (`key_live_alpha_2026,key_live_beta_2026`). |
| `LLM_PROVIDER` | **Mandatory** | Active writer LLM engine (`openrouter` or `gemini`). |
| `OPENROUTER_API_KEY` | **Conditional** | Required if `LLM_PROVIDER=openrouter`. |
| `OPENROUTER_MODEL` | Optional | LLM model name (default: `anthropic/claude-3.5-sonnet`). |
| `GEMINI_API_KEY` | **Conditional** | Required if `LLM_PROVIDER=gemini`. |
| `EMBEDDING_MODEL` | Optional | Semantic retrieval model (default: `BAAI/bge-m3`). |
| `EMBEDDING_DIMENSION`| Optional | Dense vector dimensionality (`1024`). |
| `CORS_ORIGINS` | Recommended | Allowed consumer domains (`https://app.sympl.com,https://n8n.sympl.com`). |
| `DOCS_ENABLED` | Recommended | Set to `false` in production to hide interactive Swagger/Redoc UI. |
| `STORAGE_DIR` | Optional | Base path for persistent storage (default: `/app/data/proposals`). |
| `MAX_REQUEST_SIZE_BYTES` | Optional | Payload size limit (default: `1048576` = 1MB). |
| `LLM_TIMEOUT_SECONDS` | Optional | Timeout limit for generation calls (default: `30`). |
| `LLM_MAX_RETRIES` | Optional | Retries for transient LLM generation failures (default: `2`). |

---

## 2. Database Setup & Invariant Safeguards

The database consists of two strictly isolated layers:

### Layer A: Frozen RAG Assets (ZERO MODIFICATIONS PERMITTED)
Before initiating deployment, verify that all 6 historical tables match their exact invariant counts:
```sql
SELECT count(*) FROM proposal_documents;       -- MUST EQUAL 7
SELECT count(*) FROM proposal_chunks;          -- MUST EQUAL 71
SELECT count(*) FROM proposal_chunks 
WHERE embedding IS NOT NULL;                   -- MUST EQUAL 47
SELECT count(*) FROM sympl_style_rules;        -- MUST EQUAL 21
SELECT count(*) FROM sympl_reference_blocks;   -- MUST EQUAL 13
SELECT count(*) FROM dataset_imports;          -- MUST EQUAL 7
```

### Layer B: Operational Tracking Layer
Run the operational database migration to ensure `proposal_jobs` and `proposal_runs` exist:
```bash
python scripts/init_operational_tables.py
```
> [!NOTE]
> Application startup does **NOT** auto-create tables via DDL. Running `scripts/init_operational_tables.py` is the only authorized method for provisioning operational schema.

---

## 3. Container & Service Startup Order

In containerized deployments, execute the following startup sequence:

```
Step 1: Provision / Verify PostgreSQL (pgvector enabled)
  │
  ▼
Step 2: Run Operational Migration (python scripts/init_operational_tables.py)
  │
  ▼
Step 3: Start API Service (Gunicorn + 4 Uvicorn workers)
  │  └─ Validates environment and checks operational tables on startup
  ▼
Step 4: Start Worker Service (python -m sympl_observability.worker)
  │  └─ Begins polling proposal_jobs for status = 'CREATED'
  ▼
Step 5: Start Nginx Edge Gateway (Optional if using platform ingress like Railway)
     └─ Routes traffic to API with 1MB body limit and security headers
```

---

## 4. Pre-Flight Health Verification

Run the automated health check prior to routing client or n8n traffic:
```bash
python scripts/production_health_check.py
```
Verification criteria:
- [x] API Service returns HTTP 200 on `/health`
- [x] PostgreSQL connection active
- [x] `pgvector` extension enabled
- [x] Operational tables (`proposal_jobs`, `proposal_runs`) present
- [x] All 6 frozen invariant counts verified
- [x] Business engines (Planner, Writer, Renderer) operational
- [x] LLM provider configured

---

## 5. End-to-End Smoke Test

Run the production smoke test against the deployed target:
```bash
python scripts/production_smoke_test.py --url https://<your-service-domain> --api-key <your-api-key>
```
Verification criteria:
- [x] `GET /health` returns `status="healthy"`
- [x] `POST /proposal/generate/async` returns HTTP 202 with `job_id`
- [x] `GET /proposal/status/{job_id}` transitions through `CREATED` -> `RUNNING` -> `COMPLETED`
- [x] Generated `proposal_id` exists and progress reaches `1.0`
- [x] Output artifacts (`proposal_plan.json`, `proposal_draft.json`, `rendered_proposal.json`) verified in storage

---

## 6. Zero-Downtime Rollback Procedure

If unexpected errors or health check failures occur during or immediately following deployment:

### 1. Ingress & Traffic Redirection
- Point upstream workflow engines (n8n, webhooks) to the previous stable release or pause queue triggers.

### 2. Container Rollback
- **Railway / Cloud Platforms**: Select the previous deployment in the platform dashboard and trigger **Rollback**.
- **Docker Compose**:
  ```bash
  # Rollback to previous container image tag
  docker compose -f docker-compose.production.yml down
  # Deploy previous verified image
  IMAGE_TAG=v1.0.0 docker compose -f docker-compose.production.yml up -d
  ```

### 3. Database State Safety
- **No DDL Rollback Required**: The operational tables (`proposal_jobs`, `proposal_runs`) are additive and backward-compatible.
- **Frozen Tables**: Since frozen RAG tables are never mutated by any pipeline stage, no database restore is necessary.

### 4. Verification Post-Rollback
Re-run the health verification script:
```bash
python scripts/production_health_check.py
```
Confirm all systems report `[OK]` status.
