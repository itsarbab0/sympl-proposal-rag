"""
Sympl Solutions Proposal RAG — Website Development Domain Playbook

Contains established operating methodologies for website redesign, information architecture,
portfolio showcases, responsive CMS configuration, e-commerce, and client training engagements.
Extracted strictly from historical Sympl proposal: CRAWFORD_2026.
"""

from typing import List

WEBSITE_OPERATIONAL_PLAYBOOK_SYSTEM = """SYMPL WEBSITE DEVELOPMENT PLAYBOOK (COMMON OPERATING PATTERNS):
When relevant to approved scope, incorporate Sympl's established website development methodologies:
1. Site Architecture & Collector/Audience-First UX:
   - Restructure site navigation from internal or medium-first to collector/audience-first, prioritizing effortless discovery.
   - Clean, image-forward visual hierarchy: homepage hero with clear artist/organizational statement, portfolio galleries organized by series, subject, or date.
   - Dedicated artwork/item pages featuring dimensions, medium, year, high-resolution photography, and direct enquiry or acquisition pathways.
2. Content Migration & Asset Optimization:
   - Migration of existing portfolio assets, exhibition history, biographies, and press coverage.
   - High-resolution media optimization, image re-exporting, and metadata tagging for search engine discovery.
3. E-Commerce & Acquisition Workflows:
   - Modern, client-maintainable CMS deployment (Squarespace Commerce / Webflow / WordPress).
   - "Available Now" store catalog with pricing, dimensions, and integrated payment processing (Stripe or PayPal).
   - "Sold" label functionality to preserve exhibition and portfolio history without inventory confusion.
   - Integrated inquiry form routing directly to client email.
4. Client Empowerment, Training & Warranty:
   - Live 1-on-1 walkthrough session paced to client comfort, covering content updates, catalog management, and media uploads.
   - Tailored written site guide / PDF manual covering only client-specific tasks in plain language (not a generic manual).
   - 30-day post-launch technical warranty for minor adjustments and operational support in live use.
IMPORTANT: Only use these workflows when relevant to approved scope. Do not hallucinate unapproved services, features, or administrative workflows."""

WEBSITE_OPERATIONAL_PLAYBOOK_USER_LINES: List[str] = [
    "1. SYMPL WEBSITE DEVELOPMENT PLAYBOOK (COMMON OPERATING PATTERNS):",
    "   When relevant to approved scope, incorporate Sympl's proven web methodologies:",
    "   * Site Architecture & UX Design:",
    "     - Collector/audience-first navigation restructuring and visual hierarchy",
    "     - Image-forward gallery organization (by series, subject, or date)",
    "     - Dedicated artwork/item pages with dimensions, medium, year, and enquiry pathway",
    "   * Content Migration & Media Optimization:",
    "     - Full asset migration (portfolio, biography, exhibitions, press)",
    "     - High-resolution image re-optimization and SEO metadata tagging",
    "   * E-Commerce & Acquisition Workflows:",
    "     - Modern, client-maintainable CMS setup (Squarespace Commerce or equivalent)",
    "     - Available Now store catalog with payment processing (Stripe/PayPal)",
    "     - Direct enquiry routing to client email and 'Sold' label functionality",
    "   * Training & Post-Launch Support:",
    "     - Live 1-on-1 training walkthrough and recorded video tutorials",
    "     - Tailored written site guide / PDF manual covering only client-specific tasks",
    "     - 30-day post-launch technical support window",
    "   IMPORTANT: Only use these workflows when relevant to approved scope. Do not hallucinate unapproved services."
]

# -----------------------------------------------------------------------------
# Phase 2C Domain Decoupling Metadata
# -----------------------------------------------------------------------------
BENCHMARK_REFERENCES: List[str] = ["CRAWFORD_2026"]

JSON_EXAMPLE_SUBHEADING: str = "Collector Journey / CMS Architecture"

EXECUTIVE_SUMMARY_GUIDANCE: str = """EXECUTIVE SUMMARY NARRATIVE GUIDANCE (WEBSITE DEVELOPMENT & CMS REDESIGN):
Problem:
Client's current digital presence is fragmented, difficult to navigate across portfolio collections, lacks mobile-first responsiveness, and provides no clear acquisition or inquiry pathway for art collectors and buyers.
Approach:
Sympl designs an intuitive, collector-first information architecture on Squarespace, organizing portfolios into curated thematic series, deploying high-resolution visual curation, and implementing an Available Now store catalog with direct Stripe checkout and inquiry routing.
Outcome:
Independent client publishing autonomy, streamlined collector discovery and acquisition, respectful gallery partner attribution, and zero long-term developer lock-in supported by a tailored editing guide and 30-day warranty."""

DOMAIN_VOCABULARY: List[str] = [
    "Squarespace", "Collector-First UX", "Information Architecture", "Available Now Catalog",
    "Stripe", "High-Resolution Artwork Photography", "Color Profiling", "Series Navigation",
    "Inquiry Pathway", "Gallery Attribution", "Certificate of Authenticity", "30-Day Warranty",
    "SEO Metadata Tagging", "Mobile-First Design", "Client Empowerment Guide"
]

