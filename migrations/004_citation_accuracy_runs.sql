-- Citation Accuracy Eval Runs table
-- Stores historical results of citation accuracy batch evaluations

CREATE TABLE IF NOT EXISTS citation_accuracy_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    total_examples INTEGER NOT NULL DEFAULT 0,
    total_citations INTEGER NOT NULL DEFAULT 0,
    valid_citations INTEGER NOT NULL DEFAULT 0,
    misused_citations INTEGER NOT NULL DEFAULT 0,
    hallucinated_citations INTEGER NOT NULL DEFAULT 0,
    overall_accuracy FLOAT NOT NULL DEFAULT 0,
    results JSONB NOT NULL DEFAULT '[]'::jsonb,
    config JSONB DEFAULT '{}'::jsonb
);

-- Index for querying recent runs
CREATE INDEX IF NOT EXISTS idx_citation_runs_started_at ON citation_accuracy_runs(started_at DESC);
