# Normalized Dataset Repository (`data/normalized/`)

This directory contains the canonical, structured JSON representations of approved historical Sympl Solutions proposals.

## Architecture & Workflow

1. **One Proposal per File**:
   - Every historical proposal is represented by exactly one normalized JSON file (e.g., `TACT_2026.json`).
   - Each file encapsulates the proposal-level document metadata and an ordered array of semantic proposal chunks.

2. **Curated Ingestion Artifacts**:
   - These files form the verified dataset consumed by `scripts/import_dataset.py`.
   - They must **never** be blindly machine-generated or ingested without human review.
   - For the initial seven Sympl historical proposals, human/AI-assisted curation is used to verify:
     - **Semantic section boundaries**: Logical partitioning into discrete proposal components (e.g., context, scope, onboarding).
     - **Service module taxonomy**: Accurate tagging with known modules (e.g., `payroll`, `reconciliations`, `audit`).
     - **Systems**: Accounting tools (`QuickBooks Online`, `Xero`) and payroll providers (`Payworks`, `ADP`).
     - **Cadence**: Operational cycles (e.g., `monthly`, `semi-monthly`, `annual`).
     - **Special requirements**: Compliance or funder-mandated needs.
     - **Pricing safety flags**: Explicitly marking `pricing_content: true` and `commercial_reference_only: true`.
     - **Boilerplate flags**: Distinguishing standard company language from client-adapted language.
     - **Retrieval eligibility**: Ensuring non-retrievable blocks are tagged `retrieval_enabled: false`.
     - **Cleaned text**: Canonical text correcting OCR/spelling anomalies while preserving Sympl voice.
     - **Retrieval text**: Formatted representation optimized for future embedding generation.

3. **Validation**:
   - Before running the importer, all JSON files in this directory must pass validation via:
     ```bash
     python scripts/validate_dataset.py
     ```
