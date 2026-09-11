"""
Sympl Solutions Proposal RAG — Proposal Renderer Branding Layer

Defines official Sympl Solutions brand design tokens, color palettes,
typography specifications, and styling rules for proposal presentation.
Supports custom branding configurations (logos, palettes, typography, footer metadata).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class ColorPalette:
    """Harmonious color palette for proposal presentation based on official Sympl Brand Guide."""
    primary: str = "#002236"        # Inkwell / Deep Navy (Primary text, headers, dark surfaces)
    secondary: str = "#007E7C"      # Deepwater / Brand Teal Accent (Subheadings, borders, links)
    accent: str = "#FFE079"         # Yolk / Warm Brand Highlight (CTA, swoosh, accents)
    neutral_dark: str = "#002236"   # Inkwell / Slate Charcoal Body Text
    neutral_light: str = "#FBF5F0"  # Paper / Warm Off-White Page & Card Surface
    surface: str = "#FFFFFF"        # Pure White / Card Surfaces
    border: str = "#E2E8EA"         # Delicate Hairline Divider (rgba(0,34,54,0.1))
    callout_bg: str = "#E0F2F0"     # Mist / Soft Sage-Teal Tint for Cards & Callouts
    table_header: str = "#002236"   # Inkwell for Pricing Table Headers
    badge_bg: str = "#E0F2F0"       # Mist Tint for Status Badges
    badge_text: str = "#007E7C"     # Deepwater for Badges
    ink_soft: str = "#4A5F6B"       # Ink-Soft for Subtitles, Captions, and Running Headers
    tan: str = "#F8EEE3"            # Tan for Alternate Card/Section Backgrounds
    seaglass: str = "#C2E6E1"       # Seaglass for Soft Borders & Pills
    bay: str = "#65C1BF"            # Bay for Subtle Accents
    harvest: str = "#E38900"        # Harvest for Warm Badges


@dataclass(frozen=True)
class Typography:
    """Standard typography configuration for Sympl proposals."""
    heading_font: str = "Helvetica-Bold"
    body_font: str = "Helvetica"
    monospace_font: str = "Courier"

    # Font Sizes (pt relative for ReportLab)
    title_size: str = "24pt"
    subtitle_size: str = "12pt"
    h1_size: str = "16pt"
    h2_size: str = "11.5pt"
    h3_size: str = "10pt"
    body_size: str = "9.5pt"
    bullet_size: str = "9pt"
    caption_size: str = "8pt"

    # Line Heights
    line_height_tight: str = "1.2"
    line_height_normal: str = "1.45"
    line_height_relaxed: str = "1.6"


@dataclass
class SymplBranding:
    """Encapsulates corporate identity, assets, and design tokens."""
    company_name: str = "Sympl Solutions Inc."
    tagline: str = "Operational Financial Systems & Strategic Advisory"
    website: str = "https://symplsolutions.ca"
    email: str = "info@symplsolutions.ca"
    phone: str = "+1 (647) 555-0199"
    logo_url: Optional[str] = None
    logo_path: Optional[str] = None
    footer_text: str = "Confidential — Prepared by Sympl Solutions Inc."
    colors: ColorPalette = field(default_factory=ColorPalette)
    typography: Typography = field(default_factory=Typography)
    logo_svg_placeholder: str = "assets/sympl_logo.svg"

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]] = None) -> "SymplBranding":
        """Builds a SymplBranding instance, overriding defaults with any provided values."""
        if not data:
            return cls()

        # Parse custom colors
        c_dict = data.get("colors") or {}
        palette = ColorPalette(
            primary=c_dict.get("primary") or data.get("primary_color", "#002236"),
            secondary=c_dict.get("secondary") or data.get("secondary_color", "#007E7C"),
            accent=c_dict.get("accent", "#FFE079"),
            neutral_dark=c_dict.get("neutral_dark", "#002236"),
            neutral_light=c_dict.get("neutral_light", "#FBF5F0"),
            surface=c_dict.get("surface", "#FFFFFF"),
            border=c_dict.get("border", "#E2E8EA"),
            callout_bg=c_dict.get("callout_bg", "#E0F2F0"),
            table_header=c_dict.get("table_header", "#002236"),
            badge_bg=c_dict.get("badge_bg", "#E0F2F0"),
            badge_text=c_dict.get("badge_text", "#007E7C"),
            ink_soft=c_dict.get("ink_soft", "#4A5F6B"),
            tan=c_dict.get("tan", "#F8EEE3"),
            seaglass=c_dict.get("seaglass", "#C2E6E1"),
            bay=c_dict.get("bay", "#65C1BF"),
            harvest=c_dict.get("harvest", "#E38900")
        )

        # Parse typography
        t_dict = data.get("typography") or {}
        font_family = data.get("font_family") or t_dict.get("body_font", "Helvetica")
        typography = Typography(
            heading_font=t_dict.get("heading_font", "Helvetica-Bold"),
            body_font=font_family,
            title_size=t_dict.get("title_size", "24pt"),
            subtitle_size=t_dict.get("subtitle_size", "12pt"),
            h1_size=t_dict.get("h1_size", "16pt"),
            h2_size=t_dict.get("h2_size", "11.5pt"),
            body_size=t_dict.get("body_size", "9.5pt")
        )

        return cls(
            company_name=data.get("company_name") or "Sympl Solutions Inc.",
            tagline=data.get("tagline") or "Operational Financial Systems & Strategic Advisory",
            website=data.get("website") or "https://symplsolutions.ca",
            email=data.get("email") or "info@symplsolutions.ca",
            phone=data.get("phone") or "+1 (647) 555-0199",
            logo_url=data.get("logo_url"),
            logo_path=data.get("logo_path"),
            footer_text=data.get("footer_text") or "Confidential — Prepared by Sympl Solutions Inc.",
            colors=palette,
            typography=typography
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_name": self.company_name,
            "tagline": self.tagline,
            "website": self.website,
            "email": self.email,
            "phone": self.phone,
            "logo_url": self.logo_url,
            "logo_path": self.logo_path,
            "footer_text": self.footer_text,
            "colors": {
                "primary": self.colors.primary,
                "secondary": self.colors.secondary,
                "accent": self.colors.accent,
                "neutral_dark": self.colors.neutral_dark,
                "neutral_light": self.colors.neutral_light,
                "surface": self.colors.surface,
                "border": self.colors.border,
                "callout_bg": self.colors.callout_bg,
                "table_header": self.colors.table_header,
                "badge_bg": self.colors.badge_bg,
                "badge_text": self.colors.badge_text,
                "ink_soft": self.colors.ink_soft,
                "tan": self.colors.tan,
                "seaglass": self.colors.seaglass,
                "bay": self.colors.bay,
                "harvest": self.colors.harvest
            },
            "typography": {
                "heading_font": self.typography.heading_font,
                "body_font": self.typography.body_font,
                "title_size": self.typography.title_size,
                "subtitle_size": self.typography.subtitle_size,
                "h1_size": self.typography.h1_size,
                "h2_size": self.typography.h2_size,
                "body_size": self.typography.body_size
            }
        }


# Global default branding instance
DEFAULT_BRANDING = SymplBranding()
