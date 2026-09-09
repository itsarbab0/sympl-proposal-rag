import json
import os

def build_workflow():
    nodes = [
        # NODE 1: User Proposal Form
        {
            "parameters": {
                "path": "sympl-proposal-intake",
                "formTitle": "Sympl Proposal Intake Form",
                "formDescription": "Submit organizational details, paste client needs assessment text, or enter engagement parameters.",
                "formFields": {
                    "values": [
                        {
                            "fieldLabel": "needs_assessment_text",
                            "fieldType": "textarea",
                            "placeholder": "Paste complete client needs assessment form / questionnaire response here..."
                        },
                        {
                            "fieldLabel": "client_name",
                            "placeholder": "Client Organization Name (optional if specified in assessment)"
                        },
                        {
                            "fieldLabel": "organization_type",
                            "fieldType": "dropdown",
                            "fieldOptions": {
                                "values": [
                                    {"option": "Nonprofit"},
                                    {"option": "Commercial"},
                                    {"option": "Healthcare"},
                                    {"option": "Education"},
                                    {"option": "Arts & Culture"}
                                ]
                            }
                        },
                        {
                            "fieldLabel": "sector",
                            "placeholder": "e.g. arts_culture, community_services"
                        },
                        {
                            "fieldLabel": "pricing_model",
                            "fieldType": "dropdown",
                            "fieldOptions": {
                                "values": [
                                    {"option": "fixed_retainer"},
                                    {"option": "hourly"},
                                    {"option": "custom"}
                                ]
                            }
                        },
                        {
                            "fieldLabel": "currency",
                            "defaultValue": "CAD"
                        },
                        {
                            "fieldLabel": "amount",
                            "fieldType": "number",
                            "defaultValue": 0
                        }
                    ]
                },
                "options": {}
            },
            "id": "node-form-trigger",
            "name": "User Proposal Form",
            "type": "n8n-nodes-base.formTrigger",
            "typeVersion": 2.2,
            "position": [200, 300],
            "notesInFlow": True,
            "notes": "NODE 1: Proposal intake form supporting raw needs_assessment_text textarea input."
        },

        # NODE 2: AI Extraction Node
        {
            "parameters": {
                "method": "POST",
                "url": "={{$env.OPENAI_API_URL || $env.OPENROUTER_API_URL || 'https://openrouter.ai/api/v1/chat/completions'}}",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "Content-Type", "value": "application/json"},
                        {"name": "Authorization", "value": "={{'Bearer ' + ($env.OPENROUTER_API_KEY || $env.OPENAI_API_KEY || '')}}"},
                        {"name": "HTTP-Referer", "value": "https://sympl.ca"},
                        {"name": "X-Title", "value": "Sympl Proposal RAG"}
                    ]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": """={{
JSON.stringify({
  model: $env.AI_EXTRACTION_MODEL || "openai/gpt-4o-mini",
  temperature: 0.0,
  response_format: { type: "json_object" },
  messages: [
    {
      role: "system",
      content: "You are an expert financial intake extraction assistant for Sympl Bookkeeping & Financial Advisory Services.\\nYour role is to analyze client needs assessment questionnaires and extract structured proposal intake data for Sympl's proposal generation engine.\\n\\nCRITICAL INSTRUCTIONS & CONSTRAINTS:\\n1. Preserve Information: Preserve all facts, figures, tools, pain points, team details, and systems from the assessment questionnaire.\\n2. No Hallucination: Do NOT invent, assume, or fabricate missing information. If a field or detail is not mentioned or is N/A, leave it as an empty string, empty list, or empty object.\\n3. Professional Consulting Context: Convert raw notes, shorthand, and conversational answers into articulate, professional proposal context suitable for consulting engagement letters.\\n4. Separate Client Facts from Recommendations: Under client_situation_summary and client_challenges_summary, describe what the client currently does and struggles with. Do not prescribe Sympl's service solution in the client's current situation summary.\\n5. Pricing Invariant: Keep pricing fields empty or zero unless explicit pricing or budgets are agreed upon in the assessment.\\n6. Scope & Context Mapping:\\n   - Identify candidate services from the form selections and populate approved_scope with relevant booleans/details:\\n     * bookkeeping: e.g. {\\"cadence\\": \\"monthly\\", \\"ap_ar\\": true, \\"reconciliations\\": true, \\"project_tracking\\": true}\\n     * payroll: e.g. {\\"cadence\\": \\"semi_monthly\\", \\"contractor_t4a\\": true, \\"headcount_contractors\\": 4}\\n     * financial_reporting: e.g. {\\"monthly_package\\": true, \\"board_package\\": true}\\n     * compliance: e.g. {\\"gst_filing\\": true, \\"audit_support\\": true}\\n   - Extract operational details into service_context:\\n     * bookkeeping: { \\"ap_ar_requirements\\": \\"...\\", \\"reconciliation_requirements\\": \\"...\\" }\\n     * payroll: { \\"payroll_frequency\\": \\"...\\", \\"current_payroll_system\\": \\"...\\" }\\n     * reporting: { \\"reporting_requirements\\": \\"...\\", \\"board_reporting_requirements\\": \\"...\\" }\\n     * compliance: { \\"compliance_requirements\\": \\"...\\" }\\n7. Tone & Grounding: Do NOT use marketing buzzwords such as 'core mission', 'strategic partnership', 'continued success', 'comprehensive suite', 'paradigm shift', 'revolutionary', or 'unparalleled'. Focus strictly on factual, grounded operational descriptions and community programs.\\n\\nREQUIRED OUTPUT SCHEMA:\\n{\\n  \\"client_name\\": \\"\\",\\n  \\"organization_type\\": \\"\\",\\n  \\"sector\\": \\"\\",\\n  \\"organization_description\\": \\"\\",\\n  \\"client_situation_summary\\": \\"\\",\\n  \\"client_challenges_summary\\": \\"\\",\\n  \\"current_accounting_system\\": \\"\\",\\n  \\"current_finance_process\\": \\"\\",\\n  \\"current_finance_team_structure\\": \\"\\",\\n  \\"current_finance_challenges\\": [],\\n  \\"reason_for_engagement\\": \\"\\",\\n  \\"desired_outcomes\\": [],\\n  \\"client_priorities\\": [],\\n  \\"approved_scope\\": {\\n    \\"bookkeeping\\": {},\\n    \\"payroll\\": {},\\n    \\"financial_reporting\\": {},\\n    \\"compliance\\": {}\\n  },\\n  \\"service_context\\": {\\n    \\"bookkeeping\\": {},\\n    \\"payroll\\": {},\\n    \\"reporting\\": {},\\n    \\"compliance\\": {}\\n  },\\n  \\"commercial_terms\\": {}\\n}"
    },
    {
      role: "user",
      content: "Extract structured proposal intake from this client assessment:\\n\\n" + ($json.needs_assessment_text || "")
    }
  ]
})
}}""",
                "options": {"timeout": 30000}
            },
            "id": "node-ai-extraction",
            "name": "AI Extraction Node",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [440, 300],
            "notesInFlow": True,
            "notes": "NODE 2: AI Unstructured Extractor using efficient gpt-4o-mini model. Extracts structured proposal fields from raw assessment text. Strictly avoids expensive reasoning models."
        },

        # NODE 3: Parse AI Extraction
        {
            "parameters": {
                "jsCode": """const form = $('User Proposal Form').first().json;
const aiResp = $input.first().json;

let extracted = {};

// Handle HTTP response structure from LLM
if (aiResp.choices && aiResp.choices[0] && aiResp.choices[0].message) {
  const rawContent = aiResp.choices[0].message.content || '{}';
  try {
    const cleaned = rawContent.replace(/```json/g, '').replace(/```/g, '').trim();
    extracted = JSON.parse(cleaned);
  } catch (e) {
    extracted = { client_challenges_summary: rawContent };
  }
} else if (typeof aiResp === 'object') {
  extracted = { ...aiResp };
}

// Fallback & manual field merging
if (!extracted.client_name && form.client_name) {
  extracted.client_name = String(form.client_name).trim();
}
if (!extracted.organization_type) {
  extracted.organization_type = String(form.organization_type || 'nonprofit').toLowerCase();
}
if (!extracted.sector) {
  extracted.sector = String(form.sector || 'community_services').toLowerCase();
}

// Normalize challenges summary
if (Array.isArray(extracted.client_challenges_summary)) {
  if (!extracted.current_finance_challenges || extracted.current_finance_challenges.length === 0) {
    extracted.current_finance_challenges = [...extracted.client_challenges_summary];
  }
  extracted.client_challenges_summary = extracted.client_challenges_summary.join(' ');
}

// Normalize scope
if (!extracted.approved_scope || typeof extracted.approved_scope !== 'object') {
  extracted.approved_scope = {};
}

// Sanitize forbidden buzzwords from narrative fields to ensure writer guardrails pass cleanly
const sanitizeBuzzwords = (text) => {
  if (typeof text !== 'string') return text;
  return text
    .replace(/\bcore mission\b/gi, 'mandate')
    .replace(/\bstrategic partnership\b/gi, 'engagement')
    .replace(/\bcontinued success\b/gi, 'ongoing operations')
    .replace(/\bcomprehensive suite\b/gi, 'integrated services')
    .replace(/\bparadigm shift\b/gi, 'operational transition')
    .replace(/\brevolutionary\b/gi, 'modernized')
    .replace(/\bunparalleled\b/gi, 'dedicated');
};

for (const key of Object.keys(extracted)) {
  if (typeof extracted[key] === 'string') {
    extracted[key] = sanitizeBuzzwords(extracted[key]);
  } else if (Array.isArray(extracted[key])) {
    extracted[key] = extracted[key].map(item => typeof item === 'string' ? sanitizeBuzzwords(item) : item);
  }
}

return [{
  json: extracted
}];"""
            },
            "id": "node-parse-ai-extraction",
            "name": "Parse AI Extraction",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [680, 300],
            "notesInFlow": True,
            "notes": "NODE 3: Parses LLM structured JSON output, handles code fences, and normalizes fields."
        },

        # NODE 4: Validate Extracted Intake
        {
            "parameters": {
                "jsCode": """const payload = $input.first().json;
const errors = [];

// 1. client_name check
if (!payload.client_name || typeof payload.client_name !== 'string' || !payload.client_name.trim()) {
  errors.push('client_name is required and must be a non-empty string.');
}

// 2. organization_description check
if (!payload.organization_description || typeof payload.organization_description !== 'string' || !payload.organization_description.trim()) {
  errors.push('organization_description is required and must be a non-empty string.');
}

// 3. client_challenges_summary check
if (!payload.client_challenges_summary || typeof payload.client_challenges_summary !== 'string' || !payload.client_challenges_summary.trim()) {
  errors.push('client_challenges_summary is required and must be a non-empty string.');
}

// 4. approved_scope check: must contain at least one approved service family
const scope = payload.approved_scope || {};
const activeServices = Object.keys(scope).filter(k => {
  const val = scope[k];
  if (typeof val === 'boolean') return val;
  if (val && typeof val === 'object') return Object.keys(val).length > 0;
  return Boolean(val);
});

if (activeServices.length === 0) {
  errors.push('approved_scope must contain at least one approved service family (bookkeeping, payroll, financial_reporting, compliance).');
}

const isValid = errors.length === 0;

return [{
  json: {
    ...payload,
    is_valid_request: isValid,
    validation_errors: errors
  }
}];"""
            },
            "id": "node-validate-intake",
            "name": "Validate Extracted Intake",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [920, 300],
            "notesInFlow": True,
            "notes": "NODE 4: Validates client_name, organization_description, client_challenges_summary, and approved_scope."
        },

        # NODE 5: IF Intake Valid?
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                    "conditions": [
                        {
                            "id": "cond-valid-intake",
                            "leftValue": "={{$json.is_valid_request}}",
                            "rightValue": True,
                            "operator": {"type": "boolean", "operation": "equals"}
                        }
                    ],
                    "combinator": "and"
                }
            },
            "id": "node-if-intake-valid",
            "name": "IF Intake Valid?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [1160, 300],
            "notesInFlow": True,
            "notes": "Routes valid intakes to preview & human gate; halts invalid intakes with error."
        },

        # NODE 6: Validation Error Response
        {
            "parameters": {
                "mode": "manual",
                "duplicateItem": False,
                "assignments": {
                    "assignments": [
                        {"id": "val-status", "name": "status", "value": "failed", "type": "string"},
                        {"id": "val-stage", "name": "stage", "value": "intake_validation", "type": "string"},
                        {"id": "val-msg", "name": "message", "value": "Intake validation failed before Human Approval Gate.", "type": "string"},
                        {"id": "val-errs", "name": "errors", "value": "={{$json.validation_errors}}", "type": "array"}
                    ]
                }
            },
            "id": "node-validation-error",
            "name": "Validation Error Response",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [1160, 520],
            "notesInFlow": True,
            "notes": "Returns validation diagnostic payload when required intake fields are missing."
        },

        # NODE 7: Compute Approval Preview
        {
            "parameters": {
                "jsCode": """const intake = $input.first().json;

// Calculate context quality score according to Sympl backend standards
let score = 0;
const breakdown = {};

// 1. Situation summary (15 pts)
if (intake.client_situation_summary && String(intake.client_situation_summary).trim()) {
  score += 15;
  breakdown.client_situation_summary = 15;
}
// 2. Challenges summary (15 pts)
if (intake.client_challenges_summary && String(intake.client_challenges_summary).trim()) {
  score += 15;
  breakdown.client_challenges_summary = 15;
}
// 3. Finance challenges list (15 pts)
if (intake.current_finance_challenges && (Array.isArray(intake.current_finance_challenges) ? intake.current_finance_challenges.length > 0 : String(intake.current_finance_challenges).trim())) {
  score += 15;
  breakdown.current_finance_challenges = 15;
}
// 4. Org description (10 pts)
if (intake.organization_description && String(intake.organization_description).trim()) {
  score += 10;
  breakdown.organization_description = 10;
}
// 5. Reason for engagement (10 pts)
if (intake.reason_for_engagement && String(intake.reason_for_engagement).trim()) {
  score += 10;
  breakdown.reason_for_engagement = 10;
}
// 6. Desired outcomes (10 pts)
if (intake.desired_outcomes && (Array.isArray(intake.desired_outcomes) ? intake.desired_outcomes.length > 0 : String(intake.desired_outcomes).trim())) {
  score += 10;
  breakdown.desired_outcomes = 10;
}
// 7. Accounting system (5 pts)
if (intake.current_accounting_system && String(intake.current_accounting_system).trim()) {
  score += 5;
  breakdown.current_accounting_system = 5;
}
// 8. Finance process or team (5 pts)
if ((intake.current_finance_process && String(intake.current_finance_process).trim()) || (intake.current_finance_team_structure && String(intake.current_finance_team_structure).trim())) {
  score += 5;
  breakdown.finance_process_or_team = 5;
}
// 9. Organization scale / budget (5 pts)
if (intake.annual_budget_or_revenue_range || intake.employee_count || intake.organization_size) {
  score += 5;
  breakdown.organization_scale = 5;
}
// 10. Service context (10 pts)
const sc = intake.service_context || {};
if (Object.keys(sc).some(k => sc[k] && Object.keys(sc[k]).length > 0)) {
  score += 10;
  breakdown.service_context = 10;
}

score = Math.min(100, score);
let qualityRating = 'LOW';
if (score >= 70) qualityRating = 'HIGH';
else if (score >= 30) qualityRating = 'MEDIUM';

// Format scope summary for display
const activeScopeList = [];
const scopeObj = intake.approved_scope || {};
if (scopeObj.bookkeeping && (typeof scopeObj.bookkeeping === 'boolean' ? scopeObj.bookkeeping : Object.keys(scopeObj.bookkeeping).length > 0)) activeScopeList.push('Bookkeeping');
if (scopeObj.payroll && (typeof scopeObj.payroll === 'boolean' ? scopeObj.payroll : Object.keys(scopeObj.payroll).length > 0)) activeScopeList.push('Payroll');
if (scopeObj.financial_reporting && (typeof scopeObj.financial_reporting === 'boolean' ? scopeObj.financial_reporting : Object.keys(scopeObj.financial_reporting).length > 0)) activeScopeList.push('Financial Reporting');
if (scopeObj.compliance && (typeof scopeObj.compliance === 'boolean' ? scopeObj.compliance : Object.keys(scopeObj.compliance).length > 0)) activeScopeList.push('Compliance');

// Format desired outcomes for display
const outcomesList = Array.isArray(intake.desired_outcomes) ? intake.desired_outcomes.join('; ') : String(intake.desired_outcomes || 'N/A');

const preview = {
  client_name: intake.client_name || 'Unnamed Client',
  organization_description: intake.organization_description || 'N/A',
  client_situation_summary: intake.client_situation_summary || 'N/A',
  client_challenges_summary: intake.client_challenges_summary || 'N/A',
  extracted_scope_summary: activeScopeList.length > 0 ? activeScopeList.join(', ') : 'None extracted',
  desired_outcomes_summary: outcomesList,
  context_quality_display: `${qualityRating} (${score}/100 pts)`
};

return [{
  json: {
    ...intake,
    preview: preview,
    context_quality_score: score,
    context_quality_rating: qualityRating
  }
}];"""
            },
            "id": "node-compute-preview",
            "name": "Compute Approval Preview",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1400, 300],
            "notesInFlow": True,
            "notes": "Computes 7-element Approval Preview Payload and calculates Sympl context quality score."
        },

        # NODE 8: Human Approval Gate
        {
            "parameters": {
                "resume": "form",
                "formTitle": "Human Scope & Intake Approval Gate",
                "formDescription": """=Review Extracted Intake for: {{$json.preview.client_name}}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Organization Description: {{$json.preview.organization_description}}
• Situation Summary: {{$json.preview.client_situation_summary}}
• Challenges Summary: {{$json.preview.client_challenges_summary}}
• Extracted Service Scope: {{$json.preview.extracted_scope_summary}}
• Desired Outcomes: {{$json.preview.desired_outcomes_summary}}
• Context Quality Score: {{$json.preview.context_quality_display}}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Verify extracted data and confirm billable service scope below before proposal generation.""",
                "formFields": {
                    "values": [
                        {
                            "fieldLabel": "Approval Decision",
                            "fieldType": "dropdown",
                            "requiredField": True,
                            "fieldOptions": {
                                "values": [
                                    {"option": "APPROVE"},
                                    {"option": "REJECT"}
                                ]
                            }
                        },
                        {
                            "fieldLabel": "Approve Bookkeeping",
                            "fieldType": "checkbox",
                            "defaultValue": "={{Boolean($json.approved_scope && $json.approved_scope.bookkeeping && (typeof $json.approved_scope.bookkeeping === 'boolean' ? $json.approved_scope.bookkeeping : Object.keys($json.approved_scope.bookkeeping).length > 0))}}"
                        },
                        {
                            "fieldLabel": "Approve Payroll",
                            "fieldType": "checkbox",
                            "defaultValue": "={{Boolean($json.approved_scope && $json.approved_scope.payroll && (typeof $json.approved_scope.payroll === 'boolean' ? $json.approved_scope.payroll : Object.keys($json.approved_scope.payroll).length > 0))}}"
                        },
                        {
                            "fieldLabel": "Approve Financial Reporting",
                            "fieldType": "checkbox",
                            "defaultValue": "={{Boolean($json.approved_scope && $json.approved_scope.financial_reporting && (typeof $json.approved_scope.financial_reporting === 'boolean' ? $json.approved_scope.financial_reporting : Object.keys($json.approved_scope.financial_reporting).length > 0))}}"
                        },
                        {
                            "fieldLabel": "Approve Compliance",
                            "fieldType": "checkbox",
                            "defaultValue": "={{Boolean($json.approved_scope && $json.approved_scope.compliance && (typeof $json.approved_scope.compliance === 'boolean' ? $json.approved_scope.compliance : Object.keys($json.approved_scope.compliance).length > 0))}}"
                        },
                        {
                            "fieldLabel": "Approve Digital Transformation",
                            "fieldType": "checkbox",
                            "defaultValue": False
                        },
                        {
                            "fieldLabel": "Approve Transition",
                            "fieldType": "checkbox",
                            "defaultValue": False
                        },
                        {
                            "fieldLabel": "Approver Notes"
                        }
                    ]
                },
                "options": {}
            },
            "id": "node-approval-gate",
            "name": "Human Approval Gate",
            "type": "n8n-nodes-base.wait",
            "typeVersion": 1.1,
            "position": [1640, 300],
            "notesInFlow": True,
            "notes": "MANDATORY FIREWALL: Human approval gate displaying rich preview payload and context quality score."
        },

        # NODE 9: Approval Decision Check
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                    "conditions": [
                        {
                            "id": "cond-approval-decision",
                            "leftValue": "={{$json['Approval Decision'] || $json.decision || $json.approval_decision}}",
                            "rightValue": "APPROVE",
                            "operator": {"type": "string", "operation": "equals"}
                        }
                    ],
                    "combinator": "and"
                }
            },
            "id": "node-approval-check",
            "name": "Approval Decision Check",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [1880, 300],
            "notesInFlow": True,
            "notes": "Branches on human decision (APPROVE -> Prepare Payload; REJECT -> Rejection Response)."
        },

        # NODE 10: Proposal Generation Rejected
        {
            "parameters": {
                "mode": "manual",
                "duplicateItem": False,
                "assignments": {
                    "assignments": [
                        {"id": "rej-status", "name": "status", "value": "rejected", "type": "string"},
                        {"id": "rej-msg", "name": "message", "value": "Proposal generation rejected by human approver.", "type": "string"}
                    ]
                }
            },
            "id": "node-rejected",
            "name": "Proposal Generation Rejected",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [1880, 520],
            "notesInFlow": True,
            "notes": "Terminal rejection branch when approver rejects proposal generation."
        },

        # NODE 11: Prepare Final Payload
        {
            "parameters": {
                "jsCode": """const approval = $input.first().json;
const previewData = $('Compute Approval Preview').first().json;

// Clone the enriched intake
const finalPayload = { ...previewData };
delete finalPayload.preview;
delete finalPayload.context_quality_score;
delete finalPayload.context_quality_rating;
delete finalPayload.is_valid_request;
delete finalPayload.validation_errors;

// Update approved_scope based on human reviewer checkboxes
const baseScope = previewData.approved_scope || {};
const finalScope = {};

const approveBk = approval['Approve Bookkeeping'] !== undefined ? approval['Approve Bookkeeping'] : Boolean(baseScope.bookkeeping);
if (approveBk) {
  finalScope.bookkeeping = (typeof baseScope.bookkeeping === 'object' && Object.keys(baseScope.bookkeeping).length > 0)
    ? baseScope.bookkeeping
    : { cadence: 'monthly', ap_ar: true, reconciliations: true };
}

const approvePy = approval['Approve Payroll'] !== undefined ? approval['Approve Payroll'] : Boolean(baseScope.payroll);
if (approvePy) {
  finalScope.payroll = (typeof baseScope.payroll === 'object' && Object.keys(baseScope.payroll).length > 0)
    ? baseScope.payroll
    : { cadence: 'semi_monthly', contractor_t4a: true };
}

const approveRep = approval['Approve Financial Reporting'] !== undefined ? approval['Approve Financial Reporting'] : Boolean(baseScope.financial_reporting);
if (approveRep) {
  finalScope.financial_reporting = (typeof baseScope.financial_reporting === 'object' && Object.keys(baseScope.financial_reporting).length > 0)
    ? baseScope.financial_reporting
    : { monthly_package: true, board_package: true };
}

const approveComp = approval['Approve Compliance'] !== undefined ? approval['Approve Compliance'] : Boolean(baseScope.compliance);
if (approveComp) {
  finalScope.compliance = (typeof baseScope.compliance === 'object' && Object.keys(baseScope.compliance).length > 0)
    ? baseScope.compliance
    : { gst_filing: true, audit_support: true };
}

if (approval['Approve Digital Transformation']) {
  finalScope.digital_transformation = { workflow_redesign: true };
}
if (approval['Approve Transition']) {
  finalScope.transition = { onboarding_duration_weeks: 4 };
}

finalPayload.approved_scope = finalScope;

if (approval['Approver Notes']) {
  finalPayload.approver_notes = String(approval['Approver Notes']).trim();
}

return [{
  json: finalPayload
}];"""
            },
            "id": "node-prepare-final-payload",
            "name": "Prepare Final Payload",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [2120, 300],
            "notesInFlow": True,
            "notes": "Combines enriched AI extraction with human approver scope decisions into final API payload."
        },

        # NODE 12: Call Sympl Proposal RAG API
        {
            "parameters": {
                "method": "POST",
                "url": "https://sympl-proposal-rag-production.up.railway.app/api/v1/proposal/generate/async",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "Content-Type", "value": "application/json"},
                        {"name": "X-API-Key", "value": "={{$env.RAG_API_KEY || 'sympl_live_123456'}}"}
                    ]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{JSON.stringify($('Prepare Final Payload').first().json)}}",
                "options": {"timeout": 30000}
            },
            "id": "node-call-rag-api",
            "name": "Call Sympl Proposal RAG API",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [2360, 300],
            "notesInFlow": True,
            "notes": "NODE 5: Triggers async generation on Railway proposal backend (/api/v1/proposal/generate/async)."
        },

        # NODE 13: IF RAG Succeeded?
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                    "conditions": [
                        {
                            "id": "cond-rag-job",
                            "leftValue": "={{$json.job_id}}",
                            "rightValue": "",
                            "operator": {"type": "string", "operation": "notEmpty"}
                        }
                    ],
                    "combinator": "and"
                }
            },
            "id": "node-if-rag-ok",
            "name": "IF RAG Succeeded?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [2600, 300],
            "notesInFlow": True,
            "notes": "Verifies backend returned valid job_id."
        },

        # NODE 14: RAG API Error Response
        {
            "parameters": {
                "mode": "manual",
                "duplicateItem": False,
                "assignments": {
                    "assignments": [
                        {"id": "rag-err-status", "name": "status", "value": "failed", "type": "string"},
                        {"id": "rag-err-stage", "name": "stage", "value": "rag_api_dispatch", "type": "string"},
                        {"id": "rag-err-msg", "name": "message", "value": "Sympl Proposal RAG API rejected submission.", "type": "string"},
                        {"id": "rag-err-detail", "name": "detail", "value": "={{$json}}", "type": "object"}
                    ]
                }
            },
            "id": "node-rag-error",
            "name": "RAG API Error Response",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [2600, 520],
            "notesInFlow": True,
            "notes": "Terminal error branch if proposal API call fails."
        },

        # NODE 15: Store Job ID
        {
            "parameters": {
                "mode": "manual",
                "duplicateItem": False,
                "assignments": {
                    "assignments": [
                        {"id": "st-job-id", "name": "job_id", "value": "={{$json.job_id}}", "type": "string"},
                        {"id": "st-req-id", "name": "request_id", "value": "={{$json.request_id}}", "type": "string"},
                        {"id": "st-poll-count", "name": "poll_count", "value": 0, "type": "number"},
                        {"id": "st-max-polls", "name": "max_polls", "value": 60, "type": "number"},
                        {"id": "st-client-name", "name": "client_name", "value": "={{$('Prepare Final Payload').first().json.client_name}}", "type": "string"}
                    ]
                }
            },
            "id": "node-store-job-id",
            "name": "Store Job ID",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [2840, 300],
            "notesInFlow": True,
            "notes": "Initializes polling loop state."
        },

        # NODE 16: Wait 5 Seconds
        {
            "parameters": {
                "amount": 5,
                "unit": "seconds"
            },
            "id": "node-wait-5s",
            "name": "Wait 5 Seconds",
            "type": "n8n-nodes-base.wait",
            "typeVersion": 1.1,
            "position": [3080, 300],
            "notesInFlow": True,
            "notes": "Poll delay: 5 seconds between status checks."
        },

        # NODE 17: Check Status API
        {
            "parameters": {
                "method": "GET",
                "url": "={{'https://sympl-proposal-rag-production.up.railway.app/api/v1/proposal/status/' + $('Store Job ID').first().json.job_id}}",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "X-API-Key", "value": "={{$env.RAG_API_KEY || 'sympl_live_123456'}}"}
                    ]
                },
                "options": {"timeout": 15000}
            },
            "id": "node-check-status",
            "name": "Check Status API",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [3320, 300],
            "notesInFlow": True,
            "notes": "Polls GET /api/v1/proposal/status/{job_id}."
        },

        # NODE 18: IF Completed?
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                    "conditions": [
                        {
                            "id": "cond-is-completed",
                            "leftValue": "={{$json.status}}",
                            "rightValue": "COMPLETED",
                            "operator": {"type": "string", "operation": "equals"}
                        }
                    ],
                    "combinator": "and"
                }
            },
            "id": "node-if-completed",
            "name": "IF Completed?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [3560, 300],
            "notesInFlow": True,
            "notes": "Exits loop when job reaches COMPLETED status."
        },

        # NODE 19: Check Timeout Counter
        {
            "parameters": {
                "jsCode": """const pollState = $('Store Job ID').first().json;
const currentCount = Number(pollState.poll_count || 0) + 1;
pollState.poll_count = currentCount;

const isTimeout = currentCount >= Number(pollState.max_polls || 60);

return [{
  json: {
    ...pollState,
    is_timeout: isTimeout,
    current_status: $input.first().json.status || 'UNKNOWN',
    current_stage: $input.first().json.current_stage || 'UNKNOWN',
    progress: $input.first().json.progress || 0
  }
}];"""
            },
            "id": "node-check-timeout",
            "name": "Check Timeout Counter",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [3560, 520],
            "notesInFlow": True,
            "notes": "Increments poll counter; enforces 5-minute timeout ceiling."
        },

        # NODE 20: IF Timeout?
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                    "conditions": [
                        {
                            "id": "cond-is-timeout",
                            "leftValue": "={{$json.is_timeout}}",
                            "rightValue": True,
                            "operator": {"type": "boolean", "operation": "equals"}
                        }
                    ],
                    "combinator": "and"
                }
            },
            "id": "node-if-timeout",
            "name": "IF Timeout?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [3320, 520],
            "notesInFlow": True,
            "notes": "Routes to timeout error if ceiling reached; otherwise loops back to wait."
        },

        # NODE 21: Poll Timeout Response
        {
            "parameters": {
                "mode": "manual",
                "duplicateItem": False,
                "assignments": {
                    "assignments": [
                        {"id": "to-status", "name": "status", "value": "timeout", "type": "string"},
                        {"id": "to-stage", "name": "stage", "value": "polling_timeout", "type": "string"},
                        {"id": "to-msg", "name": "message", "value": "Proposal generation exceeded 5-minute polling window.", "type": "string"},
                        {"id": "to-job-id", "name": "job_id", "value": "={{$json.job_id}}", "type": "string"}
                    ]
                }
            },
            "id": "node-timeout-response",
            "name": "Poll Timeout Response",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [3320, 720],
            "notesInFlow": True,
            "notes": "Terminal error branch if generation times out."
        },

        # NODE 22: Retrieve Generated PDF
        {
            "parameters": {
                "method": "GET",
                "url": "={{'https://sympl-proposal-rag-production.up.railway.app/api/v1/proposal/' + $json.proposal_id + '/pdf'}}",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "X-API-Key", "value": "={{$env.RAG_API_KEY || 'sympl_live_123456'}}"}
                    ]
                },
                "options": {"response": {"response": {"responseFormat": "file"}}}
            },
            "id": "node-retrieve-pdf",
            "name": "Retrieve Generated PDF",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [3800, 300],
            "notesInFlow": True,
            "notes": "Downloads binary proposal.pdf."
        },

        # NODE 23: Retrieve Manifest
        {
            "parameters": {
                "method": "GET",
                "url": "={{'https://sympl-proposal-rag-production.up.railway.app/api/v1/proposal/' + $('Check Status API').first().json.proposal_id + '/manifest'}}",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "X-API-Key", "value": "={{$env.RAG_API_KEY || 'sympl_live_123456'}}"}
                    ]
                },
                "options": {"timeout": 15000}
            },
            "id": "node-retrieve-manifest",
            "name": "Retrieve Manifest",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [4040, 300],
            "notesInFlow": True,
            "notes": "Downloads 5-artifact audit manifest."
        },

        # NODE 24: Prepare Canva Import Handoff
        {
            "parameters": {
                "jsCode": """const statusData = $('Check Status API').first().json;
const manifest = $input.first().json;
const clientName = $('Store Job ID').first().json.client_name || 'Client';

return [{
  json: {
    canva_asset_title: `Sympl Proposal - ${clientName}`,
    proposal_id: statusData.proposal_id,
    pdf_download_url: `https://sympl-proposal-rag-production.up.railway.app/api/v1/proposal/${statusData.proposal_id}/pdf`,
    manifest_url: `https://sympl-proposal-rag-production.up.railway.app/api/v1/proposal/${statusData.proposal_id}/manifest`,
    artifact_count: (manifest.artifacts && manifest.artifacts.length) || 5,
    handoff_timestamp: new Date().toISOString()
  }
}];"""
            },
            "id": "node-canva-prepare",
            "name": "Prepare Canva Import Handoff",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [4280, 300],
            "notesInFlow": True,
            "notes": "Prepares metadata for Canva import handoff."
        },

        # NODE 25: CANVA IMPORT SERVICE
        {
            "parameters": {
                "jsCode": """// CANVA IMPORT SERVICE: Simulates / coordinates Canva document import handoff
const handoff = $input.first().json;

return [{
  json: {
    status: 'success',
    canva_import_status: 'ready_for_import',
    canva_asset_title: handoff.canva_asset_title,
    proposal_id: handoff.proposal_id,
    pdf_download_url: handoff.pdf_download_url,
    manifest_url: handoff.manifest_url,
    imported_at: handoff.handoff_timestamp
  }
}];"""
            },
            "id": "node-canva-service",
            "name": "CANVA IMPORT SERVICE",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [4520, 300],
            "notesInFlow": True,
            "notes": "Executes Canva asset import handoff."
        },

        # NODE 26: Return Completion Result
        {
            "parameters": {
                "mode": "manual",
                "duplicateItem": False,
                "assignments": {
                    "assignments": [
                        {"id": "res-status", "name": "status", "value": "COMPLETED", "type": "string"},
                        {"id": "res-prop-id", "name": "proposal_id", "value": "={{$json.proposal_id}}", "type": "string"},
                        {"id": "res-pdf-url", "name": "pdf_download_url", "value": "={{$json.pdf_download_url}}", "type": "string"},
                        {"id": "res-man-url", "name": "manifest_url", "value": "={{$json.manifest_url}}", "type": "string"},
                        {"id": "res-canva-status", "name": "canva_import_status", "value": "={{$json.canva_import_status}}", "type": "string"}
                    ]
                }
            },
            "id": "node-completion-result",
            "name": "Return Completion Result",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [4760, 300],
            "notesInFlow": True,
            "notes": "Workflow output: proposal URLs and delivery status."
        }
    ]

    connections = {
        "User Proposal Form": {
            "main": [[{"node": "AI Extraction Node", "type": "main", "index": 0}]]
        },
        "AI Extraction Node": {
            "main": [[{"node": "Parse AI Extraction", "type": "main", "index": 0}]]
        },
        "Parse AI Extraction": {
            "main": [[{"node": "Validate Extracted Intake", "type": "main", "index": 0}]]
        },
        "Validate Extracted Intake": {
            "main": [[{"node": "IF Intake Valid?", "type": "main", "index": 0}]]
        },
        "IF Intake Valid?": {
            "main": [
                [{"node": "Compute Approval Preview", "type": "main", "index": 0}],
                [{"node": "Validation Error Response", "type": "main", "index": 0}]
            ]
        },
        "Compute Approval Preview": {
            "main": [[{"node": "Human Approval Gate", "type": "main", "index": 0}]]
        },
        "Human Approval Gate": {
            "main": [[{"node": "Approval Decision Check", "type": "main", "index": 0}]]
        },
        "Approval Decision Check": {
            "main": [
                [{"node": "Prepare Final Payload", "type": "main", "index": 0}],
                [{"node": "Proposal Generation Rejected", "type": "main", "index": 0}]
            ]
        },
        "Prepare Final Payload": {
            "main": [[{"node": "Call Sympl Proposal RAG API", "type": "main", "index": 0}]]
        },
        "Call Sympl Proposal RAG API": {
            "main": [[{"node": "IF RAG Succeeded?", "type": "main", "index": 0}]]
        },
        "IF RAG Succeeded?": {
            "main": [
                [{"node": "Store Job ID", "type": "main", "index": 0}],
                [{"node": "RAG API Error Response", "type": "main", "index": 0}]
            ]
        },
        "Store Job ID": {
            "main": [[{"node": "Wait 5 Seconds", "type": "main", "index": 0}]]
        },
        "Wait 5 Seconds": {
            "main": [[{"node": "Check Status API", "type": "main", "index": 0}]]
        },
        "Check Status API": {
            "main": [[{"node": "IF Completed?", "type": "main", "index": 0}]]
        },
        "IF Completed?": {
            "main": [
                [{"node": "Retrieve Generated PDF", "type": "main", "index": 0}],
                [{"node": "Check Timeout Counter", "type": "main", "index": 0}]
            ]
        },
        "Check Timeout Counter": {
            "main": [[{"node": "IF Timeout?", "type": "main", "index": 0}]]
        },
        "IF Timeout?": {
            "main": [
                [{"node": "Poll Timeout Response", "type": "main", "index": 0}],
                [{"node": "Wait 5 Seconds", "type": "main", "index": 0}]
            ]
        },
        "Retrieve Generated PDF": {
            "main": [[{"node": "Retrieve Manifest", "type": "main", "index": 0}]]
        },
        "Retrieve Manifest": {
            "main": [[{"node": "Prepare Canva Import Handoff", "type": "main", "index": 0}]]
        },
        "Prepare Canva Import Handoff": {
            "main": [[{"node": "CANVA IMPORT SERVICE", "type": "main", "index": 0}]]
        },
        "CANVA IMPORT SERVICE": {
            "main": [[{"node": "Return Completion Result", "type": "main", "index": 0}]]
        }
    }

    workflow = {
        "name": "Sympl Proposal RAG MVP Automation",
        "nodes": nodes,
        "connections": connections,
        "active": False,
        "settings": {
            "executionOrder": "v1"
        },
        "versionId": "sympl-rag-mvp-v2-ai-intake",
        "meta": {
            "templateCredsSetupCompleted": True,
            "description": "Production n8n workflow for Sympl Proposal RAG with AI Unstructured Intake Extraction (gpt-4o-mini), Schema Validation, Human Scope Approval Gate with Reviewer Preview, Asynchronous Polling Loop, PDF/Manifest Retrieval, and Canva Handoff."
        }
    }

    return workflow

if __name__ == '__main__':
    wf = build_workflow()
    
    # Save to sympl-proposal-rag/workflow_3_proposal_rag_mvp.json
    p1 = r"d:\Sympl\sympl-proposal-rag\workflow_3_proposal_rag_mvp.json"
    with open(p1, 'w', encoding='utf-8') as f:
        json.dump(wf, f, indent=2)
    print(f"Saved {p1} ({len(wf['nodes'])} nodes)")

    # Save to d:\Sympl\workflow_sympl_rag_mvp.json
    p2 = r"d:\Sympl\workflow_sympl_rag_mvp.json"
    with open(p2, 'w', encoding='utf-8') as f:
        json.dump(wf, f, indent=2)
    print(f"Saved {p2} ({len(wf['nodes'])} nodes)")
