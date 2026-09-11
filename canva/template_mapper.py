"""
Sympl Solutions — Production Hardened Canva Template Mapper
Translates generic CanvaProposalData or ProposalDraft JSON to Canva operations for master template DAHU1H8DMjc.
Applies:
- Cover asset cleanup (deletes Gary Crawford signature artwork if no client logo is provided)
- Heading list_level=0 formatting + Roman numeral stripping (prevents "1. I. EXECUTIVE SUMMARY")
- Strict 30-word commercial description constraints (prevents Page 8 visual overlap)
- Generic dynamic population across all 11 pages
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

from .models import CanvaEditingOperation, CanvaOperationType
from .template_schema import CanvaProposalData, draft_to_canva_data, compress_commercial_description
from .canva_asset_mapper import CanvaAssetMapper


class MasterTemplateMapper:
    """
    Production-hardened mapper for master template DAHU1H8DMjc.
    """

    TEMPLATE_ID = "DAHU1H8DMjc"

    def __init__(self, mapping_file_path: Optional[str] = None):
        if mapping_file_path is None:
            mapping_file_path = Path(r"d:\Sympl\canva_master_template_mapping.json")
        self.mapping_file_path = Path(mapping_file_path)
        self.asset_mapper = CanvaAssetMapper(self.TEMPLATE_ID)

    def map_proposal_to_operations(
        self,
        draft_or_data: Any,
        client_assets: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Translates either a raw ProposalDraft dictionary or normalized CanvaProposalData
        into a validated array of Canva editing operations.
        """
        if isinstance(draft_or_data, CanvaProposalData):
            data = draft_or_data
        elif isinstance(draft_or_data, dict):
            data = draft_to_canva_data(draft_or_data, client_assets)
        else:
            raise ValueError(f"Unsupported draft type: {type(draft_or_data)}")

        operations: List[CanvaEditingOperation] = []

        # =============================================================
        # 1. COVER PAGE (Page 1)
        # =============================================================
        # Clean redundant client name from proposal title if present
        clean_title = data.cover.proposal_title
        lower_client = data.cover.client_name.lower()
        if f"for {lower_client}" in clean_title.lower():
            c_idx = clean_title.lower().find(f"for {lower_client}")
            clean_title = clean_title[:c_idx].strip()
        elif " for " in clean_title:
            clean_title = clean_title.split(" for ")[0].strip()

        cover_title = f"{data.cover.client_name.upper()}\n\n{clean_title.upper()}"
        cover_client_date = f"{data.cover.client_name}\n{data.cover.date}"

        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBV1SCndGVxlSNHy-LBnKP3F5yVR4Dyj4",
            text=cover_title
        ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBV1SCndGVxlSNHy-LB20dGS480CqKK3P",
            text=cover_client_date
        ))

        # Asset Cleanup: Remove Gary Crawford watercolor artwork unless custom logo is provided
        asset_ops = self.asset_mapper.generate_asset_operations(
            client_name=data.cover.client_name,
            client_assets=data.client_assets
        )
        for aop in asset_ops:
            operations.append(CanvaEditingOperation(
                type=CanvaOperationType(aop["type"]),
                element_id=aop.get("element_id"),
                asset_id=aop.get("asset_id"),
                asset_type=aop.get("asset_type"),
                alt_text=aop.get("alt_text")
            ))

        # =============================================================
        # 2. EXECUTIVE SUMMARY (Page 2)
        # =============================================================
        # Section title: Strip Roman numerals and disable Canva list formatting
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBjf8VsrNQJPQVLD-LBl7qGKDyHrSxymB",
            text="Executive Summary"
        ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.FORMAT_TEXT,
            element_id="PBjf8VsrNQJPQVLD-LBl7qGKDyHrSxymB",
            formatting={"list_level": 0}
        ))

        # Executive summary narrative paragraphs (enforcing word bounds <= 220 words)
        exec_text = self._bound_executive_summary(data.executive_summary.full_text, max_words=215)
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBjf8VsrNQJPQVLD-LB4F546VGt88jHkB",
            text=exec_text
        ))

        # =============================================================
        # 3. SCOPE PART 1: Core Service & Deliverables Table (Page 3)
        # =============================================================
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBQnr1MNZFCPZSGT-LBjKVC2RxSFgVB25",
            text="Scope of Work"
        ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.FORMAT_TEXT,
            element_id="PBQnr1MNZFCPZSGT-LBjKVC2RxSFgVB25",
            formatting={"list_level": 0}
        ))

        service_count = len(data.services)
        overview_text = (
            f"The engagement covers {service_count} primary operational areas structured "
            f"to deliver continuous financial controls, governance clarity, and statutory compliance."
        )
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBQnr1MNZFCPZSGT-LBj38qD1z2yhxyRx",
            text=overview_text
        ))

        # Primary Service Module (Module 1)
        mod1 = data.services[0] if data.services else None
        mod1_title = mod1.title if mod1 else "Core Operations"
        mod1_context = mod1.context if mod1 and mod1.context else (
            f"We maintain {data.cover.client_name}'s general ledger on an accrual basis, "
            f"categorizing transactions, recording journal entries, and reconciling accounts monthly with digital backups."
        )
        p3_service_text = f"1. {mod1_title}\n{mod1_context}"
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBQnr1MNZFCPZSGT-LBssff5PZJ8Z97h1",
            text=p3_service_text
        ))

        # Deliverables Table (7 Rows)
        table_deliverables = self._build_deliverables_table(data)
        for idx, (col_a, col_b) in enumerate(table_deliverables, start=2):
            operations.append(CanvaEditingOperation(
                type=CanvaOperationType.REPLACE_TEXT,
                element_id=f"PBQnr1MNZFCPZSGT-LBlspJFPxTyhJsT7-A{idx}",
                text=col_a
            ))
            operations.append(CanvaEditingOperation(
                type=CanvaOperationType.REPLACE_TEXT,
                element_id=f"PBQnr1MNZFCPZSGT-LBlspJFPxTyhJsT7-B{idx}",
                text=col_b
            ))

        p3_outcome = (
            f"Rigorous financial controls ensure full audit compliance and financial transparency, "
            f"giving {data.cover.client_name}'s leadership the clarity required for long-term sustainability."
        )
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBQnr1MNZFCPZSGT-LBhRKsTqzX5VR913",
            text=p3_outcome
        ))

        # =============================================================
        # 4. SCOPE PART 2: Service Modules 2 & 3 (Page 4)
        # =============================================================
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBh3v3V5yD9235ps-LB62x8l2004g8DdT",
            text="Scope of Work"
        ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.FORMAT_TEXT,
            element_id="PBh3v3V5yD9235ps-LB62x8l2004g8DdT",
            formatting={"list_level": 0}
        ))

        mod2 = data.services[1] if len(data.services) > 1 else None
        mod3 = data.services[2] if len(data.services) > 2 else None

        mod2_title = mod2.title if mod2 else "Payroll Administration & Compliance"
        mod2_desc = mod2.context if mod2 and mod2.context else (
            f"We administer all payments for staff, artistic contractors, and touring crew, "
            f"verifying contracts and maintaining tracking required for mandatory annual T4A filing compliance."
        )
        mod3_title = mod3.title if mod3 else "Financial Reporting & Board Governance Support"
        mod3_desc = mod3.context if mod3 and mod3.context else (
            f"We prepare monthly financial packages tailored for the Financial Committee and Board: "
            f"balance sheets, project-level income statements, and budget-to-actual variance analysis."
        )

        p4_composite = f"2. {mod2_title}\n{mod2_desc}\n\n3. {mod3_title}\n{mod3_desc}"
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBh3v3V5yD9235ps-LBp7qPNvclcvg7SV",
            text=p4_composite
        ))

        # =============================================================
        # 5. SCOPE PART 3: Service Module 4 (Page 5)
        # =============================================================
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBNrhdkGL25CnND0-LBd7hDckfDxSD5pf",
            text="Scope of Work"
        ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.FORMAT_TEXT,
            element_id="PBNrhdkGL25CnND0-LBd7hDckfDxSD5pf",
            formatting={"list_level": 0}
        ))

        mod4 = data.services[3] if len(data.services) > 3 else None
        mod4_title = mod4.title if mod4 else "Year-End Preparation & Audit Support"
        mod4_desc = mod4.context if mod4 and mod4.context else (
            f"Audit readiness is built into every monthly reconciliation cycle, not treated as an afterthought. "
            f"We ensure all backup invoices and receipts are uploaded to QBO continuously.\n\n"
            f"At fiscal year-end, Sympl prepares complete digital working papers, account schedules, "
            f"and auditor binders, serving as the direct liaison for the external CPA audit team to ensure a frictionless review."
        )
        p5_text = f"4. {mod4_title}\n{mod4_desc}"
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBNrhdkGL25CnND0-LB2RStvhwrhCKPc6",
            text=p5_text
        ))

        # =============================================================
        # 6. OUR PROCESS / METHODOLOGY (Page 6)
        # =============================================================
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBRbZdkMTPgf8cWP-LBrcfXVW9JCsZC8C",
            text="Our Process"
        ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.FORMAT_TEXT,
            element_id="PBRbZdkMTPgf8cWP-LBrcfXVW9JCsZC8C",
            formatting={"list_level": 0}
        ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBRbZdkMTPgf8cWP-LBLljQR3f4jXWQ89",
            text=data.methodology.intro
        ))
        for idx, phase in enumerate(data.methodology.phases[:6], start=1):
            operations.append(CanvaEditingOperation(
                type=CanvaOperationType.REPLACE_TEXT,
                element_id=f"PBRbZdkMTPgf8cWP-LBHKpjXwHHYVX5dr-A{idx}",
                text=f"{phase.phase_name}\n{phase.description}"
            ))

        # =============================================================
        # 7. PROPOSED TIMELINE (Page 7)
        # =============================================================
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PB21P41FwcjkrKSR-LBkJ4zk76Ff13HJc",
            text="Proposed Timeline"
        ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.FORMAT_TEXT,
            element_id="PB21P41FwcjkrKSR-LBkJ4zk76Ff13HJc",
            formatting={"list_level": 0}
        ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PB21P41FwcjkrKSR-LB6z7Wx9zxYVC3WF",
            text=data.timeline.intro
        ))
        for idx, item in enumerate(data.timeline.items[:6], start=2):
            operations.append(CanvaEditingOperation(
                type=CanvaOperationType.REPLACE_TEXT,
                element_id=f"PB21P41FwcjkrKSR-LBXplPwkJYWpghqY-A{idx}",
                text=item.cadence
            ))
            operations.append(CanvaEditingOperation(
                type=CanvaOperationType.REPLACE_TEXT,
                element_id=f"PB21P41FwcjkrKSR-LBXplPwkJYWpghqY-B{idx}",
                text=item.phase
            ))
            operations.append(CanvaEditingOperation(
                type=CanvaOperationType.REPLACE_TEXT,
                element_id=f"PB21P41FwcjkrKSR-LBXplPwkJYWpghqY-C{idx}",
                text=item.deliverables
            ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PB21P41FwcjkrKSR-LBrqfbHD6Jlk0xbt",
            text=data.timeline.disclaimer
        ))

        # =============================================================
        # 8. COST & PAYMENT SCHEDULE (Page 8)
        # =============================================================
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBJbHpggXKcsRwJL-LBclS9Bl3WKcp4d3",
            text="Cost & Payment Schedule"
        ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.FORMAT_TEXT,
            element_id="PBJbHpggXKcsRwJL-LBclS9Bl3WKcp4d3",
            formatting={"list_level": 0}
        ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBJbHpggXKcsRwJL-LBClW40Hp9zJy1kg",
            text=data.pricing.intro
        ))

        # Strict 15-word constraint on investment card to prevent overlap with Fee Schedule
        compressed_desc = compress_commercial_description(data.pricing.investment_description, max_words=15)
        investment_card_text = f"{data.pricing.investment_heading}\n{data.pricing.investment_amount}\n{compressed_desc}"
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBJbHpggXKcsRwJL-LBnjdgTzYwZlPDGj-A1",
            text=investment_card_text
        ))

        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBJbHpggXKcsRwJL-LB5yZ6WVQyNzjX7c",
            text=data.pricing.schedule_header
        ))

        # Two Milestones
        m1 = data.pricing.milestones[0] if len(data.pricing.milestones) > 0 else None
        m2 = data.pricing.milestones[1] if len(data.pricing.milestones) > 1 else None

        m1_text = f"{m1.label}\n{m1.trigger}\n{m1.amount}" if m1 else "INITIATION\nOn contract signing.\n$3,500"
        m2_text = f"{m2.label}\n{m2.trigger}\n{m2.amount}" if m2 else "COMPLETION\nProject sign-off.\n$4,000"

        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBJbHpggXKcsRwJL-LBDLdTxbgC9ym6Wg-A1",
            text=m1_text
        ))
        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBJbHpggXKcsRwJL-LBDLdTxbgC9ym6Wg-B1",
            text=m2_text
        ))

        operations.append(CanvaEditingOperation(
            type=CanvaOperationType.REPLACE_TEXT,
            element_id="PBJbHpggXKcsRwJL-LBtcQdNnVgFYCgLN-A1",
            text=data.pricing.exclusions_note
        ))

        return [op.to_dict() for op in operations]

    def _bound_executive_summary(self, summary: str, max_words: int = 215) -> str:
        paragraphs = [p.strip() for p in summary.split("\n\n") if p.strip()]
        text = "\n\n".join(paragraphs)
        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words]) + "..."
        return text

    def _build_deliverables_table(self, data: CanvaProposalData) -> List[tuple]:
        """
        Extracts exactly 7 structured deliverable rows for Page 3 table.
        """
        rows = []
        # If services already contain explicit deliverables, use them
        for s in data.services:
            for d in s.deliverables:
                rows.append((d.component, d.description))

        if not rows:
            # Generate from service titles and bullets
            for s in data.services:
                comp = s.title.replace("Accounting & Bookkeeping Services", "GL Accounting")
                comp = comp.replace("Financial Reporting & Governance Support", "Financial Reporting")
                comp = comp.replace("Statutory Compliance & Filings", "Compliance")
                comp = comp.replace("Payroll Accounting & Administration", "Payroll Admin")
                desc = s.context[:100] if s.context else "Standard operational scope and documentation."
                rows.append((comp[:22], desc))

        # Default 7 rows if not filled
        default_7 = [
            ("GL Maintenance", "Accrual-basis monthly ledger updates, transaction coding, and journal entries"),
            ("Reconciliations", "Monthly reconciliation of operating accounts, credit cards, and merchant processors"),
            ("Accounts Payable", "Bill processing, vendor invoice backup matching, and payment approval workflows"),
            ("Contractor Payroll", "Performance fee payments, artist contractor tracking, and year-end T4A preparation"),
            ("Grant Tracking", "Project-based cost center accounting for arts council grants and touring shows"),
            ("Governance Pack", "Monthly financial statements and variance commentary for Financial Committee"),
            ("Audit Readiness", "Organized digital working papers and auditor binder preparation continuous throughout the year")
        ]
        while len(rows) < 7:
            rows.append(default_7[len(rows)])

        return rows[:7]
