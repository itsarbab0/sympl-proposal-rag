import json
import os
import urllib.request
import urllib.error

# Load .env
env_file = r"d:\Sympl\sympl-proposal-rag\.env"
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# Read assessment fixture
fixture_path = r"d:\Sympl\sympl-proposal-rag\tests\fixtures\tayyab_oldt_assessment.txt"
with open(fixture_path, "r", encoding="utf-8") as f:
    assessment_text = f.read()

system_prompt = """You are an expert financial intake extraction assistant for Sympl Bookkeeping & Financial Advisory Services.
Your role is to analyze client needs assessment questionnaires and extract structured proposal intake data for Sympl's proposal generation engine.

CRITICAL INSTRUCTIONS & CONSTRAINTS:
1. Preserve Information: Preserve all facts, figures, tools, pain points, team details, and systems from the assessment questionnaire.
2. No Hallucination: Do NOT invent, assume, or fabricate missing information. If a field or detail is not mentioned or is N/A, leave it as an empty string, empty list, or empty object.
3. Professional Consulting Context: Convert raw notes, shorthand, and conversational answers into articulate, professional proposal context suitable for consulting engagement letters.
4. Separate Client Facts from Recommendations: Under client_situation_summary and client_challenges_summary, describe what the client currently does and struggles with. Do not prescribe Sympl's service solution in the client's current situation summary.
5. Pricing Invariant: Keep pricing fields empty or zero unless explicit pricing or budgets are agreed upon in the assessment.
6. Scope & Context Mapping:
   - Identify candidate services from the form selections and populate approved_scope with relevant booleans/details:
     * bookkeeping: e.g. {"cadence": "monthly", "ap_ar": true, "reconciliations": true, "project_tracking": true}
     * payroll: e.g. {"cadence": "semi_monthly", "contractor_t4a": true, "headcount_contractors": 4}
     * financial_reporting: e.g. {"monthly_package": true, "board_package": true}
     * compliance: e.g. {"gst_filing": true, "audit_support": true}
   - Extract operational details into service_context:
     * bookkeeping: { "ap_ar_requirements": "...", "reconciliation_requirements": "..." }
     * payroll: { "payroll_frequency": "...", "current_payroll_system": "..." }
     * reporting: { "reporting_requirements": "...", "board_reporting_requirements": "..." }
     * compliance: { "compliance_requirements": "..." }

OUTPUT SCHEMA SPECIFICATION:
You MUST respond with a single valid JSON object containing EXACTLY these keys:
{
  "client_name": "",
  "organization_type": "",
  "sector": "",
  "organization_description": "",
  "client_situation_summary": "",
  "client_challenges_summary": "",
  "current_accounting_system": "",
  "current_finance_process": "",
  "current_finance_team_structure": "",
  "current_finance_challenges": [],
  "reason_for_engagement": "",
  "desired_outcomes": [],
  "client_priorities": [],
  "approved_scope": {
    "bookkeeping": {},
    "payroll": {},
    "financial_reporting": {},
    "compliance": {}
  },
  "service_context": {
    "bookkeeping": {},
    "payroll": {},
    "reporting": {},
    "compliance": {}
  },
  "commercial_terms": {}
}"""

openrouter_key = os.environ.get("OPENROUTER_API_KEY")
openai_key = os.environ.get("OPENAI_API_KEY")

payload = {
    "model": "openai/gpt-4o-mini" if openrouter_key else "gpt-4o-mini",
    "temperature": 0.0,
    "response_format": {"type": "json_object"},
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Extract structured proposal intake from this client assessment:\n\n{assessment_text}"}
    ]
}

url = "https://openrouter.ai/api/v1/chat/completions" if openrouter_key else "https://api.openai.com/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {openrouter_key or openai_key}"
}
if openrouter_key:
    headers["HTTP-Referer"] = "https://sympl.ca"
    headers["X-Title"] = "Sympl Proposal RAG"

req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        content = res_data["choices"][0]["message"]["content"]
        extracted = json.loads(content)
        print("=== REFINED EXTRACTION SUCCEEDED ===")
        print(json.dumps(extracted, indent=2))
        
        with open(r"d:\Sympl\sympl-proposal-rag\scratch\extracted_oldt_intake.json", "w", encoding="utf-8") as out_f:
            json.dump(extracted, out_f, indent=2)
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
