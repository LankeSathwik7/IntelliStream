-- =============================================
-- INTELLISTREAM DATABASE SCHEMA
-- Run this in Supabase SQL Editor
-- =============================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verify extensions
SELECT * FROM pg_extension WHERE extname IN ('vector', 'pg_trgm');

-- =============================================
-- TABLES
-- =============================================

-- Users Profile (extends Supabase Auth)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID REFERENCES auth.users PRIMARY KEY,
    display_name TEXT,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents for RAG
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_url TEXT,
    source_type TEXT CHECK (source_type IN ('news', 'research', 'social', 'custom')),
    embedding VECTOR(1024),  -- Voyage AI voyage-3 dimensions
    metadata JSONB DEFAULT '{}',
    chunk_index INTEGER DEFAULT 0,
    parent_doc_id UUID,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversation Threads
CREATE TABLE IF NOT EXISTS threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    agent_trace JSONB DEFAULT '[]',
    tokens_used INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent Execution Logs (for observability)
CREATE TABLE IF NOT EXISTS agent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    action TEXT NOT NULL,
    input_state JSONB,
    output_state JSONB,
    tokens_used INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- INDEXES
-- =============================================

-- Vector similarity search index (IVFFlat for large datasets)
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Full-text search index
CREATE INDEX IF NOT EXISTS documents_content_search_idx ON documents
USING gin (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')));

-- Foreign key indexes
CREATE INDEX IF NOT EXISTS threads_user_id_idx ON threads(user_id);
CREATE INDEX IF NOT EXISTS messages_thread_id_idx ON messages(thread_id);
CREATE INDEX IF NOT EXISTS agent_logs_thread_id_idx ON agent_logs(thread_id);
CREATE INDEX IF NOT EXISTS documents_source_type_idx ON documents(source_type);

-- =============================================
-- ROW LEVEL SECURITY
-- =============================================

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" ON profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Threads policies
CREATE POLICY "Users can manage own threads" ON threads
    FOR ALL USING (auth.uid() = user_id);

-- Messages policies
CREATE POLICY "Users can view messages in own threads" ON messages
    FOR ALL USING (
        thread_id IN (SELECT id FROM threads WHERE user_id = auth.uid())
    );

-- =============================================
-- FUNCTIONS
-- =============================================

-- Function for vector similarity search
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1024),
    match_count INT DEFAULT 10,
    filter_source_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    content TEXT,
    source_url TEXT,
    source_type TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.title,
        d.content,
        d.source_url,
        d.source_type,
        d.metadata,
        1 - (d.embedding <=> query_embedding) AS similarity
    FROM documents d
    WHERE (filter_source_type IS NULL OR d.source_type = filter_source_type)
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function for hybrid search (vector + keyword)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(1024),
    match_count INT DEFAULT 10,
    vector_weight FLOAT DEFAULT 0.6,
    keyword_weight FLOAT DEFAULT 0.4
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    content TEXT,
    source_url TEXT,
    combined_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        SELECT
            d.id,
            d.title,
            d.content,
            d.source_url,
            1 - (d.embedding <=> query_embedding) AS vector_score
        FROM documents d
        ORDER BY d.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    keyword_results AS (
        SELECT
            d.id,
            ts_rank(
                to_tsvector('english', coalesce(d.title, '') || ' ' || coalesce(d.content, '')),
                plainto_tsquery('english', query_text)
            ) AS keyword_score
        FROM documents d
        WHERE to_tsvector('english', coalesce(d.title, '') || ' ' || coalesce(d.content, ''))
              @@ plainto_tsquery('english', query_text)
        LIMIT match_count * 2
    )
    SELECT
        v.id,
        v.title,
        v.content,
        v.source_url,
        (COALESCE(v.vector_score, 0) * vector_weight +
         COALESCE(k.keyword_score, 0) * keyword_weight) AS combined_score
    FROM vector_results v
    LEFT JOIN keyword_results k ON v.id = k.id
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

-- =============================================
-- TRIGGERS
-- =============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER threads_updated_at
    BEFORE UPDATE ON threads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================
-- SAMPLE DATA (Optional - for testing)
-- =============================================

-- Uncomment to insert sample documents
/*
INSERT INTO documents (title, content, source_type, metadata) VALUES
    ('NVIDIA Q4 2024 Earnings', 'NVIDIA reported record revenue of $22.1 billion for Q4 2024, driven by strong demand for AI chips and data center GPUs. The company''s data center segment grew 409% year-over-year.', 'news', '{"company": "NVIDIA", "ticker": "NVDA"}'),
    ('OpenAI GPT-5 Announcement', 'OpenAI announced GPT-5, featuring enhanced reasoning capabilities and multimodal understanding. The model shows significant improvements in complex problem-solving tasks.', 'research', '{"company": "OpenAI", "model": "GPT-5"}'),
    ('Cloud Computing Market 2024', 'The global cloud computing market is projected to reach $1 trillion by 2028, with major growth driven by AI workloads and enterprise digital transformation initiatives.', 'research', '{"sector": "Cloud Computing"}');
*/
