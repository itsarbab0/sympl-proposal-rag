# Sympl Solutions Proposal RAG — Proposal Writer Layer Design (Phase 4)

## 1. Architectural Overview & Separation of Concerns

The **Proposal Writer Layer** (`sympl_writer`) is the strictly controlled narrative generation component of the Sympl Solutions Proposal RAG architecture. It serves as the deterministic translation boundary between structural decision-making (Phase 3: Proposal Planner) and document presentation (Future: Canva / PDF Renderer).

```
Client Intake
      │
      ▼
Proposal Planner (Phase 3)
      │
      │  [Input Contract: proposal_plan.json]
      │  (Contains: client_context, approved_scope, sections, exemplars, reference_blocks, pricing)
      │  (Excludes: requested_scope, unapproved_requested_scope)
      ▼
Proposal Writer Layer (Phase 4)
  ├── Input Scope Firewall
  ├── Prompt Builder (System Rules, Exemplars as Guidance Only, Reference Blocks)
  ├── LLM Client Abstraction (OpenRouter, Ollama, Mock)
  ├── Proposal Validator (Scope, Completeness, Pricing, Historical Firewall, Style, Reference Integrity)
  └── Regeneration Loop (Max 2 Retries with targeted error feedback)
      │
      │  [Output Contract: proposal_draft.json]
      ▼
Future Canva / PDF Renderer
```

### Critical Architectural Boundaries
The Proposal Writer is **strictly an operational narrative generation engine**. It is explicitly prohibited from:
- Selecting or altering proposal archetypes.
- Deciding which service families or deliverables are offered.
- Expanding or modifying approved commercial fees, rates, or payment schedules.
- Selecting, omitting, or modifying Why Us credentials or legal disclaimers.
- Ingesting raw client intake or uncurated `requested_scope`.
- Inferring client requirements beyond the approved plan.
- Executing historical vector similarity queries itself.

All structural and operational determinations belong exclusively to the **Proposal Planner**.

---

## 2. Input and Output Contracts

### 2.1 Writer Input Contract (`proposal_plan.json`)
The Writer receives only curated plans. Any plan presenting uncurated scope is rejected at ingestion.

**Mandatory Ingested Fields:**
- `client_context`: Client name, organization type (`nonprofit`, `for_profit`), sector (`community_services`, `arts_culture`), current/target systems, engagement complexity.
- `approved_scope`: Authoritative dict of approved services (e.g., `bookkeeping`, `payroll`, `financial_reporting`, `compliance`, `digital_transformation`).
- `sections`: Ordered target sections with structural roles, section instructions, applied style rules, attached canonical reference blocks, and attached historical retrieval exemplars.
- `retrieval_context.exemplars`: Top historical chunks formatted with `role`, `proposal_code`, and `cleaned_text` (strictly isolated as style/tone guidance).
- `reference_blocks`: Canonical reference block manifests (Why Us blocks, conditional backlog disclaimer, software fee disclaimer, HR boundary disclaimer).
- `pricing` / `commercial_summary`: Approved fee schedule, currency, billing frequency, and placeholder status.

**Strictly Forbidden Input Fields (Input Scope Firewall):**
- `requested_scope`
- `unapproved_requested_scope`

If either forbidden field is detected in `plan_data`, `ProposalWriter` immediately raises `ScopeFirewallError` prior to any LLM invocation.

### 2.2 Writer Output Contract (`proposal_draft.json`)
The generated draft is pure JSON without markdown wrappers or conversational preamble:

