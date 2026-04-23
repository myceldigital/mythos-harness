CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS mythos;

DO $$
DECLARE
    embedding_type TEXT;
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'mythos'
          AND table_name = 'session_snapshots'
    ) THEN
        CREATE TABLE mythos.session_snapshots (
            thread_id TEXT PRIMARY KEY,
            snapshot_json JSONB NOT NULL,
            embedding VECTOR(1536),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        RETURN;
    END IF;

    SELECT format_type(a.atttypid, a.atttypmod)
    INTO embedding_type
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'mythos'
      AND c.relname = 'session_snapshots'
      AND a.attname = 'embedding'
      AND NOT a.attisdropped;

    IF embedding_type IS NULL THEN
        ALTER TABLE mythos.session_snapshots
            ADD COLUMN embedding VECTOR(1536);
        RETURN;
    END IF;

    IF embedding_type = 'vector(1536)' THEN
        RETURN;
    END IF;

    IF embedding_type = 'vector(16)' THEN
        ALTER TABLE mythos.session_snapshots
            RENAME COLUMN embedding TO embedding_legacy_16;
        ALTER TABLE mythos.session_snapshots
            ADD COLUMN embedding VECTOR(1536);
        COMMENT ON COLUMN mythos.session_snapshots.embedding_legacy_16
            IS 'Legacy vector(16). Safe to drop after re-embedding/backfill.';
        RETURN;
    END IF;

    RAISE WARNING 'Unexpected embedding column type: %, manual migration required.', embedding_type;
END $$;
