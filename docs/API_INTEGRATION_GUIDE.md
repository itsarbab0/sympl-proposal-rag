# Sympl Solutions Proposal RAG — API Integration & Automation Guide

This guide provides technical specifications, authentication contracts, copy-pasteable JSON payloads, and integration recipes for consuming the Sympl Proposal RAG platform from external automation systems such as **n8n**, **Zapier**, **Make**, or custom applications.

---

## 1. Authentication & Security Specification

The Sympl Proposal RAG API enforces standard HTTP Header Authentication across all operational endpoints.

### 1.1 Authentication Method
- **Header Key**: `X-API-Key`
- **Format**: Plaintext API Key token
- **Example**:
  ```http
  POST /api/v1/proposal/generate/async HTTP/1.1
  Host: api.symplsolutions.ca
  X-API-Key: sympl_live_sec_994a2b1c8f
  Content-Type: application/json
  ```

### 1.2 Zero-Downtime Key Rotation
The server supports multiple concurrent authorized keys to allow seamless key rotation without taking downstream automations offline:
- Primary key: Configured via `API_KEY` environment variable.
- Multiple active keys: Configured via comma-separated `API_KEYS` environment variable:
  ```env
  API_KEY=sympl_live_sec_active_key_v2
  API_KEYS=sympl_live_sec_old_key_v1,sympl_live_sec_active_key_v2,n8n_prod_integration_token
  ```
- **Error Response on Authentication Failure**:
  ```json
  {
    "error": "UNAUTHORIZED",
    "message": "Invalid 'X-API-Key' provided.",
    "request_id": "req_84f1a0e8d"
  }
  ```

---

## 2. API Versioning & Route Mapping

The API enforces strict semantic versioning while guaranteeing **100% backward compatibility** for unversioned legacy endpoints. Both URI patterns map to identical execution controllers.

| Endpoint Description | Versioned Path (Recommended for n8n) | Legacy Path (Backward Compatible) | HTTP Method | Auth Required |
| :--- | :--- | :--- | :--- | :--- |
| **Service Health Check** | `GET /api/v1/health` | `GET /health` | `GET` | No |
| **Async Proposal Generation** | `POST /api/v1/proposal/generate/async` | `POST /proposal/generate/async` | `POST` | Yes (`X-API-Key`) |
| **Poll Job Status** | `GET /api/v1/proposal/status/{job_id}` | `GET /proposal/status/{job_id}` | `GET` | Yes (`X-API-Key`) |
| **Download PDF Proposal** | `GET /api/v1/proposal/{proposal_id}/pdf` | `GET /proposal/{proposal_id}/pdf` | `GET` | Optional (configurable) |
| **Get Artifact Manifest** | `GET /api/v1/proposal/{proposal_id}/manifest` | `GET /proposal/{proposal_id}/manifest` | `GET` | Optional |
| **List Artifact Inventory** | `GET /api/v1/proposal/{proposal_id}/artifacts` | `GET /proposal/{proposal_id}/artifacts` | `GET` | Optional |
| **Synchronous Pipeline (Blocking)** | `POST /api/v1/proposal/generate` | `POST /proposal/generate` | `POST` | Yes (`X-API-Key`) |

---

## 3. OpenAPI Schema Verification & Interactive Docs

The backend automatically publishes OpenAPI 3.1.0 specifications for schema validation:
- **Interactive Swagger UI**: `GET /docs`
- **ReDoc Technical Reference**: `GET /redoc`
- **Raw OpenAPI JSON Spec**: `GET /openapi.json`

*(Note: In production environments with `ENVIRONMENT=production`, documentation visibility is governed by `DOCS_ENABLED=false` by default to prevent reconnaissance. Set `DOCS_ENABLED=true` if internal documentation access is required).*

---

## 4. Endpoints Reference & JSON Payloads

### 4.1. POST `/api/v1/proposal/generate/async`
Queues an asynchronous proposal generation job. Validates input schema and the mandatory `approved_scope` gate before accepting.

#### Headers:
```http
Content-Type: application/json
X-API-Key: <YOUR_API_KEY>
X-Request-ID: <OPTIONAL_CORRELATION_ID>
```

