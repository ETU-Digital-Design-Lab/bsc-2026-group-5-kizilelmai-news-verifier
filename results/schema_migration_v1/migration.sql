BEGIN;
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS publisher TEXT;
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS evidence_id TEXT;
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS label_provenance TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS ingested_at TIMESTAMPTZ;
UPDATE knowledge_base SET label_provenance = 'unknown' WHERE label_provenance IS NULL OR btrim(label_provenance) = '';
COMMIT;
