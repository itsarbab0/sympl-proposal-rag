"""
Sympl Solutions Proposal RAG — ReportLab Platypus PDF Generator

Converts RenderedProposal models into polished, client-ready consulting proposals
with precise visual hierarchy, corporate branding, official Sympl color palettes
(Inkwell #002236, Deepwater #007E7C, Yolk #FFE079, Paper #FBF5F0, Mist #E0F2F0),
dynamic page numbering ("Page X of Y"), running headers/footers,
and structured commercial tables.
"""

import os
import io
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
    Image as RLImage
)
from reportlab.pdfgen import canvas

from sympl_renderer.schema import (
    RenderedProposal,
    RenderPage,
    RenderComponent,
    ComponentType,
    PageType
)
from sympl_renderer.branding import SymplBranding, DEFAULT_BRANDING


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw total page count ("Page X of Y")
    along with running corporate headers and footers.
    """

    def __init__(self, *args, **kwargs):
        self.branding_dict = kwargs.pop("branding_dict", {})
        self.doc_title = kwargs.pop("doc_title", "Proposal Document")
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages: int):
        self.saveState()

        # Canvas boundaries for Letter portrait
        page_width, page_height = letter
        margin = 36  # 0.5 in

        primary_hex = self.branding_dict.get("colors", {}).get("primary", "#002236")
        secondary_hex = self.branding_dict.get("colors", {}).get("secondary", "#007E7C")
        border_hex = self.branding_dict.get("colors", {}).get("border", "#E2E8EA")
        ink_soft_hex = self.branding_dict.get("colors", {}).get("ink_soft", "#4A5F6B")
        company_name = self.branding_dict.get("company_name", "Sympl Solutions Inc.")
        footer_text = self.branding_dict.get("footer_text", f"Confidential Proposal — {company_name}")

        primary_col = colors.HexColor(primary_hex)
        secondary_col = colors.HexColor(secondary_hex)
        border_col = colors.HexColor(border_hex)
        ink_soft_col = colors.HexColor(ink_soft_hex)

        current_page = self._pageNumber

        # Running Header (pages > 1)
        if current_page > 1:
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(secondary_col)
            self.drawString(margin, page_height - 24, "SYMPL SOLUTIONS")

            self.setFont("Helvetica", 7.5)
            self.setFillColor(ink_soft_col)
            title_snippet = self.doc_title[:50] + ("..." if len(self.doc_title) > 50 else "")
            self.drawRightString(page_width - margin, page_height - 24, title_snippet)

            # Header hairline divider
            self.setStrokeColor(border_col)
            self.setLineWidth(0.5)
            self.line(margin, page_height - 28, page_width - margin, page_height - 28)

        # Running Footer (all pages)
        self.setStrokeColor(border_col)
        self.setLineWidth(0.5)
        self.line(margin, 28, page_width - margin, 28)

        self.setFont("Helvetica", 7.5)
        self.setFillColor(ink_soft_col)
        self.drawString(margin, 16, footer_text)

        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(primary_col)
        page_str = f"Page {current_page} of {total_pages}"
        self.drawRightString(page_width - margin, 16, page_str)

        self.restoreState()


class PdfGenerationService:
    """
    Generates presentation-ready vector PDFs from RenderedProposal models.
    Adheres to the official Sympl consulting visual identity.
    """

    def __init__(self, branding: Optional[SymplBranding] = None):
        self.branding = branding or DEFAULT_BRANDING

    def generate_pdf(
        self,
        proposal: Union[RenderedProposal, Dict[str, Any]],
        output_path: Optional[Union[str, Path]] = None
    ) -> bytes:
        """
        Main PDF compilation entrypoint.

        Args:
            proposal: RenderedProposal instance or equivalent dictionary.
            output_path: Optional path to save the generated PDF file.

        Returns:
            Raw PDF bytes.
        """
        # 1. Normalize proposal into dictionary
        if isinstance(proposal, dict):
            p_dict = proposal
        else:
            p_dict = proposal.to_dict()

        title = p_dict.get("title", "Proposal Document")
        client_name = p_dict.get("client_name", "Client Organization")
        branding_data = p_dict.get("branding") or self.branding.to_dict()

        # Update service branding if custom branding is in proposal
        if branding_data:
            self.branding = SymplBranding.from_dict(branding_data)

        # 2. Build Document Template with tight, comfortable consulting margins
        buffer = io.BytesIO()
        margin = 36  # 0.5 inch margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=38,
            bottomMargin=38
        )

        # 3. Setup Design Styles
        styles = self._setup_styles()

        # 4. Build Flowable Story
        story: List[Any] = []
        pages = p_dict.get("pages", [])

        if pages:
            # Process page by page
            for i, page_data in enumerate(pages):
                if i > 0:
                    story.append(PageBreak())
                self._render_page_story(page_data, story, styles, client_name)
        else:
            # Fallback direct generation from draft dict
            self._render_direct_draft(p_dict, story, styles, client_name)

        # 5. Build PDF with NumberedCanvas
        def canvas_maker(*args, **kwargs):
            return NumberedCanvas(
                *args,
                branding_dict=branding_data,
                doc_title=title,
                **kwargs
            )

        doc.build(story, canvasmaker=canvas_maker)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # 6. Optional file write
        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "wb") as f:
                f.write(pdf_bytes)

        return pdf_bytes

    def _setup_styles(self) -> Dict[str, ParagraphStyle]:
        """Creates ReportLab styles using Sympl branding tokens."""
        c_primary = colors.HexColor(self.branding.colors.primary)
        c_secondary = colors.HexColor(self.branding.colors.secondary)
        c_soft = colors.HexColor(getattr(self.branding.colors, "ink_soft", "#4A5F6B"))

        custom_styles = {
            "CoverBrand": ParagraphStyle(
                "CoverBrand",
                fontName="Helvetica-Bold",
                fontSize=28,
                leading=32,
                textColor=c_primary,
                spaceAfter=2
            ),
            "CoverKicker": ParagraphStyle(
                "CoverKicker",
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11,
                textColor=c_secondary,
                spaceAfter=12
            ),
            "CoverCompany": ParagraphStyle(
                "CoverCompany",
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=16,
                textColor=c_secondary,
                spaceAfter=3
            ),
            "CoverTagline": ParagraphStyle(
                "CoverTagline",
                fontName="Helvetica",
                fontSize=8,
                leading=11,
                textColor=c_secondary,
                spaceBefore=2,
                spaceAfter=14
            ),
            "CoverTitle": ParagraphStyle(
                "CoverTitle",
                fontName="Helvetica-Bold",
                fontSize=24,
                leading=29,
                textColor=c_primary,
                spaceAfter=10
            ),
            "CoverSubtitle": ParagraphStyle(
                "CoverSubtitle",
                fontName="Helvetica",
                fontSize=11.5,
                leading=15,
                textColor=c_soft,
                spaceAfter=20
            ),
            "SectionTitle": ParagraphStyle(
                "SectionTitle",
                fontName="Helvetica-Bold",
                fontSize=15.5,
                leading=19.5,
                textColor=c_primary,
                spaceBefore=6,
                spaceAfter=3,
                keepWithNext=True
            ),
            "SectionSubtitle": ParagraphStyle(
                "SectionSubtitle",
                fontName="Helvetica-Oblique",
                fontSize=8.5,
                leading=12,
                textColor=c_soft,
                spaceAfter=8,
                keepWithNext=True
            ),
            "SubsectionHeading": ParagraphStyle(
                "SubsectionHeading",
                fontName="Helvetica-Bold",
                fontSize=10.5,
                leading=14,
                textColor=c_primary,
                spaceBefore=6,
                spaceAfter=3,
                keepWithNext=True
            ),
            "LeadParagraph": ParagraphStyle(
                "LeadParagraph",
                fontName="Helvetica",
                fontSize=9.5,
                leading=14,
                textColor=c_primary,
                spaceAfter=8
            ),
            "Body": ParagraphStyle(
                "Body",
                fontName="Helvetica",
                fontSize=9,
                leading=13.5,
                textColor=c_primary,
                spaceAfter=4
            ),
            "BodyMuted": ParagraphStyle(
                "BodyMuted",
                fontName="Helvetica",
                fontSize=8.5,
                leading=12.5,
                textColor=c_soft,
                spaceAfter=3
            ),
            "CalloutTitle": ParagraphStyle(
                "CalloutTitle",
                fontName="Helvetica-Bold",
                fontSize=9,
                leading=12.5,
                textColor=c_secondary,
                spaceAfter=2
            ),
            "CalloutText": ParagraphStyle(
                "CalloutText",
                fontName="Helvetica",
                fontSize=8.5,
                leading=12.5,
                textColor=c_primary
            ),
            "BulletText": ParagraphStyle(
                "BulletText",
                fontName="Helvetica",
                fontSize=8.5,
                leading=12.5,
                textColor=c_primary,
                leftIndent=12,
                firstLineIndent=-9,
                spaceAfter=2.5
            ),
            "TableHeader": ParagraphStyle(
                "TableHeader",
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11.5,
                textColor=colors.white,
                alignment=0
            ),
            "TableCell": ParagraphStyle(
                "TableCell",
                fontName="Helvetica",
                fontSize=8.5,
                leading=11.5,
                textColor=c_primary
            ),
            "TableCellBold": ParagraphStyle(
                "TableCellBold",
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11.5,
                textColor=c_secondary
            )
        }
        return custom_styles

    def _render_page_story(
        self,
        page_data: Dict[str, Any],
        story: List[Any],
        styles: Dict[str, ParagraphStyle],
        client_name: str
    ) -> None:
        """Translates a single RenderPage component tree into Platypus flowables."""
        page_type = page_data.get("page_type")
        components = page_data.get("components", [])
        page_title = page_data.get("page_title", "")
        page_subtitle = page_data.get("page_subtitle", "")

        # ----------------------------------------------------------------------
        # A. Cover Page
        # ----------------------------------------------------------------------
        if page_type == PageType.COVER:
            logo_drawn = False
            if self.branding.logo_path and os.path.exists(self.branding.logo_path):
                try:
                    img = RLImage(self.branding.logo_path, width=2.0 * inch, height=0.75 * inch)
                    img.hAlign = 'LEFT'
                    story.append(img)
                    story.append(Spacer(1, 10))
                    logo_drawn = True
                except Exception:
                    pass

            if not logo_drawn:
                story.append(Paragraph('<b>sympl<font color="#FFE079">.</font></b>', styles["CoverBrand"]))
                story.append(Paragraph(
                    '<font color="#007E7C" size="7.5"><b>OPERATIONAL FINANCIAL SYSTEMS & STRATEGIC ADVISORY</b></font>',
                    styles["CoverTagline"]
                ))

            # Elegant brand divider
            story.append(HRFlowable(
                width="100%", thickness=2.5, color=colors.HexColor(self.branding.colors.secondary),
                spaceBefore=4, spaceAfter=25
            ))

            story.append(Spacer(1, 25))
            story.append(Paragraph("STRATEGIC SERVICES PROPOSAL", styles["CoverKicker"]))
            story.append(Paragraph(page_title, styles["CoverTitle"]))
            story.append(Paragraph(f"Prepared exclusively for <b>{client_name}</b>", styles["CoverSubtitle"]))

            story.append(Spacer(1, 60))

            # Metadata box
            date_str = datetime.date.today().strftime('%B %d, %Y')
            meta_data = [
                [
                    Paragraph(
                        f'<font size="7.5" color="#007E7C"><b>CLIENT ORGANIZATION</b></font><br/>'
                        f'<b>{client_name}</b><br/><br/>'
                        f'<font size="7.5" color="#007E7C"><b>DOCUMENT DATE</b></font><br/>'
                        f'{date_str}',
                        styles["TableCell"]
                    ),
                    Paragraph(
                        f'<font size="7.5" color="#007E7C"><b>PREPARED BY</b></font><br/>'
                        f'<b>{self.branding.company_name}</b><br/>'
                        f'<font color="#4A5F6B" size="8">{self.branding.website}</font><br/><br/>'
                        f'<font size="7.5" color="#007E7C"><b>STATUS</b></font><br/>'
                        f'Commercial in Confidence',
                        styles["TableCell"]
                    )
                ]
            ]
            meta_table = Table(meta_data, colWidths=[270, 270])
            meta_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(self.branding.colors.neutral_light)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(self.branding.colors.border)),
                ('LINELEFT', (0, 0), (0, -1), 3.0, colors.HexColor(self.branding.colors.secondary)),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(meta_table)
            return

        # ----------------------------------------------------------------------
        # B. Section Header (Common to all content pages)
        # ----------------------------------------------------------------------
        if page_title:
            story.append(Paragraph(page_title, styles["SectionTitle"]))
            if page_subtitle:
                story.append(Paragraph(page_subtitle, styles["SectionSubtitle"]))
            story.append(HRFlowable(
                width="100%", thickness=1.5, color=colors.HexColor(self.branding.colors.secondary),
                spaceBefore=2, spaceAfter=10
            ))

        # ----------------------------------------------------------------------
        # C. Executive Summary Page Special Layout
        # ----------------------------------------------------------------------
        if page_type == PageType.EXECUTIVE_SUMMARY:
            narrative_text = ""
            card_title = ""
            card_items = []

            for comp in components:
                c_type = comp.get("component_type")
                if c_type == ComponentType.PARAGRAPH and comp.get("content"):
                    narrative_text = comp.get("content")
                elif c_type == ComponentType.CARD and comp.get("items"):
                    card_title = comp.get("title", "Engagement Scope")
                    card_items = comp.get("items", [])

            if narrative_text:
                story.append(Paragraph(narrative_text, styles["LeadParagraph"]))
                story.append(Spacer(1, 10))

            # Consulting 2-Column Delivery & Workstreams Grid
            col_width = 265.0

            # Column 1: Sympl Delivery Commitment
            left_flowables = [
                Paragraph("<font color='#007E7C'><b>ENGAGEMENT PRINCIPLES</b></font>", styles["SubsectionHeading"]),
                Spacer(1, 4),
                Paragraph("<font color='#007E7C'>&bull;</font> &nbsp; <b>Dedicated Advisory Lead:</b> Direct oversight and accountable executive point of contact.", styles["BulletText"]),
                Spacer(1, 3),
                Paragraph("<font color='#007E7C'>&bull;</font> &nbsp; <b>Operational Cadence:</b> Structured review checkpoints and real-time visibility.", styles["BulletText"]),
                Spacer(1, 3),
                Paragraph("<font color='#007E7C'>&bull;</font> &nbsp; <b>Predictable Execution:</b> Defined deliverables tied directly to measurable goals.", styles["BulletText"])
            ]
            left_table = Table([[left_flowables]], colWidths=[col_width if card_items else 540.0])
            left_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(self.branding.colors.neutral_light)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(self.branding.colors.border)),
                ('LINELEFT', (0, 0), (0, -1), 2.5, colors.HexColor(self.branding.colors.secondary)),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))

            # Column 2: Approved Workstreams or Scope Focus Areas
            if card_items:
                right_flowables = [
                    Paragraph(f"<font color='#007E7C'><b>{card_title.upper()}</b></font>", styles["SubsectionHeading"]),
                    Spacer(1, 4)
                ]
                for item in card_items[:5]:
                    right_flowables.append(Paragraph(f"<font color='#007E7C'>&bull;</font> &nbsp; {item}", styles["BulletText"]))
                    right_flowables.append(Spacer(1, 2))

                right_table = Table([[right_flowables]], colWidths=[col_width])
                right_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(self.branding.colors.neutral_light)),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(self.branding.colors.border)),
                    ('LINELEFT', (0, 0), (0, -1), 2.5, colors.HexColor(self.branding.colors.secondary)),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))

                grid_table = Table([[left_table, '', right_table]], colWidths=[265.0, 10.0, 265.0])
                grid_table.setStyle(TableStyle([
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                story.append(grid_table)
            else:
                story.append(left_table)

            story.append(Spacer(1, 10))

            # Strategic partnership callout
            exec_note = (
                "<b>Operational Partnership:</b> Sympl Solutions acts as an embedded strategic partner. "
                "All engagements adhere to rigorous quality controls, standard operating procedures, and "
                "continuous executive alignment to maximize organizational clarity and ROI."
            )
            story.append(self._create_callout_box(exec_note, styles["CalloutText"], width=540))
            return

        # ----------------------------------------------------------------------
        # D. Pricing Page Special Layout
        # ----------------------------------------------------------------------
        if page_type == PageType.PRICING:
            inv_summary = (
                "<b>Commercial Principles:</b> Sympl Solutions operates with transparent, predictable fee structures. "
                "All defined scope, recurring procedures, and direct advisory access are encompassed under the approved "
                "schedule below with zero unapproved hourly billing or hidden overhead."
            )
            story.append(self._create_callout_box(inv_summary, styles["CalloutText"], width=540))
            story.append(Spacer(1, 8))

            for comp in components:
                c_type = comp.get("component_type")
                c_title = comp.get("title")
                c_content = comp.get("content")
                c_table = comp.get("table_data")

                if c_type == ComponentType.TABLE and c_table:
                    if c_title:
                        story.append(Paragraph(c_title, styles["SubsectionHeading"]))
                    tbl = self._build_platypus_table(c_table, styles)
                    story.append(tbl)
                    story.append(Spacer(1, 8))

                elif c_type == ComponentType.PARAGRAPH and c_content:
                    terms_box = f"<b>Billing & Retainer Terms:</b> {c_content}<br/><font color='#4A5F6B' size='7.5'>Note: Third-party software subscriptions (accounting, file storage, payment processing) are billed directly to the client.</font>"
                    story.append(self._create_callout_box(terms_box, styles["CalloutText"], width=540))

            return

        # ----------------------------------------------------------------------
        # E. General Component Flow (Service Details, Why Us, Timeline, Exclusions, Closing)
        # ----------------------------------------------------------------------
        bullet_count_on_page = 0
        for comp in components:
            c_type = comp.get("component_type")
            c_title = comp.get("title")
            c_content = comp.get("content")
            c_items = comp.get("items", [])
            c_table = comp.get("table_data")

            # Headings
            if c_type == ComponentType.HEADING:
                if c_title:
                    story.append(Paragraph(c_title, styles["SubsectionHeading"]))
                if c_content:
                    story.append(Paragraph(c_content, styles["LeadParagraph"]))

            # Paragraphs
            elif c_type == ComponentType.PARAGRAPH:
                if c_content:
                    story.append(Paragraph(c_content, styles["LeadParagraph"]))

            # Callout boxes (e.g. boundary notes)
            elif c_type == ComponentType.CALLOUT:
                if c_content:
                    story.append(self._create_callout_box(c_content, styles["CalloutText"]))
                    story.append(Spacer(1, 6))

            # Bullet lists / Cards
            elif c_type in (ComponentType.BULLET_LIST, ComponentType.CARD):
                subsec_elements = []
                if c_title:
                    is_deliverables = "deliverable" in c_title.lower() or "output" in c_title.lower()
                    is_boundaries = "boundar" in c_title.lower() or "prereq" in c_title.lower() or "exclusion" in c_title.lower()
                    if is_deliverables:
                        subsec_elements.append(Paragraph(f"<font color='#007E7C'><b>▸ {c_title.upper()}</b></font>", styles["SubsectionHeading"]))
                    elif is_boundaries:
                        subsec_elements.append(Paragraph(f"<font color='#E38900'><b>▪ {c_title.upper()}</b></font>", styles["SubsectionHeading"]))
                    else:
                        subsec_elements.append(Paragraph(c_title, styles["SubsectionHeading"]))

                if c_content:
                    subsec_elements.append(Paragraph(c_content, styles["BodyMuted"]))

                for item in c_items:
                    if bullet_count_on_page >= 12:
                        story.append(PageBreak())
                        story.append(Paragraph(f"{page_title} (continued)", styles["SectionTitle"]))
                        if page_subtitle:
                            story.append(Paragraph(f"{page_subtitle} (continued)", styles["SectionSubtitle"]))
                        story.append(HRFlowable(
                            width="100%", thickness=1.5, color=colors.HexColor(self.branding.colors.secondary),
                            spaceBefore=2, spaceAfter=10
                        ))
                        if c_title:
                            story.append(Paragraph(f"{c_title} (continued)", styles["SubsectionHeading"]))
                        bullet_count_on_page = 0

                    bullet_p = Paragraph(f"<font color='#007E7C'>&bull;</font> &nbsp; {item}", styles["BulletText"])
                    subsec_elements.append(bullet_p)
                    bullet_count_on_page += 1

                subsec_elements.append(Spacer(1, 4))
                story.append(KeepTogether(subsec_elements))

            # Tables
            elif c_type == ComponentType.TABLE:
                if c_title:
                    story.append(Paragraph(c_title, styles["SubsectionHeading"]))
                if c_table:
                    tbl = self._build_platypus_table(c_table, styles)
                    story.append(tbl)
                    story.append(Spacer(1, 8))

        # If this is the Closing page, append formal authorization and signature table
        if page_type == PageType.CLOSING:
            story.append(Spacer(1, 10))
            story.append(Paragraph("Proposal Authorization & Formal Acceptance", styles["SubsectionHeading"]))
            story.append(Paragraph(
                "By signing below, authorized representatives acknowledge and accept the services, "
                "scope deliverables, boundaries, and commercial terms outlined in this proposal.",
                styles["Body"]
            ))
            story.append(Spacer(1, 8))
            story.append(self._build_signature_block(client_name, styles))

    def _create_callout_box(
        self,
        text: str,
        text_style: ParagraphStyle,
        width: float = 540,
        title: Optional[str] = None
    ) -> Table:
        """Wraps text in a styled callout card with brand accent left border."""
        c_bg = colors.HexColor(self.branding.colors.callout_bg)
        c_accent = colors.HexColor(self.branding.colors.secondary)
        c_border = colors.HexColor(self.branding.colors.border)

        flowables = []
        if title:
            flowables.append(Paragraph(f"<b>{title}</b>", text_style))
            flowables.append(Spacer(1, 2))
        flowables.append(Paragraph(text, text_style))

        t = Table([[flowables]], colWidths=[width])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), c_bg),
            ('BOX', (0, 0), (-1, -1), 0.5, c_border),
            ('LINELEFT', (0, 0), (0, -1), 2.5, c_accent),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        return t

    def _build_platypus_table(self, table_data: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Table:
        """Builds a formatted Platypus Table with styled headers and alternating rows."""
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])

        table_matrix = []
        if headers:
            header_row = [Paragraph(f"<b>{h}</b>", styles["TableHeader"]) for h in headers]
            table_matrix.append(header_row)

        for r in rows:
            row_cells = []
            for i, val in enumerate(r):
                val_str = str(val if val is not None else "")
                if i == 0 or (len(r) > 2 and i == 2 and "$" in val_str):
                    cell_p = Paragraph(val_str, styles["TableCellBold"])
                else:
                    cell_p = Paragraph(val_str, styles["TableCell"])
                row_cells.append(cell_p)
            table_matrix.append(row_cells)

        num_cols = len(headers) if headers else (len(rows[0]) if rows else 1)
        total_width = 540.0
        if num_cols == 3:
            col_widths = [200.0, 180.0, 160.0]
        elif num_cols == 2:
            col_widths = [360.0, 180.0]
        elif num_cols == 4:
            col_widths = [160.0, 130.0, 120.0, 130.0]
        else:
            col_widths = [total_width / num_cols] * num_cols

        t = Table(table_matrix, colWidths=col_widths)
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.branding.colors.table_header)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(self.branding.colors.border)),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]

        # Alternating row colors
        for row_idx in range(1, len(table_matrix)):
            bg = colors.HexColor(self.branding.colors.surface) if row_idx % 2 != 0 else colors.HexColor(self.branding.colors.neutral_light)
            t_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), bg))

        t.setStyle(TableStyle(t_style))
        return t

    def _build_signature_block(self, client_name: str, styles: Dict[str, ParagraphStyle]) -> Table:
        """Constructs side-by-side signature blocks for the client and Sympl Solutions."""
        col_w = 265.0
        sig_data = [
            [
                Paragraph(f"<b>For: {client_name}</b>", styles["TableCellBold"]),
                Paragraph(f"<b>For: {self.branding.company_name}</b>", styles["TableCellBold"])
            ],
            [
                Paragraph("<br/><br/>______________________________________<br/><font color='#4A5F6B' size='7.5'>Authorized Signature</font>", styles["TableCell"]),
                Paragraph("<br/><br/>______________________________________<br/><font color='#4A5F6B' size='7.5'>Authorized Signature</font>", styles["TableCell"])
            ],
            [
                Paragraph("Name: _______________________________", styles["TableCell"]),
                Paragraph("Name: _______________________________", styles["TableCell"])
            ],
            [
                Paragraph("Title: ________________________________", styles["TableCell"]),
                Paragraph("Title: ________________________________", styles["TableCell"])
            ],
            [
                Paragraph("Date: ________________________________", styles["TableCell"]),
                Paragraph("Date: ________________________________", styles["TableCell"])
            ]
        ]
        t = Table(sig_data, colWidths=[col_w, col_w])
        t.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return t

    def _render_direct_draft(
        self,
        draft_dict: Dict[str, Any],
        story: List[Any],
        styles: Dict[str, ParagraphStyle],
        client_name: str
    ) -> None:
        """Fallback renderer when pages array is not present in input dictionary."""
        title = draft_dict.get("title", "Services Proposal")
        exec_summary = draft_dict.get("executive_summary", "")

        # Cover
        story.append(Paragraph('<b>sympl<font color="#FFE079">.</font></b>', styles["CoverBrand"]))
        story.append(Paragraph(
            '<font color="#007E7C" size="7.5"><b>OPERATIONAL FINANCIAL SYSTEMS & STRATEGIC ADVISORY</b></font>',
            styles["CoverTagline"]
        ))
        story.append(HRFlowable(width="100%", thickness=2.5, color=colors.HexColor(self.branding.colors.secondary), spaceAfter=20))
        story.append(Spacer(1, 20))
        story.append(Paragraph("STRATEGIC SERVICES PROPOSAL", styles["CoverKicker"]))
        story.append(Paragraph(title, styles["CoverTitle"]))
        story.append(Paragraph(f"Prepared exclusively for <b>{client_name}</b>", styles["CoverSubtitle"]))
        story.append(Spacer(1, 40))

        # Metadata box
        date_str = datetime.date.today().strftime('%B %d, %Y')
        meta_data = [
            [
                Paragraph(
                    f'<font size="7.5" color="#007E7C"><b>CLIENT ORGANIZATION</b></font><br/><b>{client_name}</b><br/><br/>'
                    f'<font size="7.5" color="#007E7C"><b>DOCUMENT DATE</b></font><br/>{date_str}',
                    styles["TableCell"]
                ),
                Paragraph(
                    f'<font size="7.5" color="#007E7C"><b>PREPARED BY</b></font><br/><b>{self.branding.company_name}</b><br/>'
                    f'<font color="#4A5F6B" size="8">{self.branding.website}</font><br/><br/>'
                    f'<font size="7.5" color="#007E7C"><b>STATUS</b></font><br/>Commercial in Confidence',
                    styles["TableCell"]
                )
            ]
        ]
        meta_table = Table(meta_data, colWidths=[270, 270])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(self.branding.colors.neutral_light)),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(self.branding.colors.border)),
            ('LINELEFT', (0, 0), (0, -1), 3.0, colors.HexColor(self.branding.colors.secondary)),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(meta_table)

        # Executive summary
        if exec_summary:
            story.append(PageBreak())
            story.append(Paragraph("Executive Summary", styles["SectionTitle"]))
            story.append(Paragraph("Strategic Partnership & Engagement Context", styles["SectionSubtitle"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(self.branding.colors.secondary), spaceBefore=2, spaceAfter=10))
            story.append(Paragraph(exec_summary, styles["LeadParagraph"]))
            story.append(Spacer(1, 10))

            exec_note = (
                "<b>Operational Governance & Partnership:</b> Sympl Solutions provides structured financial "
                "management embedded into your organization. We establish clear operational cadences, regular management "
                "checkpoints, and direct senior advisory access to ensure complete financial visibility."
            )
            story.append(self._create_callout_box(exec_note, styles["CalloutText"], width=540))

        # Sections
        for sec in draft_dict.get("sections", []):
            story.append(PageBreak())
            sec_title = sec.get("section_title", "Service Details")
            story.append(Paragraph(sec_title, styles["SectionTitle"]))
            story.append(Paragraph("Operational Deliverables & Procedures", styles["SectionSubtitle"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(self.branding.colors.secondary), spaceBefore=2, spaceAfter=10))
            if sec.get("opening_text"):
                story.append(Paragraph(sec["opening_text"], styles["LeadParagraph"]))

            bullet_count_on_page = 0
            for sub in sec.get("subsections", []):
                sub_heading = sub.get("heading")
                bullets = sub.get("bullets", [])
                subsec_elements = []

                if sub_heading:
                    is_deliverables = "deliverable" in sub_heading.lower() or "output" in sub_heading.lower()
                    is_boundaries = "boundar" in sub_heading.lower() or "prereq" in sub_heading.lower()
                    if is_deliverables:
                        subsec_elements.append(Paragraph(f"<font color='#007E7C'><b>▸ {sub_heading.upper()}</b></font>", styles["SubsectionHeading"]))
                    elif is_boundaries:
                        subsec_elements.append(Paragraph(f"<font color='#E38900'><b>▪ {sub_heading.upper()}</b></font>", styles["SubsectionHeading"]))
                    else:
                        subsec_elements.append(Paragraph(sub_heading, styles["SubsectionHeading"]))

                if sub.get("narrative"):
                    subsec_elements.append(Paragraph(sub["narrative"], styles["BodyMuted"]))

                for b in bullets:
                    if bullet_count_on_page >= 12:
                        story.append(PageBreak())
                        story.append(Paragraph(f"{sec_title} (continued)", styles["SectionTitle"]))
                        story.append(Paragraph("Operational Deliverables & Procedures (continued)", styles["SectionSubtitle"]))
                        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(self.branding.colors.secondary), spaceBefore=2, spaceAfter=10))
                        if sub_heading:
                            story.append(Paragraph(f"{sub_heading} (continued)", styles["SubsectionHeading"]))
                        bullet_count_on_page = 0
                    subsec_elements.append(Paragraph(f"<font color='#007E7C'>&bull;</font> &nbsp; {b}", styles["BulletText"]))
                    bullet_count_on_page += 1

                subsec_elements.append(Spacer(1, 4))
                story.append(KeepTogether(subsec_elements))

        # Why Us
        why_us = draft_dict.get("why_us", [])
        if why_us:
            story.append(PageBreak())
            story.append(Paragraph("Why Sympl Solutions", styles["SectionTitle"]))
            story.append(Paragraph("Credentials & Approach", styles["SectionSubtitle"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(self.branding.colors.secondary), spaceBefore=2, spaceAfter=10))
            for item in why_us:
                story.append(Paragraph(f"<font color='#007E7C'>&bull;</font> &nbsp; {item}", styles["BulletText"]))

        # Pricing
        pricing = draft_dict.get("pricing", {})
        if pricing and pricing.get("fee_items"):
            story.append(PageBreak())
            story.append(Paragraph("Investment Schedule & Commercial Terms", styles["SectionTitle"]))
            story.append(Paragraph(f"Approved Fee Structure for {client_name}", styles["SectionSubtitle"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(self.branding.colors.secondary), spaceBefore=2, spaceAfter=10))

            inv_summary = (
                "<b>Commercial Principles:</b> Sympl Solutions operates with transparent, predictable fee structures. "
                "All defined scope, recurring procedures, and direct advisory access are encompassed under the approved "
                "schedule below with zero unapproved hourly billing or hidden overhead."
            )
            story.append(self._create_callout_box(inv_summary, styles["CalloutText"], width=540))
            story.append(Spacer(1, 8))

            fee_items = pricing.get("fee_items", [])
            currency = pricing.get("currency", "CAD")
            table_rows = []
            for item in fee_items:
                cat = item.get("category", "Professional Services")
                freq = item.get("billing_frequency", "monthly").replace("_", " ").title()
                amt = item.get("amount")
                amt_str = f"${amt:,.2f} {currency}" if amt is not None else "[Pending]"
                desc = item.get("description", "")
                table_rows.append([cat, freq, amt_str, desc])
            tbl_data = {
                "headers": ["Service Category", "Frequency", "Fee", "Scope Details"],
                "rows": table_rows
            }
            story.append(self._build_platypus_table(tbl_data, styles))
            story.append(Spacer(1, 8))

            schedule = pricing.get("billing_schedule", "Monthly retainer invoiced on the 1st of each service month.")
            terms_box = f"<b>Billing & Retainer Terms:</b> {schedule}<br/><font color='#4A5F6B' size='7.5'>Note: Third-party software subscriptions (accounting, file storage, payment processing) are billed directly to the client.</font>"
            story.append(self._create_callout_box(terms_box, styles["CalloutText"], width=540))

        # Exclusions
        exclusions = draft_dict.get("exclusions", [])
        if exclusions:
            story.append(PageBreak())
            story.append(Paragraph("Engagement Terms & Scope Boundaries", styles["SectionTitle"]))
            story.append(Paragraph("Operating Prerequisites & Boundary Conditions", styles["SectionSubtitle"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(self.branding.colors.secondary), spaceBefore=2, spaceAfter=10))
            story.append(Paragraph(
                "To ensure operational security, project alignment, and clear expectations, the following boundary conditions and client responsibilities govern this engagement:",
                styles["LeadParagraph"]
            ))
            for exc in exclusions:
                story.append(self._create_callout_box(exc, styles["CalloutText"]))
                story.append(Spacer(1, 6))

            prereqs_box = (
                "<b>Operational Prerequisites & Client Responsibilities:</b><br/>"
                "&bull; Timely provision of necessary system credentials, platform authorizations, and source documentation.<br/>"
                "&bull; Designation of primary organizational contact and authorized signing officers for written payment authorizations.<br/>"
                "&bull; Direct client ownership and billing for third-party software subscriptions, hosting, and merchant processing fees."
            )
            story.append(Spacer(1, 4))
            story.append(self._create_callout_box(prereqs_box, styles["CalloutText"]))

        # Closing / Sign-off
        story.append(PageBreak())
        story.append(Paragraph("Next Steps & Engagement Authorization", styles["SectionTitle"]))
        story.append(Paragraph("Moving Forward Together", styles["SectionSubtitle"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(self.branding.colors.secondary), spaceBefore=2, spaceAfter=10))
        story.append(Paragraph(
            "By signing below, authorized representatives acknowledge and accept the services, "
            "scope deliverables, boundaries, and commercial terms outlined in this proposal.",
            styles["Body"]
        ))
        story.append(Spacer(1, 12))
        story.append(self._build_signature_block(client_name, styles))
