"""Audit claim/evidence separation. Missing URL history or embeddings FAIL, never PASS."""
from __future__ import annotations
import argparse
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from evaluation_common import fresh_dir, manifest, finish_manifest, read_csv, write_json, write_csv, sha256

FIELDS = {"claim_id", "claim_text", "gold_verdict", "evidence_text", "evidence_url", "evidence_publisher",
          "evidence_published_at", "annotator_pseudo_ids", "guideline_version", "frozen_at"}


def normalized(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).replace("İ", "i").replace("I", "ı").lower()).strip()


def url_key(value):
    parts = urlsplit(value.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))


def audit(claims, corpus, training, *, claim_only=False):
    errors, overlaps = [], []
    if not claims or not corpus:
        return {"status": "FAIL", "errors": ["Empty claims or corpus."], "overlaps": []}
    if len({r.get("claim_id") for r in claims}) != len(claims) or any(not r.get("claim_id") for r in claims):
        errors.append("Claim IDs must be nonempty and unique.")
    if any(not r.get("claim_text", "").strip() for r in claims):
        errors.append("Empty claim text.")
    if len({normalized(r.get("claim_text", "")) for r in claims}) != len(claims):
        errors.append("Duplicate normalized claim texts.")
    if not claim_only:
        if len(claims) != 500:
            errors.append("Frozen gold protocol requires 500 claims.")
        incomplete = [r.get("claim_id") for r in claims if any(not r.get(k, "").strip() for k in FIELDS)]
        if incomplete:
            errors.append(f"Incomplete claim/evidence records: {len(incomplete)}")
        if any(r.get("gold_verdict") not in {"DOĞRU", "YALAN"} for r in claims):
            errors.append("Gold verdict must be DOĞRU or YALAN.")
    indexed_texts = {}
    for r in corpus:
        indexed_texts.setdefault(normalized(r["text"]), []).append(r["id"])
    training_texts = {normalized(r["text"]) for r in training}
    urls = {url_key(r.get("source_url", "")) for r in corpus if r.get("source_url")}
    for r in claims:
        cid, key = r.get("claim_id"), normalized(r.get("claim_text", ""))
        if key in indexed_texts:
            overlaps.append({"claim_id": cid, "type": "corpus_exact_normalized_text", "record_ids": indexed_texts[key]})
        if key in training_texts:
            overlaps.append({"claim_id": cid, "type": "training_exact_normalized_text", "record_ids": []})
        if r.get("evidence_url") and url_key(r["evidence_url"]) in urls:
            overlaps.append({"claim_id": cid, "type": "corpus_evidence_url", "record_ids": []})
    if overlaps:
        errors.append(f"Claim/evidence overlaps: {len(overlaps)}")
    missing_urls = sum(not r.get("source_url", "").strip() for r in corpus)
    if missing_urls:
        errors.append(f"Corpus records without source_url: {missing_urls}; URL disjointness cannot be certified.")
    if not training:
        errors.append("Historical training input not supplied; training disjointness unknown.")
    return {"status": "FAIL" if errors else "PENDING_SEMANTIC_CHECK", "errors": errors,
            "overlaps": overlaps, "corpus_records_without_url": missing_urls,
            "training_scope": "Only the supplied training export; historical checkpoint lineage requires separate verification."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--claims", type=Path, required=True)
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--training", type=Path)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--embedding-model", type=Path, help="Local immutable SentenceTransformer directory; all model files are hashed.")
    args = p.parse_args()
    out = fresh_dir(args.output_dir)
    claims, corpus = read_csv(args.claims), read_csv(args.corpus)
    report = audit(claims, corpus, read_csv(args.training) if args.training else [])
    inputs = [args.claims, args.corpus] + ([args.training] if args.training else [])
    record = manifest(__file__, inputs, {"near_duplicate_threshold": .95, "normalization": "NFKC, Turkish lowercase, whitespace",
                                       "embedding_prefixes": {"claims": "query: ", "corpus": "passage: "}})
    if args.embedding_model:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(str(args.embedding_model), local_files_only=True)
        npy_path = args.corpus.parent / "corpus_embeddings.npy"
        if npy_path.exists():
            doc_vecs = np.load(str(npy_path)).astype(np.float32)
            norms = np.linalg.norm(doc_vecs, axis=1, keepdims=True)
            norms[norms == 0] = 1e-9
            doc_vecs = doc_vecs / norms
        else:
            doc_vecs = model.encode(["passage: " + r["text"] for r in corpus], normalize_embeddings=True, convert_to_numpy=True)
        neighbors = []
        for start in range(0, len(claims), 32):
            batch = claims[start:start + 32]
            vecs = model.encode(["query: " + r["claim_text"] for r in batch], normalize_embeddings=True, convert_to_numpy=True)
            sims = vecs @ doc_vecs.T
            if not np.isfinite(sims).all():
                raise ValueError("Nonfinite cosine similarities.")
            for row, scores in zip(batch, sims):
                index = int(scores.argmax())
                neighbors.append({"claim_id": row["claim_id"], "nearest_record_id": corpus[index]["id"],
                                  "cosine_similarity": float(scores[index]), "excluded_at_0_95": bool(scores[index] >= .95)})
        write_csv(out / "nearest_neighbors.csv", neighbors, ["claim_id", "nearest_record_id", "cosine_similarity", "excluded_at_0_95"])
        report["near_duplicate_claim_ids"] = [r["claim_id"] for r in neighbors if r["excluded_at_0_95"]]
        if report["near_duplicate_claim_ids"]:
            report["errors"].append("Near duplicates at or above 0.95 must be excluded and replaced before freeze.")
        record["embedding_model_sha256"] = {r.relative_to(args.embedding_model).as_posix(): sha256(r) for r in args.embedding_model.rglob("*") if r.is_file()}
    else:
        report["errors"].append("Semantic nearest-neighbor check not run: immutable embedding model required.")
    report["status"] = "FAIL" if report["errors"] else "SEPARATION_CHECKS_PASS_PENDING_HUMAN_AND_TRAINING_LINEAGE_REVIEW"
    # A separation check alone is never permission to label a dataset human-gold.
    write_json(out / "separation_report.json", report)
    record["status"] = report["status"]
    finish_manifest(out, record)
    print(f"Separation report: {out}")
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
