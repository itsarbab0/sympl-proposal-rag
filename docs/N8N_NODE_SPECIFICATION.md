# Sympl Proposal RAG — n8n Node Specification

This document provides complete, node-level engineering specifications for both **Workflow 1 (Lead Intake & Proposal Generation)** and **Workflow 2 (Proposal Processing, Monitoring, & Delivery)**.

---

# Workflow 1: Sympl Lead Intake and Proposal Generation Workflow

```
[Node 1: Webhook Ingress]
         │
         ▼
[Node 2: AI Unstructured Extractor]
         │
         ▼
[Node 3: Structured Schema Validator]
         │
         ▼
[Node 4: HubSpot CRM Lead/Deal Upsert]
         │
         ▼
[Node 5: Missing Information Branch] ──────► (True: Missing Info) ──► [Node 6: Clarification Dispatcher]
         │ (False: Complete)
         ▼
[Node 7: Human Scope Approval Gate]
         │
         ▼
[Node 8: Scope Firewall Audit Guard]
         │
         ▼
[Node 9: Sympl API Dispatcher]
         │
         ▼
[Node 10: Workflow 2 Trigger Node]
```

---

### Node 1: Webhook Ingress
- **Node Name**: `Lead Webhook Ingress`
- **n8n Node Type**: `n8n-nodes-base.webhook` (Version 2.0)
- **Purpose**: Receives incoming JSON webhooks from website intake forms, Typeform, or HubSpot deal stage transitions.
- **Input**: External HTTP POST payload containing contact details, organization name, and unstructured requirements text.
- **Output**:
  ```json
  {
    "event_id": "evt_998124",
    "timestamp": "2026-09-07T12:00:00Z",
    "source": "website_form",
    "lead": {
      "name": "Sarah Jenkins",
      "email": "s.jenkins@highparkhub.ca",
      "organization": "High Park Community Hub",
      "notes": "We need help with bookkeeping and monthly reporting. We currently run 14 staff on payroll."
    }
  }
  ```
- **Configuration**:
  - `path`: `sympl-lead-intake`
  - `httpMethod`: `POST`
  - `responseMode`: `onReceived` (Returns HTTP 200 immediately)
  - `authentication`: `headerAuth` (Validates `X-Sympl-Webhook-Secret`)

---

### Node 2: AI Unstructured Extractor
- **Node Name**: `AI Unstructured Extractor`
- **n8n Node Type**: `@n8n/n8n-nodes-langchain.agent` with `@n8n/n8n-nodes-langchain.openAi`
- **Purpose**: Extracts structured client profile, candidate service requests, systems, and organizational context from unstructured text. Strictly forbidden from deciding `approved_scope` or pricing.
- **Input**: Output of Node 1 (`lead.notes`, `lead.organization`, etc.).
- **Output**:
  ```json
  {
    "organization_name": "High Park Community Hub",
    "organization_type": "nonprofit",
    "sector": "community_services",
    "current_systems": ["QuickBooks Desktop"],
    "candidate_needs": {
      "bookkeeping": true,
      "payroll": true,
      "financial_reporting": true,
      "compliance": false,
      "digital_transformation": false
    },
    "payroll_headcount_estimate": 14,
    "urgency": "medium",
    "missing_fields": []
  }
  ```
- **Configuration**:
  - `model`: `gpt-4o-mini`
  - `temperature`: `0.0` (Deterministic extraction)
  - `systemMessage`: *"You are an intake parser for an accounting and advisory practice. Extract structured organization entities, current accounting software, and candidate services requested. You MUST NOT decide final scope or pricing."*
  - `responseFormat`: `json_object`

---

