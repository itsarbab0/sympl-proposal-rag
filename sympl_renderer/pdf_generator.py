"""
Sympl Solutions Proposal RAG — ReportLab Platypus PDF Generator (Phase 8.5)

Converts RenderedProposal models into polished, production-ready PDF documents
with precise visual hierarchy, corporate branding, custom color palettes,
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

        primary_hex = self.branding_dict.get("colors", {}).get("primary", "#1A2E40")
        neutral_dark_hex = self.branding_dict.get("colors", {}).get("neutral_dark", "#2D3748")
        border_hex = self.branding_dict.get("colors", {}).get("border", "#E2E8F0")
        company_name = self.branding_dict.get("company_name", "Sympl Solutions Inc.")
        footer_text = self.branding_dict.get("footer_text", f"Confidential — Prepared by {company_name}")

        primary_col = colors.HexColor(primary_hex)
        neutral_col = colors.HexColor(neutral_dark_hex)
        border_col = colors.HexColor(border_hex)

        current_page = self._pageNumber

        # Running Header (pages > 1)
        if current_page > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(primary_col)
            self.drawString(margin, page_height - 24, company_name.upper())

            self.setFont("Helvetica", 8)
            self.setFillColor(neutral_col)
            title_snippet = self.doc_title[:45] + ("..." if len(self.doc_title) > 45 else "")
            self.drawRightString(page_width - margin, page_height - 24, title_snippet)

            # Header hairline
            self.setStrokeColor(border_col)
            self.setLineWidth(0.5)
            self.line(margin, page_height - 28, page_width - margin, page_height - 28)

        # Running Footer (all pages)
        self.setStrokeColor(border_col)
        self.setLineWidth(0.5)
        self.line(margin, 30, page_width - margin, 30)

        self.setFont("Helvetica", 8)
        self.setFillColor(neutral_col)
        self.drawString(margin, 18, footer_text)

        page_str = f"Page {current_page} of {total_pages}"
        self.drawRightString(page_width - margin, 18, page_str)

        self.restoreState()


class PdfGenerationService:
    """
    Generates presentation-ready vector PDFs from RenderedProposal models.
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
        # 1. Normalize proposal into RenderedProposal
        if isinstance(proposal, dict):
            # Parse dict into model or extract pages
            p_dict = proposal
        else:
            p_dict = proposal.to_dict()

        title = p_dict.get("title", "Proposal Document")
        client_name = p_dict.get("client_name", "Client Organization")
        branding_data = p_dict.get("branding") or self.branding.to_dict()

        # Update service branding if custom branding is in proposal
        if branding_data:
            self.branding = SymplBranding.from_dict(branding_data)

        # 2. Build Document Template
        buffer = io.BytesIO()
        margin = 36  # 0.5 inch margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=42,
            bottomMargin=42
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
        base_styles = getSampleStyleSheet()

        c_primary = colors.HexColor(self.branding.colors.primary)
        c_secondary = colors.HexColor(self.branding.colors.secondary)
        c_accent = colors.HexColor(self.branding.colors.accent)
        c_dark = colors.HexColor(self.branding.colors.neutral_dark)

        custom_styles = {
            "CoverCompany": ParagraphStyle(
                "CoverCompany",
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=18,
                textColor=c_secondary,
                spaceAfter=4
            ),
            "CoverTagline": ParagraphStyle(
                "CoverTagline",
                fontName="Helvetica",
                fontSize=9,
                leading=12,
                textColor=c_dark,
                spaceAfter=20
            ),
            "CoverTitle": ParagraphStyle(
                "CoverTitle",
                fontName="Helvetica-Bold",
                fontSize=24,
                leading=30,
                textColor=c_primary,
                spaceAfter=12
            ),
            "CoverSubtitle": ParagraphStyle(
                "CoverSubtitle",
                fontName="Helvetica",
                fontSize=12,
                leading=16,
                textColor=c_dark,
                spaceAfter=25
            ),
            "SectionTitle": ParagraphStyle(
                "SectionTitle",
                fontName="Helvetica-Bold",
                fontSize=16,
                leading=20,
                textColor=c_primary,
                spaceBefore=10,
                spaceAfter=8,
                keepWithNext=True
            ),
            "SubsectionHeading": ParagraphStyle(
                "SubsectionHeading",
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=15,
                textColor=c_secondary,
                spaceBefore=8,
                spaceAfter=4,
                keepWithNext=True
            ),
            "Body": ParagraphStyle(
                "Body",
                fontName="Helvetica",
                fontSize=9.5,
                leading=13.5,
                textColor=c_dark,
                spaceAfter=6
            ),
            "CalloutText": ParagraphStyle(
                "CalloutText",
                fontName="Helvetica",
                fontSize=9.5,
                leading=14,
                textColor=c_dark
            ),
            "BulletText": ParagraphStyle(
                "BulletText",
                fontName="Helvetica",
                fontSize=9,
                leading=12.5,
                textColor=c_dark,
                leftIndent=14,
                firstLineIndent=-10,
                spaceAfter=3
            ),
            "TableHeader": ParagraphStyle(
                "TableHeader",
                fontName="Helvetica-Bold",
                fontSize=9,
                leading=12,
                textColor=colors.white,
                alignment=0
            ),
            "TableCell": ParagraphStyle(
                "TableCell",
                fontName="Helvetica",
                fontSize=8.5,
                leading=11.5,
                textColor=c_dark
            ),
            "TableCellBold": ParagraphStyle(
                "TableCellBold",
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11.5,
                textColor=c_primary
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
            # Check for logo
            logo_drawn = False
            if self.branding.logo_path and os.path.exists(self.branding.logo_path):
                try:
                    img = RLImage(self.branding.logo_path, width=2.0 * inch, height=0.75 * inch)
                    img.hAlign = 'LEFT'
                    story.append(img)
                    story.append(Spacer(1, 15))
                    logo_drawn = True
                except Exception:
                    pass

            if not logo_drawn:
                story.append(Paragraph(self.branding.company_name.upper(), styles["CoverCompany"]))
                story.append(Paragraph(self.branding.tagline, styles["CoverTagline"]))

            story.append(HRFlowable(
                width="100%", thickness=3, color=colors.HexColor(self.branding.colors.secondary),
                spaceBefore=5, spaceAfter=25
            ))

            story.append(Spacer(1, 40))
            story.append(Paragraph(page_title, styles["CoverTitle"]))
            story.append(Paragraph(f"Prepared exclusively for <b>{client_name}</b>", styles["CoverSubtitle"]))
            story.append(Paragraph(f"Date: {datetime.date.today().strftime('%B %d, %Y')}", styles["Body"]))

            story.append(Spacer(1, 80))

            # Metadata box
            meta_text = (
                f"<b>Submitted by:</b> {self.branding.company_name}<br/>"
                f"<b>Website:</b> {self.branding.website}<br/>"
                f"<b>Contact:</b> {self.branding.email} | {self.branding.phone}"
            )
            story.append(self._create_callout_box(meta_text, styles["CalloutText"], width=540))
            return

        # ----------------------------------------------------------------------
        # B. Section Header (Common to all content pages)
        # ----------------------------------------------------------------------
        if page_title:
            story.append(Paragraph(page_title, styles["SectionTitle"]))
            if page_subtitle:
                story.append(Paragraph(f"<i>{page_subtitle}</i>", styles["Body"]))
            story.append(HRFlowable(
                width="100%", thickness=1, color=colors.HexColor(self.branding.colors.border),
                spaceBefore=4, spaceAfter=12
            ))

        # ----------------------------------------------------------------------
        # C. Render Components
        # ----------------------------------------------------------------------
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
                    story.append(Paragraph(c_content, styles["Body"]))

            # Paragraphs
            elif c_type == ComponentType.PARAGRAPH:
                if c_content:
                    story.append(Paragraph(c_content, styles["Body"]))

            # Callout boxes (e.g. Executive summary or boundary notes)
            elif c_type == ComponentType.CALLOUT:
                if c_content:
                    story.append(self._create_callout_box(c_content, styles["CalloutText"]))
                    story.append(Spacer(1, 8))

            # Bullet lists / Cards
            elif c_type in (ComponentType.BULLET_LIST, ComponentType.CARD):
                if c_title:
                    story.append(Paragraph(c_title, styles["SubsectionHeading"]))
                if c_content:
                    story.append(Paragraph(c_content, styles["Body"]))
                for item in c_items:
                    bullet_p = Paragraph(f"&bull; &nbsp; {item}", styles["BulletText"])
                    story.append(bullet_p)
                story.append(Spacer(1, 6))

            # Tables (e.g. Pricing / Timelines)
            elif c_type == ComponentType.TABLE:
                if c_title:
                    story.append(Paragraph(c_title, styles["SubsectionHeading"]))
                if c_table:
                    tbl = self._build_platypus_table(c_table, styles)
                    story.append(tbl)
                    story.append(Spacer(1, 10))

            # Closing Acceptance Block
            elif page_type == PageType.CLOSING:
                pass

        # If this is the Closing page, append the formal signature table
        if page_type == PageType.CLOSING:
            story.append(Spacer(1, 15))
            story.append(Paragraph("Proposal Acceptance & Authorization", styles["SubsectionHeading"]))
            story.append(Paragraph(
                "By signing below, the authorized representatives acknowledge and agree to the services, "
                "deliverables, boundaries, and commercial terms outlined in this proposal.",
                styles["Body"]
            ))
            story.append(Spacer(1, 10))
            story.append(self._build_signature_block(client_name, styles))

    def _create_callout_box(self, text: str, text_style: ParagraphStyle, width: float = 540) -> Table:
        """Wraps text in a styled callout card with brand accent left border."""
        c_bg = colors.HexColor(self.branding.colors.neutral_light)
        c_accent = colors.HexColor(self.branding.colors.secondary)

        p = Paragraph(text, text_style)
        t = Table([[p]], colWidths=[width])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), c_bg),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(self.branding.colors.border)),
            ('LINELEFT', (0, 0), (0, -1), 3.0, c_accent),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
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
                if i == 0 or (len(r) > 2 and i == len(r) - 1 and "$" in val_str):
                    cell_p = Paragraph(val_str, styles["TableCellBold"])
                else:
                    cell_p = Paragraph(val_str, styles["TableCell"])
                row_cells.append(cell_p)
            table_matrix.append(row_cells)

        num_cols = len(headers) if headers else (len(rows[0]) if rows else 1)
        total_width = 540.0
        if num_cols == 3:
            col_widths = [220.0, 180.0, 140.0]
        elif num_cols == 2:
            col_widths = [360.0, 180.0]
        elif num_cols == 4:
            col_widths = [160.0, 140.0, 120.0, 120.0]
        else:
            col_widths = [total_width / num_cols] * num_cols

        t = Table(table_matrix, colWidths=col_widths)
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.branding.colors.table_header)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
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
        col_w = 260.0
        sig_data = [
            [
                Paragraph(f"<b>For: {client_name}</b>", styles["TableCellBold"]),
                Paragraph(f"<b>For: {self.branding.company_name}</b>", styles["TableCellBold"])
            ],
            [
                Paragraph("<br/><br/>______________________________________<br/>Authorized Signature", styles["TableCell"]),
                Paragraph("<br/><br/>______________________________________<br/>Authorized Signature", styles["TableCell"])
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
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
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
        story.append(Paragraph(self.branding.company_name.upper(), styles["CoverCompany"]))
        story.append(Paragraph(self.branding.tagline, styles["CoverTagline"]))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(self.branding.colors.secondary), spaceAfter=20))
        story.append(Paragraph(title, styles["CoverTitle"]))
        story.append(Paragraph(f"Prepared for: <b>{client_name}</b>", styles["CoverSubtitle"]))
        story.append(Spacer(1, 30))

        # Executive summary
        if exec_summary:
            story.append(Paragraph("Executive Summary", styles["SectionTitle"]))
            story.append(self._create_callout_box(exec_summary, styles["CalloutText"]))
            story.append(Spacer(1, 15))

        # Sections
        for sec in draft_dict.get("sections", []):
            story.append(Paragraph(sec.get("section_title", "Service Details"), styles["SectionTitle"]))
            if sec.get("opening_text"):
                story.append(Paragraph(sec["opening_text"], styles["Body"]))
            for sub in sec.get("subsections", []):
                if sub.get("heading"):
                    story.append(Paragraph(sub["heading"], styles["SubsectionHeading"]))
                for b in sub.get("bullets", []):
                    story.append(Paragraph(f"&bull; &nbsp; {b}", styles["BulletText"]))
            story.append(Spacer(1, 10))
