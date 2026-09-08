# Sympl Proposal RAG — n8n Data Mapping Specification

This document defines the field-level transformation mapping between CRM source records (e.g., HubSpot / Salesforce), intermediate n8n execution variables, and the target Sympl Proposal RAG API payload (`sympl_planner.schema.ClientInput`).

---

## 1. Field Transformation Matrix

```
┌─────────────────────────────────┬─────────────────────────────────┬───────────────────────────────────┐
│ CRM SOURCE FIELD (HubSpot)      │ n8n INTERMEDIATE VARIABLE       │ SYMPL API PAYLOAD PATH            │
├─────────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┤
│ Company: Name                   │ $json.client_name               │ organization.name                 │
│ Company: Organization Type      │ $json.organization_type         │ organization.organization_type    │
│ Company: Industry / Sector      │ $json.sector                    │ organization.sector               │
│ Deal: Description / Scope Notes │ $json.description               │ organization.description          │
│ Deal: Current Accounting Tech   │ $json.current_systems           │ organization.current_systems      │
│ Deal: Target Systems            │ $json.target_systems            │ organization.target_systems       │
│ Deal: Engagement Type           │ $json.engagement_type           │ engagement.engagement_type        │
│ Deal: Complexity Level          │ $json.complexity                │ engagement.complexity             │
│ Form: Approved Services (Array) │ $json.approved_families         │ approved_scope.<family>           │
│ Form: Bookkeeping Cadence       │ $json.bk_cadence                │ approved_scope.bookkeeping.cadence│
│ Form: Bookkeeping AP/AR         │ $json.bk_ap_ar                  │ approved_scope.bookkeeping.ap_ar  │
│ Form: Bookkeeping Reconcile     │ $json.bk_reconcile              │ approved_scope.bookkeeping.reconciliations│
│ Form: Catchup Cleanup Approved  │ $json.bk_catchup                │ approved_scope.bookkeeping.catchup_cleanup│
│ Form: Payroll Cadence           │ $json.pr_cadence                │ approved_scope.payroll.cadence    │
│ Form: Employee Headcount        │ $json.pr_headcount_emp          │ approved_scope.payroll.headcount_employees│
│ Form: Contractor Headcount      │ $json.pr_headcount_ctr          │ approved_scope.payroll.headcount_contractors│
│ Form: Reporting Cadence         │ $json.rep_cadence               │ approved_scope.financial_reporting.cadence│
│ Form: GST/HST Filing Required   │ $json.comp_gst                  │ approved_scope.compliance.gst_hst_filing│
│ Form: Pricing Model             │ $json.pricing_model             │ commercial_terms.pricing_model    │
│ Form: Monthly Retainer Quote    │ $json.monthly_retainer          │ commercial_terms.monthly_retainer │
│ Form: Implementation Setup Fee  │ $json.setup_fee                 │ commercial_terms.setup_fee        │
│ Form: Billing Schedule          │ $json.billing_schedule          │ commercial_terms.billing_schedule │
│ Deal: Competitive Pitch Flag    │ $json.is_competitive            │ preferences.is_competitive_pitch  │
│ Deal: Include Why Us Section    │ $json.include_why_us            │ preferences.include_why_us        │
└─────────────────────────────────┴─────────────────────────────────┴───────────────────────────────────┘
```

---

## 2. End-to-End JSON Transformation Example

### Step A: Raw Inbound CRM / Webhook Record
```json
{
  "deal_id": "893410291",
  "company_name": "High Park Community Hub",
  "company_type": "nonprofit",
  "sector": "community_services",
  "summary": "Community center requiring ongoing accounting support and cleanup.",
  "tech_stack": "QuickBooks Desktop",
  "approved_services": ["bookkeeping", "payroll", "financial_reporting"],
  "bk_frequency": "monthly",
  "bk_ar_ap_needed": true,
  "bk_catchup_allowed": false,
  "payroll_cadence": "semi_monthly",
  "employees": 14,
  "contractors": 4,
  "pricing_type": "fixed_retainer",
  "retainer_cad": 2400.0,
  "setup_fee_cad": 1500.0,
  "include_credentials": true
}
```

---