```json
{
  "title": "Accounting & Bookkeeping Services Proposal for [Client Name]",
  "executive_summary": "Concise 1-2 paragraph executive summary framing objectives, continuity, and partnership value.",
  "sections": [
    {
      "section_title": "Section Title",
      "opening_text": "1-2 sentence operational framing text.",
      "subsections": [
        {
          "heading": "Subsection Heading",
          "bullets": [
            "Action verb starting bullet describing specific operational deliverable",
            "Action verb starting bullet describing specific operational deliverable"
          ]
        }
      ]
    }
  ],
  "why_us": [
    "Exact canonical Why Us reference block 1",
    "Exact canonical Why Us reference block 2"
  ],
  "pricing": {
    "pricing_model": "fixed_retainer | placeholder | time_and_materials",
    "currency": "CAD",
    "billing_schedule": "Monthly retainer invoiced on the 1st of each service month.",
    "fee_items": [
      {
        "category": "Monthly Recurring Retainer",
        "amount": 3650.0,
        "currency": "CAD",
        "billing_frequency": "monthly",
        "description": "Comprehensive recurring accounting, general ledger, and financial operations as scoped.",
        "is_placeholder": false
      }
    ],
    "has_placeholders": false
  },
  "exclusions": [
    "Exact canonical disclaimer string 1",
    "Exact canonical disclaimer string 2"
  ],
  "validation_metadata": {
    "passed": true,
    "retries_count": 0,
    "errors": [],
    "warnings": [],
    "details": {
      "historical_firewall": { "passed": true },
      "scope_completeness": { "passed": true },
      "scope_violations": { "passed": true },
      "pricing_safety": { "passed": true },
      "reference_blocks": { "passed": true },
      "style_compliance": { "passed": true, "warnings": [] }
    },
    "provider": "openrouter",
    "model": "google/gemini-2.5-flash",
    "timestamp": "2026-09-06T19:50:00Z"
  }
}
```

---

## 3. Validator Design

The `ProposalValidator` executes six deterministic verification checks against every candidate proposal draft:

### 3.1 Historical Data Firewall (`check_historical_firewall`)
Prevents leakage of confidential historical client entities, dates, and figures:
- **Historical Client Codes:** `TACT`, `PIRS`, `GOODFOOT`, `RPFF`, `YPT`, `CARE/OF`, `CAREOF`, `CAHOOTS`.
- **Historical Client Names:** `The Autism Centre of Toronto`, `Pacific Immigrant Resources Society`, `Good Foot Support Services`, `Regent Park Film Festival`, `Young People's Theatre`, `Care/Of Experiences`, `Cahoots Theatre Company`.
- **Forbidden Historical Years:** `2025`, `2026`.
- **Historical Figures:** Historical headcount counts (`19 employees`, `11 employees`), total budgets (`$1.4M`, `$1.1M`), and historical contract fees (`$4,500/month`, `$3,500/month`, `$8,500`).
- **Failure Mode:** Raises `HistoricalLeakageError`.

### 3.2 Scope Completeness Validator (`check_scope_completeness`)
Ensures no approved scope item is dropped or overlooked by the LLM:
- Scans `plan_data["approved_scope"]` for active service families (`bookkeeping`, `payroll`, `financial_reporting`, `compliance`, `digital_transformation`, `management_consulting`, `transition_services`, `audit_oversight`).
- Confirms corresponding section titles and deliverable bullets exist in `draft.sections`.
- **Failure Mode:** Raises `MissingApprovedScopeItemError("MISSING_APPROVED_SCOPE_ITEM: Approved scope item '[family]' is missing from generated draft")`.

### 3.3 Scope Violation Validator (`check_scope_violations`)
Ensures no unauthorized services are invented:
- Checks if unapproved service families appear in sections.
- Verifies conditional exclusions (e.g. if `compliance.t3010_support` is `false`, rejects T3010 charity filing bullets; if `bookkeeping.catchup_cleanup` is `false`, rejects backlog cleanup bullets).
- **Failure Mode:** Raises `ScopeViolationError`.

### 3.4 Pricing Safety Validator (`check_pricing_safety`)
Protects commercial integrity:
- Enforces preservation of `[PRICING_PLACEHOLDER]` tokens and flags when pricing is pending.
- Prevents invented fees or unauthorized dollar amounts.
- Confirms approved fees match `plan_data["pricing"]["fee_items"]`.
- **Failure Mode:** Raises `PricingSafetyError`.

### 3.5 Reference Block Integrity Validator (`check_reference_blocks`)
Ensures canonical reference blocks are inserted verbatim without hallucination:
- Verifies Why Us credentials, Backlog disclaimer, Software subscription disclaimer, and HR boundary disclaimer appear verbatim (whitespace-normalized) in `draft.why_us`, `draft.exclusions`, or `draft.pricing`.
- **Failure Mode:** Raises `ReferenceBlockTamperingError`.

