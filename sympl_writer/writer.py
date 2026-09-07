"""
Sympl Solutions Proposal RAG — Proposal Writer Layer

The ProposalWriter coordinates the generation of proposal_draft.json from proposal_plan.json:
  1. Enforces the Writer Input Contract (Scope Firewall):
     Rejects any plan containing requested_scope or unapproved_requested_scope.
  2. Constructs bounded prompts with historical exemplars, reference blocks, and style rules.
  3. Executes LLM generation via LLMClient abstraction (OpenRouter, Ollama, or Mock).
  4. Runs comprehensive validation (Scope, Scope Completeness, Pricing, Historical Firewall, Style, Reference Integrity).
  5. Implements the Regeneration Loop:
     If validation fails, sends structured errors back to the LLM for up to 2 retries (3 total attempts).
     Raises RegenerationExhaustedError / WriterError if failures persist.
"""

import json
import os
import re
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from sympl_writer.schema import ProposalDraft
from sympl_writer.llm_client import LLMClient, get_llm_client
from sympl_writer.prompt_builder import PromptBuilder
from sympl_writer.validator import ProposalValidator, ValidationResult
from sympl_writer.exceptions import (
    WriterError,
    ScopeFirewallError,
    RegenerationExhaustedError
)


class ProposalWriter:
    """
    Controlled narrative generation engine for Sympl Solutions proposals.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        validator: Optional[ProposalValidator] = None,
        max_retries: int = 2
    ):
        self.llm_client = llm_client or get_llm_client()
        self.validator = validator or ProposalValidator()
        self.max_retries = max_retries

    def write(self, plan_input: Union[Dict[str, Any], str, Path]) -> ProposalDraft:
        """
        Main entrypoint: converts proposal_plan data into an audited ProposalDraft.

        Args:
            plan_input: Dict of plan data, or path to proposal_plan.json, or JSON string.

        Returns:
            ProposalDraft with verified validation_metadata.

        Raises:
            ScopeFirewallError: If plan contains forbidden unapproved scope fields.
            RegenerationExhaustedError: If validation fails after max_retries.
            WriterError: On fatal JSON parsing or LLM communication failures.
        """
        # 1. Load and parse plan data
        plan_data = self._load_plan_data(plan_input)

        # 2. Strict Input Firewall Check
        self._enforce_input_firewall(plan_data)

        # 3. Generation & Regeneration Loop
        feedback_errors: Optional[List[str]] = None
        last_errors: List[str] = []
        attempt = 0

        while attempt <= self.max_retries:
            attempt += 1

            # A. Build structured prompt
            system_prompt, user_prompt = PromptBuilder.build_prompt(
                plan_data,
                feedback_errors=feedback_errors
            )

            # B. Invoke LLM client
            try:
                raw_response = self.llm_client.generate(
                    user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.1
                )
            except Exception as e:
                raise WriterError(f"LLM generation failed: {e}") from e

            # C. Parse JSON response
            draft_dict = self._extract_json(raw_response)
            draft = ProposalDraft.from_dict(draft_dict)

            # D. Validate draft against plan and invariants
            val_result = self.validator.validate(draft, plan_data, raise_on_error=False)

            # Attach audit metadata to draft
            draft.validation_metadata = {
                "passed": val_result.passed,
                "retries_count": attempt - 1,
                "errors": val_result.errors,
                "warnings": val_result.warnings,
                "details": val_result.details,
                "provider": self.llm_client.provider_name,
                "model": self.llm_client.model_name,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }

            if val_result.passed:
                return draft

            # If validation failed, record errors for next retry
            last_errors = val_result.errors
            feedback_errors = val_result.errors

        # Exceeded maximum retries
        raise RegenerationExhaustedError(
            f"Proposal generation failed validation after {self.max_retries} retry attempts. "
            f"Final errors: {'; '.join(last_errors)}"
        )

    def write_to_file(
        self,
        plan_input: Union[Dict[str, Any], str, Path],
        output_path: Union[str, Path] = "proposal_draft.json"
    ) -> ProposalDraft:
        """
        Executes generation and writes the resulting ProposalDraft to disk as formatted JSON.
        """
        draft = self.write(plan_input)
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(draft.to_json(indent=2))
        return draft

    # --------------------------------------------------------------------------
    # Private Helpers
    # --------------------------------------------------------------------------
    def _load_plan_data(self, plan_input: Union[Dict[str, Any], str, Path]) -> Dict[str, Any]:
        """Resolves input into a dictionary."""
        if hasattr(plan_input, "to_dict"):
            return plan_input.to_dict()

        if isinstance(plan_input, dict):
            return plan_input

        if isinstance(plan_input, (str, Path)):
            p = Path(plan_input)
            if p.is_file():
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            # Try parsing as raw JSON string
            if isinstance(plan_input, str) and plan_input.strip().startswith("{"):
                return json.loads(plan_input)

        raise ValueError(f"Invalid plan input type: {type(plan_input)}")

    def _enforce_input_firewall(self, plan_data: Dict[str, Any]) -> None:
        """
        The Writer MUST NOT receive:
          - requested_scope
          - unapproved_requested_scope
        All scope decisions belong exclusively to Proposal Planner.
        """
        forbidden_keys = ["requested_scope", "unapproved_requested_scope"]
        present_forbidden = [k for k in forbidden_keys if k in plan_data]

        if present_forbidden:
            raise ScopeFirewallError(
                f"Writer Input Firewall Violation: Plan contains forbidden unapproved scope fields: {present_forbidden}. "
                "The Proposal Writer layer is strictly firewalled and accepts only approved_scope."
            )

    def _extract_json(self, response_text: str) -> Dict[str, Any]:
        """Extracts and parses JSON object from model response, stripping markdown code fences if present."""
        cleaned = response_text.strip()

        # Strip markdown ```json ... ``` code fence if returned
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Fallback regex search for outermost JSON object
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            raise WriterError(f"Model output could not be parsed as valid JSON: {e}\nRaw output:\n{response_text[:300]}")
