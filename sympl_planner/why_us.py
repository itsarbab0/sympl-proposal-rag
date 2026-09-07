"""
Sympl Solutions Proposal RAG — Why Us Reference Block Assembly & Decision Engine

Implements:
  1. Dynamic Why Us inclusion evaluation (not hardcoded by archetype).
  2. Deterministic reference block assembly in canonical historical order.
  3. Sector and organization identity variant selection.
"""

from typing import List, Dict, Any, Tuple
from .schema import ClientInput


class WhyUsSelector:
    """
    Evaluates Why Us inclusion dynamically and compiles the canonical reference block sequence.
    """

    REFERENCE_BLOCKS = {
        "REF_BLOCK_WHY_US_OPENING": {
            "block_key": "REF_BLOCK_WHY_US_OPENING",
            "render_as": "intro",
            "content": "Sympl Solutions is committed to ensuring a high standard of financial clarity and timely support. We bring:"
        },
        "REF_BLOCK_WHY_US_CREDENTIAL_RESPONSIVE_TEAM": {
            "block_key": "REF_BLOCK_WHY_US_CREDENTIAL_RESPONSIVE_TEAM",
            "render_as": "bullet",
            "content": "A responsive, detail-oriented team"
        },
        "REF_BLOCK_WHY_US_EXP_NONPROFIT": {
            "block_key": "REF_BLOCK_WHY_US_EXP_NONPROFIT",
            "render_as": "bullet",
            "content": "Decade-long expertise in nonprofit finance"
        },
        "REF_BLOCK_WHY_US_EXP_CHARITY": {
            "block_key": "REF_BLOCK_WHY_US_EXP_CHARITY",
            "render_as": "bullet",
            "content": "Decade-long expertise in nonprofit and charity finance"
        },
        "REF_BLOCK_WHY_US_CREDENTIAL_TECH_INTEGRATION": {
            "block_key": "REF_BLOCK_WHY_US_CREDENTIAL_TECH_INTEGRATION",
            "render_as": "bullet",
            "content": "Streamlined tech integration and clear process flows"
        },
        "REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL": {
            "block_key": "REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL",
            "render_as": "bullet",
            "content": "BIPOC and immigrant-led leadership with lived experiences in community, social service and arts & culture"
        },
        "REF_BLOCK_WHY_US_SECTOR_ARTS_LEADERSHIP": {
            "block_key": "REF_BLOCK_WHY_US_SECTOR_ARTS_LEADERSHIP",
            "render_as": "bullet",
            "content": "BIPOC-led leadership with lived experiences in community arts"
        },
        "REF_BLOCK_WHY_US_SECTOR_ARTS_EXP_RPFF": {
            "block_key": "REF_BLOCK_WHY_US_SECTOR_ARTS_EXP_RPFF",
            "render_as": "bullet",
            "content": "Experience with arts and non-profit organizations across Canada"
        },
        "REF_BLOCK_WHY_US_CLOSING_1": {
            "block_key": "REF_BLOCK_WHY_US_CLOSING_1",
            "render_as": "paragraph",
            "content": "We value thoughtful system design, clarity in reporting, and building long-term trusted partnerships."
        },
        "REF_BLOCK_WHY_US_CLOSING_2": {
            "block_key": "REF_BLOCK_WHY_US_CLOSING_2",
            "render_as": "paragraph",
            "content": "Any new requirements or adjustments can be discussed and integrated as needed. We work with transparency, flexibility, and a commitment to helping our partners thrive."
        }
    }

    @classmethod
    def evaluate_inclusion(cls, client_input: ClientInput, selected_archetype: str) -> Tuple[bool, str]:
        """
        Dynamically evaluates whether to include Why Us.
        Does NOT hardcode inclusion solely by archetype name.
        Returns (include_why_us, rationale).
        """
        pref = client_input.preferences
        eng = client_input.engagement
        org = client_input.organization

        # 1. Explicit user/client override takes top priority
        if pref.include_why_us is not None:
            return pref.include_why_us, f"Explicit preference provided in intake (include_why_us={pref.include_why_us})."

        # 2. Competitive pitch or RFP requires credentials
        if pref.is_competitive_pitch:
            return True, "Included due to competitive pitch / RFP context requiring credentials presentation."

        # 3. Trusted existing continuity / compact extension suppresses credentials
        if pref.is_trusted_continuity and eng.complexity == "compact":
            return False, "Omitted due to trusted ongoing continuity engagement with compact scope."

        # 4. Contextual assessment based on engagement depth and organization
        if selected_archetype in ("ARCH_COMPREHENSIVE_TRANSFORMATION", "ARCH_STANDARD_NONPROFIT"):
            # Multi-stakeholder proposals benefit strongly from Why Us credentials
            return True, f"Included to establish organizational alignment for multi-stakeholder {selected_archetype}."

        if selected_archetype == "ARCH_AUDIT_OVERSIGHT_TRANSFORMATION":
            # Audit oversight demands accountability and team pedigree
            return True, "Included to reinforce governance credibility for audit diagnostic engagement."

        if selected_archetype == "ARCH_TRANSITION_INTERIM":
            # Interim engagements benefit from trust and stability messaging
            return True, "Included to support interim stability and handover trust."

        # 5. For ARCH_COMPACT_BOOKKEEPING: evaluate if new client vs routine schedule
        if selected_archetype == "ARCH_COMPACT_BOOKKEEPING":
            if org.organization_type in ("charity", "nonprofit") and not pref.is_trusted_continuity:
                return True, "Included for nonprofit bookkeeping client to affirm sector commitment."
            return False, "Omitted to maintain lean, direct operational schedule for compact bookkeeping."

        return True, "Included by standard planner evaluation."

    @classmethod
    def assemble_why_us(cls, client_input: ClientInput) -> List[Dict[str, Any]]:
        """
        Assembles canonical Why Us reference blocks in strict historical order.
        """
        org = client_input.organization
        pref = client_input.preferences
        blocks: List[Dict[str, Any]] = []

        # 1. Opening Declaration (Deterministic)
        blocks.append(cls.REFERENCE_BLOCKS["REF_BLOCK_WHY_US_OPENING"])

        # 2. Responsive Team Credential (Deterministic)
        blocks.append(cls.REFERENCE_BLOCKS["REF_BLOCK_WHY_US_CREDENTIAL_RESPONSIVE_TEAM"])

        # 3. Organization Expertise Variant (Nonprofit vs Charity)
        if org.organization_type == "charity":
            blocks.append(cls.REFERENCE_BLOCKS["REF_BLOCK_WHY_US_EXP_CHARITY"])
        elif org.organization_type == "nonprofit":
            blocks.append(cls.REFERENCE_BLOCKS["REF_BLOCK_WHY_US_EXP_NONPROFIT"])
        # For commercial/for_profit entities, omit nonprofit expertise bullet

        # 4. Tech Integration Credential (Deterministic)
        blocks.append(cls.REFERENCE_BLOCKS["REF_BLOCK_WHY_US_CREDENTIAL_TECH_INTEGRATION"])

        # 5. Sector & Identity Lived Experience Variant
        pref_id = pref.identity_credential_preference

        if pref_id == "community_social" or (
            pref_id in (None, "auto") and org.sector in ("community_services", "social_services", "literacy")
        ):
            blocks.append(cls.REFERENCE_BLOCKS["REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL"])

        elif pref_id == "arts_leadership" or (
            pref_id in (None, "auto") and org.sector == "arts_culture"
        ):
            blocks.append(cls.REFERENCE_BLOCKS["REF_BLOCK_WHY_US_SECTOR_ARTS_LEADERSHIP"])
            # If arts organization with national/cross-Canada context, add RPFF national experience
            if "across canada" in (org.description or "").lower() or "national" in (org.description or "").lower():
                blocks.append(cls.REFERENCE_BLOCKS["REF_BLOCK_WHY_US_SECTOR_ARTS_EXP_RPFF"])

        # 6. Standalone Closing Paragraph 1 (Deterministic)
        blocks.append(cls.REFERENCE_BLOCKS["REF_BLOCK_WHY_US_CLOSING_1"])

        # 7. Standalone Closing Paragraph 2 (Deterministic)
        blocks.append(cls.REFERENCE_BLOCKS["REF_BLOCK_WHY_US_CLOSING_2"])

        return blocks