### Step B: n8n Normalization Logic (JavaScript Node)
```javascript
// Executed in n8n 'Scope Firewall Audit Guard' Node
const crm = $input.first().json;

// Mandatory Scope Firewall: Build approved_scope explicitly
const approved_scope = {};

if (crm.approved_services.includes("bookkeeping")) {
  approved_scope.bookkeeping = {
    cadence: crm.bk_frequency || "monthly",
    ap_ar: Boolean(crm.bk_ar_ap_needed),
    reconciliations: true,
    expense_management: true,
    catchup_cleanup: Boolean(crm.bk_catchup_allowed) // Explicit human decision
  };
}

if (crm.approved_services.includes("payroll")) {
  approved_scope.payroll = {
    cadence: crm.payroll_cadence || "semi_monthly",
    headcount_employees: Number(crm.employees) || 0,
    headcount_contractors: Number(crm.contractors) || 0,
    sympl_processes_payroll: true,
    manager_input_responsibility: true,
    hr_functions_excluded: true
  };
}

if (crm.approved_services.includes("financial_reporting")) {
  approved_scope.financial_reporting = {
    cadence: "monthly",
    funder_tracking: false,
    board_package: true,
    budget_vs_actual: true
  };
}

// Compile target API payload
return {
  json: {
    client_id: `client_hub_${crm.deal_id}`,
    organization: {
      name: crm.company_name,
      organization_type: crm.company_type || "nonprofit",
      sector: crm.sector || "community_services",
      description: crm.summary || "",
      current_systems: crm.tech_stack ? [crm.tech_stack] : [],
      target_systems: ["QuickBooks Online", "Plooto"]
    },
    engagement: {
      engagement_type: "recurring",
      complexity: "standard",
      diagnostic_focus: ["internal_controls"]
    },
    requested_scope: {
      // Historical request retained for audit comparison only
      bookkeeping: {
        cadence: "monthly",
        catchup_cleanup: true // Client originally asked for cleanup
      }
    },
    approved_scope: approved_scope, // The ONLY scope used by backend
    commercial_terms: {
      pricing_model: crm.pricing_type || "fixed_retainer",
      currency: "CAD",
      monthly_retainer: crm.retainer_cad ? Number(crm.retainer_cad) : null,
      setup_fee: crm.setup_fee_cad ? Number(crm.setup_fee_cad) : null,
      billing_schedule: "monthly_in_advance",
      include_backlog_exclusion: !crm.bk_catchup_allowed,
      software_fees_excluded: true
    },
    preferences: {
      include_why_us: crm.include_credentials !== false,
      is_competitive_pitch: false,
      is_trusted_continuity: true,
      identity_credential_preference: "community_social"
    }
  }
};
```

---

### Step C: Validated Sympl API Payload (`POST /proposal/generate/async`)
```json
{
  "client_id": "client_hub_893410291",
  "organization": {
    "name": "High Park Community Hub",
    "organization_type": "nonprofit",
    "sector": "community_services",
    "description": "Community center requiring ongoing accounting support and cleanup.",
    "current_systems": ["QuickBooks Desktop"],
    "target_systems": ["QuickBooks Online", "Plooto"]
  },
  "engagement": {
    "engagement_type": "recurring",
    "complexity": "standard",
    "diagnostic_focus": ["internal_controls"]
  },
  "requested_scope": {
    "bookkeeping": {
      "cadence": "monthly",
      "catchup_cleanup": true
    }
  },
  "approved_scope": {
    "bookkeeping": {
      "cadence": "monthly",
      "ap_ar": true,
      "reconciliations": true,
      "expense_management": true,
      "catchup_cleanup": false
    },
    "payroll": {
      "cadence": "semi_monthly",
      "headcount_employees": 14,
      "headcount_contractors": 4,
      "sympl_processes_payroll": true,
      "manager_input_responsibility": true,
      "hr_functions_excluded": true
    },
    "financial_reporting": {
      "cadence": "monthly",
      "funder_tracking": false,
      "board_package": true,
      "budget_vs_actual": true
    }
  },
  "commercial_terms": {
    "pricing_model": "fixed_retainer",
    "currency": "CAD",
    "monthly_retainer": 2400.0,
    "setup_fee": 1500.0,
    "billing_schedule": "monthly_in_advance",
    "include_backlog_exclusion": true,
    "software_fees_excluded": true
  },
  "preferences": {
    "include_why_us": true,
    "is_competitive_pitch": false,
    "is_trusted_continuity": true,
    "identity_credential_preference": "community_social"
  }
}
```

---

## 3. Scope Container Mapping Reference

Each service family maps to its respective typed dataclass in `sympl_planner.schema`:

### Bookkeeping Scope (`BookkeepingScope`)
- `cadence`: `"weekly"` | `"biweekly"` | `"monthly"` | `"quarterly"` (Default: `"monthly"`)
- `ap_ar`: `boolean` (Accounts payable / Accounts receivable processing)
- `reconciliations`: `boolean` (Bank & credit card account reconciliations)
- `expense_management`: `boolean` (Receipt processing, Dext/Hubdoc integration)
- `catchup_cleanup`: `boolean` (Historical catch-up cleanup — defaults to `false` unless explicitly approved)

