# Sympl Solutions: Runtime Style Asset & Architecture Design Specification

> **Status:** Hardened Runtime Design Specification for Human Review  
> **Corpus Base:** 7 Verified Historical Proposals (71 Chunks in Railway PostgreSQL)  
> **Schema Reference:** `db/migrations/001_initial_schema.sql` (Verified against live Railway PostgreSQL)  
> **Style Discovery Reference:** `docs/SYMPL_STYLE_DISCOVERY.md`  
> **Purpose:** Formally specify how approved Sympl style rules, reference blocks, few-shot exemplars, safety boundaries, prompt assembly, and evaluator gates operate at runtime.

---

## 1. Actual Database Schema Inspection

Inspection of the active Railway PostgreSQL database and `db/migrations/001_initial_schema.sql` confirms the following physical table schemas:

### A. `sympl_style_rules`
| Column Name | Data Type | Nullable | Default | Constraints & Indexes |
| :--- | :--- | :---: | :---: | :--- |
| `id` | `uuid` | NO | `gen_random_uuid()` | PRIMARY KEY (`sympl_style_rules_pkey`), btree index |
| `rule_key` | `text` | NO | None | UNIQUE (`sympl_style_rules_rule_key_key`), btree index, NOT NULL |
| `category` | `text` | NO | None | NOT NULL |
| `rule_text` | `text` | NO | None | NOT NULL |
| `priority` | `text` | NO | None | NOT NULL |
| `active` | `boolean` | NO | `true` | NOT NULL |
| `metadata` | `jsonb` | NO | `'{}'::jsonb` | NOT NULL |
| `created_at`| `timestamptz` | NO | `now()` | NOT NULL |
| `updated_at`| `timestamptz` | NO | `now()` | NOT NULL, trigger `trg_sympl_style_rules_updated_at` |

### B. `sympl_reference_blocks`
| Column Name | Data Type | Nullable | Default | Constraints & Indexes |
| :--- | :--- | :---: | :---: | :--- |
| `id` | `uuid` | NO | `gen_random_uuid()` | PRIMARY KEY (`sympl_reference_blocks_pkey`), btree index |
| `block_key` | `text` | NO | None | UNIQUE (`sympl_reference_blocks_block_key_key`), btree index, NOT NULL |
| `block_type` | `text` | NO | None | NOT NULL |
| `name` | `text` | NO | None | NOT NULL |
| `content` | `text` | NO | None | NOT NULL |
| `approved` | `boolean` | NO | `false` | NOT NULL |
| `version` | `integer` | NO | `1` | NOT NULL, CHECK (`version >= 1`) |
| `metadata` | `jsonb` | NO | `'{}'::jsonb` | NOT NULL |
| `created_at`| `timestamptz` | NO | `now()` | NOT NULL |
| `updated_at`| `timestamptz` | NO | `now()` | NOT NULL, trigger `trg_sympl_reference_blocks_updated_at` |

### C. Relevant `proposal_chunks` Columns
- `chunk_key` (`text`, UNIQUE, NOT NULL)
- `proposal_id` (`uuid`, FK to `proposal_documents.id`)
- `section_order` (`integer`)
- `section_type` (`text`, NOT NULL)
- `section_title` (`text`)
- `service_modules` (`text[]`, NOT NULL, GIN indexed)
- `organization_type` (`text`, btree indexed)
- `sector` (`text`, btree indexed)
- `engagement_type` (`text`, btree indexed)
- `core_bookkeeping` (`boolean`, NOT NULL)
- `accounting_systems` (`text[]`, NOT NULL, GIN indexed)
- `payroll_systems` (`text[]`, NOT NULL, GIN indexed)
- `cadence` (`text[]`, NOT NULL, GIN indexed)
- `special_requirements` (`text[]`, NOT NULL, GIN indexed)
- `cleaned_text` (`text`, NOT NULL) — **Authoritative source of writing exemplars**
- `retrieval_text` (`text`, NOT NULL) — **Authoritative source of vector search**
- `raw_text` (`text`, NOT NULL) — **Historical audit evidence**
- `retrieval_enabled` (`boolean`, NOT NULL, btree indexed)
- `commercial_reference_only` (`boolean`, NOT NULL)
- `pricing_content` (`boolean`, NOT NULL, enforced by `chk_pricing_safety`)
- `boilerplate_content` (`boolean`, NOT NULL, enforced by `chk_boilerplate_retrieval`)
- `metadata` (`jsonb`, NOT NULL, GIN indexed)

---

## 2. Schema Capability & Gap Analysis

### `STYLE_RULE_SCHEMA_SUFFICIENT: YES`
- **Supported Concepts:**
  - `rule_key` maps to first-class column `rule_key` (`text`, UNIQUE).
  - `category` maps to first-class column `category` (`text`).
  - `instruction` maps to first-class column `rule_text` (`text`).
  - `priority` maps to first-class column `priority` (`text`).  
    *Canonical Convention:* Stored as `'P1'` (highest / critical), `'P2'` (medium / strong), and `'P3'` (lower / soft). Runtime loads deterministically using `ORDER BY priority ASC, rule_key ASC`.
  - `enabled status` maps to first-class column `active` (`boolean`).
  - `metadata` (`jsonb`) cleanly supports all nested dimensions without migration:
    - `applies_to`: strictly standardized enum `['global', 'section', 'archetype']`.
    - `target_scope`: specific text target (e.g. `'service_bullets'`, `'all_prose'`, `'why_us'`, `'pricing'`).
    - `strength`: standardized enum `['HARD', 'STRONG', 'SOFT']`.
    - `section_family`: target section family for section rules (e.g. `'bookkeeping'`, `'payroll'`).
    - `archetype_key`: target archetype key for archetype rules.
    - `evidence`: measurement methodology and corpus citations.
- **Missing Concepts:** NONE.

### `REFERENCE_BLOCK_SCHEMA_SUFFICIENT: YES`
- **Supported Concepts:**
  - `block_key` maps to first-class column `block_key` (`text`, UNIQUE).
  - `block_type` maps to first-class column `block_type` (`text`).
  - `name` maps to first-class column `name` (`text`).
  - `content` maps to first-class column `content` (`text`).
  - `approved` maps to first-class column `approved` (`boolean`).
  - `version` maps to first-class column `version` (`integer`).
  - `metadata` (`jsonb`) cleanly supports:
    - `classification`: standardized enum `['DETERMINISTIC', 'VARIANT', 'CONDITIONAL']`.
    - `source_mode`: standardized enum `['EXACT_SOURCE_BLOCK', 'COMPOSED_RUNTIME_TEXT']`. All 13 proposed rows are strictly `EXACT_SOURCE_BLOCK`.
    - `render_as`: presentation enum `['intro', 'paragraph', 'bullet', 'note']`.
    - `selection_condition`: explicit trigger logic based strictly on current client intake.
    - `fallback_behavior`: explicit fallback if condition is unmet.
    - `source_proposals`: historical lineage references.
    - `source_chunk_keys`: historical chunk keys confirming contiguous, byte-level source fidelity across 100% of listed sources.
- **Missing Concepts:** NONE.

