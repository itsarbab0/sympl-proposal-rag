"""
Tests Phase 2A Prompt Equivalence & Modular Playbook Extraction.

Verifies:
1. PromptBuilder.SYSTEM_PROMPT is character-for-character identical to pre-Phase 2A baseline snapshot.
2. PromptBuilder.build_prompt() produces character-for-character identical system and user prompts to pre-Phase 2A baseline snapshot.
3. Modular playbooks contain exact domain and base style components without changes.
4. Accounting proposal output flow remains unchanged and valid under ProposalWriter with modular playbooks.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Force offline mode for transformers/huggingface if imported transitively
os.environ["HF_HUB_OFFLINE"] = "1"

from sympl_writer.prompt_builder import PromptBuilder
from sympl_writer.playbooks.base_style import (
    BASE_STYLE_SYSTEM_PERSONA,
    BASE_STYLE_SYSTEM_RULES,
    BASE_STYLE_USER_HEADER,
    BASE_STYLE_USER_INSTRUCTIONS_LINES,
    FORBIDDEN_PHRASES,
)
from sympl_writer.playbooks.accounting_playbook import (
    ACCOUNTING_OPERATIONAL_PLAYBOOK_SYSTEM,
    ACCOUNTING_OPERATIONAL_PLAYBOOK_USER_LINES,
)
from sympl_writer.writer import ProposalWriter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "prompt_snapshot_phase2a_baseline.json"


@pytest.fixture
def snapshot_data():
    """Loads the pre-Phase 2A baseline prompt snapshot."""
    assert FIXTURE_PATH.exists(), f"Snapshot fixture missing at {FIXTURE_PATH}"
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestPromptEquivalence:
    """Test suite verifying prompt equivalence before and after Phase 2A extraction."""

    def test_system_prompt_raw_identical(self, snapshot_data):
        """Verify PromptBuilder.SYSTEM_PROMPT is byte-for-byte identical to baseline."""
        baseline_raw = snapshot_data["system_prompt_raw"]
        current_raw = PromptBuilder.SYSTEM_PROMPT

        assert current_raw == baseline_raw, (
            "PromptBuilder.SYSTEM_PROMPT diverged from pre-Phase 2A baseline!"
        )

    def test_build_prompt_system_and_user_identical(self, snapshot_data):
        """Verify build_prompt generates identical system and user prompts for accounting plan."""
        input_plan = snapshot_data["input_plan"]
        baseline_sys = snapshot_data["oldt_system_prompt"]
        baseline_user = snapshot_data["oldt_user_prompt"]

        current_sys, current_user = PromptBuilder.build_prompt(input_plan)

        assert current_sys == baseline_sys, (
            "Generated system prompt does not match pre-Phase 2A baseline snapshot!"
        )
        assert current_user == baseline_user, (
            "Generated user prompt does not match pre-Phase 2A baseline snapshot!"
        )

    def test_base_style_elements_preserved(self):
        """Verify base_style contains tone, narrative-first, bullet rules, JSON schema, and forbidden phrases."""
        # Persona & Tone
        assert "Lead Proposal Writer and Engagement Director at Sympl Solutions Inc." in BASE_STYLE_SYSTEM_PERSONA
        assert "consulting-style" in BASE_STYLE_SYSTEM_PERSONA

        # Rules
        assert "CONSULTING ENGAGEMENT PHILOSOPHY" in BASE_STYLE_SYSTEM_RULES
        assert "MANDATORY SERVICE SECTION FLOW" in BASE_STYLE_SYSTEM_RULES
        assert "BULLET POINT RULES & REDUCTION" in BASE_STYLE_SYSTEM_RULES
        assert "HISTORICAL EXEMPLAR GUIDANCE" in BASE_STYLE_SYSTEM_RULES
        assert "CORE OPERATIONAL INVARIANTS" in BASE_STYLE_SYSTEM_RULES

        # Forbidden phrases
        assert len(FORBIDDEN_PHRASES) >= 15
        assert "leverage" in FORBIDDEN_PHRASES
        assert "cutting-edge" in FORBIDDEN_PHRASES
        assert "bespoke transformation journey" in FORBIDDEN_PHRASES

        # User header and instruction lines
        assert len(BASE_STYLE_USER_HEADER) > 0
        assert len(BASE_STYLE_USER_INSTRUCTIONS_LINES) > 0

    def test_accounting_playbook_elements_preserved(self):
        """Verify accounting_playbook contains QBO, Dext, Plooto, month-end close, reporting workflows."""
        sys_playbook = ACCOUNTING_OPERATIONAL_PLAYBOOK_SYSTEM
        user_lines_text = "\n".join(ACCOUNTING_OPERATIONAL_PLAYBOOK_USER_LINES)

        for text in [sys_playbook, user_lines_text]:
            assert "QuickBooks Online" in text or "QBO" in text
            assert "Dext" in text
            assert "Plooto" in text
            assert "month-end close" in text or "Month-end close" in text
            assert "reporting" in text.lower()

    def test_accounting_proposal_writer_output_unchanged(self, snapshot_data):
        """Verify that ProposalWriter invokes the prompt builder and preserves valid proposal generation."""
        input_plan = snapshot_data["input_plan"]

        from sympl_writer.llm_client import MockLLMClient

        client = MockLLMClient()
        with patch.object(client, "generate", wraps=client.generate) as mock_gen:
            writer = ProposalWriter(llm_client=client)
            draft = writer.write(input_plan)

            # Verify that the writer passed the exact snapshot prompts to the LLM
            assert mock_gen.called
            call_args = mock_gen.call_args
            called_user_prompt = call_args[0][0]
            called_sys_prompt = call_args[1]["system_prompt"]

            assert called_sys_prompt == snapshot_data["oldt_system_prompt"]
            assert called_user_prompt == snapshot_data["oldt_user_prompt"]

            # Verify draft generated properly and passed validation
            assert draft is not None
            assert draft.title == f"Accounting & Bookkeeping Services Proposal for {input_plan['client_name']}"
            assert draft.pricing["pricing_model"] == "fixed_retainer"
            assert len(draft.pricing["fee_items"]) > 0
            assert draft.pricing["has_placeholders"] is False