### Payroll Scope (`PayrollScope`)
- `cadence`: `"weekly"` | `"biweekly"` | `"semi_monthly"` | `"monthly"` (Default: `"semi_monthly"`)
- `headcount_employees`: `integer` (T4 employee count)
- `headcount_contractors`: `integer` (T4A / independent contractor count)
- `sympl_processes_payroll`: `boolean` (Sympl submits pay runs)
- `manager_input_responsibility`: `boolean` (Client approves timesheets)
- `hr_functions_excluded`: `boolean` (HR policy/disputes explicitly excluded)

### Financial Reporting Scope (`ReportingScope`)
- `cadence`: `"monthly"` | `"quarterly"` | `"annual"` (Default: `"monthly"`)
- `funder_tracking`: `boolean` (Restricted fund/grant allocation tracking)
- `class_department_tracking`: `boolean` (Departmental segment reporting)
- `board_package`: `boolean` (Board of Directors financial review package)
- `budget_vs_actual`: `boolean` (Variance tracking against annual budget)

### Compliance Scope (`ComplianceScope`)
- `gst_hst_filing`: `boolean` (GST/HST periodic returns)
- `t3010_support`: `boolean` (Registered Charity Information Return assistance)
- `audit_support`: `boolean` (Year-end external audit preparation & liaison)
- `audit_response_sla`: `string` | `null` (e.g. `"1-2 business days"`)

### Digital Transformation Scope (`TransformationScope`)
- `system_migrations`: `list[string]` (e.g. `["QuickBooks Desktop to QBO"]`)
- `workflow_redesign`: `boolean` (Financial workflow modernization)
- `integration_milestones`: `list[string]`
- `implementation_phases`: `list[string]`

### Training Scope (`TrainingScope`)
- `target_roles`: `list[string]` (e.g. `["Program Managers", "Bookkeeper"]`)
- `format`: `"remote"` | `"onsite"` | `"hybrid"`
- `sop_documentation`: `boolean` (Standard operating procedure authoring)

### Transition Scope (`TransitionScope`)
- `onboarding_duration_weeks`: `integer` (Default: `4`)
- `historical_access`: `boolean` (Read-only access to legacy records)
- `handover_continuity`: `boolean` (Structured handover protocol)

---

## 4. Context Enrichment Mapping Reference

To support rich client storytelling and consultative proposal generation without requiring a full CRM implementation, the proposal intake schema supports optional high-value narrative and operational fields.

### 4.1 Narrative Context Fields (`sympl_planner.schema.ClientNarrativeContext`)

| Intake Field | Type | Importance | Description |
| :--- | :--- | :--- | :--- |
| `client_situation_summary` | `string` | **High (15 pts)** | Background story, organizational lifecycle, or administrative transition context |
| `client_challenges_summary` | `string` | **High (15 pts)** | Core pain points, operational backlogs, compliance risks, or internal bottlenecks |
| `current_finance_challenges` | `list[string]` | **High (15 pts)** | Specific financial symptoms (e.g. 4-month reconciliation backlog, manual checks) |
| `organization_description` | `string` | **High (10 pts)** | What the client does, their mission, community impact, or core business |
| `reason_for_engagement` | `string` | **High (10 pts)** | Why the client is hiring Sympl right now (catalyst for change) |
| `desired_outcomes` | `list[string]` | **High (10 pts)** | Client's explicit success criteria (e.g., audit-readiness, paperless migration) |
| `industry_context` | `string` | Low | Specific regulatory or funder requirements for client's industry |
| `client_priorities` | `list[string]` | Low | Ordered ranking of immediate priorities (e.g., rapid catch-up, payroll continuity) |

### 4.2 Structured & Operational Context Fields

| Intake Field | Type | Weight | Target Path |
| :--- | :--- | :--- | :--- |
| `current_accounting_system` | `string` | 5 pts | `client_context.current_accounting_system` |
| `current_finance_process` | `string` | 5 pts | `client_context.current_finance_process` |
| `current_finance_team_structure`| `string` | (shared) | `client_context.current_finance_team_structure` |
| `employee_count` / `org_size`  | `int`/`str`| 5 pts | `client_context.employee_count` / `org_size` |
| `service_context.bookkeeping.*`| `object` | 10 pts | `approved_scope.bookkeeping.*` |
| `service_context.payroll.*`    | `object` | (shared) | `approved_scope.payroll.*` |
| `service_context.reporting.*`  | `object` | (shared) | `approved_scope.financial_reporting.*` |
| `service_context.compliance.*` | `object` | (shared) | `approved_scope.compliance.*` |

---

## 5. Context Quality Scoring Matrix & Classification

The intake pipeline automatically scores inbound context on a 0–100 weighted scale:
- **Narrative Fields (75%)**: 6 core narrative fields drive consultative voice and storytelling.
- **Structured Fields (25%)**: Current systems, processes, scale, and operational specifics.

