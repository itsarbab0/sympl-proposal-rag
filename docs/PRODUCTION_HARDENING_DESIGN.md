# Sympl Solutions Proposal RAG — Production Hardening Layer Design (Phase 6B)

## 1. Architectural Overview & Hardening Objectives

The **Production Hardening Layer** provides enterprise reliability, operational observability, asynchronous job scheduling, and rate/security protection around the frozen business engines of the Sympl Proposal RAG system (Planner, Writer, and Renderer).

```
                      +------------------------------------------+
                      |   Upstream Automation Engines / n8n     |
                      +------------------------------------------+
                                           │
                           HTTPS POST /proposal/generate/async
                           Headers: X-API-Key, X-Request-ID
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 sympl_api Gateway Layer                                │
│  - RequestSizeLimitMiddleware: Rejects payloads > 1MB (413 Payload Too Large)          │
│  - RequestIdMiddleware: Propagates or allocates X-Request-ID via ASGI contextvars      │
│  - Key Rotation Dependency: Validates X-API-Key against API_KEYS set                   │
│  - Input Scope Firewall Pre-Validation: Enforces approved_scope presence               │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                     ┌─────────────────────┴─────────────────────┐
                     ▼                                           ▼
       [POST /proposal/generate/async]               [POST /proposal/generate (Sync)]
                     │                                           │
                     ▼                                           │
       ┌───────────────────────────┐                             │
       │     JobTracker (DB)       │                             │
       │ - Inserts proposal_jobs   │                             │
       │   (status = CREATED)      │                             │
       │ - Hashes input payload    │                             │
       │ - Returns job_id instantly│                             │
       └─────────────┬─────────────┘                             │
                     │                                           │
                     ▼                                           │
       ┌───────────────────────────┐                             │
       │ LocalBackgroundExecutor   │                             │
       │ (ThreadPool / Celery-ready│                             │
       └─────────────┬─────────────┘                             │
                     │                                           │
                     ▼                                           ▼
       ┌─────────────────────────────────────────────────────────────────┐
       │             sympl_observability & Pipeline Orchestration        │
       │                                                                 │
       │   Stage 1: PLANNER ──► Records proposal_runs ('PLANNER', ms)   │
       │                       Saves artifact: proposal_plan.json        │
       │                                                                 │
       │   Stage 2: WRITER  ──► Records proposal_runs ('WRITER', ms)    │
       │                       Saves artifact: proposal_draft.json       │
       │                                                                 │
       │   Stage 3: RENDERER──► Records proposal_runs ('RENDERER', ms)  │
       │                       Saves artifact: rendered_proposal.json    │
       │                                                                 │
       │   Status: Updates proposal_jobs (COMPLETED / FAILED)            │
       │   Telemetry: Emits structured JSON metrics record               │
       └─────────────────────────────────┬───────────────────────────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
               [sympl_storage Layer]         [PostgreSQL Database]
               - LocalArtifactStore          - proposal_jobs (Tracking)
               - S3ArtifactStore (Ready)     - proposal_runs (Timings)
                                             - Frozen RAG Tables (Untouched)
```

### Core Architectural Invariants
1. **Zero Modifications to Frozen RAG Assets**:
   - `proposal_documents`: 7 unchanged
   - `proposal_chunks`: 71 unchanged
   - `embeddings`: 47 unchanged
   - `sympl_style_rules`: 21 unchanged
   - `sympl_reference_blocks`: 13 unchanged
   - `dataset_imports`: 7 unchanged
2. **Business Engine Purity**:
   - `sympl_planner`: Planner logic unchanged.
   - `sympl_writer`: Writer logic unchanged.
   - `sympl_renderer`: Renderer formatting unchanged.
3. **Dedicated Operational Tables**:
   - Asynchronous job metadata is isolated strictly to two new tables: `proposal_jobs` and `proposal_runs`.
   - Tables are created explicitly via migration script (`scripts/init_operational_tables.py`). Application startup verifies existence without executing DDL automatically.

---

## 2. Operational Database Schema

The operational schema manages state transitions and stage timings for asynchronous executions.