### Node 3: Structured Schema Validator
- **Node Name**: `Structured Schema Validator`
- **n8n Node Type**: `n8n-nodes-base.code` (JavaScript runtime)
- **Purpose**: Normalizes AI extraction into Sympl draft schema format; guarantees field existence and sets deterministic defaults.
- **Input**: AI JSON extraction from Node 2.
- **Output**: Standardized intermediate schema with normalized sector (`community_services`, `arts_culture`, etc.) and preliminary scope dictionaries.
- **Configuration**:
  ```javascript
  const lead = $input.first().json;
  return {
    json: {
      client_name: lead.organization_name || "Unspecified Organization",
      sector: ["nonprofit", "charity"].includes(lead.organization_type) ? (lead.sector || "community_services") : "for_profit",
      organization_type: lead.organization_type || "nonprofit",
      current_systems: lead.current_systems || [],
      draft_requested_scope: {
        bookkeeping: lead.candidate_needs.bookkeeping ? { cadence: "monthly", ap_ar: true, reconciliations: true } : null,
        payroll: lead.candidate_needs.payroll ? { cadence: "semi_monthly", headcount_employees: lead.payroll_headcount_estimate || 0 } : null,
        financial_reporting: lead.candidate_needs.financial_reporting ? { cadence: "monthly" } : null
      },
      has_organization: Boolean(lead.organization_name),
      has_contact: Boolean(lead.email || lead.name)
    }
  };
  ```

---

### Node 4: HubSpot CRM Lead/Deal Upsert
- **Node Name**: `HubSpot CRM Lead/Deal Upsert`
- **n8n Node Type**: `n8n-nodes-base.hubspot` (Version 2.0)
- **Purpose**: Creates or updates Company, Contact, and Deal objects in HubSpot CRM, establishing audit linkage.
- **Input**: Normalized schema from Node 3.
- **Output**: HubSpot `deal_id`, `company_id`, and `contact_id`.
- **Configuration**:
  - `resource`: `deal`
  - `operation`: `upsert`
  - `dealName`: `Proposal - {{$json.client_name}}`
  - `stage`: `qualified_to_buy`
  - `customProperties`:
    - `sympl_proposal_status`: `intake_received`
    - `sympl_sector`: `{{$json.sector}}`
    - `sympl_extracted_needs`: `{{JSON.stringify($json.draft_requested_scope)}}`

---

### Node 5: Missing Information Branch
- **Node Name**: `Missing Information Branch`
- **n8n Node Type**: `n8n-nodes-base.if` (Version 2.0)
- **Purpose**: Determines if mandatory intake fields (`client_name`, `contact_email`, at least 1 identified need) are present.
- **Input**: Output of Node 3 & Node 4.
- **Condition**:
  - `Value 1`: `{{$json.has_organization && $json.has_contact && Object.keys($json.draft_requested_scope).length > 0}}`
  - `Operation`: `equal`
  - `Value 2`: `true`
- **Output Branches**:
  - `true`: Proceeds to Node 7 (Human Approval Gate).
  - `false`: Diverts to Node 6 (Clarification Dispatcher).

---

### Node 6: Clarification Dispatcher
- **Node Name**: `Clarification Dispatcher`
- **n8n Node Type**: `n8n-nodes-base.emailSend` / `n8n-nodes-base.slack`
- **Purpose**: Alerts the sales representative that lead discovery is incomplete, and drafts a clarification email to the client.
- **Input**: Incomplete lead metadata from Node 5.
- **Output**: Dispatched notification confirmation.
- **Configuration**:
  - `toEmail`: `sales-alerts@symplsolutions.ca`
  - `subject`: `[Incomplete Intake] Action Required: {{$json.client_name}}`
  - `bodyHtml`: `Lead received with missing organization or contact details. Discovery follow-up required.`

---

