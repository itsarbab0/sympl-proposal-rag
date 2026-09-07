# Normalized Dataset Data Contract

This document specifies the exact contract for normalized proposal JSON datasets consumed by the Sympl Proposal RAG system.

Every historical proposal is represented by **one JSON file** placed in `data/normalized/` (e.g., `data/normalized/TACT_2026.json`).

---

## 1. Top-Level Structure

Each JSON file contains two primary top-level keys:
- `"proposal"`: An object containing proposal-level document metadata.
- `"chunks"`: An array of objects, where each object represents a semantic section or service block.

```json
{
  "proposal": { ... },
  "chunks": [ ... ]
}
```

---

## 2. Proposal Object Specification (`proposal`)

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `proposal_code` | `string` | **Yes** | Unique business identifier for the proposal (e.g., `"TACT_2026"`). Must be globally unique across all proposal files. |
| `client_name` | `string` | **Yes** | Full commercial or legal name of the prospective or actual client (e.g., `"The Autism Centre of Toronto"`). |
| `proposal_title` | `string` \| `null` | No | Title of the proposal as presented on the cover page (e.g., `"Accounting & Bookkeeping Services Proposal"`). |
| `proposal_date` | `string` \| `null` | No | Proposal issuance date formatted as ISO `YYYY-MM-DD` (e.g., `"2026-05-01"`). |
| `source_filename` | `string` | **Yes** | Name of the source file in `data/raw/` from which this proposal was derived (e.g., `"TACT x Sympl - Bookkeeping Proposal - May 2026.pdf"`). |
| `organization_type` | `string` \| `null` | No | Type of entity (e.g., `"charity"`, `"nonprofit"`, `"social_enterprise"`, `"commercial"`). |
| `sector` | `string` \| `null` | No | Operational sector (e.g., `"arts_culture"`, `"social_services"`, `"literacy"`, `"health"`). |
| `engagement_type` | `string` \| `null` | No | Structure of engagement (e.g., `"ongoing"`, `"cleanup"`, `"ongoing_plus_transformation"`). |
| `proposal_complexity` | `string` \| `null` | No | Complexity classification (e.g., `"standard"`, `"comprehensive"`, `"multi_entity"`). |
| `core_bookkeeping` | `boolean` | **Yes** | `true` if the proposal encompasses standard core bookkeeping/accounting services; `false` if advisory/transformation only. Defaults to `true`. |
| `raw_text` | `string` \| `null` | No | Complete, unedited raw textual extraction of the entire proposal document. |
| `cleaned_text` | `string` \| `null` | No | Canonical cleaned and formatted textual extraction of the entire document. |
| `metadata` | `object` | No | Flexible JSON object for document-level tags, page counts, author details, or legacy identifiers. |

---

## 3. Proposal Chunk Object Specification (`chunks[]`)

Each entry in `"chunks"` represents a discrete, meaningful section or reusable modular block.

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `chunk_key` | `string` | **Yes** | Unique semantic identifier for the chunk (e.g., `"TACT_2026_CONTEXT_OBJECTIVES"`). Must be globally unique. |
| `section_order` | `integer` \| `null` | No | 1-based sequential position of the section within the original document. |
| `section_type` | `string` | **Yes** | Categorical classification of the proposal section (see Known Section Types). |
| `section_title` | `string` \| `null` | No | Heading or title of the section as presented in the proposal. |
| `service_modules` | `array[string]` | **Yes** | Service taxonomy tags describing the work (e.g., `["payroll", "reconciliations"]`). Empty array `[]` if not applicable. |
| `organization_type` | `string` \| `null` | No | Inherited or chunk-specific organization classification. |
| `sector` | `string` \| `null` | No | Inherited or chunk-specific industry sector. |
| `engagement_type` | `string` \| `null` | No | Inherited or chunk-specific engagement type. |
| `core_bookkeeping` | `boolean` | **Yes** | `true` if this specific chunk covers core bookkeeping work; `false` otherwise. |
| `accounting_systems` | `array[string]` | **Yes** | Accounting software cited in this chunk (e.g., `["QuickBooks Online"]`, `["Xero"]`). |
| `payroll_systems` | `array[string]` | **Yes** | Payroll tools cited (e.g., `["ADP"]`, `["Payworks"]`, `["Wagepoint"]`). |
| `cadence` | `array[string]` | **Yes** | Frequency of service delivery mentioned (e.g., `["monthly"]`, `["semi_monthly"]`, `["quarterly"]`, `["annual"]`). |
| `special_requirements` | `array[string]` | **Yes** | Specific compliance or client constraints (e.g., `["funder_reporting_t3010"]`, `["multi_currency"]`). |
| `raw_text` | `string` | **Yes** | Exact source wording from the proposal. Preserves typos, OCR anomalies, and exact layout. |
| `cleaned_text` | `string` | **Yes** | Corrected canonical text. Fixes typos and OCR artifacts while strictly preserving Sympl tone and meaning. |
| `retrieval_text` | `string` | **Yes** | Enriched textual representation formatted for embedding generation and semantic retrieval. |
| `retrieval_enabled` | `boolean` | **Yes** | Controls whether this chunk is indexed for semantic retrieval. Must be `false` for pricing and boilerplate blocks. |
| `commercial_reference_only` | `boolean` | **Yes** | If `true`, this chunk may only be used for structural formatting reference, never for dynamic scope generation. |
| `pricing_content` | `boolean` | **Yes** | Must be `true` if the chunk references fees, dollar values, rates, or payment structures. |
| `boilerplate_content` | `boolean` | **Yes** | Must be `true` if this section is standard reusable Sympl language rather than bespoke client proposal content. |
| `metadata` | `object` | No | Open JSONB object for arbitrary metadata, bounding boxes, or curation notes. |