### 2.1 Table: `proposal_jobs`
Tracks top-level proposal generation lifecycle.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(64)` | `PRIMARY KEY` | Unique job identifier (`job_<12-hex-uuid>`). |
| `proposal_id` | `VARCHAR(64)` | `NULLABLE` | Generated proposal identifier (`prop_<12-hex-uuid>`) once allocated. |
| `status` | `VARCHAR(32)` | `NOT NULL` | Lifecycle state: `CREATED`, `RUNNING`, `COMPLETED`, `FAILED`. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Job submission timestamp. |
| `completed_at` | `TIMESTAMPTZ` | `NULLABLE` | Timestamp when the job finished or failed. |
| `error_message` | `TEXT` | `NULLABLE` | Sanitized error reason if status is `FAILED`. |
| `request_payload_hash`| `VARCHAR(64)` | `NULLABLE` | Deterministic SHA-256 hash of intake payload for audit and idempotency. |

### 2.2 Table: `proposal_runs`
Tracks fine-grained execution duration for each distinct pipeline stage.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(64)` | `PRIMARY KEY` | Unique stage run identifier (`run_<12-hex-uuid>`). |
| `job_id` | `VARCHAR(64)` | `REFERENCES proposal_jobs(id) ON DELETE CASCADE` | Associated parent job identifier. |
| `stage` | `VARCHAR(32)` | `NOT NULL` | Pipeline stage: `PLANNER`, `WRITER`, `RENDERER`. |
| `started_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Stage start timestamp. |
| `completed_at` | `TIMESTAMPTZ` | `NULLABLE` | Stage completion timestamp. |
| `duration_ms` | `DOUBLE PRECISION` | `NULLABLE` | Execution duration in milliseconds. |
| `status` | `VARCHAR(32)` | `NOT NULL` | Stage outcome: `RUNNING`, `COMPLETED`, `FAILED`. |

---

## 3. Asynchronous Job Execution Architecture

### 3.1 Job Submission: `POST /proposal/generate/async`
Provides a non-blocking gateway for long-running generation tasks.

- **Authentication**: Required (`X-API-Key`).
- **Input**: Standard Client Intake JSON.
- **Immediate Validation**:
  - Checks client name presence.
  - Enforces `approved_scope` presence (`APPROVAL_REQUIRED`).
  - Rejects empty `approved_scope` (`EMPTY_APPROVED_SCOPE`).
- **Response**: `202 Accepted` returned within < 50ms:
  ```json
  {
    "job_id": "job_e917d84a1209",
    "status": "CREATED",
    "request_id": "req_88192a9cb112",
    "message": "Proposal generation job queued successfully."
  }
  ```

### 3.2 Status Polling: `GET /proposal/status/{job_id}`
Allows upstream orchestration (e.g. n8n polling loops) to monitor job progress.

- **Authentication**: Required (`X-API-Key`).
- **Response Structure**:
  ```json
  {
    "job_id": "job_e917d84a1209",
    "status": "RUNNING",
    "current_stage": "WRITER",
    "progress": 0.66,
    "proposal_id": "prop_99182ab398ef"
  }
  ```
- **Progress Calculation**:
  - `CREATED`: `0.0` (Stage: `QUEUED`)
  - `PLANNER`: `0.1` -> `0.33` (Stage: `PLANNER`)
  - `WRITER`: `0.33` -> `0.66` (Stage: `WRITER`)
  - `RENDERER`: `0.66` -> `0.95` (Stage: `RENDERER`)
  - `COMPLETED`: `1.0` (Stage: `COMPLETED`)

### 3.3 Pluggable Worker Abstraction (`JobExecutor`)
The execution system is decoupled from local thread pools via the `JobExecutor` abstract base class:
```python
class JobExecutor(ABC):
    @abstractmethod
    def submit_job(self, job_id: str, payload: Dict[str, Any], request_id: str, orchestrator: Any) -> None:
        pass
