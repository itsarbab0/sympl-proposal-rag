# Sympl Solutions Proposal RAG — Railway Deployment Checklist (Phase 7)

This checklist provides step-by-step instructions for deploying the **Sympl Proposal RAG System** onto [Railway](https://railway.app/).

---

## 1. Railway Architecture Overview

In Railway, the deployment architecture is structured as two container services and an attached managed PostgreSQL database with the `pgvector` extension:

```
                            Client / n8n / Webhooks
                                      │
                                      ▼
                        HTTPS (Managed Railway Ingress)
                                      │
                                      ▼
               ┌──────────────────────────────────────────────┐
               │              Railway API Service             │
               │  - Gunicorn + 4 Uvicorn workers              │
               │  - Listens on Railway dynamic $PORT          │
               │  - Automatic HTTPS / TLS termination         │
               │  - Enqueues async jobs to PostgreSQL         │
               └──────────────────────┬───────────────────────┘
                                      │
                     ┌────────────────┴────────────────┐
                     ▼                                 ▼
       ┌───────────────────────────┐     ┌───────────────────────────┐
       │     Railway PostgreSQL    │     │   Railway Worker Service  │
       │     (pgvector template)   │◄────┤   - Background job runner │
       │  - Frozen RAG assets (6)  │     │   - Polls proposal_jobs   │
       │  - Operational tables (2) │     │   - Planner->Writer->     │
       └───────────────────────────┘     │     Renderer pipeline     │
                                         └───────────────────────────┘
```

> [!NOTE]
> **Nginx is Optional on Railway**:
> In local and self-hosted deployments (`docker-compose.production.yml`), Nginx acts as the reverse proxy for SSL and header enforcement. On Railway, Railway's edge network automatically handles SSL termination, custom domain routing, and HTTPS forwarding.

---

## 2. Railway Pre-Flight Compatibility Audit

The Sympl Proposal RAG codebase has been specifically validated for Railway deployment:

1. **Dynamic `$PORT` Compatibility**:
   - `Dockerfile` entrypoint dynamically binds to Railway's injected port:
     `gunicorn sympl_api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000}`
   - Healthcheck checks `http://127.0.0.1:${PORT:-8000}/health`.
2. **Zero `localhost` Assumptions**:
   - Database connections use `DATABASE_URL` exclusively.
   - Cross-container and external communications use explicit host headers and request URLs.
3. **Railway `DATABASE_URL` Compatibility**:
   - `psycopg` natively supports both `postgresql://` and `postgres://` connection strings injected by Railway.
   - Private networking via Railway internal domain (e.g. `postgres.railway.internal`) is supported.
4. **Worker Independent Execution**:
   - The worker runs as an independent background service executing:
     `python -m sympl_observability.worker`
   - Consumes jobs from PostgreSQL without requiring an external message broker (no Redis, Celery, or RabbitMQ).
5. **Artifact Storage on Railway Filesystem**:
   - Supports ephemeral container storage by default or a mounted Railway persistent volume (e.g. at `/app/data/proposals` configured via `STORAGE_DIR`).

---

## 3. Step-by-Step Railway Deployment Guide

### Step 1: Create a Railway Project
1. Log in to [Railway Dashboard](https://railway.app/).
2. Click **New Project** -> **Empty Project**.
3. Name your project: `sympl-proposal-rag-production`.

### Step 2: Provision PostgreSQL Database with pgvector
1. Click **+ New** -> **Database** -> **Add PostgreSQL**.
2. Alternatively, deploy the official Railway **pgvector template**.
3. In the PostgreSQL service settings, verify that `pgvector` is enabled by running:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. Verify connection string in **Variables** tab under `DATABASE_URL`.

### Step 3: Connect GitHub Repository
1. Click **+ New** -> **GitHub Repo**.
2. Select `sympl-solutions/sympl-proposal-rag` (or your repository fork).
3. Railway will analyze the repository and detect the root `Dockerfile`.

### Step 4: Configure the API Service
Rename this service to `sympl-api`:
1. **Settings** -> **General**:
   - Service Name: `sympl-api`
2. **Settings** -> **Build & Deploy**:
   - Builder: `DOCKERFILE` (uses `/Dockerfile`)
   - Healthcheck Path: `/health`
   - Healthcheck Timeout: `15` seconds
3. **Settings** -> **Networking**:
   - Click **Generate Domain** (e.g., `sympl-api-production.up.railway.app`).
4. **Variables** (Add the required environment variables listed below).

### Step 5: Configure the Worker Service
Add a second service pointing to the same repository:
1. Click **+ New** -> **GitHub Repo** -> select the same repository.
2. Rename service to `sympl-worker`.
3. **Settings** -> **Deploy**:
   - Custom Start Command:
     ```bash
     python -m sympl_observability.worker
     ```
   - (Leave Networking / Public Domain unconfigured; workers operate as background jobs).
4. **Variables**: Link the same environment variables (or use Railway Shared Variables).

### Step 6: Environment Variables Configuration

Add these variables to **Shared Variables** or directly to both `sympl-api` and `sympl-worker`:

```ini
# Database (Reference Railway's PostgreSQL variable)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Environment & Security
ENVIRONMENT=production
API_KEYS=prod-live-key-alpha-2026,prod-live-key-beta-2026
DOCS_ENABLED=false
CORS_ORIGINS=https://app.sympl.com,https://n8n.sympl.com

# LLM Engine Configuration
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Semantic Embeddings
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIMENSION=1024

# Resilience Limits
MAX_REQUEST_SIZE_BYTES=1048576
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
WORKER_POLL_INTERVAL=2.0
STORAGE_DIR=/app/data/proposals
```

---

## 4. Operational Migration Execution

Before serving traffic, populate the operational tracking tables:
1. Open the **sympl-api** service in Railway.
2. Go to **Deployments** -> Click **...** on the active deployment -> **Deploy Shell** (or use Railway CLI).
3. Execute the migration:
   ```bash
   python scripts/init_operational_tables.py
   ```
4. Verify output:
   ```
   [OK] Operational tables verified/created: proposal_jobs, proposal_runs.
   [VERIFIED] Frozen RAG assets remain untouched: docs=7, chunks=71, embeddings=47, rules=21, refs=13, imports=7.
   ```

---

## 5. Health Verification & Smoke Testing

### 1. Health Endpoint Verification
Query the generated Railway domain:
```bash
curl -i https://<your-service-domain>.up.railway.app/health
```
Expected output:
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

### 2. Live Smoke Test Execution
Run the production smoke test pointing directly to your live Railway deployment:
```bash
python scripts/production_smoke_test.py \
  --url https://<your-service-domain>.up.railway.app \
  --api-key <one-of-your-API_KEYS>
```

Expected output:
```
==============================================================================
  Sympl Solutions Proposal RAG — Production Smoke Test (Phase 7)
  Target Endpoint: https://sympl-api-production.up.railway.app
==============================================================================

[Step 1/3] Validating /health endpoint...
  [OK] Service healthy (status=healthy, db=connected, llm=openrouter)

[Step 2/3] Submitting async proposal generation job...
  [OK] Async proposal generation job submitted successfully: job_xxxx

[Step 3/3] Polling job status for job_xxxx...
  [2.1s] Status: RUNNING | Stage: PLANNER | Progress: 0.1
  [14.2s] Status: RUNNING | Stage: WRITER | Progress: 0.33
  [24.5s] Status: RUNNING | Stage: RENDERER | Progress: 0.66
  [28.1s] Status: COMPLETED | Stage: COMPLETED | Progress: 1.0

  [OK] Async Proposal Lifecycle Completed Successfully!
==============================================================================
  RESULT: PRODUCTION SMOKE TEST PASSED (100% OPERATIONAL)
==============================================================================
```

The system is now fully live and ready for n8n integration on Railway.