#### Request Body Schema (`ClientInput`):
```json
{
  "client_id": "CLIENT_LEAD_1042",
  "organization": {
    "name": "Northstar Community Health",
    "organization_type": "nonprofit",
    "sector": "community_services",
    "description": "Community health organization providing primary care and social programs.",
    "current_systems": ["QuickBooks Desktop", "Excel"],
    "target_systems": ["QuickBooks Online", "Dext", "Wagepoint"]
  },
  "engagement": {
    "engagement_type": "recurring",
    "complexity": "standard"
  },
  "requested_scope": {
    "bookkeeping": {
      "cadence": "weekly",
      "ap_ar": true,
      "reconciliations": true
    },
    "payroll": {
      "cadence": "semi_monthly",
      "headcount_employees": 12,
      "headcount_contractors": 4
    }
  },
  "approved_scope": {
    "bookkeeping": {
      "cadence": "weekly",
      "ap_ar": true,
      "reconciliations": true
    },
    "payroll": {
      "cadence": "semi_monthly",
      "headcount_employees": 12,
      "headcount_contractors": 4
    }
  },
  "commercial_terms": {
    "pricing_model": "fixed_retainer",
    "monthly_retainer": 3200.0,
    "onboarding_fee": 1500.0,
    "payment_terms": "net_15"
  },
  "preferences": {
    "include_why_us": true,
    "target_pages": 4
  },
  "callback_url": "https://n8n.yourcompany.com/webhook/sympl-proposal-complete"
}
```

#### Scope Invariant Rules:
1. `approved_scope` is **mandatory**. Omission returns `HTTP 422 ApprovalRequiredException`.
2. `approved_scope` cannot be empty (`{}`). Omission of active service modules returns `HTTP 422 EmptyApprovedScopeException`.
3. The engine **strictly ignores unapproved requested scopes**; only services in `approved_scope` reach the Proposal Planner and Writer.
4. `callback_url` is **optional**. When provided, the server delivers an HTTP POST callback when generation finishes.

#### Response Body (`HTTP 202 Accepted`):
```json
{
  "job_id": "job_e9b1d7f30a24",
  "status": "CREATED",
  "request_id": "req_84f1a0e8d",
  "message": "Proposal generation job queued successfully."
}
```

---

### 4.2. GET `/api/v1/proposal/status/{job_id}`
Returns current operational status, active stage, completion progress, and allocated `proposal_id`.

#### Response Body — In Progress (`HTTP 200 OK`):
```json
{
  "job_id": "job_e9b1d7f30a24",
  "status": "RUNNING",
  "current_stage": "WRITER",
  "progress": 0.5,
  "proposal_id": "prop_a71c8902f41e",
  "error_message": null
}
```

#### Response Body — Completed (`HTTP 200 OK`):
```json
{
  "job_id": "job_e9b1d7f30a24",
  "status": "COMPLETED",
  "current_stage": "COMPLETED",
  "progress": 1.0,
  "proposal_id": "prop_a71c8902f41e",
  "error_message": null
}
```

---

### 4.3. GET `/api/v1/proposal/{proposal_id}/pdf`
Returns the compiled binary PDF proposal generated via ReportLab Platypus.

#### Response:
- **Status**: `200 OK`
- **Content-Type**: `application/pdf`
- **Content-Disposition**: `inline; filename="proposal_prop_a71c8902f41e.pdf"`
- **Body**: Binary vector PDF stream (magic bytes `%PDF-1.4`).

---

### 4.4. GET `/api/v1/proposal/{proposal_id}/manifest`
Returns cryptographic verification data, byte sizes, and presence confirmation for all 5 proposal artifacts.

#### Response Body (`HTTP 200 OK`):
```json
{
  "proposal_id": "prop_a71c8902f41e",
  "generated_at": "2026-09-07T21:40:12Z",
  "client_name": "Northstar Community Health",
  "title": "Accounting & Financial Operations Proposal",
  "artifact_count": 5,
  "expected_count": 5,
  "all_artifacts_present": true,
  "artifacts": {
    "proposal_plan.json": {
      "exists": true,
      "size_bytes": 18240,
      "sha256": "8f31b8a9c40217d84812a0f8b89e34c91039de4bc87123aa1289dfb890471201"
    },
    "proposal_draft.json": {
      "exists": true,
      "size_bytes": 9412,
      "sha256": "4b72ef01a89c841029471bbad091823746a89c31481bdf09128374bbcca89123"
    },
    "rendered_proposal.json": {
      "exists": true,
      "size_bytes": 22480,
      "sha256": "09182374bbcca891234b72ef01a89c841029471bbad8f31b8a9c40217d84812a"
    },
    "proposal.pdf": {
      "exists": true,
      "size_bytes": 48192,
      "sha256": "1039de4bc87123aa1289dfb8904712014b72ef01a89c841029471bbad0918237"
    },
    "manifest.json": {
      "exists": true,
      "size_bytes": 1024,
      "sha256": "c87123aa1289dfb8904712018f31b8a9c40217d84812a0f8b89e34c91039de4b"
    }
  }
}
```

