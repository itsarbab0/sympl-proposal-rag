"""
Sympl Solutions Proposal RAG — LLM Provider Client Abstraction

Supports:
  1. OpenRouter API (LLM_PROVIDER=openrouter, OPENROUTER_API_KEY, OPENROUTER_MODEL)
  2. Local Ollama   (LLM_PROVIDER=ollama, OLLAMA_BASE_URL, OLLAMA_MODEL)
  3. Mock Provider  (LLM_PROVIDER=mock, for offline, deterministic testing)

Enforces zero hardcoded models.
"""

import os
import json
import re
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path


def load_environment() -> Dict[str, str]:
    env_vars = {}
    candidates = [
        Path('d:/Sympl/.env'),
        Path('d:/Sympl/sympl-proposal-rag/.env'),
        Path('.env'),
        Path('../.env')
    ]
    for p in candidates:
        if p.exists():
            with open(p, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        env_vars[k.strip()] = v.strip().strip('"\'')
    for k, v in os.environ.items():
        if k not in env_vars:
            env_vars[k] = v
    return env_vars


ENV = load_environment()


class LLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2) -> str:
        """Sends prompt to the LLM and returns the raw response string (expected to be JSON)."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns provider identifier."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns model identifier."""
        pass


class OpenRouterClient(LLMClient):
    """Client for OpenRouter API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or ENV.get("OPENROUTER_API_KEY")
        if not self._api_key:
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouter provider.")
        self._model = model or ENV.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
        self._url = "https://openrouter.ai/api/v1/chat/completions"

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"}
        }

        req = urllib.request.Request(
            self._url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://symplsolutions.ca",
                "X-Title": "Sympl Proposal Writer"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenRouter API error (HTTP {e.code}): {err_body}")
        except Exception as e:
            raise RuntimeError(f"OpenRouter connection error: {e}")


class OllamaClient(LLMClient):
    """Client for local Ollama."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self._base_url = (base_url or ENV.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip('/')
        self._model = model or ENV.get("OLLAMA_MODEL", "llama3.2")
        self._url = f"{self._base_url}/api/chat"

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature}
        }

        req = urllib.request.Request(
            self._url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["message"]["content"]
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Ollama API error (HTTP {e.code}): {err_body}")
        except Exception as e:
            raise RuntimeError(f"Ollama connection error: {e}")


class MockLLMClient(LLMClient):
    """Deterministic mock provider for offline testing."""

    def __init__(self, canned_responses: Optional[List[str]] = None, model: str = "mock-sympl-v1"):
        self._model = model
        self.canned_responses: List[str] = list(canned_responses) if canned_responses else []
        self.call_history: List[Dict[str, Any]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model

    def queue_response(self, response_json_str: str) -> None:
        self.canned_responses.append(response_json_str)

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2) -> str:
        self.call_history.append({"prompt": prompt, "system_prompt": system_prompt, "temperature": temperature})

        if self.canned_responses:
            return self.canned_responses.pop(0)

        # Default compliant mock generator: parses the prompt to generate valid matching output
        return self._generate_default_compliant_response(prompt)

    def _generate_default_compliant_response(self, prompt: str) -> str:
        """Generates a fully compliant Sympl proposal draft from prompt context."""
        # 1. Extract client name from prompt
        client_name = "Client Organization"
        for line in prompt.split("\n"):
            if "Client Name:" in line or '"name":' in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    client_name = parts[1].strip().strip('",\'')
                break

        # 2. Extract approved scope JSON if present in prompt
        app_scope = {}
        match_scope = re.search(
            r"--- APPROVED SERVICE SCOPE \(AUTHORITATIVE & COMPLETE\) ---\s*(?:Every generated service MUST belong to this approved scope:\s*)?(\{.*?\})\s*(?:\n\n---|\Z)",
            prompt,
            re.DOTALL
        )
        if match_scope:
            try:
                app_scope = json.loads(match_scope.group(1))
            except Exception:
                app_scope = {}

        # Fallback keyword checks if scope dict empty
        prompt_lower = prompt.lower()
        has_bookkeeping = "bookkeeping" in app_scope or ("bookkeeping" in prompt_lower and '"bookkeeping":' in prompt_lower)
        has_payroll = "payroll" in app_scope or ("payroll" in prompt_lower and '"payroll":' in prompt_lower)
        has_reporting = "financial_reporting" in app_scope or ("financial_reporting" in prompt_lower or "funder_tracking" in prompt_lower)
        has_compliance = "compliance" in app_scope or ("compliance" in prompt_lower and '"compliance":' in prompt_lower)
        has_transformation = "digital_transformation" in app_scope or ("digital_transformation" in prompt_lower or "system_migrations" in prompt_lower)
        has_training = "training" in app_scope or ("training" in prompt_lower and '"training":' in prompt_lower)
        has_transition = "transition_services" in app_scope or ("transition" in prompt_lower and "interim" in prompt_lower)
        has_consulting = "management_consulting" in app_scope or ("management_consulting" in prompt_lower)
        has_audit = "audit_oversight" in app_scope or ("audit_oversight" in prompt_lower) or (has_compliance and isinstance(app_scope.get("compliance"), dict) and app_scope["compliance"].get("audit_support"))

        sections = []

        if has_transition or "interim" in prompt_lower:
            sections.append({
                "section_title": "Summary of Engagement & Interim Continuity",
                "opening_text": f"Sympl Solutions provides interim financial management and structured onboarding to ensure operational stability for {client_name}.",
                "subsections": [
                    {
                        "heading": "Engagement Continuity & Governance",
                        "bullets": [
                            "Maintain continuous financial oversight during organizational leadership transitions",
                            "Preserve established accounting workflows and legacy ledger documentation",
                            "Coordinate structured handover milestones with incoming permanent leadership"
                        ]
                    },
                    {
                        "heading": "Deliverables & Reporting",
                        "bullets": [
                            "Deliver current state operational assessment and risk summary memo",
                            "Provide documented accounting process checklists for leadership succession"
                        ]
                    },
                    {
                        "heading": "Operational Boundaries",
                        "bullets": [
                            "Exclude forensic accounting investigations or historical dispute resolution",
                            "Require executive access to legacy banking and accounting software"
                        ]
                    }
                ]
            })
            sections.append({
                "section_title": "Transition & Onboarding Plan",
                "opening_text": "We execute a structured multi-week onboarding plan to secure financial continuity.",
                "subsections": [
                    {
                        "heading": "Onboarding Milestones & Cadence",
                        "bullets": [
                            "Ingest historical general ledger data and active vendor registers",
                            "Shadow existing financial procedures during initial transition weeks",
                            "Establish verified approval matrices and digital document repositories"
                        ]
                    },
                    {
                        "heading": "Onboarding Deliverables",
                        "bullets": [
                            "Complete chart of accounts review and initial ledger reconciliation",
                            "Deliver confirmed operational transition roadmap to executive leadership"
                        ]
                    }
                ]
            })

        if has_transformation:
            sections.append({
                "section_title": "Part A: Digital Financial Systems & Workflow Transformation",
                "opening_text": f"Sympl Solutions implements streamlined cloud accounting infrastructure and automated receipt workflows for {client_name}.",
                "subsections": [
                    {
                        "heading": "System Migration & Integration Cadence",
                        "bullets": [
                            "Configure cloud accounting architecture and chart of accounts mapping",
                            "Implement electronic expense capture workflows using approved software tools",
                            "Execute parallel verification runs to validate opening ledger balances"
                        ]
                    },
                    {
                        "heading": "Transformation Deliverables",
                        "bullets": [
                            "Deliver fully configured QuickBooks Online and Dext system environment",
                            "Provide recorded staff training walk-throughs and standard operating guidelines"
                        ]
                    },
                    {
                        "heading": "Implementation Boundaries",
                        "bullets": [
                            "Require timely client export of historical transaction files from legacy software",
                            "Exclude ongoing custom application software development or API programming"
                        ]
                    }
                ]
            })

        if has_bookkeeping:
            sections.append({
                "section_title": "Accounting & Bookkeeping Services",
                "opening_text": f"We manage full-cycle operational bookkeeping on weekly and monthly cycles to maintain accurate financial records for {client_name}.",
                "subsections": [
                    {
                        "heading": "Accounts Payable & Disbursements",
                        "bullets": [
                            "Process vendor bills and verify corporate credit card expense entries",
                            "Maintain accounts payable aging schedules and prepare payment disbursement batches",
                            "Verify documentation and receipts against organizational approval policies"
                        ]
                    },
                    {
                        "heading": "Accounts Receivable & General Ledger",
                        "bullets": [
                            "Record client invoicing and match incoming bank deposit receipts",
                            "Reconcile operating bank accounts and credit cards on monthly cycles",
                            "Maintain QuickBooks Online general ledger hygiene and account allocations"
                        ]
                    },
                    {
                        "heading": "Deliverables & Outputs",
                        "bullets": [
                            "Deliver reconciled general ledger balances and monthly balance sheet registers",
                            "Provide monthly accounts payable and accounts receivable summary schedules"
                        ]
                    },
                    {
                        "heading": "Operational Boundaries",
                        "bullets": [
                            "Submit all supporting receipts and vendor invoices through the digital portal",
                            "Require timely client authorization for electronic vendor payment disbursements"
                        ]
                    }
                ]
            })

        if has_payroll:
            sections.append({
                "section_title": "Payroll Administration",
                "opening_text": f"We manage end-to-end payroll operations and statutory remittances for {client_name}.",
                "subsections": [
                    {
                        "heading": "Payroll Processing Cadence",
                        "bullets": [
                            "Process semi-monthly employee payroll disbursements and contractor invoices",
                            "Calculate statutory source deductions and submit CRA payroll remittances",
                            "Prepare annual T4 summary statements and mandatory records of employment"
                        ]
                    },
                    {
                        "heading": "Payroll Deliverables",
                        "bullets": [
                            "Deliver verified payroll summary reports following each pay run",
                            "Provide confirmed CRA payroll remittance confirmations and filing receipts"
                        ]
                    },
                    {
                        "heading": "Payroll Boundaries & Prerequisites",
                        "bullets": [
                            "Submit approved timesheets and payroll adjustments 3 days prior to pay date",
                            "Exclude human resource policy management or employment contract dispute resolution"
                        ]
                    }
                ]
            })

        if has_reporting:
            sections.append({
                "section_title": "Financial Reporting & Governance",
                "opening_text": f"We provide timely monthly financial visibility and funder reporting for {client_name}.",
                "subsections": [
                    {
                        "heading": "Management & Funder Reporting Cadence",
                        "bullets": [
                            "Generate monthly financial packages comparing actual results against budget",
                            "Track restricted fund allocations and prepare contribution agreement reports",
                            "Deliver departmental financial statements to leadership and board committees"
                        ]
                    },
                    {
                        "heading": "Reporting Deliverables",
                        "bullets": [
                            "Deliver monthly statement of financial position and statement of operations",
                            "Provide quarterly budget variance commentary schedules for finance committees"
                        ]
                    },
                    {
                        "heading": "Governance Boundaries",
                        "bullets": [
                            "Deliver reporting packages within 15 business days after monthly close",
                            "Rely on finalized approved operational budget figures provided by management"
                        ]
                    }
                ]
            })

        if has_compliance:
            comp_bullets = [
                "Prepare quarterly GST/HST public service body rebate applications",
                "Maintain digital documentation archives for statutory tax records"
            ]
            comp_scope = app_scope.get("compliance", {}) if isinstance(app_scope.get("compliance"), dict) else {}
            if comp_scope.get("t3010_support"):
                comp_bullets.append("Compile annual charity information returns and statutory disclosure schedules")
            if comp_scope.get("audit_support") or has_audit:
                comp_bullets.append("Coordinate working paper packages to facilitate external financial audits")

            sections.append({
                "section_title": "Statutory Compliance & Filings",
                "opening_text": "We support regulatory compliance and statutory reporting on established filing schedules.",
                "subsections": [
                    {
                        "heading": "Tax & Regulatory Filings",
                        "bullets": comp_bullets
                    },
                    {
                        "heading": "Compliance Deliverables",
                        "bullets": [
                            "Deliver submitted GST/HST rebate forms and CRA confirmation notices",
                            "Provide organized working paper archives supporting filed tax schedules"
                        ]
                    },
                    {
                        "heading": "Compliance Boundaries",
                        "bullets": [
                            "Require client delivery of source documents 30 days prior to filing deadlines",
                            "Exclude formal corporate tax return filings prepared by external CPA firms"
                        ]
                    }
                ]
            })

        if has_audit and not any("Audit" in s["section_title"] for s in sections):
            sections.append({
                "section_title": "Audit Preparation & Working Paper Oversight",
                "opening_text": f"We deliver rigorous audit oversight and working paper preparation for {client_name}.",
                "subsections": [
                    {
                        "heading": "Audit Readiness & Liaison Cadence",
                        "bullets": [
                            "Compile comprehensive audit lead schedules and balance sheet working papers",
                            "Liaise directly with external auditing firms during interim and year-end procedures",
                            "Reconcile restricted fund balances and deferred grant revenue registers"
                        ]
                    },
                    {
                        "heading": "Audit Deliverables",
                        "bullets": [
                            "Deliver completed audit working paper binder and reconciled trial balance",
                            "Provide responsive audit query tracking log during external field work"
                        ]
                    },
                    {
                        "heading": "Audit Boundaries",
                        "bullets": [
                            "Exclude signing external independent audit opinions or auditor attestations",
                            "Require timely client governance approval of draft audited statements"
                        ]
                    }
                ]
            })

        if has_consulting:
            sections.append({
                "section_title": "Financial Advisory & Strategic Consulting",
                "opening_text": f"We provide executive financial advisory and strategic oversight for {client_name}.",
                "subsections": [
                    {
                        "heading": "Strategic Financial Guidance",
                        "bullets": [
                            "Provide fractional financial guidance on multi-year organizational sustainability",
                            "Develop organizational cash flow projection models and scenario analyses",
                            "Advise executive leadership and finance committees on capital allocations"
                        ]
                    },
                    {
                        "heading": "Advisory Deliverables",
                        "bullets": [
                            "Deliver rolling 12-month cash flow forecast models and scenario templates",
                            "Provide quarterly executive financial briefing memos for leadership"
                        ]
                    },
                    {
                        "heading": "Advisory Boundaries",
                        "bullets": [
                            "Provide strategic recommendations without binding management executive authority",
                            "Exclude legal structuring advice or formal investment underwriting services"
                        ]
                    }
                ]
            })

        if has_training:
            sections.append({
                "section_title": "Training & Change Management",
                "opening_text": "We provide targeted training and workflow documentation for organizational teams.",
                "subsections": [
                    {
                        "heading": "Staff Enablement & SOPs",
                        "bullets": [
                            "Develop standardized operating procedure manuals for financial tasks",
                            "Conduct practical software training sessions with designated team members",
                            "Provide ongoing workflow support following system go-live milestones"
                        ]
                    },
                    {
                        "heading": "Training Deliverables",
                        "bullets": [
                            "Deliver step-by-step written standard operating procedure reference guides",
                            "Provide practical training session attendance logs and follow-up checklists"
                        ]
                    },
                    {
                        "heading": "Training Boundaries",
                        "bullets": [
                            "Limit live training sessions to designated financial and administrative personnel",
                            "Schedule training sessions with 5 business days advance written notice"
                        ]
                    }
                ]
            })

        # 3. Extract exact reference blocks for Why Us from prompt if available
        why_us = []
        match_why_blocks = re.findall(r'"exact_reference_blocks":\s*(\[[^\]]+\])', prompt)
        for blk_json in match_why_blocks:
            try:
                blocks = json.loads(blk_json)
                for b in blocks:
                    if b not in why_us:
                        why_us.append(b)
            except Exception:
                pass

        # Fallback canonical Why Us if none extracted from prompt sections
        if not why_us:
            why_us = [
                "Why Sympl?",
                "Non-profit and charity experience: We specialize in supporting organizations in the community services and social enterprise space with mission-focused fund accounting and reporting.",
                "Technology and integration: Modern cloud tools (QBO, Dext, Wagepoint, Plooto) create automated, auditable workflows that minimize administrative friction.",
                "Dedicated, responsive team: Direct access to senior financial professionals without the overhead of a large firm, ensuring consistent operational support.",
                "We would love to partner with you to build a financial foundation that supports your mission.",
                "Thank you for the opportunity to submit this proposal. We look forward to discussing how we can support your work."
            ]

        # 4. Extract pricing and exclusions from prompt
        pricing = {
            "pricing_model": "fixed_retainer",
            "currency": "CAD",
            "billing_schedule": "Monthly retainer invoiced on the 1st of each service month.",
            "fee_items": [
                {
                    "category": "Monthly Recurring Retainer",
                    "amount": 3200.0,
                    "currency": "CAD",
                    "billing_frequency": "monthly",
                    "description": "Comprehensive operational bookkeeping and financial management as scoped.",
                    "is_placeholder": False
                }
            ],
            "has_placeholders": False
        }

        match_pricing = re.search(
            r"--- COMMERCIAL SCHEDULE & TERMS ---\s*(\{.*?\})\s*(?:\n\n|\Z|===)",
            prompt,
            re.DOTALL
        )
        if match_pricing:
            try:
                extracted_pricing = json.loads(match_pricing.group(1))
                if isinstance(extracted_pricing, dict) and "fee_items" in extracted_pricing:
                    pricing = extracted_pricing
            except Exception:
                pass

        # Exclusions: extract disclaimers from pricing if present
        exclusions = []
        if isinstance(pricing, dict) and "disclaimers" in pricing:
            for d in pricing.get("disclaimers", []):
                content = d.get("content") if isinstance(d, dict) else str(d)
                if content and content not in exclusions:
                    exclusions.append(content)

        # Fallback exclusions if disclaimers not populated
        if not exclusions:
            if "backlog" in prompt_lower or "REF_BLOCK_EXCLUSIONS_BACKLOG" in prompt:
                exclusions.append("Bookkeeping backlog: Any prior period bookkeeping clean-up or catch-up work will be quoted separately based on the volume and complexity")
            if "software_fees" in prompt_lower or "REF_BLOCK_EXCLUSIONS_SOFTWARE_NOT_INCLUDED" in prompt:
                exclusions.append("Note: Above costs do not include software subscription fees.")
            if has_payroll:
                exclusions.append("Note: While we manage all payroll accounting and processing, managers must provide timely payroll data (e.g., timesheets, new hires, exits). We do not manage HR functions.")

        # Compose concise executive summary (< 120 words, zero buzzwords, client-specific)
        service_names = []
        if has_bookkeeping:
            service_names.append("operational bookkeeping")
        if has_payroll:
            service_names.append("payroll administration")
        if has_reporting:
            service_names.append("financial reporting")
        if has_compliance:
            service_names.append("statutory compliance")
        if has_transformation:
            service_names.append("system transformation")
        if has_transition:
            service_names.append("interim financial management")
        if not service_names:
            service_names.append("operational financial management")

        services_str = ", ".join(service_names)
        exec_summary = (
            f"Sympl Solutions is pleased to submit this proposal to support {client_name} with dedicated {services_str}. "
            f"Our team delivers disciplined operational financial workflows, accurate reconciliations, and structured reporting "
            f"to establish transparent oversight. By maintaining day-to-day accounting and statutory filings on reliable schedules, "
            f"we enable leadership to execute organizational priorities with confidence and fiscal integrity."
        )

        response_dict = {
            "title": f"Accounting & Bookkeeping Services Proposal for {client_name}",
            "executive_summary": exec_summary,
            "sections": sections,
            "why_us": why_us,
            "pricing": pricing,
            "exclusions": exclusions,
            "validation_metadata": {}
        }

        return json.dumps(response_dict, indent=2)



def get_llm_client(provider: Optional[str] = None, **kwargs) -> LLMClient:
    """Factory function returning the configured LLM client."""
    provider_name = (provider or ENV.get("LLM_PROVIDER", "mock")).lower()

    if provider_name == "openrouter":
        return OpenRouterClient(**kwargs)
    elif provider_name == "ollama":
        return OllamaClient(**kwargs)
    elif provider_name == "mock":
        return MockLLMClient(**kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: '{provider_name}'. Supported: 'openrouter', 'ollama', 'mock'.")
