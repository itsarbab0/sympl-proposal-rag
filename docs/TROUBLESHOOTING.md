# Sympl Solutions Proposal RAG — Deployment Troubleshooting Guide (Phase 7)

This runbook provides diagnostic commands, root causes, and remediation procedures for common operational issues encountered in production deployments.

---

## 1. Database Connection Failures

### Symptoms
- Startup fails with `PostgreSQL connection failed` or `EnvironmentValidationError`.
- `GET /health` reports `"database": "unreachable"`.
- Asynchronous jobs fail immediately in `INITIALIZING` stage.

### Potential Causes & Remediation

#### A. Incompatible SSL Mode
- **Cause**: Cloud providers (Railway, Supabase, Neon, AWS RDS) require SSL connections by default.
- **Fix**: Append `?sslmode=require` (or `?sslmode=prefer`) to `DATABASE_URL`:
  ```ini
  DATABASE_URL=postgresql://postgres:password@host:5432/dbname?sslmode=require
  ```

#### B. Internal Network vs Public Proxy in Railway
- **Cause**: Connecting from an external machine to Railway's private internal domain (`postgres.railway.internal`) instead of the public TCP proxy (`junction.proxy.rlwy.net:port`).
- **Fix**:
  - From within Railway services: Use private domain `${{Postgres.DATABASE_URL}}`.
  - From local machine / CI runners: Use public connection string provided in Railway's Connect tab.

#### C. Missing `pgvector` Extension
- **Symptoms**: Error `type "vector" does not exist` during semantic search.
- **Fix**: Connect to PostgreSQL via psql or Railway Query tool and run:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```

#### D. Missing Operational Tables
- **Symptoms**: Health check reports `Operational tables (proposal_jobs, proposal_runs) missing`.
- **Fix**: Run the operational migration script:
  ```bash
  python scripts/init_operational_tables.py
  ```

---

## 2. LLM Generation Failures

### Symptoms
- Job completes `PLANNER` stage, but fails in `WRITER` stage with `WriterError` or `LLM generation failed`.
- `proposal_runs` displays `stage="WRITER", status="FAILED"`.

### Potential Causes & Remediation

#### A. Invalid or Missing API Credentials
- **Check**: Verify that `OPENROUTER_API_KEY` (or `GEMINI_API_KEY`) is populated and has active billing credits.
- **Diagnostic Command**:
  ```bash
  curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/auth/key
  ```

#### B. Provider Rate Limiting (HTTP 429)
- **Cause**: Upstream LLM provider rate limit exceeded.
- **Remediation**:
  - Increase retry budget: `LLM_MAX_RETRIES=3`.
  - The system automatically catches transient rate limits and sanitizes error responses.
  - Temporarily switch to fallback provider (e.g., `gemini`) by setting `LLM_PROVIDER=gemini`.

#### C. LLM Generation Timeout
- **Symptoms**: Request terminates after exactly 30 seconds.
- **Fix**: Increase timeout threshold in environment variables:
  ```ini
  LLM_TIMEOUT_SECONDS=45
  ```

---

## 3. Worker Not Consuming Jobs

### Symptoms
- `POST /proposal/generate/async` returns `job_id` with `status: "CREATED"`.
- `GET /proposal/status/{job_id}` stays in `QUEUED` / `CREATED` indefinitely without transitioning to `RUNNING`.

### Potential Causes & Remediation

#### A. Worker Service Process Not Running
- **Check**: In Railway, verify the `sympl-worker` service is deployed and running.
- **Check Logs**:
  ```bash
  docker compose -f docker-compose.production.yml logs -f worker
  ```
  Expected startup log:
  ```
  [INFO] Worker initialized and ready. Polling every 2.0s...
  ```
- **Fix**: Ensure the service start command is set to:
  ```bash
  python -m sympl_observability.worker
  ```

#### B. Storage Volume Isolation (Missing Intake Payload)
- **Symptoms**: Worker log shows `Missing intake payload for job job_xxxx. Cannot proceed.`
- **Cause**: API container and Worker container do not share the artifact filesystem.
- **Fix**:
  - In Docker Compose: Ensure both services mount the same named volume `shared_artifacts:/app/data/proposals`.
  - In Railway: Configure a Railway Volume mounted at `/app/data/proposals` or verify both services write to shared disk (`STORAGE_DIR=/app/data/proposals`).

#### C. Operational Tables Uninitialized
- **Symptoms**: Worker logs `Operational tables missing. Worker aborting.`
- **Fix**: Run `python scripts/init_operational_tables.py` before starting worker containers.

---

## 4. Nginx Reverse Proxy Errors

### Symptoms
- Client receives `502 Bad Gateway`, `413 Request Entity Too Large`, or `504 Gateway Timeout`.

### Potential Causes & Remediation

#### A. HTTP 413 Payload Too Large
- **Cause**: Client payload exceeds 1MB.
- **Fix**: Confirm client intake JSON payload is within 1MB. Ensure Nginx directive matches API middleware:
  ```nginx
  client_max_body_size 1M;
  ```

#### B. HTTP 502 Bad Gateway
- **Cause**: Nginx cannot connect to the FastAPI application upstream (`api:8000`).
- **Fix**:
  - Verify API container is running: `docker compose -f docker-compose.production.yml ps`.
  - Verify API container is healthy on port 8000: `docker exec -it sympl-proposal-api curl http://localhost:8000/health`.
  - Check Nginx upstream name in `nginx/nginx.conf` matches service name `api:8000`.

