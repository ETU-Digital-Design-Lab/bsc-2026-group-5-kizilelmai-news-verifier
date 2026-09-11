"""Idempotent additive PostgreSQL migration; default is a read-only schema audit."""
import argparse
import os
import sys
from pathlib import Path
from evaluation_common import fresh_dir, manifest, finish_manifest, write_json

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".runtime" / "python"))

DDL = [
    "ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS source_url TEXT",
    "ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS publisher TEXT",
    "ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ",
    "ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS evidence_id TEXT",
    "ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS label_provenance TEXT NOT NULL DEFAULT 'unknown'",
    "ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS ingested_at TIMESTAMPTZ",
    "UPDATE knowledge_base SET label_provenance = 'unknown' WHERE label_provenance IS NULL OR btrim(label_provenance) = ''",
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true", help="Add fields in a single transaction. No deletion or invented history.")
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    out = fresh_dir(args.output_dir)
    record = manifest(__file__, config={"apply": args.apply, "url_source": "DATABASE_URL environment or local compose default"})
    # SQL is archived even when the service is unavailable; credentials are never archived.
    (out / "migration.sql").write_text("BEGIN;\n" + ";\n".join(DDL) + ";\nCOMMIT;\n", encoding="utf-8")
    try:
        import psycopg2
        url = os.environ.get("DATABASE_URL", "postgresql://kizilelmai_user:kizilelmai_pass@localhost:5433/kizilelmai")
        with psycopg2.connect(url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                if not args.apply:
                    cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("SET LOCAL statement_timeout = '30s'")
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'knowledge_base'")
                before = [r[0] for r in cur.fetchall()]
                if not before:
                    raise ValueError("knowledge_base table is absent.")
                if args.apply:
                    for statement in DDL:
                        cur.execute(statement)
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'knowledge_base'")
                after = [r[0] for r in cur.fetchall()]
                cur.execute("SELECT COUNT(*) FROM knowledge_base")
                total = cur.fetchone()[0]
                counts = {}
                for column in ("source_url", "publisher", "published_at", "evidence_id", "label_provenance", "ingested_at"):
                    if column in after:
                        cur.execute(f"SELECT COUNT(*) FROM knowledge_base WHERE {column} IS NOT NULL AND btrim({column}::text) <> ''")
                        counts[column] = cur.fetchone()[0]
                    else:
                        counts[column] = 0
                complete, unknown = None, total
                if all(c in after for c in ("source_url", "publisher", "published_at", "evidence_id", "label_provenance", "ingested_at")):
                    cur.execute("SELECT COUNT(*) FROM knowledge_base WHERE source_url IS NOT NULL AND source_url <> '' AND publisher IS NOT NULL AND publisher <> '' AND published_at IS NOT NULL AND evidence_id IS NOT NULL AND evidence_id <> '' AND label_provenance IS NOT NULL AND label_provenance NOT IN ('unknown', '') AND ingested_at IS NOT NULL")
                    complete = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM knowledge_base WHERE label_provenance IS NULL OR label_provenance IN ('unknown', '')")
                    unknown = cur.fetchone()[0]
                report = {"status": "MIGRATED" if args.apply else "INSPECTED", "columns_before": before, "columns_after": after,
                          "records": total, "nonempty": counts, "complete_chain": complete, "unknown_label_provenance": unknown,
                          "unknown_label_provenance_fraction": unknown / total if total else None,
                          "historical_ingested_at_policy": "Left NULL. Migration time is not historical ingestion time.",
                          "backfill_policy": "No URL or publisher inferred from text; authentic record-level backfill required."}
    except Exception as exc:
        report = {"status": "BLOCKED", "error_type": type(exc).__name__,
                  "reason": "Cannot inspect/migrate the target database; check service, dependency and connection configuration.",
                  "migration_committed": False}
    write_json(out / "provenance_report.json", report)
    record["status"] = report["status"]
    finish_manifest(out, record)
    print(f"Database schema/provenance report: {out}")
    return 2 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
