# Sympl Solutions: Cross-Proposal Writing-Style Discovery & Architectural Blueprint

> **Status:** Final Evidence-Hardened Review & Specification  
> **Source Base:** 7 Curated Historical Proposals (71 Chunks in PostgreSQL)  
> **Scope:** Cleaned Text Writing Style Analysis across CAREOF_2025, CAHOOTS_2026, RPFF_2025, YPT_2026, GOODFOOT_2026, TACT_2026, and PIRS_2025.  
> **Target:** Establish an empirical, high-fidelity style architecture so AI-generated proposals are indistinguishable from genuine Sympl Solutions work without overfitting or promoting source-specific commitments into universal rules.

---

## 1. Executive Summary & Corpus Baseline

This document provides a comprehensive, empirical analysis of how Sympl Solutions actually writes client proposals based on the complete, verified 7-proposal historical corpus.

### Authoritative Corpus Inventory
| Proposal Code | Client Name | Proposal Date | Pages | Chunks | Engagement Archetype | Complexity |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| `CAREOF_2025` | Care/Of Experiences | 2025-02-20 | 4 | 9 | Compact Recurring Bookkeeping | compact |
| `CAHOOTS_2026` | CAHOOTS Theatre Company | [n/d] (2026) | 3 | 9 | Compact Recurring Bookkeeping | compact |
| `RPFF_2025` | Regent Park Film Festival | 2025-06-06 | 4 | 11 | Standard Nonprofit Bookkeeping | standard |
| `YPT_2026` | Young People's Theatre | 2026-01-06 | 5 | 8 | Transition & Interim Finance Support | standard |
| `GOODFOOT_2026` | Good Foot Support Services | [n/d] (2026) | 7 | 13 | Comprehensive Finance Management | comprehensive |
| `TACT_2026` | The Autism Centre of Toronto | [n/d] (2026) | 9 | 14 | Ongoing Plus Transformation | comprehensive |
| `PIRS_2025` | Pacific Immigrant Resources Society | 2025-06-21 | 7 | 7 | Audit/Oversight + Transformation | comprehensive |

### Core Evidence Distinction
- **`cleaned_text` (Primary Writing Exemplar):** Represents authentic Sympl sentence structure, bullet rhythm, terminology, responsibility phrasing, and section layouts.
- **`raw_text` (Historical Evidence):** Used only to verify layout, table structures, and text-flow artifacts.
- **`retrieval_text` (Excluded from Style):** Exclusively utilized for vector embedding and semantic retrieval indexing; contains synthetic normalization and expanded abbreviations not representative of Sympl's writing voice.

### Core Architectural Principle
**STYLE FIDELITY ≠ FORCING EVERY HISTORICAL PHRASE INTO EVERY PROPOSAL.**  
We carefully distinguish between:
1. **Global House Style:** Universally true cross-proposal tendencies (e.g. action-verb leads, concise bullets, no trailing periods, low hype).
2. **Section-Specific Patterns:** Recurring conventions tied to a functional module (e.g. pay cycle cutoffs, PBC audit list compilation).
3. **Archetype-Specific Patterns:** Conventions driven by engagement scope (e.g. diagnostic openings in comprehensive proposals vs direct service tables in compact proposals).
4. **Client/Source-Specific Facts:** Case-specific facts that must never be generalized (e.g. specific employee counts, software platforms, 1–2 business day turnaround commitments).
5. **Conditional Reference Blocks:** Reusable approved wording deployed only when current scope calls for it (e.g. bookkeeping backlog exclusions, software pass-through disclaimers, HR boundary notes).

---

## 2. Level 1: Proposal Architecture & Archetype Discovery

Across the 7 proposals, Sympl structures proposals dynamically based on client operational maturity, engagement duration, and project scope.

### Proposal Architecture Matrix
| Proposal Code | Opening Structure | Service Structure | Transformation Placement | Audit Placement | Pricing Placement | Why Us Placement | Detail Density |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`CAREOF_2025`** | Direct service (`Weekly Bookkeeping`) | Weekly BK → Reconciliations → Expenses → Payroll → Reporting → Sales Tax | None | None | Section 7 & 9 (Monthly + Software) | Absent | Compact (Low-Medium) |
| **`CAHOOTS_2026`** | Direct service (`Biweekly Bookkeeping`) | Biweekly BK → Reconciliations → Expenses → Payroll → Reporting → Sales Tax | None | None | Section 7 & 9 (Monthly + Software) | Absent | Compact (Low-Medium) |
| **`RPFF_2025`** | Direct service (`Core Bookkeeping`) | Core BK → Grants/Funding → AP/AR → Payroll → Reporting → Compliance/Audit → Tech | End of Scope (Section 7) | Embedded in Compliance (Section 6) | Section 8 & 9 (Setup + Monthly) | Section 11 (Closing) | Standard (Medium) |
| **`YPT_2026`** | Narrative Context (`Summary of Engagement`) | Payables & Expenditures → Receivables & Revenues → Systems Continuity → Onboarding | None | None | Section 6 & 7 (Setup + Monthly) | Section 8 (Closing) | Standard (Medium-High) |
| **`GOODFOOT_2026`**| Formal Diagnostic (`1. CONTEXT & OBJECTIVES`) | Full-Service BK → Payroll → Reporting → Compliance/Audit → Financial Mgmt → Tech | Part 4 (Dedicated project) | Embedded in Compliance (Section 5) | Section 9, 10, 11 (Setup + Tech + Monthly) | Section 13 (Closing) | Comprehensive (High) |
| **`TACT_2026`** | Formal Diagnostic (`CONTEXT & OBJECTIVES`) | Part A: Ongoing (BK → Payroll → Reporting → Compliance) → Part B: Tech → Part C: Audit | Part B (3 Discrete Initiatives) | Part C (Standalone annual module) | Section 10, 11, 12 (Part A, B, C) | Section 14 (Closing) | Comprehensive (High) |
| **`PIRS_2025`** | Audit Prep & Liaison (Urgent Priority) | Audit Prep → Bookkeeping Oversight & Financial Mgmt → Payroll → Digital Transformation | Section 4 (3 Phased Subsections) | Section 1 (Lead Opening Priority) | Absent (Delivered separately) | Section 7 (Closing) | Comprehensive (High) |

