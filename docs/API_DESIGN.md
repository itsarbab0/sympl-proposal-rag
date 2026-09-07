# Sympl Solutions Proposal RAG — API Design & Orchestration Layer (Phase 6A)

## 1. Architectural Overview & System Role

The **Sympl Proposal API Layer** (`sympl_api`) serves as the production HTTP gateway and orchestration layer for the Sympl Proposal RAG system. It exposes standardized REST endpoints for upstream automation engines (such as **n8n**, HubSpot, client intake portals, or internal administrative dashboards) to plan, write, and render bespoke client proposals.

```
+-------------------------------------------------------------------------------+
|                       Upstream Clients / Automation Engines                  |
|                        (n8n Workflows, Webhooks, CRM, CLI)                     |
+-------------------------------------------------------------------------------+
                                    │
                         HTTPS POST /proposal/generate
                         (Headers: X-API-Key, X-Request-ID)
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                           sympl_api (FastAPI Core)                            │
│  - Request ID Correlation Middleware (ContextVar + X-Request-ID Header)       │
│  - API Key Security Middleware (API_AUTH_ENABLED / X-API-Key)                │
│  - Uniform JSON Error Handlers (Domain, Validation, System Exceptions)       │
│  - Orchestration Service Layer (Stage Timers, Context Serialization)          │
└───────────────────────────────────┬───────────────────────────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│  POST /plan  │             │  POST /write │             │ POST /render │
│ (Stage Only) │             │ (Stage Only) │             │ (Stage Only) │
└──────┬───────┘             └──────┬───────┘             └──────┬───────┘
       │                            │                            │
       ▼                            ▼                            ▼
┌──────────────┐  proposal_plan.json┌──────────────┐proposal_draft.json┌──────────────┐
│sympl_planner ├───────────────────►│ sympl_writer ├─────────────────►│sympl_renderer│
│ (Phase 3/4)  │                    │   (Phase 4)  │                  │  (Phase 5)   │
└──────────────┘                    └──────────────┘                  └──────┬───────┘
       │                                                                     │
       ▼                                                                     ▼
[PostgreSQL / pgvector]                                             [Rendered Proposal]
(Frozen Assets: 7 Docs,                                              - Canva Connect JSON
 71 Chunks, 47 Vectors,                                              - Slide Layouts
 21 Rules, 13 Blocks)                                               - HTML/PDF Export
```

### Core Architectural Invariants

1. **Strict Orchestration Boundary**: `sympl_api` is exclusively an orchestration wrapper. It does not implement business logic, generation logic, or formatting decisions.
2. **Zero In-Memory Mutations of Frozen Layers**:
   - Planner logic (`sympl_planner`) is frozen.
   - Writer logic (`sympl_writer`) is frozen.
   - Renderer logic (`sympl_renderer`) is frozen.
   - Embedding generation and retrieval systems are frozen.
3. **Database Immutability**:
   - Zero database mutations occur during API execution.
   - No new tables (`clients`, `proposal_runs`, `history`) are created in this phase.
   - Database invariants remain strictly intact (`proposal_documents: 7`, `proposal_chunks: 71`, `embeddings: 47`, `sympl_style_rules: 21`, `sympl_reference_blocks: 13`, `dataset_imports: 7`).
4. **Scope Firewall Enforcement**: The API layer preserves the boundary between `requested_scope` and `approved_scope`. The writer endpoint strictly rejects payloads violating this firewall.

---

## 2. Authentication & Request Tracking

### API Key Authentication

Authentication is managed via a dedicated FastAPI dependency (`sympl_api.auth.verify_api_key`) and controlled by environment variables:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `API_AUTH_ENABLED` | boolean | `false` | When `true`, all `/proposal/*` endpoints require authentication. |
| `API_KEY` | string | `sympl-dev-insecure-key-change-in-prod` | Secret key expected in the `X-API-Key` HTTP header. |

#### Authentication Behavior:
- **Enabled (`API_AUTH_ENABLED=true`)**: Incoming requests to `/proposal/*` must provide a matching `X-API-Key` header. Missing or mismatched keys immediately return `401 Unauthorized`.
- **Disabled (`API_AUTH_ENABLED=false`)**: Authentication is bypassed for seamless local development, testing, and CI/CD pipelines.
- **Public Endpoints**: The health check (`GET /health`) is always unauthenticated.

### Request Correlation & Tracing (`X-Request-ID`)

Every incoming request is tagged with a unique request correlation ID using Python `contextvars` and ASGI middleware:
- If the client transmits an `X-Request-ID` header (e.g. from n8n or an API gateway), that ID is preserved throughout logging, processing, and response delivery.
- If missing, the server automatically generates one formatted as `req_<12-hex-uuid>`.
- The `X-Request-ID` is returned in all HTTP response headers, embedded in all JSON responses, and prepended to all log messages.