### Node 7: Human Scope Approval Gate
- **Node Name**: `Human Scope Approval Gate`
- **n8n Node Type**: `n8n-nodes-base.wait` (Wait for Webhook)
- **Purpose**: **Mandatory Scope Firewall**. Halts automated execution until an authorized team member reviews the request, verifies pricing, and explicitly signs off on `approved_scope`.
- **Input**: Lead context and preliminary draft scope from Node 4.
- **Output**: Form payload submitted by Account Executive containing explicitly approved service families and commercial rates.
- **Configuration**:
  - `resume`: `webhook`
  - `webhookSuffix`: `approval-{{$json.deal_id}}`
  - `limitWaitTime`: `7 days`

---

### Node 8: Scope Firewall Audit Guard
- **Node Name**: `Scope Firewall Audit Guard`
- **n8n Node Type**: `n8n-nodes-base.code` (JavaScript)
- **Purpose**: Strictly enforces that `approved_scope` is non-empty and isolates `requested_scope` for audit only.
- **Input**: Approved payload from Node 7.
- **Output**: Clean `ClientInput` JSON ready for API consumption.
- **Configuration**:
  ```javascript
  const input = $input.first().json;
  if (!input.approved_scope || Object.keys(input.approved_scope).length === 0) {
    throw new Error("APPROVAL_REQUIRED: approved_scope cannot be empty.");
  }
  return {
    json: {
      client_id: `client_${input.deal_id}`,
      organization: {
        name: input.client_name,
        organization_type: input.organization_type,
        sector: input.sector,
        description: input.description || "",
        current_systems: input.current_systems || [],
        target_systems: input.target_systems || []
      },
      engagement: {
        engagement_type: input.engagement_type || "recurring",
        complexity: input.complexity || "standard",
        diagnostic_focus: input.diagnostic_focus || []
      },
      requested_scope: input.draft_requested_scope || {},
      approved_scope: input.approved_scope,
      commercial_terms: {
        pricing_model: input.pricing_model || "fixed_retainer",
        currency: "CAD",
        monthly_retainer: Number(input.monthly_retainer) || null,
        setup_fee: Number(input.setup_fee) || null,
        include_backlog_exclusion: true,
        software_fees_excluded: true
      },
      preferences: {
        include_why_us: input.include_why_us !== false,
        is_competitive_pitch: Boolean(input.is_competitive_pitch),
        is_trusted_continuity: Boolean(input.is_trusted_continuity)
      }
    }
  };
  ```

---

### Node 9: Sympl API Dispatcher
- **Node Name**: `Sympl API Dispatcher`
- **n8n Node Type**: `n8n-nodes-base.httpRequest` (Version 4.2)
- **Purpose**: Dispatches the asynchronous proposal generation job to the Sympl Proposal RAG backend.
- **Input**: Validated payload from Node 8.
- **Output**:
  ```json
  {
    "job_id": "job_5343d3c5009b",
    "status": "CREATED",
    "request_id": "req_n8n_10482",
    "message": "Proposal generation job queued successfully."
  }
  ```
- **Configuration**:
  - `method`: `POST`
  - `url`: `https://sympl-api-production.up.railway.app/proposal/generate/async`
  - `sendHeaders`: `true`
  - `headers`:
    - `X-API-Key`: `{{$env.SYMPL_API_KEY}}`
    - `Content-Type`: `application/json`
  - `sendBody`: `true`
  - `bodyParameters`: `{{$json}}`
  - `options`:
    - `timeout`: `15000` (15s)
    - `retryOnFail`: `true`
    - `maxTries`: `3`

---

### Node 10: Workflow 2 Trigger Node
- **Node Name**: `Trigger Proposal Processing Workflow`
- **n8n Node Type**: `n8n-nodes-base.httpRequest`
- **Purpose**: Transmits `job_id`, `deal_id`, and `client_name` to Workflow 2 to initiate background status monitoring and delivery.
- **Input**: `job_id` from Node 9 and CRM metadata.
- **Output**: HTTP 200 acknowledge from Workflow 2.
- **Configuration**:
  - `method`: `POST`
  - `url`: `https://n8n.symplsolutions.ca/webhook/sympl-proposal-processing`
  - `body`:
    ```json
    {
      "job_id": "={{$json.job_id}}",
      "deal_id": "={{$('HubSpot CRM Lead/Deal Upsert').item.json.deal_id}}",
      "client_name": "={{$('Scope Firewall Audit Guard').item.json.organization.name}}"
    }
    ```

