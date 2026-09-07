# Sympl Solutions Proposal RAG — Proposal Renderer Layer Design (Phase 5)

## 1. Architectural Overview & Separation of Concerns

The **Proposal Renderer Layer** (`sympl_renderer`) is the presentation boundary of the Sympl Proposal RAG architecture. It sits downstream from the Proposal Writer and translates the validated narrative structure (`proposal_draft.json`) into presentation-ready document outputs (Canva Connect designs, printable HTML/PDFs, Markdown, and JSON payloads).

```
Client Intake
      │
      ▼
Proposal Planner (Phase 3)
      │
      ▼ [Contract: proposal_plan.json]
Proposal Writer (Phase 4)
      │
      ▼ [Contract: proposal_draft.json]
Proposal Renderer Layer (Phase 5)
  ├── Draft Input Contract Validator
  ├── Dynamic Template Mapper (Cover, Exec Summary, Overview, Details, Timeline, Why Us, Pricing, Exclusions, Closing)
  ├── Sympl Corporate Branding Layer (Palettes, Typography, Spacing, Assets)
  ├── Layout Engine & Capacity Monitor
  ├── Canva Integration (CanvaConnectClient & MockCanvaClient)
  ├── Multi-Stage Presentation Integrity Validator (Content, Pricing, References, Layout Overflow)
  └── Output Adapters (JSON, Canva Payload, HTML/PDF, Markdown)
      │
      ▼
Presentation Delivery: Canva Design / PDF / Rendered JSON
```

### Core Architectural Invariant
The Proposal Renderer is **strictly a presentation formatting and layout compilation engine**. It is NOT an intelligence layer.

The Renderer MUST NOT:
- Generate marketing or promotional copy.
- Rewrite, truncate, or paraphrase proposal narrative.
- Summarize sections or alter bullet points.
- Add or remove approved services.
- Alter fee items, amounts, currencies, or billing terms.
- Modify or invent reference blocks (Why Us credentials or legal disclaimers).
- Invent contact details, client facts, or call-to-action statements.
- Infer missing sections.

---

## 2. Rendering Lifecycle

The rendering pipeline processes documents in six deterministic stages:

```
[proposal_draft.json]
         │
         ▼
[1. Draft Validator]       ── Rejects malformed or incomplete drafts (InvalidDraftError)
         │
         ▼
[2. Template Mapper]       ── Dynamically compiles draft sections into structured pages
         │
         ▼
[3. Branding Layer]        ── Applies Sympl corporate palette, typography, and card tokens
         │
         ▼
[4. Layout Engine]         ── Checks component capacity, density thresholds, and page counts
         │
         ▼
[5. Canva / Export Client] ── Instantiates design, populates element tree, exports PDF
         │
         ▼
[6. Render Validator]      ── Confirms zero content drift, pricing preservation, and block integrity
         │
         ▼
[7. Output Adapters]       ── Emits rendered_proposal.json, HTML/PDF, Canva payload, or Markdown
```

---

## 3. Dynamic Page Generation Architecture

The Renderer **does not enforce a rigid fixed page count (e.g. 9 pages)**. Instead, pages scale naturally to accommodate the scope of the engagement:

| Page Type | Dynamic Inclusion Rule | Purpose & Components |
| :--- | :--- | :--- |
| **Cover Page** | Always Included | Document title, prepared for client name, Sympl brand header, subtitle, date. |
| **Executive Summary** | Always Included | Executive narrative, engagement objectives, partnership framing. |
| **Services Overview** | Included if > 1 Section | Functional matrix summarizing all active operational workstreams. |
| **Service Detail Pages** | **Dynamic (1 page per draft section)** | Section opening narrative and subsection cards containing active-verb deliverable bullets. |
| **Implementation Timeline** | **Dynamic (Transformation / Transition)** | Milestone roadmap (Discovery, Migration/Parallel Run, Go-Live) included whenever digital transformation or onboarding scopes exist. |
| **Why Sympl Solutions** | **Dynamic (Why Us present)** | Multi-card grid displaying verbatim canonical Why Us credentials. Scaled down or omitted for lean/compact proposals. |
| **Investment Schedule** | Always Included | Approved fee schedule table (Category, Frequency, Fee CAD, Scope Details), billing terms, and placeholder preserving tokens. |
| **Terms & Exclusions** | Included if Exclusions present | Structured callout boxes containing verbatim Backlog, Software fee, and HR boundary notes. |
| **Closing / Next Steps** | Always Included | Acceptance sequence (Review, Agreement, Kickoff) and official contact footer. |

### Page Count Examples
- **Compact Bookkeeping Proposal:** 6 pages (Cover, Exec Summary, Bookkeeping Detail, Pricing, Exclusions, Closing).
- **Nonprofit Proposal with Why Us:** 8 pages (Cover, Exec Summary, Services Overview, Bookkeeping Detail, Reporting Detail, Why Sympl, Pricing, Exclusions, Closing).
- **Comprehensive Transformation Proposal:** 12–14 pages (Cover, Exec Summary, Services Overview, Transformation Detail, Bookkeeping Detail, Payroll Detail, Reporting Detail, Compliance Detail, Audit Detail, Timeline Roadmap, Why Sympl, Pricing, Exclusions, Closing).

---

## 4. Sympl Corporate Branding Layer (`branding.py`)

The branding layer ensures strict visual consistency across all proposals:

### Color Palette Tokens
- **Primary Navy (`#1A2E40`):** Foundation color for titles, primary headings, table headers, and borders.
- **Secondary Deep Teal (`#008080`):** Professional accent color for section dividers, highlights, and badges.
- **Ocean Accent (`#2B6CB0`):** Section subtitle highlights and interactive accents.
- **Slate Charcoal (`#2D3748`):** High-contrast neutral for readable body text.
- **Neutral Light (`#F7FAFC`):** Warm off-white surface tint for card backgrounds.
- **Surface Pure White (`#FFFFFF`):** Base container canvas.
- **Callout Background (`#EDF2F7`):** Muted container background for legal boundary notes.
- **Table Header Navy (`#2A4365`):** High-contrast table column headers.

### Typography Specifications
- **Heading Font:** `Montserrat, Inter, sans-serif`
- **Body Font:** `Inter, -apple-system, BlinkMacSystemFont, sans-serif`
- **Monospace Font:** `JetBrains Mono, Consolas, monospace`
- **Title Size:** `28pt` | **Section Headings:** `18pt`–`20pt` | **Body Size:** `10.5pt` | **Bullets:** `10pt`

---

## 5. Canva Connect API Integration (`canva_client.py`)

The Canva abstraction supports zero-downtime execution across local, testing, and production environments:

### Client Implementations
1. **`CanvaConnectClient` (Production Mode):**
   - Connects to Canva Connect REST API v1 (`https://api.canva.com/rest/v1`).
   - Uses `CANVA_API_KEY` for bearer authentication.
   - Uses `CANVA_TEMPLATE_ID` to instantiate designs via the Autofills endpoint.
   - Triggers asynchronous PDF export jobs and polls for final download URLs.

2. **`MockCanvaClient` (Local Development & CI/CD Mode):**
   - Activated automatically when `CANVA_API_KEY` or `CANVA_TEMPLATE_ID` are missing, or when `RENDERER_MODE=mock`.
   - Generates deterministic simulated design IDs (`canva_des_mock_[uuid]`).
   - Automatically writes `proposal_render.json` locally for inspection.
   - Returns mock PDF download URIs without network calls.

### Client Factory
```python
from sympl_renderer import get_canva_client

# Automatically selects CanvaConnectClient or MockCanvaClient based on credentials
client = get_canva_client()
```

---

## 6. Output Adapter Architecture (`output_adapter.py`)

The output adapter layer decouples the presentation data model from physical file formats:

| Adapter | Output Format | Use Case |
| :--- | :--- | :--- |
| **`JsonOutputAdapter`** | `rendered_proposal.json` | Canonical structured JSON artifact consumed by web frontends, n8n automations, and CI/CD pipelines. |
| **`CanvaPayloadAdapter`** | Dict / JSON | Direct payload structure expected by the Canva Connect API Autofill endpoint. |
| **`HtmlPdfAdapter`** | Standalone HTML (`.html`) | Clean, standalone printable HTML document with embedded Sympl brand CSS for headless PDF generation (e.g. WeasyPrint or Chrome print). |
| **`MarkdownAdapter`** | Document Markdown (`.md`) | Clean, page-delineated markdown representation for plain-text viewing and audits. |

---

## 7. Multi-Stage Presentation Integrity Validator (`validator.py`)

Every rendered proposal is audited by four independent validator components:

1. **`ContentIntegrityValidator`:**
   - Flattens all rendered components (headings, paragraphs, bullet lists, cards, tables, footers).
   - Confirms that every piece of text in `proposal_draft.json` (executive summary, section titles, opening texts, subsection headings, bullets) appears verbatim in the rendered document.
   - Rejects missing or altered text with `ContentIntegrityError`.

2. **`PricingIntegrityValidator`:**
   - Verifies the pricing table component exists on the Investment Schedule page.
   - Confirms every fee item category, amount, currency, and billing frequency matches the draft.
   - Enforces placeholder token preservation (`[PRICING_PLACEHOLDER...]`), preventing invented fees.
   - Rejects altered pricing with `PricingIntegrityError`.

3. **`ReferenceIntegrityValidator`:**
   - Verifies all Why Us credentials and conditional exclusion strings (backlog clean-up, software exclusions, HR boundary) match verbatim.
   - Rejects modified or missing blocks with `ReferenceIntegrityError`.

4. **`LayoutOverflowValidator`:**
   - Detects empty pages (pages containing zero components or zero content).
   - Detects missing page titles.
   - Evaluates component density (flags service detail pages with > 10 bullets or > 1,600 characters for high density / overflow warnings).
   - Raises `LayoutOverflowError` on critical layout defects.

---

## 8. Deployment & CI/CD Verification

### Automated Regression Verification Commands
```bash
# 1. Proposal Renderer Test Suite (10 scenarios)
python -m pytest tests/test_renderer.py -v

# 2. Proposal Writer Test Suite (11 scenarios)
python -m pytest tests/test_writer.py -v

# 3. Proposal Planner Regression Suite (11 scenarios)
python tests/test_proposal_planner.py
```

### Production Deployment Prerequisites
1. Provision Canva Developer account and obtain OAuth/API Key (`CANVA_API_KEY`).
2. Design master Canva Brand Template in Canva workspace and obtain `CANVA_TEMPLATE_ID`.
3. Set environment variables in deployment environment (`.env` or secret manager):
   ```env
   CANVA_API_KEY=cnv_live_...
   CANVA_TEMPLATE_ID=DAF...
   ```
4. If Canva credentials are not provided, the renderer functions completely in local development mode without failure.