---

## 3. Endpoint Contracts

### 3.1 Service Health Check

#### `GET /health`
Inspects overall system status, active database connectivity, and availability of all three core processing engines.

- **Authentication**: None (Public)
- **Response Status**: `200 OK`

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "planner": "available",
  "writer": "available",
  "renderer": "available",
  "llm_provider": "gemini"
}
```

*Note: If the PostgreSQL database cannot be reached, `"status"` degrades to `"degraded"` and `"database"` reports `"unreachable"`, while keeping the HTTP interface alive.*

---

### 3.2 End-to-End Proposal Generation

#### `POST /proposal/generate`
Executes the full pipeline: **Client Intake** -> **Proposal Planner** -> **Proposal Writer** -> **Proposal Renderer**.

- **Authentication**: Required (`X-API-Key` when enabled)
- **Request Body**: Client intake JSON payload.

```json
{
  "client_name": "High Park Community Hub",
  "organization_type": "nonprofit",
  "sector": "community_services",
  "current_systems": ["QuickBooks Online"],
  "engagement_type": "recurring",
  "complexity": "compact",
  "approved_scope": {
    "bookkeeping": {
      "cadence": "weekly",
      "ap_ar": true,
      "reconciliations": true,
      "expense_management": true
    }
  },
  "commercial_terms": {
    "pricing_model": "fixed_retainer",
    "monthly_retainer": 2200.0,
    "include_backlog_exclusion": true
  },
  "preferences": {
    "include_why_us": false
  }
}
```

- **Response Status**: `200 OK`
- **Response Structure**:

```json
{
  "proposal_id": "prop_a718d098e982",
  "request_id": "req_84ef81977b31",
  "status": "COMPLETED",
  "plan": {
    "plan_version": "1.0",
    "selected_archetype": "ARCH_COMPACT_BOOKKEEPING",
    "archetype_confidence": 1.0,
    "sections": [...],
    "approved_scope": {...},
    "reference_blocks": [...],
    "pricing": {...}
  },
  "draft": {
    "draft_version": "1.0",
    "title": "High Park Community Hub — Tailored Operational Support",
    "executive_summary": "...",
    "sections": [...],
    "pricing": {...},
    "validation_metadata": {
      "passed": true,
      "checks_performed": 6
    }
  },
  "rendered_output": {
    "design_id": "sympl_prop_a718d098e982",
    "page_count": 5,
    "export_status": "EXPORTED",
    "pages": [...],
    "metadata": {...}
  },
  "execution_metadata": {
    "planner_time_ms": 142.5,
    "writer_time_ms": 1845.2,
    "renderer_time_ms": 110.8,
    "total_time_ms": 2098.5
  }
}
```

---

### 3.3 Stage-Specific Endpoints

#### `POST /proposal/plan`
Executes only the Proposal Planner layer.
- **Input**: Client Intake JSON.
- **Output**: Validated `proposal_plan.json` structure (firewalled: strips `requested_scope` and includes only `approved_scope`).

#### `POST /proposal/write`
Executes only the Proposal Writer layer.
- **Input**: `proposal_plan.json`.
- **Output**: Validated `proposal_draft.json`.
- **Enforcement**: If `requested_scope` or `unapproved_requested_scope` is present, raises `400 Bad Request` with `SCOPEFIREWALLERROR`.

#### `POST /proposal/render`
Executes only the Proposal Renderer layer.
- **Input**: `proposal_draft.json`.
- **Output**: Presentation compilation `rendered_proposal.json` (Canva elements, pages, overflow checks).

---

### 3.4 Error Responses

All API errors return standardized JSON payloads with correlation tracking:

```json
{
  "error": "SCOPEFIREWALLERROR",
  "message": "Writer Input Firewall Violation: Plan contains forbidden unapproved scope fields: ['requested_scope'].",
  "details": {
    "exception_type": "ScopeFirewallError"
  },
  "request_id": "req_84ef81977b31"
}
```

| HTTP Status | Error Code | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | `APPROVAL_REQUIRED` | Missing `approved_scope` in client intake payload. |
| `400 Bad Request` | `EMPTY_APPROVED_SCOPE` | `approved_scope` is provided but empty or contains no active service families. |
| `400 Bad Request` | `INVALID_INTAKE` | Missing client name, empty payload, or invalid intake schema. |
| `400 Bad Request` | `SCOPEFIREWALLERROR` | Plan payload violates writer scope firewall. |
| `400 Bad Request` | `INVALIDDRAFTERROR` | Draft payload missing required fields or sections. |
| `401 Unauthorized`| `UNAUTHORIZED` | Missing or incorrect `X-API-Key` header. |
| `422 Unprocessable`| `VALIDATION_ERROR` | FastAPI request validation failure. |
| `422 Unprocessable`| `WRITERERROR` / `RENDERERERROR` | Pipeline stage execution failure. |
| `500 Internal Error`| `INTERNAL_ERROR` | Unexpected unhandled server exception. |

---

## 4. n8n Integration Plan

The Sympl Proposal API Layer is purpose-built to integrate natively with **n8n** workflows for end-to-end proposal generation automation.

```
[Form / CRM Webhook] (Typeform, HubSpot, Airtable)
         │
         ▼