#### C. HTTP 504 Gateway Timeout
- **Cause**: Pipeline processing took longer than Nginx proxy read timeout.
- **Fix**: Ensure asynchronous generation (`POST /proposal/generate/async`) is used rather than synchronous generation for large documents. Increase proxy timeout in `nginx/nginx.conf`:
  ```nginx
  proxy_read_timeout 60s;
  proxy_send_timeout 60s;
  ```

---

## 5. Authentication & Authorization Failures

### Symptoms
- API returns `HTTP 401 Unauthorized` with `{"error": "UNAUTHORIZED", "message": "..."}`.

### Potential Causes & Remediation

#### A. Missing `X-API-Key` Header
- **Cause**: Client did not pass the required authentication header.
- **Fix**: Include the header in HTTP requests:
  ```bash
  curl -H "X-API-Key: your_production_api_key" https://<domain>/proposal/status/<job_id>
  ```

#### B. Key Rotation Mismatch
- **Cause**: Client is using an old or retired key.
- **Fix**: Verify client token is present in the comma-separated `API_KEYS` environment variable:
  ```ini
  API_KEYS=key_current_active,key_new_rotation
  ```
- **Note**: `API_KEYS` supports multiple active keys simultaneously to enable zero-downtime rotation.

#### C. Production Mode Auth Enforcement
- **Cause**: In production (`ENVIRONMENT=production`), authentication cannot be bypassed. The hardcoded development key (`sympl-proposal-secret-key-2026`) is automatically disabled.
- **Fix**: Generate and configure explicit cryptographic keys in `API_KEYS`.

---

## 6. Diagnostic Runbook Commands

```bash
# 1. Check end-to-end production health and database invariants
python scripts/production_health_check.py

# 2. Run automated async smoke test against live deployment
python scripts/production_smoke_test.py --url https://<service-url> --api-key <key>

# 3. Direct verification of frozen database invariants
python -c "import psycopg; conn = psycopg.connect('$DATABASE_URL'); cur = conn.cursor(); print('docs:', cur.execute('SELECT count(*) FROM proposal_documents').fetchone()[0]); print('chunks:', cur.execute('SELECT count(*) FROM proposal_chunks').fetchone()[0]); print('embeddings:', cur.execute('SELECT count(*) FROM proposal_chunks WHERE embedding IS NOT NULL').fetchone()[0])"
```