---

# Workflow 2: Sympl Proposal Processing and Delivery Workflow

```
[Node 1: Workflow 2 Webhook Ingress]
         │
         ▼
[Node 2: HubSpot Set Generating State]
         │
         ▼
[Node 3: Polling Loop Wait Node (5s)] ◄──────────────────────┐
         │                                                    │
         ▼                                                    │ (Running / Created)
[Node 4: Sympl Job Status Querier]                            │
         │                                                    │
         ▼                                                    │
[Node 5: Lifecycle Status Router] ──► (RUNNING / CREATED) ────┘
         │
         ├──────────────────────────► (FAILED) ──► [Node 6: Failure Escalation Node]
         ▼ (COMPLETED)
[Node 7: Artifact Retrieval Downloader]
         │
         ▼
[Node 8: Presentation / PDF Compiler Adapter]
         │
         ▼
[Node 9: CRM Proposal Attachment & Deal Advance]
         │
         ▼
[Node 10: Client Delivery Dispatcher]
         │
         ▼
[Node 11: Follow-up Reminder Scheduler]
```

---

### Node 1: Workflow 2 Webhook Ingress
- **Node Name**: `Workflow 2 Webhook Ingress`
- **n8n Node Type**: `n8n-nodes-base.webhook`
- **Purpose**: Receives execution handoff event containing `job_id` and `deal_id` from Workflow 1.
- **Input**: `{ "job_id": "job_...", "deal_id": "...", "client_name": "..." }`.
- **Output**: JSON execution context for monitoring loop.

---

### Node 2: HubSpot Set Generating State
- **Node Name**: `HubSpot Set Generating State`
- **n8n Node Type**: `n8n-nodes-base.hubspot`
- **Purpose**: Updates deal status in CRM so sales rep sees active pipeline generation in progress.
- **Configuration**:
  - `resource`: `deal`
  - `dealId`: `={{$json.deal_id}}`
  - `properties`:
    - `sympl_job_id`: `={{$json.job_id}}`
    - `sympl_proposal_status`: `GENERATING`

---

### Node 3: Polling Loop Wait Node
- **Node Name**: `Polling Loop Wait (5s)`
- **n8n Node Type**: `n8n-nodes-base.wait`
- **Purpose**: Implements non-blocking sleep interval between polling requests to prevent server throttling.
- **Configuration**:
  - `resume`: `timeInterval`
  - `amount`: `5`
  - `unit`: `seconds`

---

### Node 4: Sympl Job Status Querier
- **Node Name**: `Sympl Job Status Querier`
- **n8n Node Type**: `n8n-nodes-base.httpRequest`
- **Purpose**: Queries backend operational table status for the specific proposal job.
- **Input**: `job_id` from context.
- **Output**:
  ```json
  {
    "job_id": "job_5343d3c5009b",
    "status": "RUNNING",
    "current_stage": "WRITER",
    "progress": 0.33,
    "proposal_id": "prop_56f02c7bbd8a",
    "error_message": null
  }
  ```
- **Configuration**:
  - `method`: `GET`
  - `url`: `https://sympl-api-production.up.railway.app/proposal/status/{{$json.job_id}}`
  - `headers`:
    - `X-API-Key`: `{{$env.SYMPL_API_KEY}}`

---

### Node 5: Lifecycle Status Router
- **Node Name**: `Lifecycle Status Router`
- **n8n Node Type**: `n8n-nodes-base.switch` (Version 3.0)
- **Purpose**: Branches execution based on job lifecycle status.
- **Rules**:
  - Output 0 (`COMPLETED`): `{{$json.status === "COMPLETED"}}`
  - Output 1 (`FAILED`): `{{$json.status === "FAILED"}}`
  - Output 2 (`IN_PROGRESS`): `{{$json.status === "CREATED" || $json.status === "RUNNING"}}`