---

## 4. Critical Field Definitions & Distinctions

### Text Triad: `raw_text` vs `cleaned_text` vs `retrieval_text`

The system maintains three distinct textual representations for every semantic chunk to balance historical fidelity with retrieval effectiveness:

1. **`raw_text`**:
   - **Historical truth**: Verbatim extraction from the source document.
   - **Rule**: Never edit, normalize, or correct typos here. If the source says `"issuign ROEs"`, `raw_text` must contain `"issuign ROEs"`.

2. **`cleaned_text`**:
   - **Human-readable canonical form**: Used when presenting historical context to the LLM or a human reviewer.
   - **Rule**: Correct obvious OCR errors and spelling mistakes (`"issuign ROEs"` -> `"issuing ROEs"`), but **never fundamentally rewrite or modernize** the proposal. Sympl's authentic style, syntax, and voice must be preserved.

3. **`retrieval_text`**:
   - **Vector search input**: The string representation that will eventually be passed to the embedding model.
   - **Rule**: Combines section metadata, title, and cleaned text to maximize semantic match quality during retrieval. (e.g., `"Section: Context & Objectives | Client Sector: social_services | Organization: charity\n\nThe Autism Centre of Toronto requires comprehensive..."`).

---

### `core_bookkeeping`

A boolean indicator distinguishing baseline day-to-day general ledger operations from specialized advisory or transformation work.
- `true`: General ledger entries, bank and credit card reconciliations, sales tax (GST/HST) filing, standard month-end closing, and routine accounts payable/receivable.
- `false`: System migrations, financial modeling, custom funder audits, digital workflows, or board governance advisory.

---

### `service_modules`

An array of strings tagging the specific operational functions addressed in the chunk.

**Known Taxonomy for Validation Warnings**:
- `bookkeeping`: Routine transaction recording and general ledger maintenance.
- `reconciliations`: Bank, credit card, and clearing account reconciliations.
- `accounts_payable`: Bill entry, vendor approvals, and disbursement management.
- `accounts_receivable`: Invoicing, customer collections, and receipt tracking.
- `payroll`: Pay runs, source deduction remittances, ROEs, and T4 preparation.
- `financial_reporting`: Monthly balance sheets, income statements, and budget vs. actual reports.
- `compliance`: GST/HST returns, charity T3010 filings, WSIB, and corporate registrations.
- `year_end`: Preparation of files and working papers for external accountants or auditors.
- `audit`: Direct facilitation, PBC list management, and auditor liaison.
- `financial_management`: Controller-level oversight, cash flow analysis, and advisory.
- `budgeting`: Annual budget formulation and departmental allocations.
- `cash_flow`: Forecasting and liquidity management.
- `funder_reporting`: Contribution agreement tracking and expenditure reporting.
- `digital_transformation`: Upgrading financial infrastructure and paperless transitions.
- `systems_implementation`: Deploying QBO, Plooto, Payworks, Dext, or Expensify.
- `onboarding`: Transitioning historical books and initial client setup.
- `transition`: Phased handoff from prior bookkeepers or internal staff.
- `training`: Educating client staff on document submission and approval workflows.
- `process_documentation`: Creating standard operating procedures (SOPs).

---

### Retrieval Invariants & Safety Classification

#### 1. NORMAL RAG RETRIEVAL RULE
`proposal_chunks` used for semantic content retrieval must normally have:
```text
retrieval_enabled = TRUE
```
These chunks represent unique, client-adapted narrative, scope definitions, objectives, and service descriptions from historical proposals.

#### 2. Historical Pricing Content
Historical pricing rows must satisfy:
```text
pricing_content = TRUE
commercial_reference_only = TRUE
retrieval_enabled = FALSE
```
- **Safety Enforcement**: Enforced both in JSON dataset validation and via PostgreSQL database check constraint (`chk_pricing_safety`).
- **Retention Principle**: Historical pricing is **NOT deleted**. It is retained as controlled commercial reference material to analyze presentation layout, fee structures (monthly vs. one-time), and exclusion wording.
- **Strict Invariant**: Historical pricing must **NEVER** drive, infer, interpolate, or recommend new client pricing, and must never participate in normal semantic RAG retrieval.