### `RUNTIME_STYLE_SCHEMA_STATUS: READY_AS_IS`
The existing database schema supports the entire runtime design without migrations or schema modifications.

---

## 3. Runtime Asset Storage & Boundary Matrix

| Asset Type | Runtime Storage Location | Implementation Rationale |
| :--- | :--- | :--- |
| **Global Style Rules** | `sympl_style_rules` | Prose style instructions (`metadata.applies_to = 'global'`) loaded across all sections. |
| **Section Style Rules** | `sympl_style_rules` | Specific formatting/rhythm rules (`metadata.applies_to = 'section'`) filtered by `section_family`. |
| **Archetype Style Rules** | `sympl_style_rules` | Structural and density conventions (`metadata.applies_to = 'archetype'`) filtered by `archetype_key`. |
| **Fact / Scope Safety Rules** | System Prompt & Evaluator Gate A | Hard system guardrails preventing hallucinations; not stylistic prose guidelines. |
| **Stable Reference Blocks** | `sympl_reference_blocks` | Invariant house copy (e.g. Why Us Opening & Closings) deployed when section is planned. |
| **Conditional Reference Blocks**| `sympl_reference_blocks` | Approved clauses (Backlog, Software, HR) injected only when client intake scope mandates. |
| **Historical Cleaned Exemplars**| `proposal_chunks.cleaned_text` | Retrieved dynamically by verified `chunk_key`. Never duplicated into reference blocks or design files. |
| **Historical Pricing** | `proposal_chunks` (Isolated) | Never surfaced in writer prompts; query-isolated via `pricing_content = true, retrieval_enabled = false`. |
| **Current Approved Pricing** | Human-Controlled Intake Input | Sourced exclusively from user/pricing workflow; never derived from historical RAG. |

---

## 4. Proposed Global Style Rule Manifest (6 Rules)

| rule_key | category | priority | instruction (rule_text) | strength | applies_to | target_scope | evidence |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| `RULE_GLOBAL_DIRECT_VERB_LEADS` | `syntax` | `P1` | Begin service scope bullets with an active, direct present-tense verb (e.g., Manage, Prepare, Process, Reconcile, Maintain, Record, Ensure). Avoid passive voice and introductory filler like 'Sympl will' or 'Our team will'. | `STRONG` | `global` | `service_bullets` | Analyzed across 282 service scope bullets in historical corpus: ~78.4% begin with an imperative/direct action verb. |
| `RULE_GLOBAL_NO_TRAILING_PERIODS` | `punctuation` | `P2` | Do not end standard service scope task bullets with a trailing period. Reserve terminal periods for multi-sentence descriptions or closing prose paragraphs. | `STRONG` | `global` | `service_bullets` | 95.7% (332 / 347) of all service bullets across 7 proposals omit trailing periods. |
| `RULE_GLOBAL_CONCISE_BULLETS` | `length` | `P2` | Keep service task bullets concise and operationally focused, targeting between 6 and 15 words (corpus mean ~9.4 words, median ~9.0 words). Avoid multi-sentence narrative task descriptions. | `STRONG` | `global` | `service_bullets` | Corpus service bullet word length: mean 9.4 words, median 9.0 words, 25th-75th percentile range 6–14 words. |
| `RULE_GLOBAL_LOW_HYPE_TONE` | `tone` | `P1` | Maintain a grounded, understated Canadian professional services tone. Strictly avoid generic corporate consulting buzzwords and promotional marketing prose (e.g., 'leverage cutting-edge solutions', 'unlock value', 'strategic synergies', 'game-changing', 'holistic ecosystem', 'bespoke transformation journey', 'delve', 'pivotal'). Legitimate operational terms found in the Sympl corpus (such as 'streamline', 'streamlined', and 'seamless') are permitted in concrete workflow contexts. | `HARD` | `global` | `all_prose` | Zero occurrences of generic marketing buzzwords; Sympl establishes credibility through concrete operational tasks. |
| `RULE_GLOBAL_NATURAL_VERB_REPETITION` | `lexical` | `P2` | Permit natural repetition of common operational verbs (such as Manage, Process, Prepare, Maintain, Reconcile) across adjacent task bullets. Do not force artificial synonym variation (e.g. orchestrate, spearhead, drive) to avoid repetition. | `STRONG` | `global` | `service_bullets` | Common operational verbs repeat naturally across bullets in TACT, PIRS, RPFF, and Good Foot. |
| `RULE_GLOBAL_CLIENT_SPECIFIC_INTEGRATION`| `client_adaptation` | `P2` | Integrate approved client-specific operational details (such as named software platforms, approved pay frequencies, and specific account targets) directly into service bullets and headings rather than siloing them in abstract background descriptions. | `STRONG` | `global` | `service_bullets` | Consistently observed across all 7 proposals (e.g. specific banking platforms, tools, and cadences embedded in task bullets). |

---

## 5. Proposed Section Style Rule Manifest (10 Rules)

*Crucial Architecture Principle:* These rules govern **HOW** to express approved scope in authentic Sympl style. They **NEVER** dictate **WHAT** services exist or force unrequested statutory deliverables.