```
- **Current Production Implementation**: `LocalBackgroundExecutor` uses a Python `ThreadPoolExecutor` (max workers configurable).
- **Future Scale**: Swapping to Celery, Redis Queue (RQ), or AWS SQS requires implementing a single `submit_job` adapter without touching API routes.

---

## 4. Production Observability & Telemetry

### 4.1 Structured JSON Logging
All application logs are formatted as single-line JSON objects using `StructuredJsonFormatter`:
```json
{
  "timestamp": "2026-09-07T01:54:30.123456Z",
  "level": "INFO",
  "request_id": "req_88192a9cb112",
  "logger": "sympl_observability",
  "message": "Proposal generation completed successfully in 2154.2ms",
  "module": "executor",
  "line": 105
}
```

### 4.2 Standardized Pipeline Telemetry Record
Every synchronous and asynchronous proposal generation emits a standardized telemetry record upon completion:
```json
{
  "request_id": "req_88192a9cb112",
  "proposal_id": "prop_99182ab398ef",
  "timestamp": "2026-09-07T01:54:30.123456Z",
  "stages": {
    "planner_ms": 142.5,
    "writer_ms": 1845.2,
    "renderer_ms": 110.8,
    "total_ms": 2098.5
  },
  "substages": {
    "retrieval_ms": 42.1,
    "llm_ms": 1780.0,
    "render_ms": 85.3
  },
  "status": "COMPLETED"
}
```

---

## 5. Artifact Storage Layer (`sympl_storage/`)

Generated proposal artifacts are decoupled from memory and persisted deterministically by proposal ID:

```
data/proposals/{proposal_id}/
  ├── proposal_plan.json      (Planner output)
  ├── proposal_draft.json     (Writer output)
  └── rendered_proposal.json  (Renderer presentation output)
```

- **`ArtifactStore` (ABC)**: Common contract for `save_plan()`, `save_draft()`, `save_render()`, `load_plan()`, `load_draft()`, and `load_render()`.
- **`LocalArtifactStore`**: Production local filesystem storage under `data/proposals/{proposal_id}/`.
- **`S3ArtifactStore`**: Ready extension interface for AWS S3 and Cloudflare R2 bucket persistence.

---

## 6. Security, Resilience & Rate Protection

### 6.1 Zero-Downtime API Key Rotation (`API_KEYS`)
- Authentication inspects `settings.get_valid_api_keys()`.
- Multiple active keys can be supplied as a comma-separated list via `API_KEYS="key_old,key_new"`.
- Enables rolling key rotation without interrupting active n8n workflows or external client integrations.

### 6.2 Production Environment Enforcement
- When `ENVIRONMENT=production`, authentication cannot be bypassed.
- Insecure default credentials (e.g. `sympl-proposal-secret-key-2026`) are rejected or flagged during startup.

### 6.3 Request Body Size Protection
- `RequestSizeLimitMiddleware` inspects `Content-Length` headers and stream volume.
- Requests with bodies exceeding 1MB (1,048,576 bytes) are immediately rejected with `HTTP 413 Payload Too Large`:
  ```json
  {
    "error": "PAYLOAD_TOO_LARGE",
    "message": "Request body exceeds maximum allowed size of 1MB.",
    "details": {"max_bytes": 1048576, "received_bytes": 1052300},
    "request_id": "req_..."
  }
  ```

### 6.4 LLM Timeout & Retry Policies
- **Timeout Guard**: 30 seconds enforced per LLM call.
- **Retry Policy**: Maximum 2 retries on transient network or formatting failures.
- **Error Sanitization**: `sanitize_error_message()` strips internal database connection strings, passwords, and private file paths before returning errors to clients.

---

## 7. Startup Diagnostics & Health Check

### 7.1 Startup Environment Verification
During application initialization (`lifespan`), `validate_environment()` performs comprehensive pre-flight verification:
1. `DATABASE_URL` connectivity.
2. Operational tables (`proposal_jobs`, `proposal_runs`) existence.
3. Embedding model library (`sentence_transformers`) availability.
4. Active LLM provider credentials (`OPENROUTER_API_KEY`, `GEMINI_API_KEY`).
5. Background worker pool readiness.

### 7.2 Enhanced Health Endpoint Contract: `GET /health`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "embedding": "available",
  "planner": "available",
  "writer": "available",
  "renderer": "available",
  "llm_provider": "mock",
  "worker": "ready"
}
```

---

## 8. Verification & Test Suite Summary

Phase 6B is verified by 5 automated test suites:
1. `pytest tests/test_production_hardening.py -v`: 10 tests covering async jobs, polling, recovery, telemetry, key rotation, size limits, and storage.
2. `pytest tests/test_api.py -v`: 11 tests covering all synchronous endpoints, auth, and scope firewall rules.
3. `pytest tests/test_writer.py -v`: 11 tests covering the Writer generation and validation layer.
4. `pytest tests/test_renderer.py -v`: 10 tests covering template compilation and Canva layouts.
5. `python tests/test_proposal_planner.py`: 11 tests covering the Planner decision engine and 10 client scenarios.
