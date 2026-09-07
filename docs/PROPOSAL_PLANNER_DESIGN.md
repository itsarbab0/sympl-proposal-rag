# Sympl Solutions Proposal RAG — Proposal Planner Layer Design Specification

**Status**: Verified & Active Baseline  
**Version**: 1.0  
**Date**: September 2026  
**Module**: `sympl_planner`  
**Database**: Dedicated Railway PostgreSQL with pgvector  
**Default Embedding Engine**: `BAAI/bge-m3` (1024-d Dense Vectors)  
**Verification Suite**: 10 Synthetic Scenarios + Database Invariant Check (`tests/test_proposal_planner.py` — 11/11 PASS)  

---

## 1. Executive Summary & Architectural Role

The **Proposal Planner Layer** (`sympl_planner`) is the deterministic structural orchestration engine of the Sympl Solutions Proposal RAG system. It serves as the strict firewall between uncurated raw client intake and downstream generative LLM prompts.

```
+---------------------+
|  Raw Client Intake  |
+----------+----------+
           |
           v
+---------------------------------------------------------------------------------+
|                              PROPOSAL PLANNER LAYER                             |
|                                                                                 |
|  1. Client Input Schema Validation                                              |
|     - Strict separation: requested_scope vs approved_scope                      |
|                                                                                 |
|  2. Archetype Precedence Priority System (Priorities 1 to 5)                    |
|     - Rule: PROPOSAL ARCHETYPE IS DERIVED FROM APPROVED CURRENT SCOPE.          |
|             ARCHETYPE NEVER ADDS SCOPE.                                         |
|                                                                                 |
|  3. Section Sequencing & Scope Firewall                                         |
|     - Ordered section layout tailored to archetype                              |
|     - Audit trail of excluded_sections with explicit reasons                    |
|                                                                                 |
|  4. Dynamic pgvector Exemplar Retrieval                                         |
|     - Service-Family Eligibility Version 2.0 candidate filtering                |
|     - Attaches 1-3 exemplars (Primary, Secondary, Optional Archetype)           |
|     - Rule: cleaned_text placed STRICTLY under retrieval_context.exemplars      |
|                                                                                 |
|  5. Canonical Why Us Reference Block Assembly                                   |
|     - Dynamic inclusion (not hardcoded by archetype)                            |
|     - Strict historical order & sector/identity variant resolution             |
|                                                                                 |
|  6. Commercial Terms & Pricing Placeholder Handling                             |
|     - Commercial categories appear ONLY from approved inputs                    |
|     - Structured [PRICING_PLACEHOLDER] tokens when fees pending                 |
|     - Condition-triggered disclaimers (Backlog, Software, HR boundary)          |
|                                                                                 |
|  7. Confidence Scoring & Quality Metadata                                       |
+---------------------------------------------------------------------------------+
           |
           v
   proposal_plan.json
           |
           v
+---------------------------------------------------------------------------------+
|                        LLM WRITER PROMPT / DRAFT ASSEMBLER                      |
|                       (Executes plan without inventing scope)                   |
+---------------------------------------------------------------------------------+
```

---

## 2. Core Architectural Principles

### 2.1 The Scope Precedence Invariant
> **PROPOSAL ARCHETYPE IS DERIVED FROM APPROVED CURRENT SCOPE. ARCHETYPE NEVER ADDS SCOPE.**

A proposal archetype controls **document structure, narrative density, and section organization**, but it can never introduce a service, deliverable, software tool, filing, or commercial liability. The planner first determines approved current services; only then does it route to the closest structural archetype.

### 2.2 Scope Separation Firewall (`requested_scope` vs `approved_scope`)
Intake documents, RFPs, and discovery notes often contain client wishes that Sympl leadership has not approved for inclusion. The Planner maintains strict architectural separation:
- `requested_scope`: What the client or prospect asked for.
- `approved_scope`: What Sympl leadership has explicitly authorized for this proposal.

Any service present in `requested_scope` that is absent from `approved_scope` is rejected by the scope firewall and logged into `excluded_sections` with reason `SCOPE_NOT_APPROVED_BY_LEADERSHIP` and added to `unapproved_requested_scope`.

### 2.3 Exemplar Role & Cleaned Text Isolation
- `retrieval_text` is queried against pgvector to evaluate semantic alignment.
- `cleaned_text` is attached as the high-fidelity historical style exemplar for LLM prompting.
- In `proposal_plan.json`, `cleaned_text` is stored **STRICTLY under `retrieval_context.exemplars`**, keeping the rest of the plan lightweight and architecturally clean.