---

### The Five Identified Archetypes

#### Archetype 1: Compact Recurring Bookkeeping
- **Proposal Examples:** `CAREOF_2025`, `CAHOOTS_2026`
- **When Used:** Small commercial businesses or straightforward nonprofits seeking steady recurring bookkeeping, basic payroll (under 5 staff), and routine tax compliance without organizational restructuring.
- **Typical Structure:**
  1. Service Schedule (Weekly/Biweekly Bookkeeping)
  2. Monthly Reconciliations
  3. Expense Management & AP/AR
  4. Payroll Processing
  5. Monthly Financial Statements & Check-ins
  6. Sales Tax Compliance & Year-End Closing
  7. Monthly Fees & Software Subscription Table
  8. Exclusions (Backlog & Software)
- **Features:** Direct category-labeled bullet lists (`General Bookkeeping:`, `Reconciliations:`); no Context/Objectives section; no Why Us boilerplate.

#### Archetype 2: Standard Nonprofit Bookkeeping & Governance
- **Proposal Examples:** `RPFF_2025`
- **When Used:** Small-to-midsize arts and community organizations with active project grants and annual auditor reviews.
- **Typical Structure:** Core Bookkeeping & Reconciliations → Funding, Grants & Fund Tracking → AP/AR → Payroll → Reporting & Governance → Compliance, Year-End & Audit Support → Lightweight Process Improvement → Setup & Monthly Retainer → Exclusions → Why Us.
- **Features:** Integrates fund/grant tracking into core scope; audit support embedded in compliance; includes lightweight process improvements and Why Us boilerplate.

#### Archetype 3: Transition & Interim Finance Support
- **Proposal Examples:** `YPT_2026`
- **When Used:** Organizations experiencing staff turnover, leaves, or operational transitions needing stable interim bookkeeping without disrupting current tools or systems.
- **Typical Structure:** Summary of Engagement (Narrative context + 3-month term) → Payables & Expenditures → Receivables & Revenues → Systems & Workflow Continuity → Onboarding & Setup → Setup & Monthly Retainer → Why Us.
- **Features:** Explicit time horizon (e.g. 3 months); strong emphasis on maintaining existing tools (Sage 50, Telpay, VPN) and folder hierarchies; onsite shadowing.

#### Archetype 4: Comprehensive Ongoing + Expanded Services
- **Proposal Examples:** `GOODFOOT_2026`, `TACT_2026`
- **When Used:** Multi-program nonprofits or charities with complex revenue, legacy software bottlenecks, board reporting needs, and desire for modernized, automated systems.
- **Structural Variants within Archetype:**
  - *Good Foot Variant:* Numbered/lettered sections covering Full-Service Bookkeeping + Payroll + Board Reporting + Compliance/Audit + **Fractional Financial Management (Controller advisory/cash modeling)** + **Broad Digital Transformation (budget range)**.
  - *TACT Variant:* Multi-part labeled modular architecture: **Part A: Ongoing Retainer** (BK, Payroll, Reporting, Compliance) + **Part B: Process & Digital Transformation (3 discrete initiatives: Plooto, ADP to QBO, Invoicing)** + **Part C: Standalone Annual Audit Support**.
- **Features:** In-depth diagnostic opening (`CONTEXT & OBJECTIVES`); multi-part or tiered pricing; explicit system evaluation or migration targets.

#### Archetype 5: Audit Preparation, Bookkeeping Oversight & Transformation
- **Proposal Examples:** `PIRS_2025`
- **When Used:** Organizations with internal junior bookkeeping staff needing senior supervisory oversight, historical audit catch-up, and phased technology modernization.
- **Typical Structure:** 1. Audit Preparation & Liaison (Urgent Priority) → 2. Bookkeeping Oversight & Financial Management → 3. Payroll Management → 4. Digital Transformation & Staff Training (Phased: Strategy, Implementation, Training) → Why Us.
- **Features:** Highly structured "Objective:" / "Scope of Work:" / "Timeline:" / "Note:" formatting; supervisory operating model rather than transaction-entry execution.

---

## 3. Level 2: Section Architecture & Section Families

### Section Family Analysis

#### 1. Context & Objectives (`context_objectives`)
- **Found in:** `GOODFOOT_2026`, `TACT_2026`
- **Heading Format:** `1. CONTEXT & OBJECTIVES` or `CONTEXT & OBJECTIVES`
- **Opening Style:** 2–4 narrative paragraphs diagnosing current revenue streams, staffing model, manual bottlenecks, and transformation objectives.
- **Body Structure:** Prose paragraphs describing organization mission, revenue mix (fees, grants, donations), current operational pain points (manual tracking, paper cheques, disconnected software), and engagement goals.
- **Bullet Count & Length:** Frequently pure narrative prose; when bullets occur, they are 15–25 words summarizing key diagnostic challenges.

