# Sympl Solutions Proposal Quality Scorecard

**Document Version:** 1.0.0  
**Phase:** 8.5 (Proposal Quality Optimization Layer)  
**Target:** Pre-Flight Quality Gate for n8n Automation & Production Delivery  
**Engine:** Sympl Proposal RAG (`sympl_planner`, `sympl_writer`, `sympl_renderer`, `sympl_storage`)

---

## 1. Executive Overview

The **Sympl Proposal Quality Scorecard** provides an objective, multi-dimensional evaluation framework to verify generated proposals before human dispatch or n8n workflow delivery. Every proposal must pass all **Critical Gates (Pass/Fail)** and achieve a minimum **Quality Index Score of 90/100** across six evaluation categories.

Proposals that fail any critical gate are rejected immediately, triggering automated regeneration or routing to human review.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SYMPL QUALITY EVALUATION PIPELINE                     │
│                                                                             │
│   [Generated Proposal Artifacts]                                            │
│                 │                                                           │
│                 ▼                                                           │
│   ┌──────────────────────────┐                                              │
│   │ 1. Critical Hard Gates   │── FAIL ──► [Pipeline Rejection / Log Error]  │
│   └─────────────┬────────────┘                                              │
│                 │ PASS                                                      │
│                 ▼                                                           │
│   ┌──────────────────────────┐                                              │
│   │ 2. Six-Dimension Scoring │── < 90 ──► [Flagged for Human Revision]      │
│   └─────────────┬────────────┘                                              │
│                 │ ≥ 90                                                      │
│                 ▼                                                           │
│   ┌──────────────────────────┐                                              │
│   │ 3. Manifest Verification │── MISS ──► [Artifact Compilation Error]      │
│   └─────────────┬────────────┘                                              │
│                 │ ALL 5 VERIFIED                                            │
│                 ▼                                                           │
│   [n8n Delivery / Client Ready]                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Critical Hard Gates (Zero-Tolerance Pass/Fail)

Any single failure across these gates halts delivery immediately.

| Gate ID | Gate Name | Requirement | Detection Mechanism |
| :--- | :--- | :--- | :--- |
| **GATE-01** | **Scope Firewall** | No services or deliverables outside `approved_scope`. `requested_scope` items that are unapproved must never appear. | `ProposalValidator.check_scope_violations()` |
| **GATE-02** | **Historical Firewall** | Zero historical client names (`RPFF`, `TACT`, `PIRS`, `Good Foot`, `Cahoots`, `YPT`), codes, years (`2025`, `2026`), or amounts. | `ProposalValidator.check_historical_firewall()` |
| **GATE-03** | **Pricing Safety** | No invented fee amounts. Placeholders (`[Pending Final Scope Confirmation]`) strictly preserved when pricing is unapproved. | `ProposalValidator.check_pricing_safety()` |
| **GATE-04** | **Reference Block Integrity**| Canonical reference blocks (Why Us, Backlog, Software, HR) appear verbatim without alteration. | `ProposalValidator.check_reference_blocks()` |
| **GATE-05** | **Sector Block Isolation** | Sector-specific reference blocks (`ARTS_LEADERSHIP`, `ARTS_EXP_RPFF`) never appear in non-arts proposals; community blocks never in arts. | `WhyUsSelector.assemble_why_us()` |
| **GATE-06** | **Artifact Completeness** | All 5 package artifacts exist: `proposal_plan.json`, `proposal_draft.json`, `rendered_proposal.json`, `proposal.pdf`, `manifest.json`. | `LocalArtifactStore.compile_manifest()` |

---

## 3. Evaluation Dimensions & Scoring Rubric (100 Points Total)

### Dimension 1: Scope Fidelity & Alignment (20 Points)
*Evaluates whether the proposal strictly reflects the client's approved operational scope.*

- **1.1 Scope Completeness (10 pts):** Every service family present in `approved_scope` is clearly articulated with dedicated sections and subsections.
- **1.2 Scope Boundary Defense (5 pts):** Explicit operational boundaries and client prerequisites (e.g. documentation turnaround, approval matrices) are clearly stated.
- **1.3 Exclusions Articulation (5 pts):** Canonical disclaimers (e.g. prior period backlog, software subscription exclusions, HR boundaries) are correctly attached.

### Dimension 2: Operational Depth & Specificity (20 Points)
*Evaluates whether operational details from historical benchmarks are preserved without excessive compression.*

- **2.1 Minimum Service Depth Structure (5 pts):** Each service family includes:
  1. Service Heading
  2. Cadence (e.g., weekly accounts payable cycle, semi-monthly payroll, monthly close)
  3. Operational Subsections (e.g., Accounts Payable, General Ledger Reconciliations, Remittances)
  4. Deliverables & Tangible Outputs
  5. Operational Boundaries
- **2.2 Activity Depth (10 pts):** Contains granular operational duties:
  - Accounts Payable: Bill ingestion, verification against approval policies, batch disbursement scheduling.
  - General Ledger: Bank, credit card, and clearing account reconciliations.
  - Systems: QuickBooks Online / cloud ledger maintenance and chart of accounts hygiene.
  - Compliance: Public service body rebates, remittance receipts, working paper binders.
- **2.3 Client Prerequisites (5 pts):** Specific client obligations (source document deadlines, manager sign-offs) defined.

