-- Supabase Database Schema (Structured Data + pgvector)
-- Enable the pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Structured Clients Table
CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tier TEXT NOT NULL,
    monthly_spend NUMERIC NOT NULL,
    status TEXT NOT NULL,
    account_manager TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Structured Tasks Table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    client_id TEXT REFERENCES clients(id),
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    assigned_to TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Operations Knowledge Base Chunks (pgvector)
CREATE TABLE IF NOT EXISTS ops_handbook_chunks (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR(1536)
);

-- 4. Vector Similarity Search Function (Cosine Distance)
CREATE OR REPLACE FUNCTION match_handbook_documents (
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 2
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ops_handbook_chunks.id,
        ops_handbook_chunks.content,
        ops_handbook_chunks.metadata,
        1 - (ops_handbook_chunks.embedding <=> query_embedding) AS similarity
    FROM ops_handbook_chunks
    ORDER BY ops_handbook_chunks.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Sample Seed Data
INSERT INTO clients (id, name, tier, monthly_spend, status, account_manager, contact_email) VALUES
('CL-101', 'Acme Corp', 'Enterprise', 12500, 'Active', 'Sarah Jenkins', 'ops@acmecorp.com'),
('CL-102', 'TechStart Inc', 'Growth', 2800, 'Active', 'David Ross', 'admin@techstart.io'),
('CL-103', 'BlueWave Logistics', 'Enterprise', 24000, 'Pending Renewal', 'Sarah Jenkins', 'it@bluewave.com')
ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (id, client_id, title, status, priority, assigned_to) VALUES
('TK-501', 'CL-101', 'Migrate database replica', 'In Progress', 'High', 'Alex'),
('TK-502', 'CL-102', 'Setup SSO integration', 'Blocked', 'Critical', 'Maya'),
('TK-503', 'CL-103', 'Quarterly security review', 'Completed', 'Medium', 'Alex')
ON CONFLICT (id) DO NOTHING;