---

### 4.5. GET `/api/v1/proposal/{proposal_id}/artifacts`
Returns an inventory of artifacts and direct download metadata.

#### Response Body (`HTTP 200 OK`):
```json
{
  "proposal_id": "prop_a71c8902f41e",
  "artifact_count": 5,
  "expected_count": 5,
  "all_artifacts_present": true,
  "artifacts": {
    "proposal.pdf": {
      "filename": "proposal.pdf",
      "download_url": "/api/v1/proposal/prop_a71c8902f41e/pdf",
      "media_type": "application/pdf"
    },
    "manifest.json": {
      "filename": "manifest.json",
      "download_url": "/api/v1/proposal/prop_a71c8902f41e/manifest",
      "media_type": "application/json"
    }
  }
}
```

---

## 5. Webhook Callback Specification

When `callback_url` is passed in the intake JSON, the background worker automatically issues an HTTP POST notification upon job completion or failure.

### 5.1 Callback Payload Structure
```json
{
  "job_id": "job_e9b1d7f30a24",
  "proposal_id": "prop_a71c8902f41e",
  "status": "COMPLETED",
  "pdf_url": "https://api.symplsolutions.ca/api/v1/proposal/prop_a71c8902f41e/pdf",
  "manifest_url": "https://api.symplsolutions.ca/api/v1/proposal/prop_a71c8902f41e/manifest"
}
```
*(If the job failed, `status: "FAILED"` is provided alongside `"error_message": "<reason>"`).*

### 5.2 Failure Isolation & Retry Policy
- **Failure Isolation**: A webhook delivery failure (e.g. n8n listener down, DNS resolution failure, network timeout) **NEVER affects or invalidates the completed proposal generation**. The proposal records, database entries, PDF, and artifacts remain fully saved and valid.
- **Retries**: The worker attempts delivery up to `WEBHOOK_MAX_RETRIES` (default 2 retries) with progressive backoff.
- **Timeout**: Each attempt is bounded by `WEBHOOK_TIMEOUT_SECONDS` (default 5s).
- **Telemetry**: Webhook dispatch outcomes and delivery latencies are recorded in standard observability logs.

---

## 6. Rate Limiting Protection

To protect the server from inadvertent automation loops or abusive bursts, the API implements sliding window rate limiting.

### 6.1 Policy & Defaults
- **Window**: 60-second sliding window.
- **Limit**: `60 requests / minute` per client (configured via `RATE_LIMIT_REQUESTS_PER_MINUTE`).
- **Client Identification**: Keyed by `X-API-Key` if present; otherwise keyed by client IP address.
- **Exempt Endpoints**: Health probes (`/health`, `/api/v1/health`) and OpenAPI docs (`/docs`, `/openapi.json`) are immune from rate limiting.

### 6.2 Rate Limit Exceeded Response (`HTTP 429`)
When the limit is breached, the API returns:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 28
Content-Type: application/json
```
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded. Please retry after 28 seconds.",
  "details": {
    "limit": 60,
    "window_seconds": 60,
    "retry_after": 28
  },
  "request_id": "req_1a7b9c"
}
```

> [!NOTE]
> **Single-Instance Protection vs. Horizontal Distributed Scaling**:
> The current rate limiter uses an in-memory thread-safe sliding window implementation designed for single-container/single-node deployments.
> When scaling horizontally across multiple cluster pods or container replicas behind an AWS ALB / NGINX load balancer, this limiter can be migrated to Redis-backed distributed token buckets via atomic Lua scripts without changing the client-facing API contract.

---

## 7. CORS & Network Security for n8n

### 7.1 Server-to-Server vs. Browser Execution
- **Server-to-Server (Standard n8n Workflow)**:
  n8n runs server-side on Node.js. When an **HTTP Request** node calls the Sympl API, it does **NOT** issue CORS preflight (`OPTIONS`) requests; server-to-server HTTP calls bypass browser CORS security checks.
- **Browser-Initiated Requests (n8n Webhook Test UI / Embedded Widgets)**:
  If webhooks or custom frontend forms interact directly from client browsers, CORS is active.