| rule_key | section_family | priority | instruction (rule_text) | strength | current-client-dependent content |
| :--- | :--- | :---: | :--- | :---: | :--- |
| `RULE_SEC_BOOKKEEPING_WORKFLOW` | `bookkeeping` | `P2` | Organize approved bookkeeping tasks into clear operational categories. Use direct action bullets. When reconciliations are in scope, name the account/reconciliation target and cadence when known. When AP/AR or approval workflows are included, preserve current responsibility boundaries. Do NOT force services absent from current scope. | `STRONG` | Reconciliation targets, approval roles, accounting platform, and transaction cadence. |
| `RULE_SEC_PAYROLL_STRUCTURE` | `payroll` | `P2` | Present approved payroll responsibilities in a logical operational sequence. State cadence and staff coverage when known. Group current processing, remittance/compliance, reconciliation, year-end filings, systems, and responsibility boundaries only when those items are actually part of current scope. Historical payroll examples must NEVER add a statutory filing or compliance task not present in current requirements. | `STRONG` | Headcount, pay frequency (bi-weekly/semi-monthly), software platform, and specific statutory forms. |
| `RULE_SEC_REPORTING_GOVERNANCE` | `financial_reporting` | `P2` | Present current approved reports as clearly named deliverables, normally grouped by audience/cadence where useful. State delivery frequency when known. Distinguish management, board, funder, and program reporting only where current requirements include them. Do NOT force a standard reporting package (Balance Sheet, P&L, Cash Flow, Aging) unless present in client scope. | `STRONG` | Reporting recipients, meeting schedules, and required report formats. |
| `RULE_SEC_COMPLIANCE_DELINEATION` | `compliance` | `P2` | Name the specific approved statutory/compliance responsibility directly, including cadence and responsible party when known. Avoid vague compliance guarantees. Preserve exact current filing and external-party boundaries. Do NOT assume auditor files T3010, CPA files tax return, PSB rebate applies, or HST applies unless established by current client facts. | `STRONG` | Tax jurisdiction, filing schedules, charity status, and external CPA/auditor filing divisions. |
| `RULE_SEC_AUDIT_LIAISON_FRAMEWORK` | `audit` | `P2` | Describe approved audit-preparation/support tasks operationally and preserve a clear distinction between Sympl support and the external audit itself. Include PBC items, schedules, query-response commitments, meetings, or cleanup methodology only when explicitly scoped. Do NOT universally force PBC lists or response SLAs. | `STRONG` | Audit firm name, fiscal year-end, specific PBC deliverables, and turnaround commitments. |
| `RULE_SEC_TRANSFORMATION_MODULARITY`| `digital_transformation`| `P2` | Structure transformation work around the current project's actual modules — which may be discrete software initiatives, assessment/strategy, implementation, workflow redesign, migration, integration, or training. Use concrete operational tasks and approved systems; avoid abstract transformation language. Do NOT force a rigid 4-stage lifecycle unless scoped. | `STRONG` | Specific software tools, implementation milestones, and migration objectives. |
| `RULE_SEC_TRAINING_SUPPORT` | `training` | `P3` | Present approved training/change-management work as concrete deliverables and audiences. State training format, documentation, handoff, and post-go-live support only when they are part of current scope. Do NOT force SOPs, quick guides, or multi-month support unless approved. | `SOFT` | Target staff roles, training format, documentation scope, and post-go-live duration. |
| `RULE_SEC_TRANSITION_CONTINUITY` | `transition` | `P2` | Frame transition engagements around continuity and handoff. Organize approved transition tasks chronologically when useful, while preserving existing systems/processes only where current client scope requires continuity. Do NOT force legacy tool retention or shadowing unless scoped. | `STRONG` | Handover cutoff dates, legacy systems, and onboarding milestones. |
| `RULE_SEC_WHY_US_STRUCTURE` | `why_us` | `P2` | Structure Why Us as: (1) invariant opening declaration ('Sympl Solutions is committed...'), (2) bulleted base credentials with optional sector-adapted lived experience variant, and (3) concluding standalone commitment paragraphs emphasizing partnership, transparency, and flexibility. | `STRONG` | Sector/identity match (nonprofit, charity, community arts, social services). |
| `RULE_SEC_PRICING_FORMATTING` | `pricing` | `P1` | Present ONLY approved pricing categories. When multiple fee types exist, separate them clearly with concise labels and place relevant conditions adjacent to the corresponding fee. Never invent amounts, fee categories, tax treatment, or exclusions. | `HARD` | Human-approved pricing schedule, currency, and commercial terms. |

---

## 6. Proposed Archetype Style Rule Manifest (5 Archetypes)

Archetype style rules control **document structure, narrative depth, and detail density**, NOT mandatory service scope.

### Crucial Precedence Rule:
**PROPOSAL ARCHETYPE IS DERIVED FROM APPROVED CURRENT SCOPE. ARCHETYPE NEVER ADDS SCOPE.**  
The planner first determines approved current services and responsibility boundaries. It then selects the closest structural archetype. Archetype rules may only alter section organization, narrative density, and document structure; they cannot introduce a service, deliverable, system, filing, or commercial commitment.

| archetype_key | historical_exemplars | Structural Tendencies | Historical Services NOT Forced | Scope Creation Allowed |
| :--- | :--- | :--- | :--- | :---: |
| `ARCH_COMPACT_BOOKKEEPING` | `CAREOF_2025`, `CAHOOTS_2026` | Direct operational schedule (Weekly/Biweekly); minimal diagnostic prose; compact section count; short service blocks; high conciseness; Why Us omitted as a soft tendency (planner may still include it). | Does NOT force payroll, compliance, sales tax, software pass-through, or backlog exclusions unless current scope requires them. | **NO** |
| `ARCH_STANDARD_NONPROFIT` | `RPFF_2025` | Moderate-detail operational structure; service categories adapted to organization requirements; governance and funder detail included only when present in approved scope; Why Us commonly included; clear grouping of recurring operational services. | Does NOT force bookkeeping, grants, board reporting, compliance, audit, payroll, or transformation unless current scope contains them. | **NO** |
| `ARCH_TRANSITION_INTERIM` | `YPT_2026` | Narrative `Summary of Engagement` framing fixed-term horizon and continuity priorities when known; chronological milestones. | Does NOT force catch-up, handover, shadowing, legacy systems, or folder preservation unless current scope contains them. | **NO** |
| `ARCH_COMPREHENSIVE_TRANSFORMATION`| `TACT_2026`, `GOODFOOT_2026` | Formal diagnostic `CONTEXT & OBJECTIVES` opening; higher detail density; modular service sections; multiple distinct workstreams when current scope contains them; fuller closing and Why Us tendency. | Does NOT force digital transformation, financial management, audit, training, Part A/B/C lettering, or multiple initiatives unless scoped. | **NO** |
| `ARCH_AUDIT_OVERSIGHT_TRANSFORMATION`| `PIRS_2025` | Diagnostic framing around internal controls and audit readiness; granular reconciliation tasks (Objective, Scope, Timeline). Archetype is selected only when current planner has already established those scope families. | Does NOT force full outsourced transaction entry mechanics, 4-week access commitments, or create audit/transformation scope. | **NO** |

---

## 7. Fact / Scope Safety Contract (Gate A)

These non-negotiable guardrails are evaluated in the System Prompt, Generation Contract, and Evaluator Gate A. Violations trigger **immediate draft rejection**:

| safety_rule_key | rule description | enforcement_location | failure_behavior |
| :--- | :--- | :---: | :--- |
| `SAFE_NO_INVENTED_CLIENT_FACTS` | Never invent client headcounts, revenue, software tools, or dates not provided in current intake. | Gate A & System Prompt | Immediate Draft Rejection (`REJECT_INVENTED_FACTS`) |
| `SAFE_NO_HISTORICAL_FACT_LEAKAGE`| Never copy historical client names, dates, or dollar amounts from few-shot examples into new proposals. | Gate A & System Prompt | Immediate Draft Rejection (`REJECT_HISTORICAL_LEAK`) |
| `SAFE_NO_HISTORICAL_SCOPE_LEAKAGE`| Every generated service, deliverable, statutory form, or compliance task must map directly to a current approved scope item. Historical exemplars must NEVER introduce unrequested services or compliance duties. | Gate A & Evaluator | Immediate Draft Rejection (`REJECT_SCOPE_LEAKAGE`) |
| `SAFE_NO_INVENTED_PRICING` | Never invent retainer amounts, setup fees, or hourly rates; pricing must come strictly from approved commercial input. | Gate A & Input Contract| Immediate Draft Rejection (`REJECT_UNAUTHORIZED_PRICING`) |
| `SAFE_NO_HISTORICAL_PRICING_COPY`| Never copy fee amounts, retainer structures, or billing terms from historical proposals. | Gate A & Evaluator | Immediate Draft Rejection (`REJECT_HISTORICAL_PRICING`) |
| `SAFE_NO_INVENTED_BANK_AUTHORITY`| Never grant Sympl bank wire release, cheque signing, or banking authority unless explicitly in client scope. | Gate A & Evaluator | Immediate Draft Rejection (`REJECT_UNAUTHORIZED_AUTHORITY`) |
| `SAFE_PRESERVE_SYSTEM_STATES` | Preserve exact distinction between current client software, proposed migrations, and options under evaluation. | Gate A & System Prompt | Immediate Draft Rejection (`REJECT_SYSTEM_AMBIGUITY`) |
| `SAFE_NO_AUTOMATIC_SLA_REUSE` | Audit turnaround commitments (e.g. 1-2 business days) must come from current client scope, never reused automatically. | Gate A & System Prompt | Immediate Draft Rejection (`REJECT_UNAUTHORIZED_SLA`) |
| `SAFE_COMMERCIAL_TERMS_SOURCE_ONLY`| Backlog exclusions and software pass-through terms must be explicitly approved in commercial intake. | Gate A & Input Contract| Immediate Draft Rejection (`REJECT_UNAPPROVED_TERMS`) |
| `SAFE_CLIENT_FACTS_OVERRIDE_RAG` | Current client input and approved scope strictly supersede any pattern, phrasing, or convention in historical exemplars. | Runtime Prompt Assembly | Enforced at prompt assembly |