---

## 3. Client Input Schema Specification

Defined in [`sympl_planner/schema.py`](file:///d:/Sympl/sympl-proposal-rag/sympl_planner/schema.py):

| Schema Component | Field | Type | Description |
| :--- | :--- | :--- | :--- |
| **`OrganizationInfo`** | `name` | `str` | Full legal/operating name of client |
| | `organization_type` | `str` | `nonprofit`, `charity`, `for_profit`, `social_enterprise`, `unspecified` |
| | `sector` | `str` | `community_services`, `social_services`, `arts_culture`, `health`, `literacy`, `other` |
| | `current_systems` | `List[str]` | Systems currently in use (e.g., `["QuickBooks Online", "Manual Timesheets"]`) |
| | `target_systems` | `List[str]` | Approved future systems (e.g., `["QuickBooks Online", "Wagepoint", "Dext"]`) |
| | `evaluation_systems`| `List[str]` | Tools under evaluation (distinguished from approved migrations) |
| **`EngagementContext`** | `engagement_type` | `str` | `recurring`, `interim`, `transformation`, `project`, `catchup` |
| | `complexity` | `str` | `standard`, `comprehensive`, `compact` |
| | `fixed_term_duration`| `Optional[str]` | E.g., `"6 months"`, `"12 months"` |
| | `diagnostic_focus` | `List[str]` | E.g., `["internal_controls", "audit_readiness", "workflow_efficiency"]` |
| **`ScopeContainer`** | `bookkeeping` | `BookkeepingScope` | Cadence (weekly/biweekly/monthly), AP/AR, reconciliations, expense tracking |
| | `payroll` | `PayrollScope` | Cadence, headcounts, parallel run, manager inputs, HR boundary |
| | `financial_reporting`| `ReportingScope` | Cadence, funder tracking, class/department tracking, board package |
| | `compliance` | `ComplianceScope` | GST/HST rebate/filing, T3010 charity return, audit support |
| | `digital_transformation`| `TransformationScope`| Software migrations, workflow redesign, integration milestones |
| | `training` | `TrainingScope` | Target roles, training format, SOP documentation |
| | `transition` | `TransitionScope` | Onboarding duration, historical access, legacy shadowing |
| **`ApprovedCommercialInputs`** | `pricing_model` | `str` | `fixed_retainer`, `hourly`, `phased_milestone`, `placeholder` |
| | `monthly_retainer` | `Optional[float]` | Approved monthly recurring retainer amount |
| | `setup_fee` | `Optional[float]` | Approved one-time onboarding/setup fee |
| | `hourly_rate` | `Optional[float]` | Approved out-of-scope hourly rate |
| | `currency` | `str` | Currency code (default: `"CAD"`) |
| | `include_backlog_exclusion` | `bool` | Triggers `REF_BLOCK_EXCLUSIONS_BACKLOG` |
| | `software_fees_excluded` | `bool` | Triggers `REF_BLOCK_EXCLUSIONS_SOFTWARE_NOT_INCLUDED` |
| **`Preferences`** | `include_why_us` | `Optional[bool]` | Explicit override (None = dynamic evaluation) |
| | `is_competitive_pitch`| `bool` | Triggers Why Us inclusion for competitive pitches/RFPs |
| | `is_trusted_continuity`| `bool` | May suppress Why Us for lean compact extensions |
| | `identity_credential_preference`| `Optional[str]` | `community_social`, `arts_leadership`, `none`, `auto` |

---

## 4. Archetype Precedence Priority System

When client scope satisfies multiple archetype conditions, the engine resolves routing deterministically via the **Archetype Precedence Priority System** implemented in [`sympl_planner/archetype.py`](file:///d:/Sympl/sympl-proposal-rag/sympl_planner/archetype.py):

| Precedence | Archetype Key | Base Weight | Mandatory Qualifying Criteria | Historical Exemplars |
| :---: | :--- | :---: | :--- | :--- |
| **Priority 1** | `ARCH_TRANSITION_INTERIM` | **100.0** | `engagement_type == "interim"` OR (`fixed_term_duration` set AND approved transition scope contains handover continuity/shadowing). | `YPT_2026` |
| **Priority 2** | `ARCH_AUDIT_OVERSIGHT_TRANSFORMATION` | **85.0** | `diagnostic_focus` contains `internal_controls` or `audit_readiness` AND approved scope contains audit support or catch-up reconciliations. | `PIRS_2025` |
| **Priority 3** | `ARCH_COMPREHENSIVE_TRANSFORMATION` | **70.0** | Approved digital transformation with migrations/redesign OR multi-workstream scope (3+ active service families) with comprehensive complexity. | `TACT_2026`, `GOODFOOT_2026` |
| **Priority 4** | `ARCH_STANDARD_NONPROFIT` | **55.0** | Nonprofit/charity organization AND (funder/grant tracking OR board reporting package OR standard complexity operational accounting). | `RPFF_2025` |
| **Priority 5** | `ARCH_COMPACT_BOOKKEEPING` | **40.0** | Base/fallback priority for direct operational schedules, focused general ledger/bookkeeping tasks without heavy diagnostic overlays. | `CAREOF_2025`, `CAHOOTS_2026` |

---

## 5. Section Sequencing & Scope Firewall

Implemented in [`sympl_planner/section_selector.py`](file:///d:/Sympl/sympl-proposal-rag/sympl_planner/section_selector.py):

### 5.1 Archetype Section Orderings

#### `ARCH_COMPACT_BOOKKEEPING`
1. `operational_schedule`: Direct schedule of weekly/biweekly/monthly bookkeeping tasks.
2. `payroll` *(if approved)*: Payroll administration & tax remittance.
3. `why_us` *(if dynamically selected)*: Credential blocks.
4. `pricing`: Investment schedule (approved retainer or placeholder).
5. `exclusions` *(if backlog or software exclusions active)*: Conditioned notes.

#### `ARCH_STANDARD_NONPROFIT`
1. `context_objectives`: Narrative organizational framing and engagement objectives.
2. `bookkeeping`: Full-cycle bookkeeping and general ledger maintenance.
3. `payroll` *(if approved)*: Payroll accounting, T4s, and ROEs.
4. `financial_reporting` *(if approved)*: Monthly board package and funder/grant reporting.
5. `compliance` *(if approved)*: GST/HST public service body rebate and T3010 charity return.
6. `why_us` *(if dynamically selected)*: Credential blocks.
7. `pricing`: Investment schedule.
8. `exclusions`: Conditioned terms and disclaimers.

#### `ARCH_TRANSITION_INTERIM`
1. `context_objectives`: Summary of Engagement (framing fixed-term horizon and continuity).
2. `transition`: Transition, Onboarding & Handover Plan (chronological milestones).
3. `bookkeeping`: Ongoing Operational Accounting.
4. `payroll` *(if approved)*: Payroll Management.
5. `why_us` *(if dynamically selected)*: Credential blocks.
6. `pricing`: Investment schedule.
7. `exclusions`: Conditioned notes.

#### `ARCH_COMPREHENSIVE_TRANSFORMATION`
1. `context_objectives`: Formal diagnostic Context & Objectives.
2. `digital_transformation`: Part A: Digital Financial Systems & Workflow Transformation.
3. `bookkeeping`: Part B: Ongoing Accounting & Bookkeeping Operations.
4. `training` *(if approved)*: Part C: Training, Process Documentation & Change Management.
5. `why_us` *(if dynamically selected)*: Credential blocks.
6. `pricing`: Investment schedule.
7. `exclusions`: Conditioned terms.

#### `ARCH_AUDIT_OVERSIGHT_TRANSFORMATION`
1. `context_objectives`: Context & Financial Diagnostic.
2. `financial_management`: Diagnostic Reconciliation & Cleanup Tasks (Objective, Scope, Timeline).
3. `compliance`: Audit Readiness & Oversight Support.
4. `why_us` *(if dynamically selected)*: Credential blocks.
5. `pricing`: Investment schedule.
6. `exclusions`: Conditioned notes.

### 5.2 `excluded_sections` Taxonomy
The planner automatically populates `excluded_sections` with explicit categorization:
- `SCOPE_NOT_APPROVED_BY_LEADERSHIP`: Requested in raw intake, but rejected by Sympl leadership.
- `NOT_IN_APPROVED_SCOPE`: Standard service family outside approved engagement boundaries.
- `EXCLUDED_BY_PLANNER_DECISION`: Why Us or secondary modules omitted based on contextual evaluation.

---

## 6. Dynamic pgvector Exemplar Retrieval (1–3 Exemplars)

Implemented in [`sympl_planner/retrieval.py`](file:///d:/Sympl/sympl-proposal-rag/sympl_planner/retrieval.py):

For every service section requiring exemplar guidance, the retriever:
1. Formulates a rich semantic query incorporating organization type, sector, active service modules, systems, and cadence.
2. Applies **Service-Family Eligibility Version 2.0** hard candidate pool resolution.
3. Queries PostgreSQL pgvector using cosine distance (`<=>` operator):
   ```sql
   SELECT 
       pc.chunk_key,
       pd.proposal_code,
       pc.section_type,
       1 - (pc.embedding <=> %s::vector) AS cosine_similarity
   FROM proposal_chunks pc
   JOIN proposal_documents pd ON pc.proposal_id = pd.id
   WHERE pc.chunk_key = ANY(%s) AND pc.embedding IS NOT NULL
   ORDER BY pc.embedding <=> %s::vector ASC
   LIMIT 5;
   ```
4. Attaches **1 to 3 exemplars**:
   - `primary`: Top-ranked candidate chunk matching section intent.
   - `secondary`: Runner-up candidate chunk within service family.
   - `optional_archetype`: A candidate chunk originating from the target archetype proposal, or third top-ranked chunk.
5. **Strict Cleaned Text Isolation**: `cleaned_text` is placed **strictly inside `retrieval_context.exemplars`** and nowhere else.

---

## 7. Dynamic Why Us Reference Block Assembly

Implemented in [`sympl_planner/why_us.py`](file:///d:/Sympl/sympl-proposal-rag/sympl_planner/why_us.py):

### 7.1 Inclusion Decision Logic
Why Us inclusion is **not hardcoded by archetype**:
- Explicit intake override (`preferences.include_why_us`) takes top priority.
- Competitive pitch / RFP (`preferences.is_competitive_pitch == True`) -> **Include**.
- Trusted continuity on compact scope (`preferences.is_trusted_continuity == True`) -> **Omit**.
- Multi-stakeholder archetypes (`ARCH_COMPREHENSIVE_TRANSFORMATION`, `ARCH_STANDARD_NONPROFIT`) -> **Include** by soft tendency.
- Lean compact schedule (`ARCH_COMPACT_BOOKKEEPING`) -> **Omit** unless nonprofit client or competitive pitch.

### 7.2 Canonical Assembly Order
When Why Us is included, reference blocks are compiled in strict historical order:
1. `REF_BLOCK_WHY_US_OPENING` (`intro`)
2. `REF_BLOCK_WHY_US_CREDENTIAL_RESPONSIVE_TEAM` (`bullet`)
3. Expertise variant:
   - If registered charity: `REF_BLOCK_WHY_US_EXP_CHARITY` (`bullet`)
   - If nonprofit: `REF_BLOCK_WHY_US_EXP_NONPROFIT` (`bullet`)
   - If commercial/for-profit: *Omitted*
4. `REF_BLOCK_WHY_US_CREDENTIAL_TECH_INTEGRATION` (`bullet`)
5. Sector & identity variant:
   - Community / Social Services: `REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL` (`bullet`)
   - Arts & Culture: `REF_BLOCK_WHY_US_SECTOR_ARTS_LEADERSHIP` (`bullet`) (+ `REF_BLOCK_WHY_US_SECTOR_ARTS_EXP_RPFF` if national scope)
   - Commercial / Other: *Omitted*
6. `REF_BLOCK_WHY_US_CLOSING_1` (`paragraph`)
7. `REF_BLOCK_WHY_US_CLOSING_2` (`paragraph`)

---

## 8. Pricing Categories & Placeholder Handling

Implemented in [`sympl_planner/pricing.py`](file:///d:/Sympl/sympl-proposal-rag/sympl_planner/pricing.py):

### 8.1 Gate A Pricing Firewall
- **Rule**: Pricing categories must ONLY appear from approved commercial inputs.
- Unapproved categories (e.g. unsolicited hourly rates, audit fees) are **never** invented.
- If amounts are confirmed: emitted as numeric values with approved billing frequency.
- If amounts are pending: emitted as explicit structured placeholders:
  - `[PRICING_PLACEHOLDER: Monthly Retainer Fee (CAD)]`
  - `[PRICING_PLACEHOLDER: One-Time Onboarding & System Setup Fee (CAD)]`
  - `[PRICING_PLACEHOLDER: Hourly Out-of-Scope Advisory Rate (CAD)]`

### 8.2 Conditional Disclaimer Attachments
- **`REF_BLOCK_EXCLUSIONS_BACKLOG`**: Attached when `commercial_terms.include_backlog_exclusion == True`.
- **`REF_BLOCK_EXCLUSIONS_SOFTWARE_NOT_INCLUDED`**: Attached when `commercial_terms.software_fees_excluded == True`.
- **`REF_BLOCK_PAYROLL_HR_BOUNDARY`**: Attached when `approved_scope.payroll` is active with Sympl processing, manager input responsibility, and HR exclusion.

---

## 9. Confidence Metadata & Quality Flags

Calculated in [`sympl_planner/engine.py`](file:///d:/Sympl/sympl-proposal-rag/sympl_planner/engine.py):

$$\text{Overall Confidence} = 0.40 \times \text{Archetype Conf} + 0.35 \times \text{Scope Alignment} + 0.25 \times \text{Avg Retrieval Conf}$$

- `archetype_confidence`: Proportional margin of archetype score over baseline.
- `scope_alignment_score`: Penalized if `requested_scope` contained items rejected by leadership.
- `retrieval_confidence`: Mean cosine similarity of attached primary exemplars.
- `flags`: List of operational notices (`UNAPPROVED_REQUESTED_ITEMS_PRESENT`, `PRICING_PLACEHOLDERS_ACTIVE`, `CONDITIONAL_DISCLAIMERS_ACTIVE`, `WHY_US_INCLUDED/OMITTED: rationale`).

---

## 10. Synthetic Scenario Verification Results

The test suite in [`tests/test_proposal_planner.py`](file:///d:/Sympl/sympl-proposal-rag/tests/test_proposal_planner.py) evaluates 10 synthetic scenarios plus database invariant verification:

| Scenario | Client Profile | Target Archetype | Key Verification Focus | Test Result |
| :---: | :--- | :--- | :--- | :---: |
| **1** | Meadowvale Community Hub | `ARCH_COMPACT_BOOKKEEPING` | Unapproved requested payroll rejected to `excluded_sections`; backlog disclaimer; placeholder retainer. | **PASS** |
| **2** | St. Jude Literacy Foundation | `ARCH_COMPACT_BOOKKEEPING` | Registered charity; approved fees ($1,850/mo, $500 setup); `REF_BLOCK_WHY_US_EXP_CHARITY`. | **PASS** |
| **3** | Toronto Community Care Society | `ARCH_STANDARD_NONPROFIT` | Recurring accounting + payroll + reporting + compliance; software disclaimer + HR boundary. | **PASS** |
| **4** | Canadian Contemporary Arts Guild | `ARCH_STANDARD_NONPROFIT` | Arts charity with national scope; `ARTS_LEADERSHIP` + `ARTS_EXP_RPFF` credentials. | **PASS** |
| **5** | Eastside Youth Alliance | `ARCH_TRANSITION_INTERIM` | Interim 6-month horizon; Summary of Engagement + Transition Onboarding milestones. | **PASS** |
| **6** | Metro Health Alliance | `ARCH_COMPREHENSIVE_TRANSFORMATION` | Sage to QBO + Dext migration; Part A Transformation + Part C Training. | **PASS** |
| **7** | Community Housing Collective | `ARCH_COMPREHENSIVE_TRANSFORMATION` | Multi-workstream; 1-3 exemplars attached per section with primary/secondary roles. | **PASS** |
| **8** | Ontario Immigrant Support Services | `ARCH_AUDIT_OVERSIGHT_TRANSFORMATION` | Internal controls & audit readiness; diagnostic reconciliation tasks. | **PASS** |
| **9** | EcoTech Innovations Inc. | Commercial (`for_profit`) | USD currency; suppression of nonprofit/charity credentials from Why Us. | **PASS** |
| **10** | Acme Org (Minimal Intake) | `ARCH_COMPACT_BOOKKEEPING` | Graceful execution on minimal intake; safe fallback placeholders. | **PASS** |
| **11** | Frozen DB Invariant Audit | All Tables | Verified: 0 database writes, 0 embedding mutations, all row counts intact. | **PASS** |

**Execution**: `Ran 11 tests in 49.723s — OK`.