### 3.6 Style Compliance Validator (`check_style_compliance`)
Enforces the Sympl house style:
- **Forbidden Buzzwords:** `leverage`, `cutting-edge`, `game-changing`, `holistic ecosystem`, `unlock value`, `bespoke transformation journey`, `strategic synergies`, `world-class`, `paradigm shift`.
- **Bullet Word Count:** Service bullets target 6–15 words (flags bullets > 25 words).
- **Active Verbs:** Bullets must start with active imperative verbs (`Manage`, `Reconcile`, `Configure`, `Prepare`, `Review`, `Process`, `Deliver`).
- **Passive Voice Suppression:** Rejects patterns such as `will be managed by`, `will be reconciled by`, `is handled by`.
- **Typography:** No trailing periods on bullet points.
- **Failure Mode:** Raises `StyleViolationError`.

---

## 4. Regeneration & Error Feedback Loop

```
    [Plan Ingestion]
           │
           ▼
    [Prompt Builder]
           │
           ▼
      [LLM Call]  ◄───────────────────────────┐
           │                                  │
           ▼                                  │
    [JSON Parse]                              │
           │                                  │
           ▼                                  │ (Retry with structured errors)
      [Validator]                             │ (Max 2 retries)
           │                                  │
      Passed? ─── No (Attempts <= 2) ─────────┘
           │
          Yes
           │
           ▼
     [Final Draft]
```

If validation detects errors on any generation attempt:
1. The specific violation messages (e.g., `MISSING_APPROVED_SCOPE_ITEM`, `Detected historical client code: 'TACT'`, `Forbidden buzzword: 'leverage'`) are formatted into a `CRITICAL: PREVIOUS ATTEMPT FAILED VALIDATION` prompt block.
2. The prompt builder re-submits the plan with explicit correction guidance to the LLM.
3. The writer allows up to **2 retries** (3 total attempts).
4. If validation fails after 2 retries, `RegenerationExhaustedError` (subclass of `WriterError`) is raised, halting pipeline execution and logging audit trails.

---

## 5. LLM Provider System

The LLM abstraction (`sympl_writer/llm_client.py`) provides unified access across cloud, local, and testing environments:

| Provider | Environment Variables | Description |
| :--- | :--- | :--- |
| **OpenRouter** | `LLM_PROVIDER=openrouter`<br>`OPENROUTER_API_KEY`<br>`OPENROUTER_MODEL` | High-quality frontier models (e.g. `google/gemini-2.5-flash`, `anthropic/claude-3.5-sonnet`). |
| **Local Ollama** | `LLM_PROVIDER=ollama`<br>`OLLAMA_BASE_URL`<br>`OLLAMA_MODEL` | Air-gapped local execution (e.g. `llama3.2`, `mistral`, `qwen2.5`). |
| **Mock** | `LLM_PROVIDER=mock` | Deterministic, zero-network offline testing provider. Fully supports all 5 archetypes and scope modules. |

Model names are never hardcoded and default to environment settings.

---

## 6. Security and Data Protection Rules

1. **Firewall Invariant:** The writer never receives intake transcripts, prospect raw wishlists, or unapproved scope.
2. **Exemplar Quarantine:** Historical chunks in `retrieval_context.exemplars` are tagged with explicit prompt firewalls (`STYLE GUIDANCE ONLY — DO NOT COPY FACTS OR ENTITIES`).
3. **Database Immutability:** The Writer layer does not open write connections to PostgreSQL. All historical corpus tables (`proposal_documents`, `proposal_chunks`, `embeddings`, `sympl_style_rules`, `sympl_reference_blocks`) remain completely frozen.

---

## 7. Canva / Renderer Handoff Specification

The generated `proposal_draft.json` is directly compatible with the upcoming Canva Automator and PDF rendering engines:

- **Section Hierarchy:** Predictable structure (`sections[].section_title`, `sections[].opening_text`, `sections[].subsections[].heading`, `sections[].subsections[].bullets[]`) maps 1-to-1 to Canva multi-column slide layouts.
- **Why Us Callout Cards:** Clean array of string blocks in `why_us` maps directly to grid testimonial and credentials cards.
- **Commercial Schedule:** Structured `pricing.fee_items` with explicit billing frequencies and placeholder markers enables table generation without freeform text parsing.
- **Exclusions Callout Box:** Consolidated string array in `exclusions` maps to footer disclaimer boxes.
- **Audit Verification:** `validation_metadata` provides complete provenance for automated CI/CD and compliance signoff.