---

## 8. Reference Block Design

### Reference Block Atomicity Rule
For all rows marked `EXACT_SOURCE_BLOCK`, every stored reference block must contain text that appears as an exact, contiguous substring in each of its listed historical cleaned_text sources.

For bullet content, the visual bullet glyph or Markdown prefix (`-`, `•`, etc.) is presentation metadata (`render_as = "bullet"`) and is **NOT** stored in `content`. This guarantees:
- 100% byte-level contiguous substring matches across historical proposals regardless of source bullet glyphs (`•` vs `-`).
- Strict separation of source wording from visual layout rendering (Canva / Markdown / Web renderer).

A reference block may **NOT** be constructed by joining non-adjacent bullets, stitching text from disparate proposals, removing internal words with ellipses, or altering punctuation. If multi-sentence synthesis is needed at generation time, the runtime generates `COMPOSED_RUNTIME_TEXT` from current client facts.

Reference blocks must **NEVER** be selected via vector similarity or nearest-neighbor RAG; selection is strictly deterministic or condition-triggered.

### A. Why Us Sub-Blocks (Exact Source-Backed Text & Canonical Assembly Order)

When Why Us is included, the section is assembled strictly in canonical historical order:
1. `REF_BLOCK_WHY_US_OPENING` (`render_as = "intro"`)
2. `REF_BLOCK_WHY_US_CREDENTIAL_RESPONSIVE_TEAM` (`render_as = "bullet"`)
3. ONE expertise variant if explicitly supported: `REF_BLOCK_WHY_US_EXP_NONPROFIT` OR `REF_BLOCK_WHY_US_EXP_CHARITY` (`render_as = "bullet"`)
4. `REF_BLOCK_WHY_US_CREDENTIAL_TECH_INTEGRATION` (`render_as = "bullet"`)
5. At most the appropriate approved sector/identity variants: `REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL` OR `REF_BLOCK_WHY_US_SECTOR_ARTS_LEADERSHIP` (+ optionally `REF_BLOCK_WHY_US_SECTOR_ARTS_EXP_RPFF`) (`render_as = "bullet"`)
6. `REF_BLOCK_WHY_US_CLOSING_1` (`render_as = "paragraph"`)
7. `REF_BLOCK_WHY_US_CLOSING_2` (`render_as = "paragraph"`)

The document assembler renders bullet glyphs around blocks where `render_as = "bullet"`.

