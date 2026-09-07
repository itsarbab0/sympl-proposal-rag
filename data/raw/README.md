# Raw Proposal Archive (`data/raw/`)

This directory is the dedicated repository for immutable source files representing historical Sympl Solutions proposals (e.g., original PDFs, source docx files, client exports, or initial raw text extractions).

## Core Principles

1. **Source Immutability**:
   - Files stored here are strictly historical source records.
   - They must **never** be silently modified, overwritten, or auto-formatted in place.
   - If a source file contains typographical errors, formatting artifacts, or historical irregularities, those must remain intact in the raw record.

2. **Separation of Raw and Normalized Data**:
   - Raw source documents serve as the permanent baseline and verification benchmark.
   - Structured, cleaned, and section-chunked data is maintained independently in `data/normalized/` as curated JSON documents.
   - Any cleaning, standardizing, or enrichment occurs exclusively during the creation of normalized dataset artifacts, preserving the raw artifacts for complete lineage and auditing.