#### 2. Bookkeeping (`bookkeeping`)
- **Found in:** All 7 proposals
- **Heading Format:** Direct operational titles (e.g. `Weekly Bookkeeping`, `Core Bookkeeping & Reconciliations`, `1) BOOKKEEPING & RECONCILIATIONS`, `A. Full-Service Bookkeeping`)
- **Body Structure:**
  - *Compact proposals:* Sub-headers with colons (`General Bookkeeping:`, `Reconciliations:`, `Expense Management:`) followed by 2–4 short bullets.
  - *Comprehensive proposals:* Flat bulleted lists led by imperative verbs (`Record`, `Process`, `Maintain`, `Reconcile`, `Manage`).
- **Bullet Count & Length:** 4 to 10 bullets per section; average 8–11 words per bullet.
- **Core Coverage:** Bill entry, invoice generation, payment runs with ED/management, monthly bank and credit card reconciliations, general ledger maintenance.

#### 3. Payroll (`payroll`)
- **Found in:** `CAREOF`, `CAHOOTS`, `RPFF`, `GOODFOOT`, `TACT`, `PIRS` (and embedded in `YPT`)
- **Heading Format:** `Payroll Processing via [Software] (up to [N] Employees)`, `Payroll Administration & Compliance`, `2. PAYROLL ADMINISTRATION & COMPLIANCE`, `B. Payroll Management`
- **Body Structure:** Operational progression:
  1. Pay cadence and employee classifications (salaried, hourly, contract, seasonal, CSJ).
  2. Timesheet/data cutoffs (`data provided by Client` or `managers must provide timely payroll data`).
  3. Source deduction tracking (CPP, EI, income tax) and remittance submission.
  4. General ledger reconciliation with accounting software.
  5. Year-end tax filings (T4, T4A, ROE).
