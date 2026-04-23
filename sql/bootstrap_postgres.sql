CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS mythos;

CREATE TABLE IF NOT EXISTS mythos.session_snapshots (
    thread_id TEXT PRIMARY KEY,
    snapshot_json JSONB NOT NULL,
    embedding VECTOR(1536),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mythos.trajectory_logs (
    id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_session_snapshots_updated_at
    ON mythos.session_snapshots (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_trajectory_logs_created_at
    ON mythos.trajectory_logs (created_at DESC);
