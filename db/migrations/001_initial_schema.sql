-- =============================================================================
-- Migration: 001_initial_schema.sql
-- Description: Initial database schema for Sympl Proposal RAG System
-- Target: PostgreSQL 18 with pgvector 0.8.6
-- =============================================================================

BEGIN;

-- 1. EXTENSIONS
-- Enable pgvector extension if not already present
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. REUSABLE TRIGGER FUNCTION FOR updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. TABLE: proposal_documents
-- Represents a single historical Sympl proposal document
CREATE TABLE IF NOT EXISTS proposal_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_code TEXT NOT NULL UNIQUE,
    client_name TEXT NOT NULL,
    proposal_title TEXT,
    proposal_date DATE,
    source_filename TEXT NOT NULL,
    organization_type TEXT,
    sector TEXT,
    engagement_type TEXT,
    proposal_complexity TEXT,
    core_bookkeeping BOOLEAN NOT NULL DEFAULT TRUE,
    raw_text TEXT,
    cleaned_text TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. TABLE: proposal_chunks
-- Represents a semantic section or service block within a proposal.
-- This is the primary table queried by the semantic RAG retriever.
CREATE TABLE IF NOT EXISTS proposal_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES proposal_documents(id) ON DELETE CASCADE,
    chunk_key TEXT NOT NULL UNIQUE,
    section_order INTEGER,
    section_type TEXT NOT NULL,
    section_title TEXT,
    service_modules TEXT[] NOT NULL DEFAULT '{}'::text[],
    organization_type TEXT,
    sector TEXT,
    engagement_type TEXT,
    core_bookkeeping BOOLEAN NOT NULL DEFAULT FALSE,
    accounting_systems TEXT[] NOT NULL DEFAULT '{}'::text[],
    payroll_systems TEXT[] NOT NULL DEFAULT '{}'::text[],
    cadence TEXT[] NOT NULL DEFAULT '{}'::text[],
    special_requirements TEXT[] NOT NULL DEFAULT '{}'::text[],
    raw_text TEXT NOT NULL,
    cleaned_text TEXT NOT NULL,
    retrieval_text TEXT NOT NULL,
    retrieval_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    commercial_reference_only BOOLEAN NOT NULL DEFAULT FALSE,
    pricing_content BOOLEAN NOT NULL DEFAULT FALSE,
    boilerplate_content BOOLEAN NOT NULL DEFAULT FALSE,
    -- Unconstrained vector dimension until the embedding model is finalized
    embedding VECTOR,
    embedded_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Pricing Safety Constraint:
    -- When pricing_content is true, the chunk must be commercial_reference_only
    -- AND must NOT be retrieval_enabled.
    CONSTRAINT chk_pricing_safety CHECK (
        NOT pricing_content
        OR (
            commercial_reference_only
            AND NOT retrieval_enabled
        )
    ),

    -- Boilerplate Retrieval Safety Constraint:
    -- When boilerplate_content is true, retrieval_enabled must be false.
    CONSTRAINT chk_boilerplate_retrieval CHECK (
        NOT boilerplate_content
        OR NOT retrieval_enabled
    ),

    -- Section Order Sanity Constraint:
    -- section_order must be NULL or non-negative (>= 0).
    CONSTRAINT chk_proposal_chunks_section_order CHECK (
        section_order IS NULL
        OR section_order >= 0
    )
);

-- 5. TABLE: sympl_reference_blocks
-- Stores approved, canonical Sympl boilerplate, disclaimers, and standard exclusions
-- intended for deterministic insertion rather than semantic discovery.
CREATE TABLE IF NOT EXISTS sympl_reference_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    block_key TEXT NOT NULL UNIQUE,
    block_type TEXT NOT NULL,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Version Sanity Constraint:
    -- Version must be >= 1.
    CONSTRAINT chk_sympl_reference_blocks_version CHECK (version >= 1)
);

-- 6. TABLE: sympl_style_rules
-- Stores persistent Sympl writing, syntax, tone, and scope rules to be injected into prompts.
CREATE TABLE IF NOT EXISTS sympl_style_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_key TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    rule_text TEXT NOT NULL,
    priority TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. TABLE: dataset_imports
-- Tracks ingestion runs, source content hashes, and record counts for auditability.
CREATE TABLE IF NOT EXISTS dataset_imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name TEXT NOT NULL,
    source_hash TEXT,
    records_imported INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    -- Records Imported Sanity Constraint:
    -- records_imported must be >= 0.
    CONSTRAINT chk_dataset_imports_records_imported CHECK (records_imported >= 0)
);

-- 8. TRIGGERS: AUTOMATIC updated_at MAINTENANCE
DROP TRIGGER IF EXISTS trg_proposal_documents_updated_at ON proposal_documents;
CREATE TRIGGER trg_proposal_documents_updated_at
BEFORE UPDATE ON proposal_documents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_proposal_chunks_updated_at ON proposal_chunks;
CREATE TRIGGER trg_proposal_chunks_updated_at
BEFORE UPDATE ON proposal_chunks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_sympl_reference_blocks_updated_at ON sympl_reference_blocks;
CREATE TRIGGER trg_sympl_reference_blocks_updated_at
BEFORE UPDATE ON sympl_reference_blocks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_sympl_style_rules_updated_at ON sympl_style_rules;
CREATE TRIGGER trg_sympl_style_rules_updated_at
BEFORE UPDATE ON sympl_style_rules
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 9. INDEXES
-- Standard B-tree indexes for relational joins and metadata filtering on proposal_chunks
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_proposal_id ON proposal_chunks(proposal_id);
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_section_type ON proposal_chunks(section_type);
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_organization_type ON proposal_chunks(organization_type);
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_sector ON proposal_chunks(sector);
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_engagement_type ON proposal_chunks(engagement_type);
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_retrieval_enabled ON proposal_chunks(retrieval_enabled);
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_pricing_content ON proposal_chunks(pricing_content);
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_core_bookkeeping ON proposal_chunks(core_bookkeeping);

-- GIN indexes for array containment queries on proposal_chunks
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_service_modules ON proposal_chunks USING GIN (service_modules);
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_accounting_systems ON proposal_chunks USING GIN (accounting_systems);
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_payroll_systems ON proposal_chunks USING GIN (payroll_systems);
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_cadence ON proposal_chunks USING GIN (cadence);
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_special_requirements ON proposal_chunks USING GIN (special_requirements);
CREATE INDEX IF NOT EXISTS idx_proposal_chunks_metadata ON proposal_chunks USING GIN (metadata);

-- GIN index for JSONB metadata on proposal_documents
CREATE INDEX IF NOT EXISTS idx_proposal_documents_metadata ON proposal_documents USING GIN (metadata);

-- Indexes for ingestion tracking
CREATE INDEX IF NOT EXISTS idx_dataset_imports_source_hash ON dataset_imports(source_hash);
CREATE INDEX IF NOT EXISTS idx_dataset_imports_status ON dataset_imports(status);

-- Partial unique index: prevents duplicate completed imports for identical source file contents
CREATE UNIQUE INDEX IF NOT EXISTS idx_dataset_imports_completed_unique
ON dataset_imports(source_name, source_hash)
WHERE status = 'completed'
AND source_hash IS NOT NULL;

COMMIT;