| block_key | classification | exact_source_backed_content | render_as | selection_condition | source_proposals | source_chunk_keys |
| :--- | :---: | :--- | :---: | :---: | :--- | :--- |
| `REF_BLOCK_WHY_US_OPENING` | `DETERMINISTIC` | `Sympl Solutions is committed to ensuring a high standard of financial clarity and timely support. We bring:` | `intro` | Planner includes Why Us section | `["RPFF_2025", "YPT_2026", "GOODFOOT_2026", "TACT_2026", "PIRS_2025"]` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US`, `GOODFOOT_2026_WHY_US`, `TACT_2026_WHY_US`, `PIRS_2025_WHY_US` |
| `REF_BLOCK_WHY_US_CREDENTIAL_RESPONSIVE_TEAM` | `DETERMINISTIC` | `A responsive, detail-oriented team` | `bullet` | Planner includes Why Us section | `["RPFF_2025", "YPT_2026", "GOODFOOT_2026", "TACT_2026", "PIRS_2025"]` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US`, `GOODFOOT_2026_WHY_US`, `TACT_2026_WHY_US`, `PIRS_2025_WHY_US` |
| `REF_BLOCK_WHY_US_EXP_NONPROFIT` | `VARIANT` | `Decade-long expertise in nonprofit finance` | `bullet` | Client `organization_type` explicitly supports non-profit (default for non-profits; never inferred from name or funders) | `["RPFF_2025", "YPT_2026", "GOODFOOT_2026", "PIRS_2025"]` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US`, `GOODFOOT_2026_WHY_US`, `PIRS_2025_WHY_US` |
| `REF_BLOCK_WHY_US_EXP_CHARITY` | `VARIANT` | `Decade-long expertise in nonprofit and charity finance` | `bullet` | Client `organization_type` explicitly supports registered charity (TACT variant; never inferred) | `["TACT_2026"]` | `TACT_2026_WHY_US` |
| `REF_BLOCK_WHY_US_CREDENTIAL_TECH_INTEGRATION` | `DETERMINISTIC` | `Streamlined tech integration and clear process flows` | `bullet` | Planner includes Why Us section | `["RPFF_2025", "YPT_2026", "GOODFOOT_2026", "TACT_2026", "PIRS_2025"]` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US`, `GOODFOOT_2026_WHY_US`, `TACT_2026_WHY_US`, `PIRS_2025_WHY_US` |
| `REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL` | `VARIANT` | `BIPOC and immigrant-led leadership with lived experiences in community, social service and arts & culture` | `bullet` | Current client sector is explicitly established as `social_services`, `community_services`, `community_organization`, or another approved community category AND planner selects this identity credential. (Omit if sector is arts_culture or unknown). | `["GOODFOOT_2026", "TACT_2026", "PIRS_2025"]` | `GOODFOOT_2026_WHY_US`, `TACT_2026_WHY_US`, `PIRS_2025_WHY_US` |
| `REF_BLOCK_WHY_US_SECTOR_ARTS_LEADERSHIP`| `VARIANT` | `BIPOC-led leadership with lived experiences in community arts` | `bullet` | Current sector explicitly supports arts/culture context AND planner selects the arts identity credential. | `["RPFF_2025", "YPT_2026"]` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US` |
| `REF_BLOCK_WHY_US_SECTOR_ARTS_EXP_RPFF` | `VARIANT` | `Experience with arts and non-profit organizations across Canada` | `bullet` | Current client is explicitly an arts/culture organization AND planner selects the national arts-sector experience credential. | `["RPFF_2025"]` | `RPFF_2025_WHY_US` |
| `REF_BLOCK_WHY_US_CLOSING_1` | `DETERMINISTIC` | `We value thoughtful system design, clarity in reporting, and building long-term trusted partnerships.` | `paragraph` | Planner includes Why Us section | `["RPFF_2025", "YPT_2026", "GOODFOOT_2026", "TACT_2026"]` *(Note: PIRS source omits period)* | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US`, `GOODFOOT_2026_WHY_US`, `TACT_2026_WHY_US` |
| `REF_BLOCK_WHY_US_CLOSING_2` | `DETERMINISTIC` | `Any new requirements or adjustments can be discussed and integrated as needed. We work with transparency, flexibility, and a commitment to helping our partners thrive.` | `paragraph` | Planner includes Why Us section | `["RPFF_2025", "YPT_2026", "GOODFOOT_2026", "TACT_2026", "PIRS_2025"]` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US`, `GOODFOOT_2026_WHY_US`, `TACT_2026_WHY_US`, `PIRS_2025_WHY_US` |

### B. Approved Conditional Disclaimers (Exact Source-Backed Text)

| block_key | classification | exact_source_backed_content | render_as | selection_condition | source_proposals | source_chunk_keys |
| :--- | :---: | :--- | :---: | :--- | :--- | :--- |
| `REF_BLOCK_EXCLUSIONS_BACKLOG` | `CONDITIONAL` | `Bookkeeping backlog: Any prior period bookkeeping clean-up or catch-up work will be quoted separately based on the volume and complexity` | `note` | `commercial_terms.include_backlog_exclusion == true` *(explicit current commercial approval)* | `["CAREOF_2025", "CAHOOTS_2026", "RPFF_2025"]` | `CAREOF_2025_EXCLUSIONS`, `CAHOOTS_2026_EXCLUSIONS`, `RPFF_2025_EXCLUSIONS` |
| `REF_BLOCK_EXCLUSIONS_SOFTWARE_NOT_INCLUDED` | `CONDITIONAL` | `Note: Above costs do not include software subscription fees.` | `note` | `commercial_terms.software_fees_excluded == true` *(explicit commercial approval that software fees are excluded from Sympl fees; communicates zero assumption on payer or maintenance)* | `["GOODFOOT_2026"]` | `GOODFOOT_2026_EXCLUSIONS` |
| `REF_BLOCK_PAYROLL_HR_BOUNDARY` | `CONDITIONAL` | `Note: While we manage all payroll accounting and processing, managers must provide timely payroll data (e.g., timesheets, new hires, exits). We do not manage HR functions.` | `note` | `current_scope.payroll_processing_by_sympl == true AND current_scope.manager_payroll_input_responsibility == true AND current_scope.hr_functions_excluded == true` *(explicit current-scope compatibility)* | `["PIRS_2025"]` | `PIRS_2025_PAYROLL` |
| *Audit Response SLA* | *DO_NOT_STANDARDIZE* | *Never automatic. Turnaround commitments (1–2 business days) must be injected dynamically into section scope from client intake.* | N/A | N/A | N/A | N/A |

---

## 9. Few-Shot Exemplar Registry (Exact Database Keys)

**CRITICAL POLICY: HISTORICAL EXEMPLAR CONTENT MUST BE LOADED DIRECTLY FROM THE DATABASE BY EXACT `chunk_key`. NEVER DUPLICATE OR HARDCODE `cleaned_text` IN RUNTIME CONFIGURATION.**

All 27 keys verified against `proposal_chunks` in live Railway PostgreSQL:

| Service Family | chunk_key | proposal_code | usage | selection_reason |
| :--- | :--- | :---: | :---: | :--- |
| **Context & Objectives** | `TACT_2026_CONTEXT_OBJECTIVES` | TACT_2026 | PRIMARY (DEFAULT) | Masterclass in diagnostic framing, revenue breakdown, and operational pain point articulation. |
| **Context & Objectives** | `GOODFOOT_2026_CONTEXT_OBJECTIVES` | GOODFOOT_2026 | SECONDARY | Clear operational overview of multi-program fees and historical software bottlenecks. |
| **Bookkeeping** | `TACT_2026_BOOKKEEPING` | TACT_2026 | PRIMARY (DEFAULT) | Comprehensive AP/AR with twice-monthly ED payment runs and reconciliation rigor. |
| **Bookkeeping** | `CAREOF_2025_WEEKLY_BOOKKEEPING` | CAREOF_2025 | SECONDARY | Gold standard for compact weekly scheduling with sub-category headers. |
| **Bookkeeping** | `RPFF_2025_BOOKKEEPING_RECONCILIATIONS`| RPFF_2025 | OPTIONAL | Nonprofit grant and fund balance reconciliation focus. |
| **Payroll** | `TACT_2026_PAYROLL` | TACT_2026 | PRIMARY (DEFAULT) | Headcount specificity, multi-cycle management, deductions, and transition notes. |
| **Payroll** | `PIRS_2025_PAYROLL` | PIRS_2025 | SECONDARY | Manager data cutoffs, CSJ grant staff, and clean HR boundary note. |
| **Payroll** | `RPFF_2025_PAYROLL` | RPFF_2025 | OPTIONAL | Compact salaried and seasonal staff administration via QBO Payroll. |
| **Financial Reporting** | `TACT_2026_FINANCIAL_REPORTING` | TACT_2026 | PRIMARY (DEFAULT) | Clean separation of monthly management reporting and board governance packages. |
| **Financial Reporting** | `GOODFOOT_2026_FINANCIAL_REPORTING` | GOODFOOT_2026 | SECONDARY | Board finance committee support and variance analysis. |
| **Financial Reporting** | `CAREOF_2025_FINANCIAL_REPORTING` | CAREOF_2025 | OPTIONAL | Compact reporting deliverable list and virtual check-in cadence. |
| **Compliance & Tax** | `TACT_2026_COMPLIANCE` | TACT_2026 | PRIMARY (DEFAULT) | Public service body (PSB) rebate calculations and auditor liaison coordination. |
| **Compliance & Tax** | `RPFF_2025_COMPLIANCE_YEAR_END` | RPFF_2025 | SECONDARY | Year-end closing, CRA filing, and audit working paper prep. |
| **Compliance & Tax** | `CAREOF_2025_COMPLIANCE_YEAR_END` | CAREOF_2025 | OPTIONAL | Compact sales tax closing adjustments. |
| **Audit Preparation** | `PIRS_2025_AUDIT_PREPARATION` | PIRS_2025 | PRIMARY (DEFAULT) | Urgent standalone audit preparation, working alongside outgoing FD, 1–2 business day SLA. |
| **Audit Preparation** | `TACT_2026_AUDIT_SUPPORT` | TACT_2026 | SECONDARY | Structured 3-step annual audit support (Clean-up → PBC Binder → Auditor Liaison). |
| **Audit Preparation** | `GOODFOOT_2026_COMPLIANCE_AUDIT` | GOODFOOT_2026 | OPTIONAL | Embedded annual audit documentation and schedule preparation. |
| **Financial Management**| `GOODFOOT_2026_FINANCIAL_MANAGEMENT` | GOODFOOT_2026 | PRIMARY (DEFAULT) | Fractional controller advisory, cash flow forecasting, and budgeting. |
| **Financial Management**| `PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT`| PIRS_2025 | SECONDARY | Junior bookkeeper supervision, quality control, and staffing model evaluation. |
| **Digital Transformation**| `TACT_2026_TRANSFORMATION_AP_PLOOTO`| TACT_2026 | PRIMARY (DEFAULT) | Discrete initiative-based software automation via Plooto. |
| **Digital Transformation**| `PIRS_2025_TRANSFORMATION_IMPLEMENTATION`| PIRS_2025 | SECONDARY | GL/COA system integration and cash flow tool configuration. |
| **Digital Transformation**| `GOODFOOT_2026_DIGITAL_TRANSFORMATION`| GOODFOOT_2026 | OPTIONAL | Broad process improvement and tool exploration. |
| **Training & SOPs** | `PIRS_2025_TRAINING_CHANGE_MANAGEMENT`| PIRS_2025 | PRIMARY (DEFAULT) | Role-specific training, SOP development, and 2-month post-training adoption support. |
| **Training & SOPs** | `GOODFOOT_2026_SETUP_TRANSITION_SCOPE`| GOODFOOT_2026 | SECONDARY | Process documentation and workflow setup during onboarding. |
| **Transition & Interim** | `YPT_2026_CONTEXT_TRANSITION` | YPT_2026 | PRIMARY (DEFAULT) | Fixed-term interim context, shadowing outgoing staff, and zero payment disruption. |
| **Transition & Interim** | `YPT_2026_SYSTEMS_CONTINUITY` | YPT_2026 | SECONDARY | Preserving existing legacy platforms (Sage 50, Telpay) and digital folder hierarchies. |
| **Transition & Interim** | `YPT_2026_ONBOARDING_SETUP` | YPT_2026 | OPTIONAL | Onsite onboarding, VPN access, and workflow review. |

### Fixed Exemplar Fallback & Archetype Alignment Policy
The `PRIMARY` exemplar is a **DEFAULT**, not an **IMMUTABLE** lock. If the primary exemplar exhibits significantly higher complexity than the current client scope (e.g. TACT payroll is comprehensive multi-cycle, whereas current intake requires a compact single-cycle payroll), the runtime planner/retriever may select a verified `SECONDARY` or `OPTIONAL` gold exemplar (such as `RPFF_2025_PAYROLL` or `CAREOF_2025_WEEKLY_BOOKKEEPING`) that better matches the target archetype and detail density.

---

## 10. Section Family Eligibility & Retrieval Metadata Policy

### A. Section Family Eligibility Map
Exact `section_type` matching fails because several valid chunks span multiple service modules (e.g. `PIRS_2025_TRAINING_CHANGE_MANAGEMENT` has `section_type = 'digital_transformation'` with `service_modules = ['training', 'process_documentation']`).

The retrieval engine resolves the target writer service family using this explicit eligibility map before vector scoring:

| service_family | allowed_section_types | eligible_service_modules | SQL Selection Rule |
| :--- | :--- | :--- | :--- |
| `bookkeeping` | `bookkeeping`, `service_module` | `bookkeeping`, `reconciliations`, `accounts_payable`, `accounts_receivable` | `section_type IN ('bookkeeping', 'service_module') OR service_modules && ARRAY['bookkeeping', 'reconciliations', 'accounts_payable', 'accounts_receivable']` |
| `payroll` | `payroll` | `payroll` | `section_type = 'payroll' OR 'payroll' = ANY(service_modules)` |
| `financial_reporting` | `financial_reporting` | `financial_reporting`, `funder_reporting` | `section_type = 'financial_reporting' OR service_modules && ARRAY['financial_reporting', 'funder_reporting']` |
| `financial_management`| `financial_management` | `financial_management` | `section_type = 'financial_management' OR 'financial_management' = ANY(service_modules)` |
| `compliance` | `compliance` | `compliance`, `year_end` | `section_type = 'compliance' OR service_modules && ARRAY['compliance', 'year_end']` |
| `audit` | `audit`, `compliance` | `audit` | `section_type = 'audit' OR 'audit' = ANY(service_modules)` |
| `digital_transformation`| `digital_transformation` | `digital_transformation`, `systems_implementation` | `section_type = 'digital_transformation' OR service_modules && ARRAY['digital_transformation', 'systems_implementation']` |
| `training` | `digital_transformation`, `onboarding` | `training` *(primary)*, `process_documentation` *(secondary, conditional)* | **Primary:** `'training' = ANY(service_modules)`.<br>**Secondary:** `'process_documentation' = ANY(service_modules)` **ONLY IF** the current requested scope explicitly includes SOP / workflow-documentation deliverables. Process-documentation-only chunks are NOT automatically treated as training. |
| `transition` | `transition`, `onboarding` | `transition`, `onboarding` | `section_type IN ('transition', 'onboarding') OR service_modules && ARRAY['transition', 'onboarding']` |
| `context` | `context_objectives` | N/A | `section_type = 'context_objectives'` |

*Corpus Verification:* Tested and verified against all 47 retrieval-enabled chunks:
- Training dynamic retrieval supported: **PASS** (retrieves PIRS training; retrieves Good Foot onboarding ONLY when process documentation is explicitly requested).
- Hybrid audit/compliance retrieval supported: **PASS** (retrieves PIRS audit prep, TACT audit support, and Good Foot compliance/audit).
- Onboarding/transition retrieval supported: **PASS** (retrieves YPT transition and Good Foot onboarding).

### B. Universal Hard Filters
Before vector scoring or reranking, the retrieval engine strictly enforces:
1. `retrieval_enabled = true`
2. `pricing_content = false`
3. `boilerplate_content = false`
4. `service_family_eligibility` (via eligibility map above)

### C. Metadata Reranking Policy
| Field | Policy | Operational Rationale |
| :--- | :---: | :--- |
| `retrieval_enabled` | **HARD_FILTER** | Mandatory. Only chunks approved for search are eligible. |
| `pricing_content` | **HARD_FILTER** | Mandatory (must be `false`). Historical pricing chunks are never retrieved for service drafting. |
| `boilerplate_content` | **HARD_FILTER** | Mandatory (must be `false`). Standard house copy is handled via `sympl_reference_blocks`. |
| `service_family` | **HARD_FILTER** | Enforced via Section Family Eligibility Map. |
| `service_modules` | **STRONG_BOOST** | Chunks sharing specific operational tasks (e.g. `accounts_payable`, `reconciliations`) receive high similarity weight. |
| `special_requirements` | **STRONG_BOOST** | Boosts chunks matching specific intake conditions (e.g. `grant_tracking`, `multi_entity`). |
| `engagement_type` | **STRONG_BOOST** | Aligns exemplar style with the selected proposal archetype. |
| `accounting_systems` | **STRONG_BOOST** | Boosts chunks referencing the client's software stack (e.g. QBO vs Xero). |
| `payroll_systems` | **STRONG_BOOST** | Boosts chunks referencing the client's payroll platform (e.g. Wagepoint). |
| `organization_type` | **SOFT_BOOST** | Softly aligns peer organization tone (nonprofit, charity, for-profit). |
| `sector` | **SOFT_BOOST** | Softly favors sector terminology (arts, social services) without excluding high-quality chunks. |
| `cadence` | **SOFT_BOOST** | Aligns operational rhythm (weekly vs bi-weekly vs monthly). |
| `core_bookkeeping` | **SOFT_BOOST** | Differentiates core operational engagements from specialized advisory. |

---

## 11. Section Writer Prompt Architecture & Output Contract

### A. Prompt Assembly Order
1. **System Identity & Role:** Senior Sympl Solutions finance consultant; authoritative, grounded Canadian professional.
2. **Fact / Scope Safety Guardrails (Gate A):** Non-negotiable safety rules preventing hallucinations, pricing generation, or scope leakage.
3. **Historical Fact Firewall:** Explicit directive that few-shot examples provide *writing style and syntax only*.
4. **Current Client Intake Facts:** Target organization name, sector, operational setup, pain points, and current software.
5. **Current Section Plan & Objectives:** Section title, required scope deliverables, and presentation structure.
6. **Current Approved Responsibility Boundaries:** Scope cutoffs, approval roles, client vs Sympl responsibilities.
7. **Global Sympl Style Rules:** Direct verb leads, concise bullets, no trailing periods, low hype.
8. **Section-Specific Style Rules:** Formatting and structural rules for the target section family.
9. **Archetype-Specific Style Rules:** Document pacing and detail density guidance.
10. **Fixed Gold Exemplar `cleaned_text`:** Loaded dynamically from DB by `chunk_key` (labeled `STYLE_EXAMPLE_ONLY`).
11. **Dynamic Retrieved Exemplar `cleaned_text`:** Context-matched reference from DB (labeled `STYLE_EXAMPLE_ONLY`).
12. **Approved Reference Blocks:** Injected canonical clauses (Why Us or conditional disclaimers). For blocks with `render_as = "bullet"`, the prompt instructs rendering as a bullet.
13. **Flexible Output Schema Directive:** Strict JSON output schema.

### B. Instruction Precedence Hierarchy (Strict Descending Order)
1. **Current Client Facts & Human Scope Directives** *(Highest priority; cannot be overridden)*
2. **Fact / Scope Safety Rules (Gate A Guardrails)**
3. **Current Section Plan & Approved Deliverables**
4. **Current Approved Responsibility Boundaries**
5. **Current Approved Commercial / Pricing Input**
6. **Global & Section Style Rules**
7. **Approved Reference Blocks**
8. **Historical Exemplars (Cleaned Text)** *(Lowest priority; syntax and rhythm guide only, zero factual authority)*

### C. Historical Fact Firewall Directive
```
HISTORICAL FACT FIREWALL:
The historical exemplars provided below are included EXCLUSIVELY as writing-style,
rhythm, and structural formatting references. You are strictly forbidden from copying
or referencing historical organization names (such as Care/of, Cahoots, RPFF, Young People's
Theatre, Good Foot, The Autism Centre of Toronto, or PIRS), historical employee counts,
specific grant programs, past software licenses, calendar dates, or past dollar figures.
Every entity, system, volume, deliverable, and statutory form in your output MUST originate
exclusively from the CURRENT CLIENT FACTS provided in this prompt.
```

### D. Flexible Writer Output Contract
The output schema accommodates varied historical Sympl layouts (subsections with category headers, Objective/Scope/Timeline blocks, plain bullet lists, notes):

```json
{
  "section_title": "Scope of Services: Bookkeeping & Reconciliations",
  "opening_text": null,
  "subsections": [
    {
      "heading": "Accounts Payable & Banking:",
      "intro_text": null,
      "bullets": [
        "Process vendor invoices and verify general ledger coding",
        "Prepare bi-weekly payment runs in Plooto for management approval",
        "Reconcile operating bank accounts on a monthly basis"
      ]
    },
    {
      "heading": "Reconciliations & Month-End:",
      "intro_text": null,
      "bullets": [
        "Reconcile corporate credit cards and verify receipt capture in Dext",
        "Maintain balance sheet schedules and deferred revenue accounts"
      ]
    }
  ],
  "note": null,
  "timeline": null,
  "reference_block_keys": []
}
```

---

## 12. Commercial Input Contract (Field-Only Specification)

To prevent commercial anchoring, the runtime design defines **schema fields only** without sample prices:

```json
{
  "currency": null,
  "billing_structure": null,
  "monthly_fees": [],
  "one_time_fees": [],
  "annual_fees": [],
  "setup_fees": [],
  "tax_treatment": null,
  "software_terms": null,
  "payment_terms": null,
  "conditions": [],
  "exclusions": [],
  "notes": [],
  "approved_by_human": false
}
```

---

## 13. Dual-Gate Evaluator Architecture

```
[Section Writer Draft]
        │
        ▼