### 7.2 CORS Configuration
The backend allows explicit origins configured via environment variables:
```env
CORS_ORIGINS=https://app.symplsolutions.ca,https://n8n.yourcompany.com
N8N_ORIGIN=http://localhost:5678
```
- **Allowed Methods**: `GET`, `POST`, `OPTIONS`
- **Allowed Headers**: `Content-Type`, `X-API-Key`, `X-Request-ID`, `Authorization`
- **Production Safety**: Wildcards (`*`) with credentials enabled are strictly rejected in production mode.

---

## 8. Complete n8n Integration Recipes

### 8.1 Workflow Architecture
```
┌────────────────────────┐
│     Webhook Trigger    │ (Lead Intake from HubSpot / Typeform)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  MANDATORY HUMAN GATE  │ (AE checks scope & approved pricing)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│   HTTP Request Node    │ POST /api/v1/proposal/generate/async
└───────────┬────────────┘
            │
     ┌──────┴──────────────────────────┐
     │ OPTION A: Polling Loop          │ OPTION B: Webhook Callback
     ▼                                 ▼
┌────────────────────────┐       ┌────────────────────────┐
│ Loop: Wait 5s          │       │ n8n Webhook Listener   │
│ GET /status/{job_id}   │       │ (Receives callback_url)│
└───────────┬────────────┘       └───────────┬────────────┘
            │ COMPLETED                      │ COMPLETED
            └────────────────┬───────────────┘
                             │
                             ▼
┌────────────────────────────────────────┐
│ Download PDF Node                      │ GET /api/v1/proposal/{id}/pdf
└────────────────────────────┬───────────┘
                             │
                             ▼
┌────────────────────────────────────────┐
│ CRM Update & Email Delivery            │ Attach PDF & email client
└────────────────────────────────────────┘
```

---

### 8.2 Configuring n8n HTTP Request Node

#### Node: "Trigger Proposal Generation"
- **Method**: `POST`
- **URL**: `{{ $env.SYMPL_API_BASE_URL }}/api/v1/proposal/generate/async`
- **Authentication**: `Generic Credential Type` -> `Header Auth`
  - **Name**: `X-API-Key`
  - **Value**: `{{ $env.SYMPL_API_KEY }}`
- **Send Body**: `JSON`
- **Body**:
  ```json
  {
    "client_id": "LEAD_{{ $json.deal_id }}",
    "organization": {
      "name": "{{ $json.company_name }}",
      "organization_type": "{{ $json.org_type }}",
      "sector": "{{ $json.sector }}"
    },
    "engagement": {
      "engagement_type": "recurring",
      "complexity": "standard"
    },
    "requested_scope": {
      "bookkeeping": { "cadence": "weekly", "ap_ar": true, "reconciliations": true }
    },
    "approved_scope": {
      "bookkeeping": { "cadence": "weekly", "ap_ar": true, "reconciliations": true }
    },
    "commercial_terms": {
      "pricing_model": "fixed_retainer",
      "monthly_retainer": {{ $json.monthly_fee }}
    },
    "callback_url": "{{ $env.N8N_WEBHOOK_BASE }}/webhook/sympl-proposal-done"
  }
  ```

---

#### Node: "Poll Job Status" (If using Polling)
- **Method**: `GET`
- **URL**: `{{ $env.SYMPL_API_BASE_URL }}/api/v1/proposal/status/{{ $node["Trigger Proposal Generation"].json["job_id"] }}`
- **Authentication**: `Header Auth` (`X-API-Key`)
- **If Node**: Condition `{{ $json.status }} === "COMPLETED"`:
  - If `true` -> proceed to Download PDF.
  - If `false` -> Wait 5 seconds -> Poll again (max 12 iterations).

---

#### Node: "Download Proposal PDF"
- **Method**: `GET`
- **URL**: `{{ $env.SYMPL_API_BASE_URL }}/api/v1/proposal/{{ $json.proposal_id }}/pdf`
- **Response Format**: `File` (Binary)
- **Put Output in Field**: `data`

---

## 9. Invariant Verification Checklist

All integrations must respect the following core system invariants:
1. **Never bypass `approved_scope`**: Automation workflows must never pass raw, unapproved user forms directly into `approved_scope` without human validation.
2. **Never alter frozen database tables**: External automations must not insert, delete, or modify rows in the 6 frozen proposal tables (`proposal_documents`, `proposal_chunks`, `embeddings`, `sympl_style_rules`, `sympl_reference_blocks`, `dataset_imports`).
3. **Respect idempotency**: Duplicate lead submissions should be deduplicated by assigning consistent `client_id` values.
