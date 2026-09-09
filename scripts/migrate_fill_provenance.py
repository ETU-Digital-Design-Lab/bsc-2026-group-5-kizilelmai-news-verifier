"""Populate evidence provenance fields and diversify authority in knowledge_base table.

Fulfills Task B7 and B8 requirements from audit report.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".runtime" / "python"))

from scripts.evaluation_common import fresh_dir, manifest, finish_manifest, write_json, sha256


def clean_text(text_str: str) -> str:
    if not isinstance(text_str, str):
        return ""
    text_str = re.sub(r"https?://\S+|www\.\S+", "", text_str)
    text_str = re.sub(r"\S+@\S+", "", text_str)
    text_str = re.sub(r"@\S+", "", text_str)
    text_str = re.sub(r"\s+", " ", text_str)
    return text_str.strip()


def parse_date(date_str: str):
    if not date_str or not isinstance(date_str, str) or date_str.lower() in ("nan", "none", ""):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%a %b %d %H:%M:%S +0000 %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def build_raw_provenance_index(raw_dir: Path) -> dict[str, dict]:
    import pandas as pd
    index = {}

    # 1. Isakulaksiz (Teyit.org / Dogruluk Payi)
    isa_path = raw_dir / "isakulaksiz_dataset.csv"
    if isa_path.exists():
        df_isa = pd.read_csv(isa_path)
        for idx, row in df_isa.iterrows():
            desc = row.get("description") if pd.notna(row.get("description")) else row.get("title", "")
            key = clean_text(str(desc))
            if key and key not in index:
                res = str(row.get("Resource", "") or "").strip()
                pub = "Teyit.org" if "teyit.org" in res.lower() else ("Dogruluk Payi" if "dogrulukpayi" in res.lower() else "Teyit / Dogruluk Payi Arşivi")
                auth = 0.98 if "teyit.org" in res.lower() else (0.97 if "dogrulukpayi" in res.lower() else 0.95)
                index[key] = {
                    "source_url": res if res.startswith("http") else (f"https://{res}" if res else "https://teyit.org"),
                    "publisher": pub,
                    "published_at": None,
                    "evidence_id": f"isa_{idx}",
                    "label_provenance": "fact_check_archive",
                    "authority": auth,
                }

    # 2. Diken (Gazete / Web haber)
    diken_path = raw_dir / "diken_non-clickbait.csv"
    if diken_path.exists():
        df_diken = pd.read_csv(diken_path)
        for idx, row in df_diken.iterrows():
            key = clean_text(str(row.get("full_text", "")))
            if key and key not in index:
                index[key] = {
                    "source_url": "https://www.diken.com.tr",
                    "publisher": "Diken",
                    "published_at": parse_date(str(row.get("created_at", ""))),
                    "evidence_id": f"diken_{idx}",
                    "label_provenance": "verified_news_archive",
                    "authority": 0.82,
                }

    # 3. Evrensel (Gazete)
    evrensel_path = raw_dir / "evrensel_non-clickbait.csv"
    if evrensel_path.exists():
        df_evrensel = pd.read_csv(evrensel_path)
        for idx, row in df_evrensel.iterrows():
            key = clean_text(str(row.get("full_text", "")))
            if key and key not in index:
                t_id = str(row.get("tweet_id", ""))
                url = f"https://twitter.com/evrenselgzt/status/{t_id}" if t_id and t_id != "nan" else "https://www.evrensel.net"
                index[key] = {
                    "source_url": url,
                    "publisher": "Evrensel",
                    "published_at": parse_date(str(row.get("created_at", ""))),
                    "evidence_id": f"evrensel_{t_id or idx}",
                    "label_provenance": "verified_news_archive",
                    "authority": 0.80,
                }

    # 4. Limon (Clickbait / Sansasyonel)
    limon_path = raw_dir / "limon_clickbait.csv"
    if limon_path.exists():
        df_limon = pd.read_csv(limon_path)
        for idx, row in df_limon.iterrows():
            key = clean_text(str(row.get("full_text", "")))
            if key and key not in index:
                t_id = str(row.get("tweet_id", ""))
                index[key] = {
                    "source_url": f"https://twitter.com/limon/status/{t_id}" if t_id and t_id != "nan" else "https://twitter.com",
                    "publisher": "Limon Haber (Clickbait)",
                    "published_at": parse_date(str(row.get("created_at", ""))),
                    "evidence_id": f"limon_{t_id or idx}",
                    "label_provenance": "clickbait_archive",
                    "authority": 0.60,
                }

    # 5. Ogozcelik (MIDE22 Twitter Dataset)
    ogo_path = raw_dir / "ogozcelik_dataset.tsv"
    if ogo_path.exists():
        try:
            df_ogo = pd.read_csv(ogo_path, sep="\t")
            for idx, row in df_ogo.iterrows():
                key = clean_text(str(row.get("tweet", "")))
                if key and key not in index:
                    index[key] = {
                        "source_url": "https://huggingface.co/datasets/ogozcelik/turkish-fake-news-detection",
                        "publisher": "MIDE22 Research Dataset",
                        "published_at": None,
                        "evidence_id": f"ogo_{idx}",
                        "label_provenance": "research_annotated_corpus",
                        "authority": 0.85,
                    }
        except Exception:
            pass

    return index


def main():
    parser = argparse.ArgumentParser(description="Fill provenance data and diversify authority in DB.")
    parser.add_argument("--apply", action="store_true", help="Apply updates to database.")
    parser.add_argument("--output-dir", type=Path, default=Path("results/provenance_v1"), help="Report output directory.")
    args = parser.parse_args()

    out_dir = fresh_dir(args.output_dir)
    run_rec = manifest(__file__, config={"apply": args.apply})

    import psycopg2
    from psycopg2.extras import execute_batch

    db_url = os.environ.get("DATABASE_URL", "postgresql://kizilelmai_user:kizilelmai_pass@localhost:5433/kizilelmai")
    raw_dir = ROOT / "data" / "raw"

    print("Building raw provenance mapping index...")
    mapping = build_raw_provenance_index(raw_dir)
    print(f"Index built: {len(mapping)} raw entries available.")

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("SELECT id, text, authority FROM knowledge_base ORDER BY id ASC")
        db_rows = cur.fetchall()
        using_db = True
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}. Falling back to CSV.")
        using_db = False
        import pandas as pd
        corpus_csv_path = ROOT / "data" / "corpus_snapshots" / "local_csv_20260909_v1" / "corpus.csv"
        df_corpus = pd.read_csv(corpus_csv_path)
        db_rows = []
        for idx, row in df_corpus.iterrows():
            db_rows.append((row['id'], row['text'], row.get('authority', 0.85)))

    total_records = len(db_rows)
    print(f"Total records loaded: {total_records}")

    matched_count = 0
    unmatched_count = 0
    updates = []
    now_iso = datetime.now(timezone.utc)

    for row_id, raw_text, old_auth in db_rows:
        key = clean_text(raw_text)
        meta = mapping.get(key)
        if meta is not None:
            matched_count += 1
            updates.append((
                meta["source_url"],
                meta["publisher"],
                meta["published_at"],
                meta["evidence_id"],
                meta["label_provenance"],
                now_iso,
                meta["authority"],
                row_id
            ))
        else:
            unmatched_count += 1
            updates.append((
                None,
                None,
                None,
                f"unlinked_{row_id}",
                "unknown",
                now_iso,
                float(old_auth) if old_auth is not None and pd.notna(old_auth) else 0.85,
                row_id
            ))

    print(f"Matching results: {matched_count} / {total_records} matched ({matched_count / total_records * 100:.2f}%)")
    print(f"Unmatched (marked unknown): {unmatched_count} ({unmatched_count / total_records * 100:.2f}%)")

    if args.apply:
        if using_db:
            print("Applying updates to PostgreSQL database in batches...")
            update_sql = """
            UPDATE knowledge_base
            SET source_url = %s,
                publisher = %s,
                published_at = %s,
                evidence_id = %s,
                label_provenance = %s,
                ingested_at = %s,
                authority = %s
            WHERE id = %s
            """
            batch_size = 2000
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                execute_batch(cur, update_sql, batch)
                conn.commit()
                print(f"  Committed batch {i}..{min(i + batch_size, len(updates))}")

        print("Updating corpus CSV snapshot to match database provenance and authorities...")
        corpus_csv_path = ROOT / "data" / "corpus_snapshots" / "local_csv_20260909_v1" / "corpus.csv"
        if corpus_csv_path.exists():
            import pandas as pd
            df_corpus = pd.read_csv(corpus_csv_path)
            update_dict = {u[7]: u for u in updates}  # row_id -> tuple
            if "id" in df_corpus.columns:
                df_corpus["authority"] = df_corpus["id"].map(lambda rid: update_dict.get(rid, (None, None, None, None, None, None, 0.85, None))[6])
                df_corpus["publisher"] = df_corpus["id"].map(lambda rid: update_dict.get(rid, (None, "", None, None, None, None, None, None))[1] or "")
                df_corpus["source_url"] = df_corpus["id"].map(lambda rid: update_dict.get(rid, ("", None, None, None, None, None, None, None))[0] or "")
                df_corpus["label_provenance"] = df_corpus["id"].map(lambda rid: update_dict.get(rid, (None, None, None, None, "unknown", None, None, None))[4])
                df_corpus.to_csv(corpus_csv_path, index=False, encoding="utf-8")
                print("Corpus snapshot CSV updated successfully.")

    if using_db:
        # Compute final DB distribution
        cur.execute("SELECT authority, COUNT(*) FROM knowledge_base GROUP BY authority ORDER BY authority DESC")
        auth_dist = {str(k): int(v) for k, v in cur.fetchall()}

        cur.execute("SELECT label_provenance, COUNT(*) FROM knowledge_base GROUP BY label_provenance ORDER BY COUNT(*) DESC")
        prov_dist = {str(k): int(v) for k, v in cur.fetchall()}

        cur.execute("SELECT publisher, COUNT(*) FROM knowledge_base WHERE publisher IS NOT NULL GROUP BY publisher ORDER BY COUNT(*) DESC LIMIT 10")
        pub_dist = {str(k): int(v) for k, v in cur.fetchall()}
        conn.close()
    else:
        auth_dist = df_corpus['authority'].value_counts().to_dict()
        auth_dist = {str(k): int(v) for k, v in auth_dist.items()}
        prov_dist = df_corpus['label_provenance'].value_counts().to_dict()
        prov_dist = {str(k): int(v) for k, v in prov_dist.items()}
        pub_dist = df_corpus['publisher'].value_counts().head(10).to_dict()
        pub_dist = {str(k): int(v) for k, v in pub_dist.items() if str(k) != 'nan'}


    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_records": total_records,
        "provenance_matched": matched_count,
        "provenance_matched_pct": round(matched_count / total_records * 100, 2),
        "unknown_provenance": unmatched_count,
        "unknown_provenance_pct": round(unmatched_count / total_records * 100, 2),
        "authority_distribution": auth_dist,
        "label_provenance_distribution": prov_dist,
        "top_publishers": pub_dist,
    }

    write_json(out_dir / "provenance_report.json", report)
    finish_manifest(out_dir, run_rec)
    print(f"Report saved to {out_dir / 'provenance_report.json'}")


if __name__ == "__main__":
    main()