[GATE A: Fact & Scope Safety Evaluator] (Pass / Fail)
  ├─ Check 1: Zero invented client facts (revenue, dates, staff)
  ├─ Check 2: Zero historical fact leakage (old client names, numbers)
  ├─ Check 3: Zero historical scope leakage (unapproved statutory filings, extra services)
  ├─ Check 4: Zero invented banking/release authority
  ├─ Check 5: Zero unapproved pricing, rates, or SLA commitments
  ▼
  Pass? ──► NO  ──► [REJECT DRAFT: Immediate Regenerate with Safety Violation]
  │
  YES
  │
  ▼
[GATE B: Sympl Writing Fidelity Evaluator] (Scored out of 100%)
  │
  ├─ SEMANTIC WRITING FIDELITY (70%):
  │   ├─ Historical Exemplar Similarity & Prose Rhythm (25%)
  │   ├─ Natural Client-Specific Integration (15%)
  │   ├─ Responsibility-Language Style & Boundaries (15%)
  │   └─ Section Architecture & Detail-Density Match (15%)
  │
  └─ MECHANICAL FORMATTING CHECKS (30%):
      ├─ Direct Action Verb Leads [Target >= 75%] (10%)
      ├─ AI Hype & Buzzword Avoidance [0 Banned Buzzwords] (10%)
      ├─ Bullet Conciseness & Length [Target 6–15 words] (5%)
      └─ Punctuation Hygiene [0 Trailing Periods on Bullets] (5%)
  ▼
  Score >= 90%? ──► YES ──► [PASS: Stage Section for Proposal Assembly]
  │
  NO ──► [REWRITE: Regenerate with Targeted Linter Feedback on Failed Dimensions]