### Dimension 3: Style, Voice & Executive Precision (15 Points)
*Evaluates adherence to Sympl Solutions editorial standards.*

- **3.1 Executive Summary Conciseness (5 pts):** 
  - Word count strictly $\le 120$ words.
  - Client-specific opening referencing the client organization by name.
  - References approved service families.
  - Explains operational value and fiscal control.
- **3.2 Bullet Quality & Syntax (5 pts):**
  - Begins with active, operational verb (e.g., *Process*, *Reconcile*, *Maintain*, *Compile*, *Deliver*).
  - Length between 6 and 20 words (acceptable window 4–25 words).
  - Zero trailing periods on bullet points.
- **3.3 Buzzword Elimination (5 pts):** Complete absence of generic LLM hype:
  - Forbidden: *"comprehensive suite"*, *"continued success"*, *"core mission"*, *"strategic partnership"*, *"leverage"*, *"synergy"*, *"cutting-edge"*, *"seamlessly"*.

### Dimension 4: Pricing Schedule Integrity (15 Points)
*Evaluates commercial accuracy and clarity.*

- **4.1 Commercial Truth (5 pts):** Fixed retainers, hourly rates, or milestones match approved commercial inputs to the cent.
- **4.2 Placeholder Handling (5 pts):** Placeholder tags clearly identified with no phantom dollar figures.
- **4.3 Schedule Transparency (5 pts):** Billing cadence, invoicing schedule, and software fee disclaimers explicitly stated.

### Dimension 5: Presentation & PDF Compilation (15 Points)
*Evaluates the visual quality, layout balance, and branding of the compiled PDF.*

- **5.1 Layout & Visual Hierarchy (5 pts):** 
  - Clean page breaks avoiding orphan headings (`keepWithNext=True`).
  - Balanced margins (0.5 in / 36 pt) and readable font sizes.
- **5.2 Corporate Branding & Palette (5 pts):**
  - Primary Navy (`#1A2E40`) for headings, Secondary Teal (`#008080`) for accents/dividers, Neutral Slate (`#2D3748`) for body.
  - Company metadata (name, tagline, website, email, phone) accurately rendered.
- **5.3 Running Headers, Footers & Signatures (5 pts):**
  - Dynamic two-pass page numbering ("Page X of Y").
  - Running header on continuation pages with hairline divider.
  - Formal side-by-side signature acceptance block on closing page.

### Dimension 6: Artifact Delivery & Manifest Integrity (15 Points)
*Evaluates storage organization and digital asset packaging.*

- **6.1 Artifact Generation (5 pts):** All 5 discrete files generated in `/data/proposals/{proposal_id}/`:
  - `proposal_plan.json`
  - `proposal_draft.json`
  - `rendered_proposal.json`
  - `proposal.pdf`
  - `manifest.json`
- **6.2 Checksum & Metadata Validation (5 pts):** `manifest.json` contains valid SHA256 checksums, byte sizes, and timestamps for each artifact.
- **6.3 API Download Readiness (5 pts):** PDF and manifest are downloadable via `/proposal/{id}/pdf` and `/proposal/{id}/manifest`.

---

## 4. Scorecard Evaluation Matrix

| Category | Max Score | Min Threshold | Actual Score | Status |
| :--- | :---: | :---: | :---: | :---: |
| **1. Scope Fidelity & Alignment** | 20 | 18 | `___` | `[PASS / FAIL]` |
| **2. Operational Depth & Specificity** | 20 | 18 | `___` | `[PASS / FAIL]` |
| **3. Style, Voice & Executive Precision** | 15 | 14 | `___` | `[PASS / FAIL]` |
| **4. Pricing Schedule Integrity** | 15 | 15 | `___` | `[PASS / FAIL]` |
| **5. Presentation & PDF Compilation** | 15 | 13 | `___` | `[PASS / FAIL]` |
| **6. Artifact Delivery & Manifest Integrity** | 15 | 15 | `___` | `[PASS / FAIL]` |
| **TOTAL SCORE** | **100** | **90** | `___` | `[OVERALL STATUS]`|

---

## 5. Decision Rules & Next Actions

| Total Score | Critical Gates | Classification | Workflow Action |
| :--- | :--- | :--- | :--- |
| **95 – 100** | ALL PASS | **Ready for Automatic Delivery** | n8n dispatches proposal.pdf to CRM and triggers client delivery webhook. |
| **90 – 94** | ALL PASS | **Ready with Minor Notes** | n8n creates human approval task with highlighted suggestions before dispatch. |
| **< 90** | ALL PASS | **Quality Warning** | Re-routed to ProposalWriter with automated feedback error loop for regeneration. |
| **ANY** | ANY FAIL | **CRITICAL REJECTION** | Automated pipeline termination. Error logged to `proposal_runs` table. |

---

## 6. n8n Pre-Flight Integration Checklist

Before triggering client notification or CRM attachment:
- [ ] Call `GET /proposal/{proposal_id}/artifacts` to confirm `all_artifacts_present == true`.
- [ ] Verify `artifact_count == 5`.
- [ ] Call `GET /proposal/{proposal_id}/manifest` to verify SHA256 non-empty strings.
- [ ] Verify PDF byte size is $> 1,000$ bytes (not an empty file).
- [ ] Ensure validation metadata in `proposal_draft.json` has `passed == true` and `len(errors) == 0`.