- **Boundary Conditions:** When present in client requirements, explicit boundaries are stated (e.g. PIRS's `"We do not manage HR functions"`).

#### 4. Financial Reporting (`financial_reporting`)
- **Found in:** `CAREOF`, `CAHOOTS`, `RPFF`, `GOODFOOT`, `TACT` (integrated in `PIRS`)
- **Heading Format:** `Monthly Financial Statements and Virtual Check-ins`, `Financial Reporting & Governance`, `Monthly & Board Reporting`, `A. Reporting & Board Support`
- **Body Structure:** Deliverable-based list:
  - Standard financial statements: Balance Sheet, Income Statement (P&L), AP/AR Aging, Cash Flow summary.
  - Governance & Board packages: Departmental/program actuals vs. budget, board finance committee reports.
  - Meeting cadence: Virtual monthly check-in (or bi-weekly check-in during ramp-up).

#### 5. Compliance & Year-End (`compliance`)
- **Found in:** `CAREOF`, `CAHOOTS`, `RPFF`, `GOODFOOT`, `TACT`
- **Heading Format:** `Sales Tax Compliance and Year-end Closing`, `Compliance, Year-End & Audit Support`, `HST & PSB Rebate / CRA & Audit Compliance`
- **Body Structure:**
  - GST/HST or Public Service Body (PSB) rebate calculations and electronic filing.
  - Annual fiscal year-end closing, adjusting entries, accruals, and trial balance validation.
  - Coordination with external CPA/auditor; preparation of working papers and lead schedules.

#### 6. Financial Management & Controller Advisory (`financial_management`)
- **Found in:** `GOODFOOT_2026`, `PIRS_2025`
- **Heading Format:** `C. Fractional Financial Management`, `2. BOOKKEEPING OVERSIGHT & FINANCIAL MANAGEMENT`
- **Body Structure:** Advisory, controller-level oversight:
  - Cash flow forecasting and rolling projections.
  - Organizational and departmental budgeting support with ED/leadership.
  - Bookkeeping team oversight, workflow review, and future finance staffing recommendations.
  - Standard operating procedures and GL coding architecture.

#### 7. Audit Support & Preparation (`audit`)
- **Found in:** `TACT_2026` (Part C), `PIRS_2025` (Section 1), embedded in `RPFF_2025` & `GOODFOOT_2026`
- **Heading Format:** `PART C - YEAR-END AUDIT SUPPORT (ANNUAL ENGAGEMENT)`, `1. AUDIT PREPARATION & LIAISON`
- **Body Structure:** Step-by-step or prioritized liaison scope:
  - Step 1: Year-end book review, reconciliations, and clean-up.
  - Step 2: Audit binder / PBC (Prepared By Client) list compilation.
  - Step 3: Primary auditor liaison, meeting attendance, and query response.
- **Boundary:** Sympl prepares documentation and liaises with the external auditor; Sympl never performs the independent financial audit.
- **Response Commitments:** When a response turnaround is scoped, it is stated concretely (e.g. *1–2 business days* in PIRS; *2 days* in TACT).

#### 8. Digital Transformation & Systems Modernization (`digital_transformation`)
- **Found in:** `RPFF_2025`, `GOODFOOT_2026`, `TACT_2026`, `PIRS_2025`
- **Heading Format:** `*NEW* Process & Technology Improvements`, `4. SCOPE - PROCESS IMPROVEMENT & DIGITAL TRANSFORMATION`, `Initiative [N]: [Title] via [Tool]`, `4. DIGITAL TRANSFORMATION & STAFF TRAINING`
- **Body Structure:** Modular and task-specific. Organizes work by discrete initiatives (TACT), sequential phases (PIRS), or broad technology exploration (RPFF, Good Foot).
- **Core Software:** Scopes specific platforms when approved (Plooto, QBO Payroll, Dext).

#### 9. Why Us Boilerplate (`why_us`)
- **Found in:** 5 of 7 proposals (`RPFF_2025`, `YPT_2026`, `GOODFOOT_2026`, `TACT_2026`, `PIRS_2025`)
- **Structure:** Deterministic 3-part layout (see Section 6 for full decomposition).

#### 10. Pricing & Commercial Structure (`pricing`)
- **Found in:** 6 of 7 proposals (omitted in `PIRS_2025`)
- **Structure:** Unbundled pricing blocks: Monthly Retainer / Service Fees, One-Time Setup & Onboarding Fees, and Software Pass-Through Table.

#### 11. Notes & Exclusions (`exclusions`)
- **Found in:** `CAREOF`, `CAHOOTS`, `RPFF`, `GOODFOOT`, `TACT`
- **Structure:** Backlog clean-up disclaimers and software subscription pass-through notes.

---

## 4. Level 3: Sentence & Bullet Syntax Statistics

### Quantitative Syntax Metrics
| Metric | Corpus Measurement | Evidence / Context |
| :--- | :--- | :--- |
| **Total Bullets Analyzed** | 347 bullets | Across all 71 cleaned chunks |
| **Average Words per Bullet** | 9.4 words | Tight, concise, action-focused phrasing |
| **Common Length Range** | 6 to 14 words | Min: 1 word, Max: 39 words |
| **Verb-Led Bullets** | ~78.4% of all bullets | Direct action verb starts the bullet line |
| **Bullets Ending with Period** | 4.3% (15 / 347) | **95.7% of bullets have NO trailing period** |
| **Explicit Future "Sympl will"**| 5 occurrences total | Rare; only in YPT transition and TACT audit intro |
| **Explicit Future "We will"** | 2 occurrences total | Rare; avoid using in normal scope bullets |
| **Subcategory Colons** | Highly frequent | Used to group tasks (e.g. `General Bookkeeping:`, `Reconciliations:`) |
| **Parentheses Usage** | 82 occurrences | Clarifications: `(up to 3 Employees)`, `(via Plooto)`, `(CPP, EI, income tax)` |
| **En-Dash / Range Usage** | 46 occurrences | Durations and numbers: `1–2 business days`, `8–10 weeks`, `2–3 month` |

### Top 20 Recurring Action Verbs
Sympl relies on an unpretentious, highly operational core verb vocabulary:

| Rank | Action Verb | Frequency | Primary Section Families | Typical Object / Completion Context |
| :---: | :--- | :---: | :--- | :--- |
| 1 | **Process** | 11 | Bookkeeping, Payroll, Pricing | Biweekly payroll, vendor bills, hourly contractor payments |
| 2 | **Prepare** | 11 | Payroll, Compliance, Audit | T4/T4A tax forms, monthly financial packages, audit schedules |
| 3 | **Maintain** | 10 | Bookkeeping, Payroll, Transition | General ledger accounts, employee payroll records, digital filing |
| 4 | **Ensure** | 10 | Payroll, Compliance, Audit | Accurate source deductions, CRA compliance, timely remittance |
| 5 | **Manage** | 8 | Bookkeeping, Payroll, Management | AP/AR workflows, payroll cycles, bi-weekly payment runs |
| 6 | **Set up** | 7 | Transformation, Onboarding | Software integrations, cash flow tools, chart of accounts |
| 7 | **Develop** | 7 | Financial Mgmt, Transformation | Bookkeeping calendars, approval workflows, reporting templates |
| 8 | **Record** | 6 | Bookkeeping, Service Modules | Day-to-day transactions, bank deposits, credit card expenses |
| 9 | **Conduct** | 6 | Audit, Transformation, Mgmt | Deep-dive financial reviews, digital literacy audits, check-ins |
| 10 | **Configure** | 5 | Transformation, Bookkeeping | Chart of accounts, GL classes, Plooto approval matrices |
| 11 | **Oversee** | 4 | Bookkeeping, Financial Mgmt | Tasks of junior bookkeeper, day-to-day accounts payable functions |
| 12 | **Reconcile** | 4 | Bookkeeping, Payroll | Bank accounts, credit cards, payroll data to QuickBooks GL |
| 13 | **Review** | 4 | Audit, Compliance, Mgmt | Prior year financials, monthly trial balances, vendor invoices |
| 14 | **Coordinate** | 4 | Audit, Compliance, Transformation | External auditor requests, bookkeeper backup documents, vendors |
| 15 | **Deliver** | 3 | Transformation, Training | Role-specific training sessions, future-state process roadmaps |
| 16 | **Track** | 2 | Bookkeeping, Payroll | Overdue accounts receivable, vacation pay & statutory liabilities |
| 17 | **Submit** | 2 | Payroll, Compliance | Federal and provincial tax remittances, GST/HST rebate filings |
| 18 | **Implement** | 2 | Transformation, Bookkeeping | Budget tracking mechanisms, internal control standards |
| 19 | **Liaise** | 2 | Compliance, Audit | External auditor during year-end, tax authorities |
| 20 | **Support** | 2 | Onboarding, Training | Post-training adoption and troubleshooting, board committees |

---

## 5. Level 4: Lexical Style, Tone & Boundary Architecture

### The Sympl Tone Fingerprint (10 Dimensions)
| Dimension | Rating (1–5) | Empirical Evidence from Corpus |
| :--- | :---: | :--- |
| **Operational vs. Conceptual** | **4.8 / 5** | Scopes specific systems (QBO, Plooto, WagePoint), cadences (bi-weekly, monthly), forms (T4, ROE, PSB rebate), and cutoffs. |
| **Formal vs. Conversational** | **3.0 / 5** | Direct, clear Canadian business English; avoids archaic legalese as well as casual startup slang. |
| **Sales-Heavy vs. Low-Hype** | **1.2 / 5** | Extremely low hype. Zero consulting buzzwords (*synergy, leverage, cutting-edge*). Value is conveyed strictly through concrete tasks. |
| **Dense vs. Explanatory** | **4.2 / 5** | Bullets average 9.4 words. No long narrative justifications for standard tasks. High information-to-word ratio. |
| **Confident vs. Cautious** | **4.0 / 5** | Clear commitments on timelines and response windows (e.g. 1–2 business days), combined with explicit client dependencies. |
| **Generic vs. Client-Specific** | **4.6 / 5** | Embeds client employee counts, revenue volume, software stack, and exact historical dates directly into the scope lines. |
| **Strategic vs. Execution-Focused** | **4.5 / 5** | Deeply execution-focused. Primary goal is accurate entries, reconciled ledgers, paid bills, and timely statutory filings. |
| **Technical vs. Accessible** | **3.8 / 5** | Uses standard Canadian accounting concepts (GL, trial balance, source deductions, PSB rebate, CRA) without unnecessary jargon. |
| **Polished vs. Natural** | **4.2 / 5** | Retains genuine human rhythm, realistic ranges (*1–2 days*, *8–10 weeks*), and practical phrasing over robotic polish. |
| **Directive vs. Collaborative** | **4.0 / 5** | Emphasizes working *"alongside"* staff, regular check-ins with Executive Directors, and supporting internal teams. |

### Natural Repetition Tolerance
- **Observed Pattern:** High within operational scopes. Action verbs like `Process`, `Manage`, `Prepare`, and `Maintain` naturally repeat across adjacent bullets.
- **Evidence:** In `TACT_2026`, `Prepare` appears 3 times in payroll and reporting; in `PIRS_2025`, `Manage` and `Review` appear repeatedly across bookkeeping and transformation.
- **Rule for Future Generation:** **Do NOT force artificial synonym variation.** LLMs often attempt to avoid repeating verbs by introducing awkward synonyms (*orchestrate, execute, oversee, spearhead*). In genuine Sympl writing, repeating `Manage`, `Process`, or `Prepare` is standard, authentic, and operationally grounding.

---

## 6. Why Us Decomposition

The Why Us section must NOT be treated as a single monolithic block. It decomposes into four discrete sub-components:

### A. Stable Opening (`REF_WHY_US_OPENING`)
- **Exact Corpus Text (Present in 5/5 Why Us chunks):**  
  `Sympl Solutions is committed to ensuring a high standard of financial clarity and timely support. We bring:`
- **Stability:** Invariant (100%).
- **Recommendation:** `DETERMINISTIC` (when Why Us is selected).

### B. Stable Core Credentials (`REF_WHY_US_CREDENTIALS_BASE`)
- **Exact Corpus Text (Present in 5/5 Why Us chunks):**
  - `A responsive, detail-oriented team`
  - `Streamlined tech integration and clear process flows`
  - `Decade-long expertise in nonprofit finance` *(Note: TACT expands to `nonprofit and charity finance`)*
- **Stability:** Invariant (100%).
- **Recommendation:** `DETERMINISTIC` (when Why Us is selected).

### C. Sector & Identity Variant (`REF_WHY_US_SECTOR_VARIANT`)
- **Corpus Variants:**
  - *Arts Organizations (`RPFF_2025`, `YPT_2026`):*  
    `BIPOC-led leadership with lived experiences in community arts`  
    *(Plus sector expansion: `Experience with arts and non-profit organizations across Canada` / `Deep experience working with organizations across the arts, education, and immigration nonprofit sectors in Canada`)*
  - *Community / Social Services (`GOODFOOT_2026`, `TACT_2026`, `PIRS_2025`):*  
    `BIPOC and immigrant-led leadership with lived experiences in community, social service and arts & culture`
- **Stability:** Variant by client sector.
- **Recommendation:** `VARIANT` (Selected based on client mission).

### D. Stable Closing (`REF_WHY_US_CLOSING_1` & `REF_WHY_US_CLOSING_2`)
- **Closing Paragraph 1:**  
  `We value thoughtful system design, clarity in reporting, and building long-term trusted partnerships.` *(Present in all 5 proposals; period omitted in PIRS)*
- **Closing Paragraph 2:**  
  `Any new requirements or adjustments can be discussed and integrated as needed. We work with transparency, flexibility, and a commitment to helping our partners thrive.` *(Present in all 5 proposals)*
- **Stability:** Invariant (100%).
- **Recommendation:** `DETERMINISTIC` (when Why Us is selected).

---

## 7. Section-Specific Style & Boundary Nuances

### Payroll Style Nuance
- **Global Payroll Style:** Action-led operational bullets, specific cadence, processing/remittance orientation, year-end tax forms (T4, T4A, ROE) where scoped.
- **Variant Content:** Headcount (present in Care/Of, Cahoots, Good Foot, TACT; omitted in RPFF, PIRS), benefit deductions, WSIB (only in Good Foot), Canada Summer Jobs (RPFF, PIRS), explicit HR exclusion (only in PIRS), system migrations (TACT).
- **Boundary Rule:** Do NOT force `"We do not manage HR functions"` into all payroll sections. State it only when client requirements require an explicit boundary.

### Audit Style Nuance
- **Global Audit Tendency:** Operational preparation tasks, clear liaison boundaries, working schedule compilation, trial balance reviews.
- **Variant Content:** Formal PBC binder lists, specific auditor response turnaround (1–2 business days in PIRS vs 2 days in TACT; absent in RPFF and Good Foot), auditor meeting attendance, specific fiscal year-end dates.
- **Boundary Rule:** Do NOT universalize a 1–2 business day SLA. Concrete response windows must be sourced from current client requirements.

### Transformation Style Nuance
- **Global Transformation Tendency:** Modular, task-specific scopes focusing on practical automation (reducing manual entry, eliminating paper cheques, improving reporting).
- **Structural Variants:** Discrete numbered software initiatives (TACT), sequential phased implementation (PIRS), or broad systems exploration (RPFF, Good Foot).
- **Rule:** Do NOT force a single mandatory lifecycle. Structure transformation based on client project scope.

---

## 8. AI-Fingerprint Avoidance: What Sympl NEVER Writes

| AI-Generated Cliché / Pattern | Why It Violates Sympl Style | Preferred Sympl-Style Alternative |
| :--- | :--- | :--- |
| *"Leverage cutting-edge financial solutions"* | Marketing fluff; Sympl never uses "leverage" as a verb or "cutting-edge". | *"Configure QuickBooks Online and Plooto to automate bill payments"* |
| *"Embark on a transformative journey"* | Dramatic and theatrical; Sympl views transformation as practical workflow improvement. | *"Implement process improvements and digital tools across 12–18 weeks"* |
| *"Unlock value and drive strategic synergies"* | Corporate consultant jargon; Sympl focuses on bookkeeping accuracy and audit readiness. | *"Ensure accurate GL coding aligned with funder reporting needs"* |
| *"Empower your organization to thrive seamlessly"* | Overly emotional, hollow hype. | *"Provide reliable financial clarity and timely support for leadership"* |
| *"Robust, scalable, holistic framework"* | Generic AI filler adjectives. | Specific tool names, step numbers, and concrete deliverables. |
| Ending every bullet with a period | Violates Sympl's 95.7% no-period bullet standard. | Omit trailing periods on service bullets. |

---

## 9. Chronological Style Evolution (2025 vs. 2026)

- **Corpus Observation:** Several 2026 comprehensive proposals (`GOODFOOT`, `TACT`) display increased structural modularity, formal diagnostic openings (`CONTEXT & OBJECTIVES`), and labeled parts (Part A Ongoing Retainer, Part B Digital Transformation, Part C Audit).
- **Critical Policy:** **Increased modularity in 2026 is an observation, NOT a mandatory prescription.** Proposal architecture must be selected based on engagement archetype and client requirements, not by chronological bias.

---

## 10. Candidate Rules Architecture (Style vs. Safety)

### A. Style Rule Candidates (Prose & Syntax)

| Rule Key | Category | Description | Strength | Applies To | Evidence Proposals | Anti-Pattern |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| `RULE_DIRECT_VERB_LEAD` | Syntax | Begin service bullets with an imperative action verb. | STRONG | Service Scope Bullets | All 7 proposals | *"Sympl will manage..."*, *"Our team handles..."* |
| `RULE_NO_TRAILING_PERIOD` | Punctuation | Service scope bullets must not end with a period. | STRONG | Service Scope Bullets | All 7 proposals (95.7%) | Putting periods at the end of every bullet line. |
| `RULE_CONCISE_BULLET_LENGTH`| Length | Keep service bullets between 6 and 15 words (target average ~9 words). | STRONG | Service Scope Bullets | All 7 proposals | Long, multi-sentence narrative paragraph bullets. |
| `RULE_NO_CONSULTING_HYPE` | Tone | Never use *"leverage"*, *"unlock value"*, *"holistic"*, *"cutting-edge"*, or *"synergy"*. | HARD | Global Output | All 7 proposals | Generic AI / McKinsey marketing prose. |
| `RULE_STANDARDIZED_WHY_US` | Structure | Why Us must follow the 3-part layout: Opening promise → Core bullets → 2 closing paragraphs. | STRONG | Why Us Section | RPFF, YPT, GOODFOOT, TACT, PIRS | Rewriting Why Us into a custom sales narrative. |
| `RULE_DIAGNOSTIC_OPENING` | Structure | Comprehensive proposals should open with a diagnostic CONTEXT & OBJECTIVES section. | STRONG | Comprehensive Archetypes | GOODFOOT, TACT | Jumping straight into technical service bullets. |
| `RULE_NATURAL_REPETITION` | Lexical | Permit natural repetition of common action verbs (`Manage`, `Prepare`, `Process`) across adjacent bullets. | STRONG | Service Scope Bullets | TACT, PIRS, GOODFOOT | Awkward synonym churning (*orchestrate, spearhead*). |

---

### B. Fact & Scope Safety Rules (Zero-Tolerance Boundaries)

| Rule Key | Category | Description | Strength | Failure Example |
| :--- | :--- | :--- | :---: | :--- |
| `RULE_NO_INVENTED_CLIENT_FACTS` | Safety | Never invent client headcounts, revenue, software tools, or dates not in the prompt. | HARD | Adding 25 staff when prompt does not specify employee count. |
| `RULE_NO_INVENTED_BANK_RELEASE` | Safety | Never grant Sympl bank wire release, cheque signing, or banking authority unless source backed. | HARD | *"Sympl approves and releases all bill payments from the client bank account."* |
| `RULE_PRESERVE_PAYROLL_BOUNDARIES`| Safety | If current requirements specify explicit HR/payroll boundaries, state them; do not invent generic HR exclusions. | HARD | Hallucinating HR exclusions when not in scope, or omitting scoped client payroll cutoffs. |
| `RULE_PRESERVE_SYSTEM_STATE` | Safety | Maintain strict distinction between current systems, proposed migrations, and options under evaluation. | HARD | Asserting an evaluation platform (e.g. QBO Payroll in PIRS) is an approved target. |
| `RULE_COMMERCIAL_SAFETY_ONLY` | Safety | Software pass-through costs and backlog clean-up terms must be sourced strictly from current commercial terms. | HARD | Automatically injecting backlog fees or software exclusions into every engagement. |
| `RULE_AUDIT_SLA_SOURCE_ONLY` | Safety | Audit turnaround commitments (e.g. 1–2 business days) must come from current client scope, never reused automatically. | HARD | Copying PIRS's 1–2 day SLA into an engagement with no response commitment. |

---

## 11. Few-Shot Exemplar Matrix (Exact Database Keys)

Every chunk key listed below has been verified via direct PostgreSQL lookup against `proposal_chunks`:

| Service Family | Primary Gold Exemplar | Secondary Exemplar | Optional Third Exemplar | Selection Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Context & Objectives** | `TACT_2026_CONTEXT_OBJECTIVES` | `GOODFOOT_2026_CONTEXT_OBJECTIVES` | — | Masterclass in diagnostic framing, revenue breakdown, and operational pain point articulation. |
| **Bookkeeping** | `TACT_2026_BOOKKEEPING` | `CAREOF_2025_WEEKLY_BOOKKEEPING` | `RPFF_2025_BOOKKEEPING_RECONCILIATIONS` | TACT demonstrates comprehensive AP/AR with ED oversight; CAREOF demonstrates compact category structure. |
| **Payroll** | `TACT_2026_PAYROLL` | `PIRS_2025_PAYROLL` | `RPFF_2025_PAYROLL` | TACT shows multi-cycle complexity and deductions; PIRS shows clean manager dependency and HR exclusion notes. |
| **Financial Reporting** | `TACT_2026_FINANCIAL_REPORTING` | `GOODFOOT_2026_FINANCIAL_REPORTING` | `CAREOF_2025_FINANCIAL_REPORTING` | Clear breakdown of management vs board packages, variance analysis, and check-in cadence. |
| **Compliance & Tax** | `TACT_2026_COMPLIANCE` | `RPFF_2025_COMPLIANCE_YEAR_END` | `CAREOF_2025_COMPLIANCE_YEAR_END` | Excellent treatment of Canadian public service body (PSB) rebate and CRA year-end compliance. |
| **Audit Preparation** | `PIRS_2025_AUDIT_PREPARATION` | `TACT_2026_AUDIT_SUPPORT` | `GOODFOOT_2026_COMPLIANCE_AUDIT` | PIRS demonstrates urgent standalone audit liaison; TACT demonstrates structured 3-step annual audit support. |
| **Financial Management** | `GOODFOOT_2026_FINANCIAL_MANAGEMENT` | `PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT` | — | Controller-level oversight, cash flow modeling, and internal junior bookkeeper evaluation. |
| **Digital Transformation** | `TACT_2026_TRANSFORMATION_AP_PLOOTO` | `PIRS_2025_TRANSFORMATION_IMPLEMENTATION` | `GOODFOOT_2026_DIGITAL_TRANSFORMATION` | TACT provides initiative-based software automation; PIRS provides GL/COA system integration structures. |
| **Training & SOPs** | `PIRS_2025_TRAINING_CHANGE_MANAGEMENT` | `GOODFOOT_2026_SETUP_TRANSITION_SCOPE` | — | Direct phrasing for role-specific training sessions, quick guides, and 2-month post-go-live adoption. |
| **Transition & Interim** | `YPT_2026_CONTEXT_TRANSITION` | `YPT_2026_SYSTEMS_CONTINUITY` | `YPT_2026_ONBOARDING_SETUP` | Gold standard for handling staff leaves, shadowing outgoing personnel, and preserving existing file systems. |

---

## 12. Reference Block Candidates for Future Storage

| Candidate Key | Classification | Source Proposals | Stability | Selection Condition | Reason / Content Description |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `REF_BLOCK_WHY_US_OPENING` | **DETERMINISTIC** | RPFF, YPT, GOODFOOT, TACT, PIRS | Invariant (100%) | When Why Us section is included | Opening declaration: *"Sympl Solutions is committed to ensuring a high standard of financial clarity and timely support. We bring:"* |
| `REF_BLOCK_WHY_US_CREDENTIALS`| **DETERMINISTIC** | RPFF, YPT, GOODFOOT, TACT, PIRS | Invariant (100%) | When Why Us section is included | Base 3 core bullets (responsive team, decade-long expertise, streamlined tech). |
| `REF_BLOCK_WHY_US_SECTOR_ARTS`| **VARIANT** | RPFF, YPT | High | When client is arts/cultural nonprofit | *"BIPOC-led leadership with lived experiences in community arts"* + Canadian arts experience. |
| `REF_BLOCK_WHY_US_SECTOR_COMM`| **VARIANT** | GOODFOOT, TACT, PIRS | High | When client is community / social services | *"BIPOC and immigrant-led leadership with lived experiences in community, social service and arts & culture"*. |
| `REF_BLOCK_WHY_US_CLOSING_1` | **DETERMINISTIC** | RPFF, YPT, GOODFOOT, TACT, PIRS | Invariant (100%) | When Why Us section is included | Closing paragraph: *"We value thoughtful system design, clarity in reporting, and building long-term trusted partnerships."* |
| `REF_BLOCK_WHY_US_CLOSING_2` | **DETERMINISTIC** | RPFF, YPT, GOODFOOT, TACT, PIRS | Invariant (100%) | When Why Us section is included | Closing paragraph: *"Any new requirements or adjustments can be discussed and integrated as needed. We work with transparency, flexibility, and a commitment to helping our partners thrive."* |
| `REF_BLOCK_EXCLUSIONS_BACKLOG`| **CONDITIONAL** | CAREOF, CAHOOTS, RPFF | High | When backlog exclusion is approved | `"Bookkeeping backlog: Any prior period bookkeeping clean-up or catch-up work will be quoted separately."` |
| `REF_BLOCK_EXCLUSIONS_SOFTWARE`| **CONDITIONAL** | GOODFOOT, TACT, RPFF | High | When software costs are client-maintained | `"Note: Does not include software subscription fees. The cost of software subscriptions must be maintained by the Client."` |
| `REF_BLOCK_PAYROLL_HR_BOUNDARY`| **CONDITIONAL** | PIRS | High | When explicit HR boundary is requested | `"Note: While we manage all payroll accounting and processing, managers must provide timely payroll data... We do not manage HR functions."` |
| `REF_BLOCK_AUDIT_RESPONSE_SLA`| **DO_NOT_STANDARDIZE**| PIRS, TACT | Variable | Never automatic | Turnaround deadlines must be sourced strictly from current client intake terms. |

---

## 13. Proposed Dual-Gate Style & Safety Evaluator Design

### Gate A: Fact & Scope Safety (Pass/Fail Gate)
*Any single failure immediately rejects the draft for re-planning.*
1. **No Invented Client Facts:** Verifies client headcount, revenue, and programs strictly match prompt inputs.
2. **No Invented Systems:** Verifies only scoped software (e.g. QBO, Plooto) is named.
3. **No Invented Banking Authority:** Verifies Sympl is not assigned wire release or bank signing power.
4. **Preserve System States:** Verifies current vs proposed platforms match intake facts.
5. **No Automatic Historical SLA Insertion:** Verifies audit response times are not hallucinated.
6. **Commercial Terms Integrity:** Verifies pricing and exclusions match human inputs.

### Gate B: Sympl Writing Fidelity (Scored out of 100%)
*Target passing threshold: ≥ 90%*

| Evaluation Dimension | Recommended Weight | Failure / Low-Score Condition |
| :--- | :---: | :--- |
| **Direct Verb Lead Percentage** | **20%** | Fewer than 75% of service scope bullets start directly with an imperative action verb. |
| **AI Hype & Buzzword Avoidance**| **20%** | Presence of forbidden corporate/AI buzzwords (*leverage, unlock value, seamless, synergy, holistic*). |
| **Bullet Length & Conciseness** | **15%** | Average bullet length exceeds 16 words, or contains long narrative multi-sentence bullets. |
| **Punctuation & Formatting Integrity**| **15%** | More than 10% of service bullets end with periods; or Why Us prose blocks are converted to bullets. |
| **Vocabulary & Action Verb Match**| **10%** | Fails to use core operational verbs (`Record`, `Process`, `Maintain`, `Reconcile`, `Prepare`). |
| **Natural Repetition Tolerance**| **10%** | Uses strained, artificial synonyms to avoid repeating operational verbs. |
| **Archetype Structural Match** | **10%** | Fails to match selected archetype (e.g. adding Why Us to a compact proposal, or omitting diagnostic context from a comprehensive proposal). |
| **TOTAL** | **100%** | Passing Grade: **≥ 90%** |

---

## 14. Recommended Blind Human Test Methodology

To validate the ultimate quality target (*"a Sympl team member cannot distinguish AI-generated proposals from genuine human-written ones"*):

### Test A: Style Match (Authenticity Evaluation)
- **Design:** Present a panel of 2–3 Sympl team members with an AI-generated proposal section created from a new, fictional client intake scenario.
- **Evaluation:** Assess whether the tone, formatting, bullet rhythm, and vocabulary feel authentically "Sympl" on a 1–10 scale.
- **Requirement:** 100% fact and scope accuracy (zero hallucinated systems or bank powers).

### Test B: Real vs. Generated Discrimination (Blind Detection Test)
- **Design:** Assemble 10 randomized section pairs across Bookkeeping, Payroll, Reporting, Transformation, and Audit.
  - Pair Item 1: Real historical Sympl section (`cleaned_text`).
  - Pair Item 2: AI-generated section produced from matched intake facts.
  - De-identify client names and specific calendar dates.
- **Evaluation:** Ask reviewers: *"Which section was written by a human Sympl team member?"*
- **Success Criteria:** Reviewer discrimination accuracy near chance (~50%), demonstrating indistinguishability, paired with **zero AI buzzword flags** and **100% scope safety**.

---

## 15. Summary of Runtime Asset Classes

When transitioning to runtime implementation, assets will be formally registered under the following classes:

1. `GLOBAL_STYLE_RULE`: Invariant syntax, verb leads, conciseness, low-hype constraints.
2. `SECTION_STYLE_RULE`: Conventions specific to Bookkeeping, Payroll, Reporting, Transformation, Audit.
3. `ARCHETYPE_STYLE_RULE`: Layout rules governing Compact, Standard Nonprofit, Transition, or Comprehensive structures.
4. `FACT_SCOPE_SAFETY_RULE`: Hard constraints preventing invented facts, bank powers, or scope creep.
5. `REFERENCE_BLOCK_DETERMINISTIC`: Invariant approved text blocks (e.g. Why Us Opening and Closings).
6. `REFERENCE_BLOCK_VARIANT`: Approved text blocks tailored to client sector (e.g. Why Us sector bullets).
7. `REFERENCE_BLOCK_CONDITIONAL`: Approved text blocks injected only when scope requires (e.g. Backlog exclusion, HR boundary).
8. `FEW_SHOT_EXEMPLAR`: Verified database chunk keys retrieved dynamically during generation.

---
*End of Evidence-Hardened Specification. Ready for Runtime Architecture Implementation.*