```

---

## 14. Human Approval Points

1. **Commercial Pricing Approval:** Fee schedules, billing structure, currency, and software terms must be explicitly approved by human input before proposal generation.
2. **Scope Ambiguity Resolution:** If client intake lacks clear boundaries (e.g. unverified backlog or ambiguous payment authority), human confirmation is required.
3. **Banking / Payment Release Sign-Off:** Any assignment of payment preparation or release authority requires explicit human confirmation.
4. **Final Proposal Package Review:** Final assembled proposal undergoes standard human review before delivery.

---

## 15. Final Proposed Runtime Asset Manifests

### A. Style Rule Manifest (`sympl_style_rules` — 21 Rows)
All rows stored with canonical priority `'P1'`, `'P2'`, or `'P3'` and loaded with `ORDER BY priority ASC, rule_key ASC`:
- **6 Global Rules:** `RULE_GLOBAL_DIRECT_VERB_LEADS`, `RULE_GLOBAL_NO_TRAILING_PERIODS`, `RULE_GLOBAL_CONCISE_BULLETS`, `RULE_GLOBAL_LOW_HYPE_TONE`, `RULE_GLOBAL_NATURAL_VERB_REPETITION`, `RULE_GLOBAL_CLIENT_SPECIFIC_INTEGRATION`.
- **10 Section Rules:** `RULE_SEC_BOOKKEEPING_WORKFLOW`, `RULE_SEC_PAYROLL_STRUCTURE`, `RULE_SEC_REPORTING_GOVERNANCE`, `RULE_SEC_COMPLIANCE_DELINEATION`, `RULE_SEC_AUDIT_LIAISON_FRAMEWORK`, `RULE_SEC_TRANSFORMATION_MODULARITY`, `RULE_SEC_TRAINING_SUPPORT`, `RULE_SEC_TRANSITION_CONTINUITY`, `RULE_SEC_WHY_US_STRUCTURE`, `RULE_SEC_PRICING_FORMATTING`.
- **5 Archetype Rules:** `RULE_ARCH_COMPACT_BOOKKEEPING`, `RULE_ARCH_STANDARD_NONPROFIT`, `RULE_ARCH_TRANSITION_INTERIM`, `RULE_ARCH_COMPREHENSIVE_TRANSFORMATION`, `RULE_ARCH_AUDIT_OVERSIGHT_TRANSFORMATION`.

### B. Reference Block Manifest (`sympl_reference_blocks` — 13 Rows)
All rows stored with exact, source-backed contiguous text (`source_mode = 'EXACT_SOURCE_BLOCK'`) and explicit presentation metadata:

| block_key | block_type | classification | content | render_as | source_chunk_keys | selection_condition | contiguous_exact_match |
|---|---|:---:|---|:---:|---|---|:---:|
| `REF_BLOCK_WHY_US_OPENING` | `why_us` | `DETERMINISTIC` | `Sympl Solutions is committed to ensuring a high standard of financial clarity and timely support. We bring:` | `intro` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US`, `GOODFOOT_2026_WHY_US`, `TACT_2026_WHY_US`, `PIRS_2025_WHY_US` | Planner includes Why Us section | `YES` |
| `REF_BLOCK_WHY_US_CREDENTIAL_RESPONSIVE_TEAM` | `why_us` | `DETERMINISTIC` | `A responsive, detail-oriented team` | `bullet` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US`, `GOODFOOT_2026_WHY_US`, `TACT_2026_WHY_US`, `PIRS_2025_WHY_US` | Planner includes Why Us section | `YES` |
| `REF_BLOCK_WHY_US_EXP_NONPROFIT` | `why_us` | `VARIANT` | `Decade-long expertise in nonprofit finance` | `bullet` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US`, `GOODFOOT_2026_WHY_US`, `PIRS_2025_WHY_US` | Client `organization_type` explicitly supports non-profit (never inferred) | `YES` |
| `REF_BLOCK_WHY_US_EXP_CHARITY` | `why_us` | `VARIANT` | `Decade-long expertise in nonprofit and charity finance` | `bullet` | `TACT_2026_WHY_US` | Client `organization_type` explicitly supports registered charity (never inferred) | `YES` |
| `REF_BLOCK_WHY_US_CREDENTIAL_TECH_INTEGRATION` | `why_us` | `DETERMINISTIC` | `Streamlined tech integration and clear process flows` | `bullet` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US`, `GOODFOOT_2026_WHY_US`, `TACT_2026_WHY_US`, `PIRS_2025_WHY_US` | Planner includes Why Us section | `YES` |
| `REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL` | `why_us` | `VARIANT` | `BIPOC and immigrant-led leadership with lived experiences in community, social service and arts & culture` | `bullet` | `GOODFOOT_2026_WHY_US`, `TACT_2026_WHY_US`, `PIRS_2025_WHY_US` | Current client sector explicitly established as `social_services`, `community_services`, `community_organization` AND planner selects this identity credential | `YES` |
| `REF_BLOCK_WHY_US_SECTOR_ARTS_LEADERSHIP`| `why_us` | `VARIANT` | `BIPOC-led leadership with lived experiences in community arts` | `bullet` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US` | Current sector explicitly supports arts/culture context AND planner selects the arts identity credential | `YES` |
| `REF_BLOCK_WHY_US_SECTOR_ARTS_EXP_RPFF` | `why_us` | `VARIANT` | `Experience with arts and non-profit organizations across Canada` | `bullet` | `RPFF_2025_WHY_US` | Current client is explicitly an arts/culture organization AND planner selects the national arts-sector experience credential | `YES` |
| `REF_BLOCK_WHY_US_CLOSING_1` | `why_us` | `DETERMINISTIC` | `We value thoughtful system design, clarity in reporting, and building long-term trusted partnerships.` | `paragraph` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US`, `GOODFOOT_2026_WHY_US`, `TACT_2026_WHY_US` *(PIRS source omits period)* | Planner includes Why Us section | `YES` |
| `REF_BLOCK_WHY_US_CLOSING_2` | `why_us` | `DETERMINISTIC` | `Any new requirements or adjustments can be discussed and integrated as needed. We work with transparency, flexibility, and a commitment to helping our partners thrive.` | `paragraph` | `RPFF_2025_WHY_US`, `YPT_2026_WHY_US`, `GOODFOOT_2026_WHY_US`, `TACT_2026_WHY_US`, `PIRS_2025_WHY_US` | Planner includes Why Us section | `YES` |
| `REF_BLOCK_EXCLUSIONS_BACKLOG` | `exclusions` | `CONDITIONAL` | `Bookkeeping backlog: Any prior period bookkeeping clean-up or catch-up work will be quoted separately based on the volume and complexity` | `note` | `CAREOF_2025_EXCLUSIONS`, `CAHOOTS_2026_EXCLUSIONS`, `RPFF_2025_EXCLUSIONS` | `commercial_terms.include_backlog_exclusion == true` *(explicit current commercial approval)* | `YES` |
| `REF_BLOCK_EXCLUSIONS_SOFTWARE_NOT_INCLUDED`| `exclusions` | `CONDITIONAL` | `Note: Above costs do not include software subscription fees.` | `note` | `GOODFOOT_2026_EXCLUSIONS` | `commercial_terms.software_fees_excluded == true` *(explicit commercial approval; makes zero assumption on payer)* | `YES` |
| `REF_BLOCK_PAYROLL_HR_BOUNDARY` | `boundary` | `CONDITIONAL` | `Note: While we manage all payroll accounting and processing, managers must provide timely payroll data (e.g., timesheets, new hires, exits). We do not manage HR functions.` | `note` | `PIRS_2025_PAYROLL` | `current_scope.payroll_processing_by_sympl == true AND current_scope.manager_payroll_input_responsibility == true AND current_scope.hr_functions_excluded == true` | `YES` |

---
*End of Hardened Runtime Style Asset & Architecture Design Specification.*