- **Routing**:
  - Output 0 $\rightarrow$ Node 7 (Artifact Retrieval Downloader)
  - Output 1 $\rightarrow$ Node 6 (Failure Escalation Node)
  - Output 2 $\rightarrow$ Loops back to Node 3 (with loop iteration counter safety cap: max 24 cycles = 120s)

---

### Node 6: Failure Escalation Node
- **Node Name**: `Failure Escalation Node`
- **n8n Node Type**: `n8n-nodes-base.slack` / `n8n-nodes-base.hubspot`
- **Purpose**: Escalates generation failure to Account Executive and technical support team; posts error reason to CRM deal.
- **Configuration**:
  - `channel`: `#sympl-proposal-alerts`
  - `message`: `*Generation Failed:* Job {{$json.job_id}} for Deal {{$json.deal_id}} failed at stage {{$json.current_stage}}. Reason: {{$json.error_message}}`

---

### Node 7: Artifact Retrieval Downloader
- **Node Name**: `Artifact Retrieval Downloader`
- **n8n Node Type**: `n8n-nodes-base.httpRequest`
- **Purpose**: Retrieves generated artifacts (`proposal_draft.json` and `rendered_proposal.json`) from the backend storage API or object store.
- **Configuration**:
  - `method`: `GET`
  - `url`: `https://sympl-api-production.up.railway.app/proposal/{{$json.proposal_id}}/artifacts`
  - `headers`:
    - `X-API-Key`: `{{$env.SYMPL_API_KEY}}`

---

### Node 8: Presentation / PDF Compiler Adapter
- **Node Name**: `Presentation / PDF Compiler Adapter`
- **n8n Node Type**: `n8n-nodes-base.code` / Gotenberg Headless PDF
- **Purpose**: Compiles rendered presentation layout JSON into a high-resolution, branded PDF proposal document ready for client presentation.
- **Input**: `rendered_proposal.json` from Node 7.
- **Output**: Binary PDF document buffer (`proposal_document.pdf`).

---

### Node 9: CRM Proposal Attachment & Deal Advance
- **Node Name**: `CRM Proposal Attachment & Deal Advance`
- **n8n Node Type**: `n8n-nodes-base.hubspot`
- **Purpose**: Uploads compiled proposal PDF to HubSpot Deal files, stores proposal link, and advances stage to `Proposal Sent`.
- **Configuration**:
  - `resource`: `file` / `deal`
  - `dealId`: `={{$json.deal_id}}`
  - `properties`:
    - `sympl_proposal_status`: `PROPOSAL_DELIVERED`
    - `sympl_proposal_id`: `={{$json.proposal_id}}`
    - `dealstage`: `presentationscheduled`

---

### Node 10: Client Delivery Dispatcher
- **Node Name**: `Client Delivery Dispatcher`
- **n8n Node Type**: `n8n-nodes-base.emailSend` (SMTP / SendGrid)
- **Purpose**: Sends branded proposal presentation email with attached PDF and personalized discovery recap to the prospective client.
- **Configuration**:
  - `toEmail`: `={{$json.client_contact_email}}`
  - `subject`: `Sympl Solutions — Service Proposal for {{$json.client_name}}`
  - `attachments`: `proposal_document.pdf`

---

### Node 11: Follow-up Reminder Scheduler
- **Node Name**: `Follow-up Reminder Scheduler`
- **n8n Node Type**: `n8n-nodes-base.wait`
- **Purpose**: Automated sales nurture sequence. Pauses for 3 business days; if deal stage remains `Proposal Sent`, alerts Account Executive to initiate follow-up outreach.
- **Configuration**:
  - `amount`: `3`
  - `unit`: `days`
