#!/usr/bin/env python3
"""Dataset validation utility for Sympl Proposal RAG.

Inspects normalized proposal JSON files in data/normalized/ against the data contract.
Produces separate human-readable errors and warnings.
Exits 0 if valid (even with warnings), exits 1 if hard errors exist.
Never modifies files.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any, List, Set, Tuple

# Known taxonomies for validation warnings
KNOWN_SERVICE_MODULES: Set[str] = {
    "bookkeeping",
    "reconciliations",
    "accounts_payable",
    "accounts_receivable",
    "payroll",
    "financial_reporting",
    "compliance",
    "year_end",
    "audit",
    "financial_management",
    "budgeting",
    "cash_flow",
    "funder_reporting",
    "digital_transformation",
    "systems_implementation",
    "onboarding",
    "transition",
    "training",
    "process_documentation",
}

KNOWN_SECTION_TYPES: Set[str] = {
    "cover",
    "context_objectives",
    "engagement_summary",
    "scope",
    "service_module",
    "bookkeeping",
    "payroll",
    "financial_reporting",
    "compliance",
    "audit",
    "financial_management",
    "digital_transformation",
    "onboarding",
    "transition",
    "timeline",
    "pricing",
    "exclusions",
    "client_responsibilities",
    "why_us",
}


class ValidationReport:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.files_checked: int = 0
        self.chunks_checked: int = 0

    def add_error(self, filepath: Path | str, message: str) -> None:
        name = Path(filepath).name if isinstance(filepath, (Path, str)) else str(filepath)
        self.errors.append(f"[{name}] ERROR: {message}")

    def add_warning(self, filepath: Path | str, message: str) -> None:
        name = Path(filepath).name if isinstance(filepath, (Path, str)) else str(filepath)
        self.warnings.append(f"[{name}] WARNING: {message}")

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def is_strict_bool(val: Any) -> bool:
    """Ensure value is strictly a boolean, not int (0/1) or None."""
    return type(val) is bool


def is_string_list(val: Any) -> bool:
    """Ensure value is a list of strings."""
    if not isinstance(val, list):
        return False
    return all(isinstance(item, str) for item in val)


def validate_iso_date(val: Any) -> bool:
    """Validate ISO YYYY-MM-DD date string."""
    if not isinstance(val, str):
        return False
    try:
        parts = val.split("-")
        if len(parts) != 3 or len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
            return False
        datetime.date.fromisoformat(val)
        return True
    except (ValueError, TypeError):
        return False


def validate_proposal_object(
    proposal: Any,
    filepath: Path,
    seen_proposal_codes: Set[str],
    report: ValidationReport,
) -> str | None:
    """Validate top-level 'proposal' dictionary."""
    if not isinstance(proposal, dict):
        report.add_error(filepath, "'proposal' field must be a JSON object (dict)")
        return None

    # Required proposal fields
    code = proposal.get("proposal_code")
    if not isinstance(code, str) or not code.strip():
        report.add_error(filepath, "Missing or empty required field 'proposal.proposal_code'")
        code = None
    else:
        code = code.strip()
        if code in seen_proposal_codes:
            report.add_error(filepath, f"Duplicate proposal_code '{code}' detected across files")
        else:
            seen_proposal_codes.add(code)

    client_name = proposal.get("client_name")
    if not isinstance(client_name, str) or not client_name.strip():
        report.add_error(filepath, "Missing or empty required field 'proposal.client_name'")

    source_filename = proposal.get("source_filename")
    if not isinstance(source_filename, str) or not source_filename.strip():
        report.add_error(filepath, "Missing or empty required field 'proposal.source_filename'")

    core_bookkeeping = proposal.get("core_bookkeeping")
    if not is_strict_bool(core_bookkeeping):
        report.add_error(filepath, "Field 'proposal.core_bookkeeping' must be a boolean (true/false)")

    # Optional proposal date
    proposal_date = proposal.get("proposal_date")
    if proposal_date is not None and not validate_iso_date(proposal_date):
        report.add_error(
            filepath,
            f"Invalid 'proposal.proposal_date': '{proposal_date}'. Expected ISO format YYYY-MM-DD",
        )

    # Optional metadata
    metadata = proposal.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        report.add_error(filepath, "Field 'proposal.metadata' must be a JSON object (dict) if present")

    return code


def validate_chunk_object(
    chunk: Any,
    index: int,
    filepath: Path,
    proposal_code: str | None,
    seen_chunk_keys: Set[str],
    report: ValidationReport,
) -> None:
    """Validate a single proposal chunk object."""
    report.chunks_checked += 1
    prefix = f"Chunk [{index}]"

    if not isinstance(chunk, dict):
        report.add_error(filepath, f"{prefix} must be a JSON object (dict)")
        return

    # chunk_key
    chunk_key = chunk.get("chunk_key")
    if not isinstance(chunk_key, str) or not chunk_key.strip():
        report.add_error(filepath, f"{prefix} missing or empty required field 'chunk_key'")
        loc_desc = f"{prefix}"
    else:
        chunk_key = chunk_key.strip()
        loc_desc = f"Chunk '{chunk_key}'"
        if chunk_key in seen_chunk_keys:
            report.add_error(filepath, f"Duplicate chunk_key '{chunk_key}' detected globally")
        else:
            seen_chunk_keys.add(chunk_key)

    # section_type
    section_type = chunk.get("section_type")
    if not isinstance(section_type, str) or not section_type.strip():
        report.add_error(filepath, f"{loc_desc} missing or empty required field 'section_type'")
    else:
        section_type = section_type.strip()
        if section_type not in KNOWN_SECTION_TYPES:
            report.add_warning(
                filepath,
                f"{loc_desc} has unknown section_type '{section_type}'. Valid known types: {sorted(KNOWN_SECTION_TYPES)}",
            )

    # Text fields: raw_text, cleaned_text, retrieval_text
    for field_name in ("raw_text", "cleaned_text", "retrieval_text"):
        val = chunk.get(field_name)
        if not isinstance(val, str) or not val.strip():
            report.add_error(filepath, f"{loc_desc} missing or empty required field '{field_name}'")

    # Array fields
    array_fields = [
        "service_modules",
        "accounting_systems",
        "payroll_systems",
        "cadence",
        "special_requirements",
    ]
    for field_name in array_fields:
        val = chunk.get(field_name)
        if val is None or not is_string_list(val):
            report.add_error(filepath, f"{loc_desc} field '{field_name}' must be an array of strings")

    # Check service modules against known taxonomy
    service_modules = chunk.get("service_modules")
    if isinstance(service_modules, list):
        for sm in service_modules:
            if isinstance(sm, str) and sm not in KNOWN_SERVICE_MODULES:
                report.add_warning(
                    filepath,
                    f"{loc_desc} contains unknown service_module '{sm}'. Valid known modules: {sorted(KNOWN_SERVICE_MODULES)}",
                )

    # Boolean fields
    boolean_fields = [
        "core_bookkeeping",
        "retrieval_enabled",
        "commercial_reference_only",
        "pricing_content",
        "boilerplate_content",
    ]
    for field_name in boolean_fields:
        val = chunk.get(field_name)
        if not is_strict_bool(val):
            report.add_error(filepath, f"{loc_desc} field '{field_name}' must be a boolean (true/false)")

    # Section order sanity
    section_order = chunk.get("section_order")
    if section_order is not None and (not isinstance(section_order, int) or is_strict_bool(section_order) or section_order < 0):
        report.add_error(filepath, f"{loc_desc} field 'section_order' must be null or an integer >= 0")

    # Pricing & Safety Invariants
    pricing_content = chunk.get("pricing_content") is True
    commercial_ref = chunk.get("commercial_reference_only") is True
    retrieval_enabled = chunk.get("retrieval_enabled") is True
    boilerplate_content = chunk.get("boilerplate_content") is True

    # Rule 1: pricing_content=true IMPLIES commercial_reference_only=true
    if pricing_content and not commercial_ref:
        report.add_error(
            filepath,
            f"{loc_desc} has pricing_content=true but commercial_reference_only=false. "
            "Safety requirement: Historical pricing must always be marked commercial_reference_only=true.",
        )

    # Rule 2: pricing_content=true IMPLIES retrieval_enabled=false (Database Constraint chk_pricing_safety)
    if pricing_content and retrieval_enabled:
        report.add_error(
            filepath,
            f"{loc_desc} has pricing_content=true AND retrieval_enabled=true. "
            "Hard safety error: Historical pricing must never be retrieval_enabled.",
        )

    # Rule 3: boilerplate_content=true IMPLIES retrieval_enabled=false (Database Constraint chk_boilerplate_retrieval)
    if boilerplate_content and retrieval_enabled:
        report.add_error(
            filepath,
            f"{loc_desc} has boilerplate_content=true AND retrieval_enabled=true. "
            "Hard safety error: Historical boilerplate must never be retrieval_enabled. "
            "Approved standard boilerplate belongs in sympl_reference_blocks.",
        )

    # Optional metadata
    metadata = chunk.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        report.add_error(filepath, f"{loc_desc} field 'metadata' must be a JSON object (dict) if present")


def validate_file(
    filepath: Path,
    seen_proposal_codes: Set[str],
    seen_chunk_keys: Set[str],
    report: ValidationReport,
) -> None:
    """Validate a single JSON file."""
    report.files_checked += 1
    try:
        with filepath.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        report.add_error(filepath, f"Invalid JSON syntax: {exc}")
        return
    except Exception as exc:
        report.add_error(filepath, f"Failed to read file: {exc}")
        return

    if not isinstance(data, dict):
        report.add_error(filepath, "Top-level JSON structure must be an object (dict)")
        return

    # Check top-level keys
    if "proposal" not in data:
        report.add_error(filepath, "Missing required top-level object 'proposal'")
        proposal_code = None
    else:
        proposal_code = validate_proposal_object(
            data["proposal"], filepath, seen_proposal_codes, report
        )

    if "chunks" not in data:
        report.add_error(filepath, "Missing required top-level array 'chunks'")
    elif not isinstance(data["chunks"], list):
        report.add_error(filepath, "Top-level field 'chunks' must be a JSON array (list)")
    else:
        for idx, chunk in enumerate(data["chunks"]):
            validate_chunk_object(
                chunk, idx, filepath, proposal_code, seen_chunk_keys, report
            )


def validate_directory(target_dir: Path) -> ValidationReport:
    """Scan and validate all *.json files in target_dir."""
    report = ValidationReport()
    seen_proposal_codes: Set[str] = set()
    seen_chunk_keys: Set[str] = set()

    if not target_dir.exists():
        report.add_error(target_dir, f"Directory does not exist: {target_dir}")
        return report

    json_files = sorted(target_dir.glob("*.json"))
    if not json_files:
        # Empty normalized directory is not an error before curation begins
        return report

    for f in json_files:
        validate_file(f, seen_proposal_codes, seen_chunk_keys, report)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate normalized Sympl proposal JSON dataset.")
    parser.add_argument(
        "--dir",
        type=str,
        default=None,
        help="Path to normalized dataset directory (defaults to data/normalized relative to project root)",
    )
    args = parser.parse_args()

    if args.dir:
        target_dir = Path(args.dir).resolve()
    else:
        # Resolve project root relative to this script
        project_root = Path(__file__).resolve().parent.parent
        target_dir = project_root / "data" / "normalized"

    print("============================================================")
    print("SYMPL PROPOSAL DATASET VALIDATION")
    print("============================================================")
    print(f"Target Directory: {target_dir}")

    report = validate_directory(target_dir)

    print(f"Files Checked:   {report.files_checked}")
    print(f"Chunks Checked:  {report.chunks_checked}")
    print(f"Hard Errors:     {len(report.errors)}")
    print(f"Warnings:        {len(report.warnings)}")
    print("------------------------------------------------------------")

    if report.warnings:
        print("\n[!] VALIDATION WARNINGS:")
        for w in report.warnings:
            print(f"  {w}")

    if report.errors:
        print("\n[x] HARD VALIDATION ERRORS:")
        for e in report.errors:
            print(f"  {e}")
        print("\nResult: VALIDATION FAILED")
        return 1

    if report.files_checked == 0:
        print("\nNo JSON files found in data/normalized/. (Ready for curated files)")
        print("Result: VALIDATION PASSED (0 files)")
        return 0

    print("\nResult: VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
