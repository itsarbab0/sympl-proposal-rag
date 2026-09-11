"""
Sympl Solutions — Generic Canva Proposal Schema
Provides intermediate normalized representation decoupling ProposalDraft JSON from specific Canva templates.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import re


@dataclass
class CanvaCoverData:
    client_name: str
    proposal_title: str
    service_category: str
    date: str


@dataclass
class CanvaExecutiveSummaryData:
    title: str = "Executive Summary"
    paragraphs: List[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(self.paragraphs)


@dataclass
class CanvaDeliverableRow:
    component: str
    description: str


@dataclass
class CanvaServiceModule:
    service_number: int
    title: str
    context: str = ""
    approach: str = ""
    workflow: str = ""
    outcome: str = ""
    bullets: List[str] = field(default_factory=list)
    deliverables: List[CanvaDeliverableRow] = field(default_factory=list)


@dataclass
class CanvaMethodologyPhase:
    phase_name: str
    description: str


@dataclass
class CanvaMethodologyData:
    title: str = "Our Process"
    intro: str = ""
    phases: List[CanvaMethodologyPhase] = field(default_factory=list)


@dataclass
class CanvaTimelineItem:
    cadence: str
    phase: str
    deliverables: str


@dataclass
class CanvaTimelineData:
    title: str = "Proposed Timeline"
    intro: str = ""
    items: List[CanvaTimelineItem] = field(default_factory=list)
    disclaimer: str = ""


@dataclass
class CanvaMilestoneItem:
    label: str
    trigger: str
    amount: str


@dataclass
class CanvaPricingData:
    title: str = "Cost & Payment Schedule"
    intro: str = ""
    investment_heading: str = "TOTAL PROJECT INVESTMENT"
    investment_amount: str = "$0"
    investment_description: str = ""
    schedule_header: str = "Fee Schedule"
    milestones: List[CanvaMilestoneItem] = field(default_factory=list)
    exclusions_note: str = ""


@dataclass
class CanvaProposalData:
    cover: CanvaCoverData
    executive_summary: CanvaExecutiveSummaryData
    services: List[CanvaServiceModule] = field(default_factory=list)
    methodology: CanvaMethodologyData = field(default_factory=CanvaMethodologyData)
    timeline: CanvaTimelineData = field(default_factory=CanvaTimelineData)
    pricing: CanvaPricingData = field(default_factory=CanvaPricingData)
    client_assets: Dict[str, str] = field(default_factory=dict)
    raw_draft: Dict[str, Any] = field(default_factory=dict)


def compress_commercial_description(desc: str, max_words: int = 15) -> str:
    """
    Compresses commercial proposal investment description to strictly <= max_words (default 15)
    to prevent visual overlap on Canva template commercial pages.
    """
    cleaned = " ".join(desc.strip().split())
    words = cleaned.split()
    if len(words) <= max_words:
        return cleaned

    # Rule-based compression preserving deliverables and terms
    # E.g. replace verbose phrasing with punchy concise summaries
    replacements = [
        ("Comprehensive recurring accounting, general ledger, and financial operations as scoped.", "Includes full general ledger maintenance, monthly reconciliations, payroll, and reporting."),
        ("Comprehensive monthly bookkeeping, general ledger, reconciliations, contractor payroll, and committee reporting.", "Includes GL maintenance, reconciliations, payroll administration, reporting, and audit defense."),
        ("Fixed monthly fee. Includes general ledger management, monthly multi-account reconciliations, contractor payroll, monthly Financial Committee reporting, and ongoing audit defense.", "Fixed monthly fee covering general ledger maintenance, multi-account reconciliations, payroll, committee reporting, and audit support.")
    ]
    for orig, repl in replacements:
        if orig.lower() in cleaned.lower():
            words_repl = repl.split()
            if len(words_repl) <= max_words:
                return repl

    # Truncate cleanly at word boundary
    truncated = " ".join(words[:max_words])
    if not truncated.endswith("."):
        truncated += "..."
    return truncated


def draft_to_canva_data(draft: Dict[str, Any], client_assets: Optional[Dict[str, str]] = None) -> CanvaProposalData:
    """
    Converts a ProposalDraft dictionary into normalized CanvaProposalData.
    """
    title = draft.get("title") or draft.get("proposal_title") or "Professional Services Proposal"
    
    # 1. Extract Client Name
    client_name = "Client"
    if "for " in title:
        client_name = title.split("for ", 1)[1].strip()
    elif "Old Trout" in title or "OldT" in title:
        client_name = "Old Trout Puppet Workshop"
    elif "Crawford" in title:
        client_name = "Gary Crawford Art"
    elif "AKM" in title:
        client_name = "Aga Khan Museum"
    elif "Compass" in title:
        client_name = "Compass"

    # Clean service title
    if draft.get("proposal_title"):
        service_title = draft["proposal_title"]
    elif "for " in title:
        service_title = title.split("for ", 1)[0].strip()
    else:
        service_title = title

    category = "Bookkeeping & Financial Administration"
    if "Website" in title:
        category = "Website Design & Redesign"
    elif "Analytics" in title or "Database" in title:
        category = "Data Analytics & Centralized Systems"
    elif "Transformation" in title or "Forecasting" in title:
        category = "Financial Strategy & Transformation"

    cover = CanvaCoverData(
        client_name=client_name,
        proposal_title=service_title,
        service_category=category,
        date=datetime.now().strftime("%B %d, %Y")
    )

    # 2. Executive Summary
    raw_summary = draft.get("executive_summary") or ""
    paragraphs = [p.strip() for p in raw_summary.split("\n\n") if p.strip()]
    if len(paragraphs) == 1:
        # Split into logical paragraphs by sentence clusters
        sentences = [s.strip() + "." for s in raw_summary.split(". ") if s.strip()]
        if len(sentences) >= 6:
            chunk_size = len(sentences) // 3
            p1 = " ".join(sentences[:chunk_size])
            p2 = " ".join(sentences[chunk_size:chunk_size*2])
            p3 = " ".join(sentences[chunk_size*2:])
            paragraphs = [p1, p2, p3]

    exec_summary = CanvaExecutiveSummaryData(
        title="Executive Summary",
        paragraphs=paragraphs
    )

    # 3. Services & Scope
    services: List[CanvaServiceModule] = []
    raw_sections = draft.get("sections") or []
    for s in raw_sections:
        stitle = s.get("section_title") or s.get("section_name") or s.get("title") or ""
        # Filter out meta sections (Why Us, Pricing, Exclusions)
        if any(skip in stitle.lower() for skip in ["why", "pricing", "investment", "exclusion", "term"]):
            continue

        subs = s.get("subsections", [])
        combined_context = s.get("opening_text") or s.get("content") or ""
        combined_bullets = []
        for sub in subs:
            if sub.get("bullets"):
                combined_bullets.extend(sub["bullets"])

        mod = CanvaServiceModule(
            service_number=len(services) + 1,
            title=stitle,
            context=combined_context,
            bullets=combined_bullets
        )
        services.append(mod)

    # 4. Pricing
    raw_pricing = draft.get("pricing") or {}
    fee_items = raw_pricing.get("fee_items") or []
    
    investment_amount = raw_pricing.get("investment_amount") or "$1,100 / month"
    investment_desc = raw_pricing.get("investment_description") or "Fixed monthly retainer including reconciliations, payroll, and reporting."
    investment_heading = raw_pricing.get("investment_heading")
    milestones = []

    if raw_pricing.get("milestones"):
        for m in raw_pricing["milestones"]:
            milestones.append(CanvaMilestoneItem(
                label=m.get("label", "MILESTONE"),
                trigger=m.get("trigger", ""),
                amount=m.get("amount", "")
            ))
    elif fee_items:
        for item in fee_items:
            cat = item.get("category", "")
            amt = item.get("amount", 0)
            freq = item.get("billing_frequency", "")
            curr = item.get("currency", "CAD")
            desc = item.get("description", "")

            if freq == "monthly" or "retainer" in cat.lower():
                investment_amount = f"${int(amt):,} / month"
                investment_desc = desc or f"Fixed monthly retainer. Includes {cat.lower()} as scoped."
                milestones.append(CanvaMilestoneItem(
                    label="MONTHLY RETAINER",
                    trigger="Billed at the beginning of each service month.",
                    amount=f"${int(amt):,} / Month"
                ))
            elif freq == "one_time" or "setup" in cat.lower() or "onboarding" in cat.lower():
                milestones.append(CanvaMilestoneItem(
                    label="ONBOARDING & SETUP",
                    trigger="On contract signing, before work begins.",
                    amount=f"${int(amt):,} One-Time"
                ))

    if not milestones:
        milestones = [
            CanvaMilestoneItem("INITIATION", "On contract signing, before work begins.", "$3,500"),
            CanvaMilestoneItem("COMPLETION", "Project deliverable acceptance.", "$4,000")
        ]
        if not raw_pricing.get("investment_amount"):
            investment_amount = "$7,500"
        if not raw_pricing.get("investment_description"):
            investment_desc = "Fixed fee engagement. Covers complete end-to-end deliverables as scoped."

    # Exclusions
    exclusions = draft.get("exclusions") or []
    exclusions_note = (
        "Note on third-party costs & exclusions: Accounting software subscriptions, "
        "external auditor fees, and prior fiscal year tax filings are client-responsible expenses separate from this service retainer."
    )
    if exclusions:
        first_few = "; ".join(exclusions[:2])
        exclusions_note = f"Note on third-party costs & exclusions: {first_few}. Third-party software subscriptions are separate from this service fee."

    if not investment_heading:
        investment_heading = "MONTHLY RECURRING INVESTMENT" if "/ month" in investment_amount else "TOTAL PROJECT INVESTMENT"

    pricing = CanvaPricingData(
        title="Cost & Payment Schedule",
        intro="Services are priced as a predictable fixed retainer, ensuring transparency without hourly overages.",
        investment_heading=investment_heading,
        investment_amount=investment_amount,
        investment_description=compress_commercial_description(investment_desc, max_words=15),
        schedule_header="Fee Schedule",
        milestones=milestones[:2],
        exclusions_note=exclusions_note
    )

    # 5. Methodology & Process (6 Phases)
    methodology = CanvaMethodologyData(
        title="Our Process",
        intro="Our onboarding and monthly operating cadence follows a disciplined six-phase cycle designed for non-profit and mission-driven organizations.",
        phases=[
            CanvaMethodologyPhase("Phase 1: Discovery & Intake", "Kickoff meeting with leadership, system access setup, chart of accounts review, and prior audit analysis."),
            CanvaMethodologyPhase("Phase 2: System Clean-Up", "Resolution of historical ledger backlog, account re-alignment, and initial reconciliation catch-up."),
            CanvaMethodologyPhase("Phase 3: Workflow Setup", "Establishing invoice approval chains, payment schedules, and documentation protocols."),
            CanvaMethodologyPhase("Phase 4: Monthly Cadence", "Accrual transaction coding, regular accounts payable runs, and multi-account reconciliations."),
            CanvaMethodologyPhase("Phase 5: Financial Review", "Preparation and presentation of monthly financial packages for the Board Financial Committee."),
            CanvaMethodologyPhase("Phase 6: Year-End & Audit", "Year-end ledger close, digital working paper assembly, and direct liaison with external CPA auditor.")
        ]
    )

    # 6. Timeline (6 Items)
    timeline = CanvaTimelineData(
        title="Proposed Timeline",
        intro="The transition begins immediately upon agreement signing. The schedule below details onboarding, steady-state monthly operations, and year-end milestones.",
        items=[
            CanvaTimelineItem("Week 1 - 2", "Discovery & Access", "Initial kickoff call, granting accountant access to systems, bank feeds connected, and prior year review."),
            CanvaTimelineItem("Week 3 - 4", "System Clean-Up", "Chart of accounts optimized, historical transaction verification, and initial reconciliation catch-up."),
            CanvaTimelineItem("Month 2+", "Monthly Cadence", "Regular monthly bookkeeping, transaction coding, and multi-account reconciliations completed by Day 15."),
            CanvaTimelineItem("Monthly", "Financial Reporting", "Delivery of monthly Financial Committee package, project P&L reports, and cash flow commentary."),
            CanvaTimelineItem("Quarterly", "Statutory Filings", "GST/HST return working paper preparation and remittance verification filed on schedule."),
            CanvaTimelineItem("Year-End", "Audit Support", "Fiscal year-end ledger close and working paper coordination with external CPA auditor.")
        ],
        disclaimer="Timelines are subject to prompt access to banking records, source documentation, and existing accounting files."
    )

    return CanvaProposalData(
        cover=cover,
        executive_summary=exec_summary,
        services=services,
        methodology=methodology,
        timeline=timeline,
        pricing=pricing,
        client_assets=client_assets or {},
        raw_draft=draft
    )