#### 3. Historical Boilerplate Content
Historical boilerplate rows must satisfy:
```text
boilerplate_content = TRUE
retrieval_enabled = FALSE
```
- **Safety Enforcement**: Enforced in JSON validation and via PostgreSQL database check constraint (`chk_boilerplate_retrieval`).
- **Approved Blocks Distinction**: Approved reusable boilerplate belongs in:
  ```text
  sympl_reference_blocks
  ```
  (e.g., standard software subscription exclusions, bookkeeping backlog exclusions, "Why Sympl" introductions, client responsibilities). Reusable boilerplate must be inserted deterministically, not fuzzy-matched via semantic RAG similarity.

---

### Flexibility of `metadata`

The `metadata` field on both proposals and chunks is stored as PostgreSQL `JSONB`. It is intentionally unconstrained to accommodate:
- Page numbers and bounding box references from source PDFs.
- Curating analyst notes.
- Specific client-requested exceptions.
- Ingestion pipeline markers.

---

## 5. Complete Illustrative Example

```json
{
  "proposal": {
    "proposal_code": "TACT_2026",
    "client_name": "The Autism Centre of Toronto",
    "proposal_title": "Accounting & Bookkeeping Services Proposal",
    "proposal_date": "2026-05-01",
    "source_filename": "TACT x Sympl - Bookkeeping Proposal - May 2026.pdf",
    "organization_type": "charity",
    "sector": "social_services",
    "engagement_type": "ongoing_plus_transformation",
    "proposal_complexity": "comprehensive",
    "core_bookkeeping": true,
    "raw_text": "Proposal for Bookkeeping and Financial Operations Support...",
    "cleaned_text": "Proposal for Bookkeeping and Financial Operations Support...",
    "metadata": {
      "curated_by": "Senior Operations Analyst",
      "curated_date": "2026-05-15",
      "original_page_count": 14
    }
  },
  "chunks": [
    {
      "chunk_key": "TACT_2026_CONTEXT_OBJECTIVES",
      "section_order": 1,
      "section_type": "context_objectives",
      "section_title": "Context & Objectives",
      "service_modules": [
        "bookkeeping",
        "digital_transformation"
      ],
      "organization_type": "charity",
      "sector": "social_services",
      "engagement_type": "ongoing_plus_transformation",
      "core_bookkeeping": false,
      "accounting_systems": [
        "QuickBooks Online"
      ],
      "payroll_systems": [
        "ADP Workforce Now"
      ],
      "cadence": [
        "monthly"
      ],
      "special_requirements": [
        "funder_reporting_t3010"
      ],
      "raw_text": "The Autism Centre of Toronto (TACT) is seeking an experienced financial operations partner to modernise their bookkeeping workflows and support ongoing compliance.",
      "cleaned_text": "The Autism Centre of Toronto (TACT) is seeking an experienced financial operations partner to modernise their bookkeeping workflows and support ongoing compliance.",
      "retrieval_text": "Section: Context & Objectives | Sector: social_services | Org: charity | Systems: QuickBooks Online, ADP Workforce Now\n\nThe Autism Centre of Toronto (TACT) is seeking an experienced financial operations partner to modernise their bookkeeping workflows and support ongoing compliance.",
      "retrieval_enabled": true,
      "commercial_reference_only": false,
      "pricing_content": false,
      "boilerplate_content": false,
      "metadata": {
        "page_number": 2
      }
    },
    {
      "chunk_key": "TACT_2026_PRICING_TABLE",
      "section_order": 8,
      "section_type": "pricing",
      "section_title": "Investment Schedule",
      "service_modules": [
        "bookkeeping",
        "payroll"
      ],
      "organization_type": "charity",
      "sector": "social_services",
      "engagement_type": "ongoing_plus_transformation",
      "core_bookkeeping": true,
      "accounting_systems": [
        "QuickBooks Online"
      ],
      "payroll_systems": [
        "ADP Workforce Now"
      ],
      "cadence": [
        "monthly"
      ],
      "special_requirements": [],
      "raw_text": "Monthly Bookkeeping and Payroll Retainer: $2,850 + HST per month. One-time Setup & Historical Cleanup: $4,500 + HST.",
      "cleaned_text": "Monthly Bookkeeping and Payroll Retainer: $2,850 + HST per month. One-time Setup & Historical Cleanup: $4,500 + HST.",
      "retrieval_text": "Section: Investment Schedule | Commercial Reference\n\nMonthly Bookkeeping and Payroll Retainer: $2,850 + HST per month. One-time Setup & Historical Cleanup: $4,500 + HST.",
      "retrieval_enabled": false,
      "commercial_reference_only": true,
      "pricing_content": true,
      "boilerplate_content": false,
      "metadata": {
        "page_number": 11,
        "pricing_model": "fixed_monthly_plus_setup"
      }
    }
  ]
}
```