### Quality Thresholds
- **`HIGH` (70–100 pts)**: Rich context available. Writer generates deeply tailored, consultative narrative.
- **`MEDIUM` (30–69 pts)**: Standard context available. Sufficient for customized service delivery.
- **`LOW` (0–29 pts)**: Minimal/legacy payload. Pipeline generates valid proposals but logs a warning: `Low proposal intake context quality (<score>/100)`.

---

## 6. Enriched Payload Example (OldT Needs Assessment)

```json
{
  "client_name": "OldT Community Arts Workshop",
  "organization_type": "nonprofit",
  "sector": "arts_culture",
  "client_situation_summary": "Mid-sized arts and cultural organization undergoing a key administrative transition following the departure of their long-time in-house bookkeeper. Operations span seasonal performance productions and educational workshops.",
  "client_challenges_summary": "Accumulated backlog of 4 months in vendor payments and credit card reconciliations. Financial records reside in legacy desktop software with high reliance on paper receipts and manual approvals, creating risk for upcoming annual grant compliance deadlines.",
  "organization_description": "Nonprofit performing arts company dedicated to innovative puppetry, community youth workshops, and multidisciplinary theatrical productions.",
  "industry_context": "Charitable arts and culture sector with complex multi-funder grant tracking requirements (Canada Council for the Arts, provincial, and municipal arts councils).",
  "employee_count": 16,
  "organization_size": "medium",
  "annual_budget_or_revenue_range": "$1.2M - $1.8M",
  "current_accounting_system": "Sage 50 Desktop",
  "current_finance_process": "Paper invoice approvals, manual check printing, physical receipt envelopes, spreadsheet-based budget tracking.",
  "current_finance_team_structure": "1 departing part-time bookkeeper, Managing Director handling approvals and grant reporting, external CPA firm handling year-end compilation.",
  "current_finance_challenges": [
    "4-month backlog in reconciliations and vendor disbursements",
    "Lack of real-time visibility into production budgets and grant drawdowns",
    "Heavy reliance on paper processes hindering remote collaboration"
  ],
  "reason_for_engagement": "Transition from vulnerable single in-house bookkeeper model to a modern, reliable outsourced managed accounting partner with robust internal controls.",
  "desired_outcomes": [
    "Catch-up and clean reconciliation of prior 4 months of records",
    "Seamless migration to QuickBooks Online and Dext for paperless workflow",
    "Audit-ready financial statements and quarterly board reporting packages",
    "Consistent, timely bi-weekly payroll for core staff and seasonal guest artists"
  ],
  "client_priorities": [
    "Rapid catch-up cleanup before upcoming fiscal year-end",
    "Seamless artist payroll continuity",
    "Funder-compliant grant tracking"
  ],
  "approved_scope": {
    "bookkeeping": {
      "cadence": "weekly",
      "ap_ar": true,
      "reconciliations": true,
      "expense_management": true,
      "catchup_cleanup": true
    },
    "payroll": {
      "cadence": "biweekly",
      "headcount_employees": 12,
      "headcount_contractors": 4,
      "sympl_processes_payroll": true
    },
    "financial_reporting": {
      "cadence": "monthly",
      "funder_tracking": true,
      "board_package": true,
      "budget_vs_actual": true
    },
    "compliance": {
      "gst_hst_filing": true,
      "audit_support": true
    }
  },
  "service_context": {
    "bookkeeping": {
      "bookkeeping_volume": "150-250 monthly transactions across 3 operating accounts",
      "bookkeeping_frequency": "weekly",
      "ap_ar_requirements": "Bi-weekly vendor check runs and EFT payments, quarterly customer box-office invoicing",
      "reconciliation_requirements": "3 bank accounts, 2 credit cards, and PayPal box-office gateway monthly",
      "cleanup_requirements": "Complete catch-up cleanup for FY2025 Q3 and Q4"
    },
    "payroll": {
      "employee_count_for_payroll": 16,
      "payroll_frequency": "biweekly",
      "current_payroll_system": "Manual bank EFT and spreadsheet calculations",
      "payroll_transition_requirements": "Parallel run for 1 pay period, ROE preparation for seasonal contract staff"
    },
    "reporting": {
      "reporting_requirements": "Monthly departmental P&L, balance sheet, and grant drawdown reports",
      "board_reporting_requirements": "Quarterly board governance package delivered by 15th of following month",
      "budgeting_requirements": "Production-level budget vs actual variance analysis"
    },
    "compliance": {
      "compliance_requirements": "Quarterly GST/HST filings, annual T3010 charity return coordination",
      "regulatory_requirements": "Funder audit compliance and grant expenditure certification"
    }
  },
  "commercial_terms": {
    "pricing_model": "fixed_retainer",
    "currency": "CAD",
    "monthly_retainer": 3200.0,
    "setup_fee": 1500.0
  }
}
```