[n8n Workflow Trigger]
         │
         ▼
[n8n Code Node: Format Client Intake JSON]
         │
         ▼
[n8n HTTP Request Node] ──► POST /proposal/generate
         │                  Headers: X-API-Key: {{$env.SYMPL_API_KEY}}
         │                           X-Request-ID: {{$execution.id}}
         ▼
[n8n Router Node: Check status == 'COMPLETED']
    ├── Success ──► [n8n Canva Connect / PDF Delivery Node]
    │                 - Export Canva design link
    │                 - Send notification to Slack (#proposals)
    │                 - Update CRM deal record with proposal draft URL
    └── Failure ──► [n8n Incident Node]
                      - Log error code and request_id
                      - Notify internal operations team
```

### Step-by-Step n8n Workflow Configuration

#### Node 1: Webhook Trigger
- Receives completed client discovery intake forms (e.g., from Typeform or a custom onboarding portal).

#### Node 2: Intake Normalizer (Code Node)
Maps the raw webhook fields to the Sympl intake schema:
```javascript
return [{
  json: {
    client_name: $json.company_name,
    organization_type: $json.legal_type || "nonprofit",
    sector: $json.industry_sector || "community_services",
    current_systems: $json.accounting_software ? [$json.accounting_software] : ["QuickBooks Online"],
    engagement_type: "recurring",
    complexity: "compact",
    approved_scope: {
      bookkeeping: {
        cadence: $json.bookkeeping_cadence || "weekly",
        ap_ar: Boolean($json.needs_ap_ar),
        reconciliations: true,
        expense_management: true
      }
    },
    commercial_terms: {
      pricing_model: "fixed_retainer",
      monthly_retainer: Number($json.budget_amount) || 2500,
      include_backlog_exclusion: true
    },
    preferences: {
      include_why_us: true
    }
  }
}];
```

#### Node 3: Sympl Orchestration Request (HTTP Request Node)
- **Method**: `POST`
- **URL**: `http://sympl-api:8000/proposal/generate`
- **Authentication**: Generic Credential Header
  - Header Name: `X-API-Key`
  - Value: `={{$env.SYMPL_API_KEY}}`
- **Headers**:
  - `Content-Type`: `application/json`
  - `X-Request-ID`: `n8n_={{$execution.id}}`
- **Body Content Type**: `JSON`
- **Send Body**: Enabled (`{{$json}}`)
- **Timeout**: `60000` (60 seconds for full LLM generation)

#### Node 4: Downstream Distribution
- Updates CRM (HubSpot/Salesforce) with `proposal_id` and rendered slide links.
- Pushes draft review link to team Slack channel:
  `New proposal generated for {{$json.draft.title}} (ID: {{$json.proposal_id}}, Duration: {{$json.execution_metadata.total_time_ms}}ms)`.

---

## 5. Deployment Instructions

### 5.1 Local Development

Run the API service locally using Uvicorn with auto-reload:

```bash
# Set environment variables (or copy .env.example)
export API_AUTH_ENABLED=false
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/sympl_proposals"

# Start Uvicorn development server
uvicorn sympl_api.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

### 5.2 Containerized Deployment (Docker)

#### Build the Docker Image
```bash
docker build -t sympl-proposal-api:latest .
```

#### Run Standalone Container
```bash
docker run -d \
  --name sympl-api \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://postgres:postgres@host.docker.internal:5432/sympl_proposals" \
  -e API_AUTH_ENABLED="true" \
  -e API_KEY="your-production-secret-key" \
  sympl-proposal-api:latest
```

---

### 5.3 Multi-Container Orchestration (Docker Compose)

Launch the API alongside supporting infrastructure with `docker-compose`:

```bash
# Start all services in detached mode
docker compose up -d

# Check service logs
docker compose logs -f api

# Verify health endpoint
curl -i http://localhost:8000/health
```

---

## 6. Verification and Regression Testing

To verify the API layer without altering any frozen database assets or prior phase code:

```bash
# 1. Run API integration tests
pytest tests/test_api.py -v

# 2. Run Renderer regression suite
pytest tests/test_renderer.py -v

# 3. Run Writer regression suite
pytest tests/test_writer.py -v

# 4. Run Planner regression suite
python tests/test_proposal_planner.py
```
