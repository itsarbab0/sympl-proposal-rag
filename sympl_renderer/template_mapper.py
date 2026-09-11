"""
Sympl Solutions Proposal RAG — Template Mapper Layer

Translates validated ProposalDraft into dynamic presentation pages:
  - Dynamically scales page count to match approved proposal sections (does not force 9 pages).
  - Preserves every piece of draft text, pricing, reference blocks, and exclusions verbatim.
  - Implements dynamic inclusion for Timeline (transformations), Why Us, and Service Details.
"""

import re
from typing import Dict, Any, List, Optional
from pathlib import Path

from sympl_renderer.schema import (
    RenderPage,
    RenderComponent,
    ComponentType,
    PageType
)
from sympl_renderer.branding import DEFAULT_BRANDING, SymplBranding


class TemplateMapper:
    """
    Compiles a validated ProposalDraft into a dynamic sequence of RenderPages.
    """

    def __init__(self, branding: Optional[SymplBranding] = None):
        self.branding = branding or DEFAULT_BRANDING

    def map_draft_to_pages(self, draft_data: Dict[str, Any]) -> List[RenderPage]:
        """
        Main mapping method. Ingests raw or parsed proposal_draft dictionary
        and returns the ordered list of RenderPage objects.
        """
        pages: List[RenderPage] = []
        page_num = 1

        title = draft_data.get("title") or draft_data.get("proposal_title") or "Operational Financial Services Proposal"
        client_name = self._extract_client_name(title, draft_data)
        sections = draft_data.get("sections") or []
        exec_summary = draft_data.get("executive_summary") or ""
        why_us = draft_data.get("why_us") or []
        pricing = draft_data.get("pricing") or {}
        exclusions = draft_data.get("exclusions") or []

        # ----------------------------------------------------------------------
        # 1. Cover Page (Always present)
        # ----------------------------------------------------------------------
        cover_page = self._build_cover_page(page_num, title, client_name)
        pages.append(cover_page)
        page_num += 1

        # ----------------------------------------------------------------------
        # 2. Executive Summary Page (Always present)
        # ----------------------------------------------------------------------
        exec_page = self._build_executive_summary_page(page_num, exec_summary, client_name, sections=sections)
        pages.append(exec_page)
        page_num += 1

        # ----------------------------------------------------------------------
        # 3. Services Overview: Standalone page omitted to prevent empty pages;
        # functional workstream summary is integrated into Executive Summary.
        # ----------------------------------------------------------------------

        # ----------------------------------------------------------------------
        # 4. Service Detail Pages (Dynamic: automatically paginated per section)
        # ----------------------------------------------------------------------
        for sec in sections:
            detail_pages = self._build_service_detail_pages(page_num, sec, client_name)
            pages.extend(detail_pages)
            page_num += len(detail_pages)

        # ----------------------------------------------------------------------
        # 5. Implementation Timeline Page (Dynamic: Transformation / Transition)
        # ----------------------------------------------------------------------
        if self._should_include_timeline(sections, draft_data):
            timeline_page = self._build_timeline_page(page_num, sections, client_name)
            pages.append(timeline_page)
            page_num += 1

        # ----------------------------------------------------------------------
        # 6. Why Sympl Page (Dynamic: Included only when Why Us present)
        # ----------------------------------------------------------------------
        if why_us:
            why_us_page = self._build_why_us_page(page_num, why_us, client_name)
            pages.append(why_us_page)
            page_num += 1

        # ----------------------------------------------------------------------
        # 7. Investment Schedule Page (Always present)
        # ----------------------------------------------------------------------
        pricing_page = self._build_pricing_page(page_num, pricing, client_name)
        pages.append(pricing_page)
        page_num += 1

        # ----------------------------------------------------------------------
        # 8. Terms & Exclusions Page (Dynamic: Included when exclusions exist)
        # ----------------------------------------------------------------------
        if exclusions:
            exclusions_page = self._build_exclusions_page(page_num, exclusions, client_name)
            pages.append(exclusions_page)
            page_num += 1

        # ----------------------------------------------------------------------
        # 9. Closing Page (Always present)
        # ----------------------------------------------------------------------
        closing_page = self._build_closing_page(page_num, client_name)
        pages.append(closing_page)
        page_num += 1

        return pages

    # --------------------------------------------------------------------------
    # Page Builders
    # --------------------------------------------------------------------------
    def _build_cover_page(self, page_num: int, title: str, client_name: str) -> RenderPage:
        components = [
            RenderComponent(
                component_id="cover_branding",
                component_type=ComponentType.HEADING,
                title=self.branding.company_name,
                content=self.branding.tagline,
                styling={"color": self.branding.colors.primary, "font_size": self.branding.typography.h2_size}
            ),
            RenderComponent(
                component_id="cover_title",
                component_type=ComponentType.HEADING,
                title=title,
                content=f"Prepared exclusively for {client_name}",
                styling={"color": self.branding.colors.primary, "font_size": self.branding.typography.title_size}
            ),
            RenderComponent(
                component_id="cover_footer",
                component_type=ComponentType.FOOTER,
                content=f"Confidential Proposal | {self.branding.company_name} | {self.branding.website}"
            )
        ]
        return RenderPage(
            page_number=page_num,
            page_type=PageType.COVER,
            page_title=title,
            page_subtitle="Proposal Submission",
            components=components
        )

    def _build_executive_summary_page(
        self,
        page_num: int,
        exec_summary: str,
        client_name: str,
        sections: Optional[List[Dict[str, Any]]] = None
    ) -> RenderPage:
        components = [
            RenderComponent(
                component_id="exec_summary_heading",
                component_type=ComponentType.HEADING,
                title="Executive Summary",
                content=f"Strategic Partnership & Operational Engagement for {client_name}",
                styling={"color": self.branding.colors.primary}
            ),
            RenderComponent(
                component_id="exec_summary_narrative",
                component_type=ComponentType.PARAGRAPH,
                content=exec_summary,
                styling={"color": self.branding.colors.neutral_dark, "font_size": self.branding.typography.body_size}
            )
        ]
        if sections:
            if len(sections) > 1:
                workstream_items = [
                    s.get("section_title", "") for s in sections if s.get("section_title")
                ]
                card_title = "Approved Functional Workstreams"
            else:
                subs = sections[0].get("subsections", [])
                sub_headings = [sub.get("heading", "") for sub in subs if sub.get("heading")]
                workstream_items = sub_headings[:5] if sub_headings else [sections[0].get("section_title", "")]
                card_title = f"Scope Focus: {sections[0].get('section_title', '')}"

            if workstream_items:
                components.append(RenderComponent(
                    component_id="exec_summary_workstreams",
                    component_type=ComponentType.CARD,
                    title=card_title,
                    items=workstream_items,
                    styling={"background_color": self.branding.colors.callout_bg}
                ))
        return RenderPage(
            page_number=page_num,
            page_type=PageType.EXECUTIVE_SUMMARY,
            page_title="Executive Summary",
            page_subtitle="Engagement Overview",
            components=components,
            capacity_metrics={"char_count": len(exec_summary)}
        )

    def _build_services_overview_page(self, page_num: int, sections: List[Dict[str, Any]], client_name: str) -> RenderPage:
        overview_items = []
        for sec in sections:
            sec_title = sec.get("section_title", "")
            subs = sec.get("subsections", [])
            sub_headings = ", ".join(sub.get("heading", "") for sub in subs[:3] if sub.get("heading"))
            summary_line = f"{sec_title}: {sub_headings}" if sub_headings else sec_title
            overview_items.append(summary_line)

        components = [
            RenderComponent(
                component_id="services_overview_heading",
                component_type=ComponentType.HEADING,
                title="Services Overview",
                content=f"Operational Scope Structure for {client_name}",
                styling={"color": self.branding.colors.primary}
            ),
            RenderComponent(
                component_id="services_overview_list",
                component_type=ComponentType.CARD,
                title="Approved Functional Workstreams",
                items=overview_items,
                styling={"background_color": self.branding.colors.neutral_light}
            )
        ]
        return RenderPage(
            page_number=page_num,
            page_type=PageType.SERVICES_OVERVIEW,
            page_title="Services Overview",
            page_subtitle="Operational Workstreams",
            components=components
        )

    def _build_service_detail_pages(
        self,
        start_page_num: int,
        section: Dict[str, Any],
        client_name: str,
        max_bullets_per_page: int = 12
    ) -> List[RenderPage]:
        """
        Translates a single proposal_draft service section into one or more RenderPage instances.
        Intelligently paginates subsections and bullet lists when content exceeds max_bullets_per_page (12).
        Continuation pages are titled '{Section Title} (continued)' with matching subtitles.
        """
        sec_title = section.get("section_title", "Service Details")
        opening_text = section.get("opening_text", "")
        subsections = section.get("subsections", [])

        pages: List[RenderPage] = []
        current_components: List[RenderComponent] = []
        current_bullets = 0
        current_chars = 0
        page_idx = 0

        def start_page():
            nonlocal current_components, current_bullets, current_chars
            p_num = start_page_num + page_idx
            p_title = sec_title if page_idx == 0 else f"{sec_title} (continued)"
            header_content = opening_text if page_idx == 0 and opening_text else None
            current_components.append(RenderComponent(
                component_id=f"sec_heading_{p_num}",
                component_type=ComponentType.HEADING,
                title=p_title,
                content=header_content,
                styling={"color": self.branding.colors.primary}
            ))
            current_chars = len(p_title) + (len(header_content) if header_content else 0)
            current_bullets = 0

        def finalize_page():
            nonlocal current_components, current_bullets, current_chars, page_idx
            p_num = start_page_num + page_idx
            p_title = sec_title if page_idx == 0 else f"{sec_title} (continued)"
            p_sub = "Deliverables & Procedures" if page_idx == 0 else "Deliverables & Procedures (continued)"

            pages.append(RenderPage(
                page_number=p_num,
                page_type=PageType.SERVICE_DETAIL,
                page_title=p_title,
                page_subtitle=p_sub,
                components=current_components,
                overflow_detected=False,
                capacity_metrics={
                    "bullet_count": current_bullets,
                    "char_count": current_chars,
                    "max_bullet_capacity": max_bullets_per_page
                }
            ))
            current_components = []
            current_bullets = 0
            current_chars = 0
            page_idx += 1

        start_page()

        if not subsections:
            finalize_page()
            return pages

        for sub_i, sub in enumerate(subsections):
            sub_heading = sub.get("heading", "")
            bullets = sub.get("bullets", [])

            if not bullets:
                current_components.append(RenderComponent(
                    component_id=f"subsec_{start_page_num + page_idx}_{sub_i}",
                    component_type=ComponentType.BULLET_LIST,
                    title=sub_heading,
                    items=[],
                    styling={"color": self.branding.colors.neutral_dark}
                ))
                current_chars += len(sub_heading)
                continue

            b_idx = 0
            while b_idx < len(bullets):
                avail = max_bullets_per_page - current_bullets
                if avail <= 0:
                    finalize_page()
                    start_page()
                    avail = max_bullets_per_page

                chunk = bullets[b_idx : b_idx + avail]
                h_title = sub_heading if b_idx == 0 else f"{sub_heading} (continued)"
                current_components.append(RenderComponent(
                    component_id=f"subsec_{start_page_num + page_idx}_{sub_i}_{b_idx}",
                    component_type=ComponentType.BULLET_LIST,
                    title=h_title,
                    items=chunk,
                    styling={"color": self.branding.colors.neutral_dark}
                ))
                current_bullets += len(chunk)
                current_chars += len(h_title) + sum(len(b) for b in chunk)
                b_idx += len(chunk)

        if current_components:
            finalize_page()

        return pages

    def _build_service_detail_page(self, page_num: int, section: Dict[str, Any], client_name: str) -> RenderPage:
        """
        Backward-compatible single-page builder. Returns the primary service detail page.
        For complete multi-page pagination, use _build_service_detail_pages.
        """
        pages = self._build_service_detail_pages(page_num, section, client_name)
        return pages[0]

    def _build_timeline_page(self, page_num: int, sections: List[Dict[str, Any]], client_name: str) -> RenderPage:
        phases = [
            "Phase 1 (Weeks 1–2): Discovery, system access configuration, and baseline data ingestion",
            "Phase 2 (Weeks 3–4): Workflow integration, system configuration, and parallel verification run",
            "Phase 3 (Weeks 5+): Operational go-live, governance review cadence, and ongoing handover"
        ]

        components = [
            RenderComponent(
                component_id="timeline_heading",
                component_type=ComponentType.HEADING,
                title="Implementation Roadmap & Milestones",
                content=f"Structured Onboarding Schedule for {client_name}",
                styling={"color": self.branding.colors.primary}
            ),
            RenderComponent(
                component_id="timeline_phases",
                component_type=ComponentType.CARD,
                title="Implementation Milestones",
                items=phases,
                styling={"background_color": self.branding.colors.neutral_light}
            )
        ]
        return RenderPage(
            page_number=page_num,
            page_type=PageType.TIMELINE,
            page_title="Implementation Roadmap",
            page_subtitle="Onboarding Schedule",
            components=components
        )

    def _build_why_us_page(self, page_num: int, why_us: List[str], client_name: str) -> RenderPage:
        components = [
            RenderComponent(
                component_id="why_us_heading",
                component_type=ComponentType.HEADING,
                title="Why Sympl Solutions",
                content="Our Commitment, Sector Experience, and Technology Approach",
                styling={"color": self.branding.colors.primary}
            ),
            RenderComponent(
                component_id="why_us_credentials",
                component_type=ComponentType.CARD,
                title="Partner Advantages",
                items=why_us,
                styling={"background_color": self.branding.colors.neutral_light}
            )
        ]
        return RenderPage(
            page_number=page_num,
            page_type=PageType.WHY_US,
            page_title="Why Sympl Solutions",
            page_subtitle="Credentials & Approach",
            components=components,
            capacity_metrics={"item_count": len(why_us)}
        )

    def _build_pricing_page(self, page_num: int, pricing: Dict[str, Any], client_name: str) -> RenderPage:
        fee_items = pricing.get("fee_items", [])
        schedule = pricing.get("billing_schedule", "Monthly retainer invoiced on the 1st of each service month.")
        currency = pricing.get("currency", "CAD")

        table_rows = []
        for item in fee_items:
            category = item.get("category", "Professional Services")
            frequency = item.get("billing_frequency", "monthly")
            amount = item.get("amount")

            if item.get("is_placeholder") or amount is None:
                amt_str = item.get("placeholder_token") or "[PRICING_PLACEHOLDER: Pending Confirmation]"
            else:
                amt_str = f"${amount:,.2f} {currency}"

            desc = item.get("description", "")
            table_rows.append([category, frequency.replace("_", " ").title(), amt_str, desc])

        components = [
            RenderComponent(
                component_id="pricing_heading",
                component_type=ComponentType.HEADING,
                title="Investment & Fee Schedule",
                content=f"Commercial Terms for {client_name}",
                styling={"color": self.branding.colors.primary}
            ),
            RenderComponent(
                component_id="pricing_table",
                component_type=ComponentType.TABLE,
                title="Approved Schedule of Fees",
                table_data={
                    "headers": ["Service Category", "Billing Frequency", "Fee (CAD)", "Scope Details"],
                    "rows": table_rows
                }
            ),
            RenderComponent(
                component_id="pricing_schedule_note",
                component_type=ComponentType.PARAGRAPH,
                title="Billing Terms",
                content=schedule,
                styling={"font_size": self.branding.typography.caption_size}
            )
        ]
        return RenderPage(
            page_number=page_num,
            page_type=PageType.PRICING,
            page_title="Investment Schedule",
            page_subtitle="Commercial Terms",
            components=components
        )

    def _build_exclusions_page(self, page_num: int, exclusions: List[str], client_name: str) -> RenderPage:
        components = [
            RenderComponent(
                component_id="exclusions_heading",
                component_type=ComponentType.HEADING,
                title="Engagement Terms & Boundaries",
                content=f"Important Boundary Conditions & Exclusions for {client_name}",
                styling={"color": self.branding.colors.primary}
            )
        ]

        for i, exc in enumerate(exclusions):
            components.append(RenderComponent(
                component_id=f"exclusion_note_{i}",
                component_type=ComponentType.CALLOUT,
                content=exc,
                styling={
                    "background_color": self.branding.colors.callout_bg,
                    "border_color": self.branding.colors.primary
                }
            ))

        components.append(RenderComponent(
            component_id="exclusions_operating_prereqs",
            component_type=ComponentType.CARD,
            title="Operational Prerequisites & Client Responsibilities",
            items=[
                "Timely provision of necessary system credentials, platform authorizations, and source documentation.",
                "Designation of primary organizational contact and authorized signing officers for written payment authorizations.",
                "Direct client ownership and billing for third-party software subscriptions, hosting, and merchant processing fees."
            ],
            styling={"background_color": self.branding.colors.neutral_light}
        ))

        return RenderPage(
            page_number=page_num,
            page_type=PageType.EXCLUSIONS,
            page_title="Engagement Terms & Exclusions",
            page_subtitle="Service Boundaries & Operating Prerequisites",
            components=components
        )

    def _build_closing_page(self, page_num: int, client_name: str) -> RenderPage:
        steps = [
            "1. Formal Acceptance: Confirm authorization of this proposal and terms.",
            "2. Engagement Agreement: Review and execute the standard master services contract.",
            "3. Kickoff & Integration: Schedule initial workflow discovery and ledger access handover."
        ]

        components = [
            RenderComponent(
                component_id="closing_heading",
                component_type=ComponentType.HEADING,
                title="Next Steps & Engagement Authorization",
                content="Moving Forward Together",
                styling={"color": self.branding.colors.primary}
            ),
            RenderComponent(
                component_id="closing_steps",
                component_type=ComponentType.CARD,
                title="Onboarding Sequence",
                items=steps,
                styling={"background_color": self.branding.colors.neutral_light}
            ),
            RenderComponent(
                component_id="closing_contact",
                component_type=ComponentType.FOOTER,
                title="Contact Information",
                content=f"{self.branding.company_name} | {self.branding.email} | {self.branding.website}"
            )
        ]
        return RenderPage(
            page_number=page_num,
            page_type=PageType.CLOSING,
            page_title="Next Steps",
            page_subtitle="Partnership Authorization",
            components=components
        )

    # --------------------------------------------------------------------------
    # Utility Methods
    # --------------------------------------------------------------------------
    def _extract_client_name(self, title: str, draft_data: Dict[str, Any]) -> str:
        """Extracts client name from title or returns clean fallback."""
        if " for " in title:
            return title.split(" for ", 1)[1].strip()
        return "Client Organization"

    def _should_include_timeline(self, sections: List[Dict[str, Any]], draft_data: Dict[str, Any]) -> bool:
        """Determines whether to include an Implementation Timeline page."""
        # Include timeline if transformation, transition, or multiple systems setup present
        all_text = " ".join(s.get("section_title", "") + " " + s.get("opening_text", "") for s in sections).lower()
        has_transform = "transformation" in all_text or "cloud migration" in all_text or "system migration" in all_text or "database discovery" in all_text
        has_transition = "transition roadmap" in all_text or "onboarding schedule" in all_text or "implementation roadmap" in all_text

        # Also check pricing setup fee
        pricing = draft_data.get("pricing", {})
        has_setup_fee = any(
            "setup" in item.get("category", "").lower() or "onboarding" in item.get("category", "").lower()
            for item in pricing.get("fee_items", [])
        )

        return has_transform or has_transition or has_setup_fee
