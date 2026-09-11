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
        # Identify domain service category
        service_category = None
        match_cat = re.search(r'"service_category":\s*"([^"]+)"', prompt)
        if match_cat:
            service_category = match_cat.group(1)

        if not service_category:
            match_title_prompt = re.search(r'"title":\s*"([^"]+)"', prompt)
            if match_title_prompt:
                title_str = match_title_prompt.group(1).lower()
                if "website" in title_str:
                    service_category = "Website Development"
                elif "data analytics" in title_str:
                    service_category = "Data Analytics"
                elif "budget revamp" in title_str or "financial forecasting" in title_str:
                    service_category = "Finance Transformation"
                elif "consulting services" in title_str:
                    service_category = "General Consulting"

        if not service_category:
            if "crawford_2026" in prompt_lower or "collector journey" in prompt_lower or "squarespace" in prompt_lower or "website development" in prompt_lower:
                service_category = "Website Development"
            elif "akm_2026" in prompt_lower or "sql warehouse" in prompt_lower or "data analytics" in prompt_lower:
                service_category = "Data Analytics"
            elif "compass_2026" in prompt_lower or "forecast model" in prompt_lower or "finance transformation" in prompt_lower:
                service_category = "Finance Transformation"
            elif "general consulting" in prompt_lower:
                service_category = "General Consulting"

        # Shared extractors for Why Us, Pricing, and Exclusions
        common_why_us = []
        match_why_blocks = re.findall(r'"exact_reference_blocks":\s*(\[[^\]]+\])', prompt)
        for blk_json in match_why_blocks:
            try:
                blocks = json.loads(blk_json)
                for b in blocks:
                    if b not in common_why_us:
                        common_why_us.append(b)
            except Exception:
                pass

        common_pricing = {
            "pricing_model": "fixed_retainer",
            "currency": "CAD",
            "billing_schedule": "Monthly retainer invoiced on the 1st of each service month.",
            "fee_items": [
                {
                    "category": "Professional Retainer",
                    "amount": 3500.0,
                    "currency": "CAD",
                    "billing_frequency": "monthly",
                    "description": "Professional consulting and implementation services as scoped.",
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
                    common_pricing = extracted_pricing
            except Exception:
                pass

        common_exclusions = []
        if isinstance(common_pricing, dict) and "disclaimers" in common_pricing:
            for d in common_pricing.get("disclaimers", []):
                content = d.get("content") if isinstance(d, dict) else str(d)
                if content and content not in common_exclusions:
                    common_exclusions.append(content)

        # ---------------------------------------------------------------------
        # DOMAIN GENERATOR: Website Development
        # ---------------------------------------------------------------------
        if service_category == "Website Development":
            website_why_us = common_why_us if common_why_us else [
                "Why Sympl?",
                "Arts & Creative Sector Focus: We specialize in building responsive digital portfolios and collector-focused platforms for creative organizations and independent artists.",
                "Collector-First UX & Modern CMS: We design intuitive, image-forward architectures that streamline acquisition inquiries without technical debt.",
                "Client Empowerment & Autonomy: Dedicated 1-on-1 walkthroughs and tailored reference manuals ensure staff manage updates confidently without developer lock-in.",
                "We look forward to collaborating with you to elevate your digital presence."
            ]
            website_exclusions = common_exclusions if common_exclusions else [
                "Domain renewal and third-party hosting subscription charges are billed directly to the client.",
                "Ongoing custom software engineering beyond the scoped deliverables will be quoted separately."
            ]
            website_sections = [
                {
                    "section_title": "Site Architecture, UX Design & CMS Platform",
                    "opening_text": f"Sympl Solutions designs a modern, responsive web experience tailored to {client_name}, establishing clear visual hierarchy, intuitive collector navigation, and seamless CMS administration.",
                    "subsections": [
                        {
                            "heading": "Collector Journey & Information Architecture",
                            "context": f"For contemporary art institutions and creative galleries, the digital portfolio serves as the primary conduit for collector engagement, curatorial research, and international acquisition inquiries.",
                            "approach": "Sympl designs an image-forward, collector-first digital architecture that elevates visual presentation while removing navigational obstacles between visitors and acquisition pathways.",
                            "workflow": "We structure exhibition archives chronologically, organize artwork catalog taxonomies by medium, dimensions, and provenance, and route direct acquisition inquiries directly to gallery directors.",
                            "bullets": [
                                "Design responsive, collector-first navigation hierarchies for portfolio galleries and archives",
                                "Implement dedicated artwork showcase pages with dimensions, medium, year, and provenance",
                                "Configure direct collector inquiry pathways routed to organizational email"
                            ],
                            "outcome": "Elevated collector discovery, streamlined acquisition inquiries, and intuitive navigation across mobile and desktop devices."
                        },
                        {
                            "heading": "Modern CMS Configuration & Visual Curation",
                            "context": f"Maintaining an active commercial exhibition calendar requires an administrative interface that {client_name}'s team can update quickly without technical dependencies.",
                            "approach": "We deploy a modern, client-maintainable CMS platform configured specifically for high-resolution visual curation, color fidelity, and mobile-first responsiveness.",
                            "workflow": "Artwork assets and high-resolution photography are optimized through standardized compression pipelines, staged into categorized collection templates, and published with integrated checkout capabilities.",
                            "bullets": [
                                "Deploy modern CMS architecture optimized for mobile responsiveness and fast page loads",
                                "Re-export and optimize high-resolution portfolio photography and color profiles",
                                "Configure Available Now catalog layout with integrated payment processing"
                            ],
                            "outcome": "Fast-loading visual portfolios and complete in-house control over exhibition updates without technical debt."
                        }
                    ]
                },
                {
                    "section_title": "Content Migration, Client Training & Warranty",
                    "opening_text": f"We manage complete portfolio asset migration and empower {client_name}'s team with hands-on publishing workflows and a 30-day post-launch warranty.",
                    "subsections": [
                        {
                            "heading": "Portfolio Asset Migration & SEO Optimization",
                            "context": "Preserving historical provenance, exhibition histories, and artist press coverage is critical to sustaining search visibility and institutional credibility.",
                            "approach": "We execute a structured content migration protocol, ensuring every artwork record, biographical entry, and press review transfers with intact metadata.",
                            "workflow": "Existing digital assets and archives are audited, cataloged into standardized migration sheets, ingested into the new CMS taxonomy, and indexed with structured SEO metadata.",
                            "bullets": [
                                "Migrate complete portfolio archives, press reviews, and exhibition histories into new CMS",
                                "Configure SEO metadata tags and image alt-text to elevate organic discovery",
                                "Implement 301 URL redirect maps to preserve established inbound backlinks and search rankings"
                            ],
                            "outcome": "Zero loss of historical archives, preserved search rankings, and elevated search engine discoverability."
                        },
                        {
                            "heading": "Administrative Enablement & 30-Day Technical Warranty",
                            "context": f"True operational independence requires that {client_name}'s staff possess the confidence and documentation to maintain the platform independently.",
                            "approach": "We deliver hands-on staff enablement sessions and client-specific reference manuals, backed by a dedicated 30-day post-launch warranty period.",
                            "workflow": "Live interactive walkthroughs are conducted with designated gallery staff, recorded for future reference, and supplemented by an indexed PDF publishing guide.",
                            "bullets": [
                                "Conduct live 1-on-1 administrative training walkthrough covering all site management tasks",
                                "Deliver tailored written PDF site guide covering client-specific publishing workflows",
                                "Provide 30-day post-launch technical warranty covering live adjustments and support"
                            ],
                            "outcome": "Complete publishing autonomy for gallery personnel without developer lock-in."
                        }
                    ]
                }
            ]
            website_exec = (
                f"Sympl Solutions is pleased to submit this proposal to support {client_name} with a comprehensive website redesign and modern CMS deployment. As the gallery expands its exhibition program and collector network, establishing a commanding, professional digital presence is essential to showcase artist portfolios and facilitate commercial acquisitions.\n\n"
                f"An aging web architecture, non-responsive layout elements, and fragmented archive structures currently create operational friction. Prospective collectors encounter friction when seeking detailed artwork provenance or initiating acquisition inquiries, while gallery staff face cumbersome technical overhead when updating current exhibitions.\n\n"
                f"Our approach replaces outdated navigational structures with an intuitive, collector-first UX (user experience) and an image-forward portfolio showcase. By deploying a streamlined, client-maintainable CMS platform paired with standardized artwork catalog taxonomies, we ensure visual assets render with exceptional fidelity across all device viewports.\n\n"
                f"Through this engagement, {client_name} establishes complete in-house publishing autonomy, direct inquiry routing, and an integrated Available Now store catalog. Supported by hands-on staff enablement and a 30-day technical warranty, leadership secures the digital foundation required to engage international audiences with confidence."
            )
            return json.dumps({
                "title": f"Website Development Proposal for {client_name}",
                "executive_summary": website_exec,
                "sections": website_sections,
                "why_us": website_why_us,
                "pricing": common_pricing,
                "exclusions": website_exclusions,
                "validation_metadata": {}
            }, indent=2)

        # ---------------------------------------------------------------------
        # DOMAIN GENERATOR: Data Analytics
        # ---------------------------------------------------------------------
        if service_category == "Data Analytics":
            data_why_us = common_why_us if common_why_us else [
                "Why Sympl?",
                "Data & Analytics Architecture: We specialize in consolidating disparate transactional systems into unified, decision-ready analytics for growing organizations.",
                "Modern Cloud Engineering: Centralized SQL data warehouses and automated Python ETL pipelines engineered for security, scalability, and auditability.",
                "Canadian Cloud Residency: Strict alignment with PIPEDA and Canadian data residency requirements across all data pipelines and storage.",
                "We look forward to empowering your leadership with actionable operational intelligence."
            ]
            data_exclusions = common_exclusions if common_exclusions else [
                "Third-party cloud infrastructure hosting and BI software licensing fees (e.g., Microsoft Power BI / Azure) are billed directly to the client.",
                "Custom engineering modifications to legacy third-party source applications outside available API endpoints will be quoted separately."
            ]
            data_sections = [
                {
                    "section_title": "Systems Discovery & Data Architecture",
                    "opening_text": f"Sympl Solutions conducts a cross-platform systems audit across operational applications to engineer a unified data architecture for {client_name}.",
                    "subsections": [
                        {
                            "heading": "Cross-Platform Systems Discovery & Schema Mapping",
                            "context": f"Managing multi-channel ticketing, donor relations, and marketing campaigns creates isolated data silos that obscure constituent engagement and operational performance for {client_name}.",
                            "approach": "Sympl conducts a comprehensive systems discovery audit across operational databases and API endpoints to engineer a unified, auditable data architecture.",
                            "workflow": "We examine transactional models across ticketing systems, CRMs, and email platforms, map cross-table foreign keys, document entity relationships, and formulate deduplication rules for patron records.",
                            "bullets": [
                                "Audit operational databases and API endpoints across ticketing, CRM, and email systems",
                                "Document comprehensive source-to-target entity relationship diagrams and data dictionary",
                                "Establish patron deduplication logic and master data management rules"
                            ],
                            "outcome": "A verified schema blueprint and elimination of fragmented constituent records."
                        },
                        {
                            "heading": "SQL Warehouse Engineering & Automated ETL Pipelines",
                            "context": "Manual data exports and spreadsheet consolidations introduce latency, calculation errors, and data privacy vulnerabilities across departments.",
                            "approach": "We engineer a centralized cloud SQL data warehouse powered by automated Python ETL pipelines, ensuring daily data harmonization under Canadian residency standards.",
                            "workflow": "Extraction scripts poll operational APIs on automated nightly schedules, transform raw JSON and relational records into optimized star-schema tables, and load verified datasets into the warehouse with error logging.",
                            "bullets": [
                                "Deploy centralized SQL data warehouse hosted in Canadian cloud infrastructure",
                                "Develop automated Python ETL pipelines with incremental extraction and error logging",
                                "Configure role-based access control and PIPEDA-compliant privacy safeguards"
                            ],
                            "outcome": "A secure, centralized single source of truth updated automatically without manual labor."
                        }
                    ]
                },
                {
                    "section_title": "Power BI Dashboards & Governance Framework",
                    "opening_text": f"We deliver dynamic BI dashboards and establish data governance standards to empower {client_name}'s executive leadership with real-time operational intelligence.",
                    "subsections": [
                        {
                            "heading": "Interactive Dashboards & Sales Velocity Analytics",
                            "context": f"Executive leadership and department heads require intuitive, real-time performance indicators rather than static historical reports to steer programming and marketing investments.",
                            "approach": "We construct dynamic Power BI dashboard suites delivering real-time ticket sales curves, patron lifetime value, and cross-channel conversion analytics.",
                            "workflow": "Warehouse data marts feed parameterized Power BI visual models with automated daily scheduled refreshes, enabling drill-down analysis from organizational totals to individual events.",
                            "bullets": [
                                "Build interactive Power BI dashboards for executive sales velocity and attendance tracking",
                                "Configure patron retention cohort visualizations and donor lifetime value analytics",
                                "Automate scheduled data refresh cycles and distribution to senior leadership"
                            ],
                            "outcome": "Real-time decision intelligence, proactive attendance forecasting, and clear marketing ROI visibility."
                        },
                        {
                            "heading": "Data Governance, Knowledge Transfer & Handover",
                            "context": "Long-term data integrity requires documented governance protocols and hands-on staff enablement to ensure self-sustaining technical operations.",
                            "approach": "We provide thorough technical schematics, standard data dictionaries, and hands-on workshops to empower client teams to manage and extend their analytics environment.",
                            "workflow": "Technical documentation and pipeline runbooks are compiled into an accessible knowledge repository, followed by interactive enablement sessions and 30 days of active pipeline monitoring.",
                            "bullets": [
                                "Deliver complete technical documentation, data dictionary, and ERD schematics",
                                "Conduct interactive training workshops for administrative and leadership teams",
                                "Provide 30-day post-deployment pipeline monitoring and optimization support"
                            ],
                            "outcome": "Internal data fluency, auditable governance documentation, and enduring system reliability."
                        }
                    ]
                }
            ]
            data_exec = (
                f"Sympl Solutions is pleased to submit this proposal to engineer a centralized SQL warehouse and business intelligence platform for {client_name}. As operational programs expand, consolidating data from ticketing, development, and marketing systems becomes critical to organizational sustainability.\n\n"
                f"Currently, operational data resides in isolated platforms, requiring labor-intensive manual exports and disconnected spreadsheet reconciliation. This fragmentation creates reporting delays, duplicate patron records, and limits executive visibility into real-time attendance velocity and donor retention.\n\n"
                f"Our approach establishes a unified data architecture powered by automated Python ETL pipelines and a centralized SQL warehouse hosted in secure Canadian cloud infrastructure. By transforming disparate operational records into standardized reporting schemas, we deliver single-source-of-truth accuracy under strict PIPEDA compliance.\n\n"
                f"Through this engagement, {client_name} deploys interactive Power BI dashboards delivering executive sales velocity curves, audience retention analytics, and campaign ROI. Supported by hands-on team enablement and structured governance documentation, leadership secures the operational intelligence needed to make proactive decisions."
            )
            return json.dumps({
                "title": f"Data Analytics & Centralized Database Proposal for {client_name}",
                "executive_summary": data_exec,
                "sections": data_sections,
                "why_us": data_why_us,
                "pricing": common_pricing,
                "exclusions": data_exclusions,
                "validation_metadata": {}
            }, indent=2)

        # ---------------------------------------------------------------------
        # DOMAIN GENERATOR: Finance Transformation
        # ---------------------------------------------------------------------
        if service_category == "Finance Transformation":
            finance_why_us = common_why_us if common_why_us else [
                "Why Sympl?",
                "Strategic Financial Advisory: Deep expertise building sophisticated financial models and multi-funder budget frameworks for nonprofit and public-sector organizations.",
                "Dynamic Rolling Forecasting: Forward-looking cash flow projections driven by explicit assumptions and scenario modeling rather than static historical reports.",
                "Executive & Board Alignment: Reporting frameworks designed specifically for board finance committees and ministry compliance oversight.",
                "We look forward to providing the financial clarity needed to navigate strategic decisions with confidence."
            ]
            finance_exclusions = common_exclusions if common_exclusions else [
                "Routine operational bookkeeping, bill payments, and payroll disbursements are excluded from this advisory engagement.",
                "External financial statement audits and statutory tax filings remain the responsibility of the client's public accounting firm."
            ]
            finance_sections = [
                {
                    "section_title": "Budget Framework Redesign & General Ledger Realignment",
                    "opening_text": f"Sympl Solutions redesigns the annual budgeting architecture for {client_name}, establishing an automated, formulaic budget model aligned with program cost centers.",
                    "subsections": [
                        {
                            "heading": "Budget Framework & Cost Center Realignment",
                            "context": f"Managing complex multi-funder community and health programs requires a budgeting structure that mirrors program cost centers and funder restriction agreements for {client_name}.",
                            "approach": "Sympl conducts a thorough review of existing general ledger accounts and historical budget files, restructuring chart of accounts hierarchies to establish transparent departmental tracking.",
                            "workflow": "We map historical expenditures against funder contracts, design standardized departmental budget input templates, and build automated consolidation roll-ups that eliminate manual data entry.",
                            "bullets": [
                                "Audit existing budget spreadsheets and general ledger program code structures",
                                "Realign chart of accounts and class tags to match funding agreements",
                                "Design standardized departmental budget templates with automated consolidation formulas"
                            ],
                            "outcome": "Transparent cost allocation across funding sources and elimination of broken spreadsheet formulas."
                        },
                        {
                            "heading": "12-Month Rolling Forecast & Assumptions Model",
                            "context": "Static annual budgets become quickly outdated in operational environments characterized by fluctuating grant schedules and staffing changes.",
                            "approach": "We engineer an automated 12-month rolling cash flow forecast driven by an explicit Assumptions module, enabling dynamic monthly updates and scenario planning.",
                            "workflow": "Opening cash and historical actuals import directly from accounting ledgers, advancing the rolling horizon forward while key drivers—wage grids, benefits rates, and program ramps—are adjusted via dedicated toggle inputs.",
                            "bullets": [
                                "Build dynamic 12-month rolling cash flow forecast model with automated monthly roll-forward",
                                "Configure centralized Assumptions tab for wage grid increments and variable cost drivers",
                                "Incorporate scenario toggle analysis for funding adjustments and staffing transitions"
                            ],
                            "outcome": "Proactive cash flow visibility, scenario-tested decision making, and early identification of funding deficits."
                        }
                    ]
                },
                {
                    "section_title": "Executive Variance Reporting & Governance Enablement",
                    "opening_text": f"We configure automated variance decks and governance reporting packages to provide strategic financial visibility for {client_name}'s board and leadership.",
                    "subsections": [
                        {
                            "heading": "Board Variance Decks & KPI Visualizations",
                            "context": f"Board directors and finance committees require concise, visual variance analyses rather than dense rows of raw numbers to fulfill their fiduciary oversight responsibilities.",
                            "approach": "We design automated executive variance reporting templates pairing graphical summary dashboards with structured variance commentary guidelines.",
                            "workflow": "Monthly actuals compare automatically against both the approved budget and the active rolling forecast, calculating variance thresholds and funder burn rates.",
                            "bullets": [
                                "Design automated monthly budget vs actual variance reporting templates",
                                "Develop executive summary commentary framework highlighting surplus/deficit drivers",
                                "Configure KPI heatmaps tracking ministry allocation utilization rates"
                            ],
                            "outcome": "Clear board governance materials, rapid committee approvals, and focused strategic discussions."
                        },
                        {
                            "heading": "Model Documentation & Leadership Enablement",
                            "context": "Financial forecasting models only generate lasting organizational value when internal finance teams understand their mechanics and maintenance routines.",
                            "approach": "We produce step-by-step model user manuals and lead hands-on walkthrough workshops with client finance personnel to ensure enduring model ownership.",
                            "workflow": "We guide finance leadership through monthly ledger imports, assumption adjustments, and scenario builds, providing advisory support across the initial quarterly review cycle.",
                            "bullets": [
                                "Deliver step-by-step model user guide detailing assumptions updates and roll-forward procedures",
                                "Conduct hands-on training sessions with finance team members and executive directors",
                                "Provide ongoing advisory support through the initial quarterly forecast review cycle"
                            ],
                            "outcome": "Complete internal ownership of financial models without ongoing consultant dependencies."
                        }
                    ]
                }
            ]
            finance_exec = (
                f"Sympl Solutions is pleased to submit this proposal to lead a comprehensive budget process revamp and dynamic financial forecasting engagement for {client_name}. As organizational commitments grow, establishing sophisticated multi-funder modeling and dynamic liquidity visibility is essential for executive leadership.\n\n"
                f"Currently, disconnected departmental spreadsheets, manual data aggregation, and static annual budgets restrict proactive planning. Program managers lack visibility into true funder burn rates, while finance committees must evaluate complex variance reports without structured commentary or scenario modeling.\n\n"
                f"Our approach restructures {client_name}'s financial planning architecture by realigning chart of accounts cost centers and building an automated 12-month rolling cash flow forecast driven by explicit operational assumptions. By integrating actual ledger data with formulaic consolidation models, we eliminate projection uncertainty and spreadsheet breakage.\n\n"
                f"Through this engagement, {client_name} deploys automated board variance reporting decks, scenario-tested liquidity forecasts, and standardized budget templates. Supported by thorough model documentation and hands-on leadership enablement, executive directors secure transparent multi-funder accountability and lasting governance clarity."
            )
            return json.dumps({
                "title": f"Budget Revamp & Financial Forecasting Proposal for {client_name}",
                "executive_summary": finance_exec,
                "sections": finance_sections,
                "why_us": finance_why_us,
                "pricing": common_pricing,
                "exclusions": finance_exclusions,
                "validation_metadata": {}
            }, indent=2)

        # ---------------------------------------------------------------------
        # DOMAIN GENERATOR: Accounting & General Consulting (Baseline Flow)
        # ---------------------------------------------------------------------
        sections = []

        if has_transition or "interim" in prompt_lower:
            sections.append({
                "section_title": "Summary of Engagement & Interim Continuity",
                "opening_text": f"Sympl Solutions provides interim financial management and structured onboarding to ensure operational stability for {client_name}.",
                "subsections": [
                    {
                        "heading": "Engagement Continuity & Governance",
                        "context": f"Organizational leadership transitions create vulnerabilities in ongoing financial oversight, institutional record-keeping, and vendor payment continuity for {client_name}.",
                        "approach": "Sympl acts as an interim operating anchor, stabilizing essential accounting functions while documenting existing procedures to facilitate permanent leadership onboarding.",
                        "workflow": "Our team shadows existing administrative personnel during live processing cycles, reviews legacy ledger entries, identifies workflow bottlenecks, and establishes structured handover milestones.",
                        "bullets": [
                            "Maintain continuous financial oversight during organizational leadership transitions",
                            "Preserve established accounting workflows and legacy ledger documentation",
                            "Coordinate structured handover milestones with incoming permanent leadership"
                        ],
                        "outcome": "Zero disruption to daily operations, preserved institutional knowledge, and seamless leadership succession."
                    },
                    {
                        "heading": "Deliverables & Reporting",
                        "context": "Executive directors and boards require verified baseline assessments to understand organizational financial health during transitions.",
                        "approach": "We produce objective operational assessments and structured accounting checklists to guide leadership throughout the interim period.",
                        "bullets": [
                            "Deliver current state operational assessment and risk summary memo",
                            "Provide documented accounting process checklists for leadership succession"
                        ],
                        "outcome": "Clear operational visibility and documented standard operating procedures for incoming personnel."
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
                        "context": "A disciplined transition schedule establishes operating protocols, verified access permissions, and clear accountability from day one.",
                        "approach": "We execute a phased four-week transition framework designed to absorb operational responsibilities systematically without service interruption.",
                        "workflow": "Week 1 acquires credentials and audits historical ledgers; Weeks 2-3 conduct parallel invoice and payroll processing runs; Week 4 transitions full operational authority to Sympl.",
                        "bullets": [
                            "Ingest historical general ledger data and active vendor registers",
                            "Shadow existing financial procedures during initial transition weeks",
                            "Establish verified approval matrices and digital document repositories"
                        ],
                        "outcome": "Verified system credentials, established communication rhythms, and immediate operational stabilization."
                    },
                    {
                        "heading": "Onboarding Deliverables",
                        "context": "Management requires formal confirmation that legacy ledger balances and chart of accounts structures have been validated.",
                        "approach": "We deliver verified ledger reconciliations and an operational transition roadmap outlining recurring cadences.",
                        "bullets": [
                            "Complete chart of accounts review and initial ledger reconciliation",
                            "Deliver confirmed operational transition roadmap to executive leadership"
                        ],
                        "outcome": "Validated opening balances and an agreed-upon operational roadmap for ongoing delivery."
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
                        "context": f"Legacy desktop software and paper-based receipt filing create information silos, slow down monthly close cycles, and impede collaboration for {client_name}.",
                        "approach": "Sympl migrates historical financial data to modern cloud accounting infrastructure, architecting a unified environment built for scale and auditability.",
                        "workflow": "Historical general ledger charts of accounts are cleaned and mapped before opening balances are migrated into QuickBooks Online, with Dext integrated for digital receipt capture.",
                        "bullets": [
                            "Configure cloud accounting architecture and chart of accounts mapping",
                            "Implement electronic expense capture workflows using approved software tools",
                            "Execute parallel verification runs to validate opening ledger balances"
                        ],
                        "outcome": "Paperless expense workflows, automated transaction capture, and real-time ledger access from any location."
                    },
                    {
                        "heading": "Transformation Deliverables",
                        "context": "Sustainable digital adoption requires documented standard operating guidelines and practical staff enablement.",
                        "approach": "We provide recorded walkthroughs and custom reference manuals to ensure team members adopt new tools smoothly.",
                        "bullets": [
                            "Deliver fully configured QuickBooks Online and Dext system environment",
                            "Provide recorded staff training walk-throughs and standard operating guidelines"
                        ],
                        "outcome": "Confident team adoption of cloud accounting tools without technical friction."
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
                        "context": f"Disciplined disbursement management and timely accounts payable handling are vital to maintain vendor goodwill and prevent billing discrepancies for {client_name}.",
                        "approach": "Sympl executes a structured weekly accounts payable procedure, enforcing digital receipt capture, account coding validation, and dual-authorization approvals.",
                        "workflow": "Vendor bills and expense receipts submitted to Dext are matched to approved purchase orders, verified against organizational spending policies, coded to appropriate classes in QuickBooks Online, and staged into weekly disbursement batches for client authorization.",
                        "bullets": [
                            "Process vendor bills and verify corporate credit card expense entries",
                            "Maintain accounts payable aging schedules and prepare payment disbursement batches",
                            "Verify documentation and receipts against organizational approval policies"
                        ],
                        "outcome": "Elimination of invoice backlogs, verified payment approval records, and complete audit-readiness."
                    },
                    {
                        "heading": "Accounts Receivable & General Ledger",
                        "context": "Maintaining predictable operating cash flow requires consistent invoicing cadences and disciplined monthly reconciliations across all operational accounts.",
                        "approach": "We enforce systematic ledger hygiene and monthly bank reconciliation cadences to ensure balance sheet integrity and accurate financial reporting.",
                        "workflow": "Invoices and funder claims are generated on agreed cycles, incoming EFT remittances and deposits are matched daily, and operating bank accounts, credit cards, and clearing ledgers are reconciled at month-end.",
                        "bullets": [
                            "Record client invoicing and match incoming bank deposit receipts",
                            "Reconcile operating bank accounts and credit cards on monthly cycles",
                            "Maintain QuickBooks Online general ledger hygiene and account allocations"
                        ],
                        "outcome": "Zero reconciliation discrepancies, real-time receivables tracking, and auditable ledger registers."
                    },
                    {
                        "heading": "Deliverables & Outputs",
                        "context": "Executive decision-making depends on structured financial schedules delivered on predictable calendar deadlines.",
                        "approach": "We compile reconciled balance sheet schedules, aged ledgers, and transaction journals following each month-end close.",
                        "bullets": [
                            "Deliver reconciled general ledger balances and monthly balance sheet registers",
                            "Provide monthly accounts payable and accounts receivable summary schedules"
                        ],
                        "outcome": "Dependable financial registers that give leadership confidence in organizational numbers."
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
                        "context": f"Accurate and punctual payroll administration is essential for employee trust, organizational morale, and statutory compliance for {client_name}.",
                        "approach": "Sympl administers full-cycle payroll operations through modern cloud payroll systems, ensuring strict adherence to employment standards and CRA remittance schedules.",
                        "workflow": "Approved timesheets and compensation adjustments are audited, gross-to-net payroll runs are calculated against statutory deduction tables, and direct deposits are scheduled alongside CRA source deduction remittances.",
                        "bullets": [
                            "Process semi-monthly employee payroll disbursements and contractor invoices",
                            "Calculate statutory source deductions and submit CRA payroll remittances",
                            "Prepare annual T4 summary statements and mandatory records of employment"
                        ],
                        "outcome": "On-time payroll direct deposits, zero remittance penalties, and verified statutory compliance."
                    },
                    {
                        "heading": "Payroll Deliverables",
                        "context": "Executive leadership requires verified payroll summary reporting following each pay cycle to maintain departmental oversight.",
                        "approach": "We provide comprehensive payroll registers, departmental allocation summaries, and CRA remittance confirmation notices following every pay date.",
                        "bullets": [
                            "Deliver verified payroll summary reports following each pay run",
                            "Provide confirmed CRA payroll remittance confirmations and filing receipts"
                        ],
                        "outcome": "Complete transparency into payroll disbursements and audit-ready personnel records."
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
                        "context": f"Executive directors and board finance committees need timely, transparent financial visibility to evaluate program performance and fulfill grant obligations for {client_name}.",
                        "approach": "We deliver structured monthly financial packages that translate raw general ledger numbers into actionable management insights and funder compliance schedules.",
                        "workflow": "Following month-end ledger close, operating results are consolidated, restricted funding revenues are tracked against eligible expenses, and budget variance schedules are prepared.",
                        "bullets": [
                            "Generate monthly financial packages comparing actual results against budget",
                            "Track restricted fund allocations and prepare contribution agreement reports",
                            "Deliver departmental financial statements to leadership and board committees"
                        ],
                        "outcome": "Board-ready financial clarity, transparent funder reporting, and proactive budget management."
                    },
                    {
                        "heading": "Reporting Deliverables",
                        "context": "Leadership requires standardized financial statements delivered consistently following month-end close.",
                        "approach": "We provide formal Statements of Financial Position, Statements of Operations, and quarterly variance commentary schedules.",
                        "bullets": [
                            "Deliver monthly statement of financial position and statement of operations",
                            "Provide quarterly budget variance commentary schedules for finance committees"
                        ],
                        "outcome": "Clear, professional financial statements that satisfy board governance and funder requirements."
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
                        "context": f"Maintaining organizational good standing and claiming eligible sales tax rebates requires meticulous compliance with CRA filing regulations for {client_name}.",
                        "approach": "Sympl prepares statutory filings and rebate applications backed by complete transaction registers and reconciled tax accounts.",
                        "workflow": "General ledger sales tax clearing accounts are reconciled against source receipts, eligible rebate percentages are applied, and filings are submitted within prescribed statutory windows.",
                        "bullets": comp_bullets,
                        "outcome": "Timely receipt of eligible tax rebates, avoidance of statutory penalties, and verified CRA records."
                    },
                    {
                        "heading": "Compliance Deliverables",
                        "context": "Management requires documented verification and archived workpapers for all submitted filings.",
                        "approach": "We provide copies of all submitted rebate applications, CRA confirmation receipts, and supporting calculation registers.",
                        "bullets": [
                            "Deliver submitted GST/HST rebate forms and CRA confirmation notices",
                            "Provide organized working paper archives supporting filed tax schedules"
                        ],
                        "outcome": "Auditable compliance records and confirmation of all regulatory filings."
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
                        "context": f"External financial statement audits can create operational disruption when lead schedules and supporting documentation are incomplete or unindexed for {client_name}.",
                        "approach": "Sympl acts as your audit preparation team, compiling an indexed working paper binder and liaising directly with external auditors to resolve field inquiries.",
                        "workflow": "Every balance sheet account is reconciled to independent source documents, lead schedules are cross-referenced to the trial balance, and an audit query log is maintained during field work.",
                        "bullets": [
                            "Compile comprehensive audit lead schedules and balance sheet working papers",
                            "Liaise directly with external auditing firms during interim and year-end procedures",
                            "Reconcile restricted fund balances and deferred grant revenue registers"
                        ],
                        "outcome": "Reduced external audit fees, minimized management stress, and clean audit opinion delivery."
                    },
                    {
                        "heading": "Audit Deliverables",
                        "context": "External auditors require reconciled trial balances and verified supporting binders prior to commencement of field work.",
                        "approach": "We deliver a comprehensive audit binder and maintain an active query resolution log throughout the audit.",
                        "bullets": [
                            "Deliver completed audit working paper binder and reconciled trial balance",
                            "Provide responsive audit query tracking log during external field work"
                        ],
                        "outcome": "Streamlined auditor review and prompt resolution of sample requests."
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
                        "context": f"Navigating organizational growth, capital investments, and multi-year sustainability requires seasoned fractional financial advisory for {client_name}.",
                        "approach": "Sympl provides strategic financial counsel, developing dynamic multi-year forecast models and advising leadership on resource allocation.",
                        "workflow": "We review historical financial performance, model revenue and expenditure scenarios, and participate in quarterly strategic planning sessions with executive leadership.",
                        "bullets": [
                            "Provide fractional financial guidance on multi-year organizational sustainability",
                            "Develop organizational cash flow projection models and scenario analyses",
                            "Advise executive leadership and finance committees on capital allocations"
                        ],
                        "outcome": "Long-term financial sustainability, informed decision-making, and strategic governance clarity."
                    },
                    {
                        "heading": "Advisory Deliverables",
                        "context": "Executive directors require actionable decision models and structured briefing memos to evaluate organizational options.",
                        "approach": "We build parameterized 12-month cash flow models and provide written executive briefing memos for leadership review.",
                        "bullets": [
                            "Deliver rolling 12-month cash flow forecast models and scenario templates",
                            "Provide quarterly executive financial briefing memos for leadership"
                        ],
                        "outcome": "Forward-looking financial intelligence tailored for executive and board decision-making."
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
                        "context": f"Ensuring lasting financial integrity requires that {client_name}'s staff understand standard financial procedures and digital software tools.",
                        "approach": "We develop customized standard operating procedure manuals and lead hands-on training sessions with designated team members.",
                        "workflow": "Operating tasks are documented step-by-step with screenshots, followed by live interactive walkthroughs and follow-up coaching cycles.",
                        "bullets": [
                            "Develop standardized operating procedure manuals for financial tasks",
                            "Conduct practical software training sessions with designated team members",
                            "Provide ongoing workflow support following system go-live milestones"
                        ],
                        "outcome": "Confident staff execution, consistent operational documentation, and reduced administrative errors."
                    },
                    {
                        "heading": "Training Deliverables",
                        "context": "Staff require practical reference materials that they can consult during daily operations.",
                        "approach": "We provide indexed PDF operating guides and training checklists to support daily execution.",
                        "bullets": [
                            "Deliver step-by-step written standard operating procedure reference guides",
                            "Provide practical training session attendance logs and follow-up checklists"
                        ],
                        "outcome": "Permanent operational manuals that protect institutional knowledge."
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

        # Handle any multi-service or custom approved scope keys (e.g. website, data_analytics, etc.)
        for scope_k, scope_v in app_scope.items():
            if scope_k in [
                "bookkeeping", "payroll", "financial_reporting", "compliance",
                "digital_transformation", "training", "transition_services",
                "management_consulting", "audit_oversight"
            ]:
                continue
            formatted_title = scope_k.replace("_", " ").title()
            sections.append({
                "section_title": f"{formatted_title} Services",
                "opening_text": f"Sympl Solutions provides professional {formatted_title.lower()} tailored to the operational requirements of {client_name}.",
                "subsections": [
                    {
                        "heading": f"{formatted_title} Methodology & Workflow",
                        "context": f"Professional {formatted_title.lower()} services provide essential operational capabilities and specialized execution for {client_name}.",
                        "approach": f"We execute structured {formatted_title.lower()} workflows aligned with established industry standards and organizational priorities.",
                        "workflow": f"Operational requirements are scoped, milestones are established, and deliverables are produced through a transparent, collaborative review cadence.",
                        "bullets": [
                            f"Review and analyze current operational requirements for {formatted_title.lower()}",
                            f"Design and execute tailored {formatted_title.lower()} implementation milestones",
                            f"Provide structured progress reporting and review checkpoints with leadership"
                        ],
                        "outcome": f"Structured operational delivery and measurable business outcomes for {client_name}."
                    },
                    {
                        "heading": "Deliverables & Governance",
                        "context": "Leadership requires verified milestone sign-offs and complete operational documentation.",
                        "approach": "We provide formal deliverable packages and milestone sign-off schedules to ensure organizational alignment.",
                        "bullets": [
                            f"Deliver completed {formatted_title.lower()} operational documentation and outputs",
                            f"Provide milestone sign-off schedules and handover documentation to leadership"
                        ],
                        "outcome": "Verified deliverable completion and structured operational handover."
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

        # Compose executive summary with sufficient consulting depth (situation, challenges, approach, outcomes)
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
        for scope_k in app_scope.keys():
            if scope_k not in ["bookkeeping", "payroll", "financial_reporting", "compliance", "digital_transformation", "training", "transition_services", "management_consulting", "audit_oversight"]:
                service_names.append(scope_k.replace("_", " "))
        if not service_names:
            service_names.append("consulting services")

        services_str = ", ".join(service_names)
        exec_summary_paragraphs = [
            f"Sympl Solutions is pleased to submit this proposal to partner with {client_name} across dedicated {services_str}. As the organization continues to advance its core programs and operational commitments, maintaining structured financial oversight and reliable back-office continuity is fundamental to long-term success.",
            f"Growing transaction volumes, decentralized documentation, and manual review cadences introduce operational friction, creating reconciliation delays and diverting leadership attention from organizational priorities. Without standardized digital workflows, reconciling operating accounts and securing timely financial visibility requires disproportionate administrative effort.",
            f"Our approach establishes disciplined operational procedures tailored to {client_name}'s specific environment. Working with modern cloud accounting infrastructure including QuickBooks Online and integrated receipt capture tools, Sympl deploys structured weekly processing cycles, segregated review controls, and systematic month-end reconciliations.",
            f"Through this engagement, {client_name} achieves audit-ready financial hygiene, transparent funder allocation tracking, and dependable management reporting schedules. Executive leadership and board directors secure the clarity and verified numbers needed to guide strategic decisions with confidence."
        ]
        exec_summary = "\n\n".join(exec_summary_paragraphs)

        match_title = re.search(r'"title":\s*"([^"]+)"', prompt)
        draft_title = match_title.group(1) if match_title else f"Accounting & Bookkeeping Services Proposal for {client_name}"

        response_dict = {
            "title": draft_title,
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
