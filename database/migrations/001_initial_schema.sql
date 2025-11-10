-- Fugitive Data Pipeline - Evidence Store Schema
-- This database stores all processed documents with their extracted text

-- Create extension for full-text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Main documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    source_url TEXT NOT NULL,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    document_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256 hash for deduplication
    raw_text_content TEXT,
    document_type VARCHAR(10) NOT NULL CHECK (document_type IN ('pdf', 'html', 'forum')),
    nlp_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (nlp_status IN ('pending', 'processing', 'completed', 'failed')),
    nlp_processed_at TIMESTAMPTZ,
    file_size_bytes INTEGER,
    page_count INTEGER,
    is_scanned BOOLEAN DEFAULT FALSE,  -- True if OCR was required
    metadata JSONB,  -- Additional metadata (manufacturer, product line, etc.)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for efficient lookups
CREATE INDEX idx_documents_document_hash ON documents(document_hash);
CREATE INDEX idx_documents_nlp_status ON documents(nlp_status);
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_scraped_at ON documents(scraped_at DESC);

-- Full-text search index on content
CREATE INDEX idx_documents_text_content ON documents USING gin(to_tsvector('english', raw_text_content));

-- Trigram index for fuzzy part number search
CREATE INDEX idx_documents_text_trgm ON documents USING gin(raw_text_content gin_trgm_ops);

-- Extracted entities table (populated by NER)
CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    entity_text VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- PART_NUMBER, MANUFACTURER, SPECIFICATION, EQUIPMENT_MODEL
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    confidence_score FLOAT,  -- NER model confidence
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_entities_document_id ON entities(document_id);
CREATE INDEX idx_entities_entity_type ON entities(entity_type);
CREATE INDEX idx_entities_entity_text ON entities(entity_text);

-- Relationships table (populated by Relation Extraction)
CREATE TABLE relationships (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL,  -- REPLACES, EQUIVALENT_TO, COMPATIBLE_WITH, ADAPTER_REQUIRED, HAS_SPEC
    confidence_score FLOAT,  -- RE model confidence
    context_text TEXT,  -- The sentence/paragraph where the relation was found
    is_tribal_knowledge BOOLEAN DEFAULT FALSE,  -- True if from forum
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_relationships_document_id ON relationships(document_id);
CREATE INDEX idx_relationships_source_entity ON relationships(source_entity_id);
CREATE INDEX idx_relationships_target_entity ON relationships(target_entity_id);
CREATE INDEX idx_relationships_relation_type ON relationships(relation_type);
CREATE INDEX idx_relationships_tribal ON relationships(is_tribal_knowledge);

-- Processing errors table for debugging
CREATE TABLE processing_errors (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    error_stage VARCHAR(50) NOT NULL,  -- scraping, pdf_extraction, ocr, ner, relation_extraction
    error_message TEXT NOT NULL,
    error_traceback TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_processing_errors_document_id ON processing_errors(document_id);
CREATE INDEX idx_processing_errors_stage ON processing_errors(error_stage);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- View for documents ready for NLP processing
CREATE VIEW documents_pending_nlp AS
SELECT
    id,
    source_url,
    document_type,
    raw_text_content,
    scraped_at
FROM documents
WHERE nlp_status = 'pending'
  AND raw_text_content IS NOT NULL
  AND LENGTH(raw_text_content) > 100  -- Skip documents with minimal content
ORDER BY scraped_at ASC;

-- View for tribal knowledge relationships
CREATE VIEW tribal_knowledge_graph AS
SELECT
    r.id,
    r.relation_type,
    se.entity_text AS source_part,
    se.entity_type AS source_type,
    te.entity_text AS target_part,
    te.entity_type AS target_type,
    r.context_text,
    d.source_url AS forum_url,
    r.confidence_score
FROM relationships r
JOIN entities se ON r.source_entity_id = se.id
JOIN entities te ON r.target_entity_id = te.id
JOIN documents d ON r.document_id = d.id
WHERE r.is_tribal_knowledge = TRUE
ORDER BY r.confidence_score DESC;

-- Grant permissions (adjust as needed for production)
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO fugitive_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO fugitive_app;
