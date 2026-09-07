"""
Sympl Solutions Proposal RAG — Proposal Renderer Branding Layer

Defines official Sympl Solutions brand design tokens, color palettes,
typography specifications, and styling rules for proposal presentation.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass(frozen=True)
class ColorPalette:
    """Official Sympl Solutions harmonious color palette."""
    primary: str = "#1A2E40"        # Deep Navy / Foundation
    secondary: str = "#008080"      # Deep Teal / Professional Accent
    accent: str = "#2B6CB0"         # Ocean Blue / Section Header Highlight
    neutral_dark: str = "#2D3748"   # Slate Charcoal / Primary Body Text
    neutral_light: str = "#F7FAFC"  # Warm Off-White / Background Tint
    surface: str = "#FFFFFF"        # Pure White / Card Surfaces
    border: str = "#E2E8F0"         # Soft Border Gray / Dividers
    callout_bg: str = "#EDF2F7"     # Subtle Grey for Boundary Callouts
    table_header: str = "#2A4365"   # Navy Slate for Pricing Table Headers
    badge_bg: str = "#E6FFFA"       # Mint Tint for Approved Status Badges
    badge_text: str = "#234E52"     # Deep Green for Badges


@dataclass(frozen=True)
class Typography:
    """Standard typography configuration for Sympl proposals."""
    heading_font: str = "Montserrat, Inter, sans-serif"
    body_font: str = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    monospace_font: str = "JetBrains Mono, Consolas, monospace"

    # Font Sizes (pt / px relative)
    title_size: str = "28pt"
    subtitle_size: str = "14pt"
    h1_size: str = "20pt"
    h2_size: str = "15pt"
    h3_size: str = "12pt"
    body_size: str = "10.5pt"
    bullet_size: str = "10pt"
    caption_size: str = "8.5pt"

    # Line Heights
    line_height_tight: str = "1.2"
    line_height_normal: str = "1.5"
    line_height_relaxed: str = "1.65"


@dataclass
class SymplBranding:
    """Encapsulates corporate identity, assets, and design tokens."""
    company_name: str = "Sympl Solutions Inc."
    tagline: str = "Operational Financial Systems & Strategic Advisory"
    website: str = "https://symplsolutions.ca"
    email: str = "info@symplsolutions.ca"
    colors: ColorPalette = field(default_factory=ColorPalette)
    typography: Typography = field(default_factory=Typography)
    logo_svg_placeholder: str = "assets/sympl_logo.svg"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_name": self.company_name,
            "tagline": self.tagline,
            "website": self.website,
            "email": self.email,
            "colors": {
                "primary": self.colors.primary,
                "secondary": self.colors.secondary,
                "accent": self.colors.accent,
                "neutral_dark": self.colors.neutral_dark,
                "neutral_light": self.colors.neutral_light,
                "surface": self.colors.surface,
                "border": self.colors.border,
                "callout_bg": self.colors.callout_bg,
                "table_header": self.colors.table_header
            },
            "typography": {
                "heading_font": self.typography.heading_font,
                "body_font": self.typography.body_font,
                "title_size": self.typography.title_size,
                "body_size": self.typography.body_size
            }
        }


# Global default branding instance
DEFAULT_BRANDING = SymplBranding()
