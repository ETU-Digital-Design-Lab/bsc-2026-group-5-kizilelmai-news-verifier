#!/usr/bin/env python3
"""Capture inspectable provenance for an existing local classifier checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a non-destructive checkpoint manifest.")
    parser.add_argument("--checkpoint", type=Path, default=Path("src/ai_core/models/kizilelma_classifier_v1"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference-vocab", type=Path, default=None, help="Optional official vocab.txt for tokenizer identity verification")
    parser.add_argument("--reference-model-id", default=None, help="Model ID associated with --reference-vocab")
    args = parser.parse_args()

    config_path = args.checkpoint / "config.json"
    if not config_path.is_file():
        raise SystemExit(f"config.json not found in {args.checkpoint}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    files = [path for path in sorted(args.checkpoint.iterdir()) if path.is_file()]
    tokenizer_evidence = None
    if args.reference_vocab:
        tokenizer_path = args.checkpoint / "tokenizer.json"
        if not tokenizer_path.is_file() or not args.reference_vocab.is_file():
            raise SystemExit("Both checkpoint tokenizer.json and --reference-vocab must exist.")
        tokenizer = json.loads(tokenizer_path.read_text(encoding="utf-8"))
        local_vocab = tokenizer["model"]["vocab"]
        reference_vocab = args.reference_vocab.read_text(encoding="utf-8").splitlines()
        tokenizer_evidence = {
            "reference_model_id": args.reference_model_id,
            "reference_vocab_sha256": sha256(args.reference_vocab),
            "local_vocab_size": len(local_vocab),
            "reference_vocab_size": len(reference_vocab),
            "identical_token_to_id_mapping": all(local_vocab.get(token) == index for index, token in enumerate(reference_vocab)),
        }
    manifest = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_path": str(args.checkpoint),
        "checkpoint_config": {
            "model_type": config.get("model_type"),
            "architectures": config.get("architectures"),
            "hidden_size": config.get("hidden_size"),
            "num_hidden_layers": config.get("num_hidden_layers"),
            "vocab_size": config.get("vocab_size"),
            "num_labels": config.get("num_labels"),
        },
        "upstream_base_model": args.reference_model_id if tokenizer_evidence and tokenizer_evidence["identical_token_to_id_mapping"] else "Not recoverable from this checkpoint configuration alone.",
        "tokenizer_identity_evidence": tokenizer_evidence,
        "interpretation": "The architecture is BERT, not XLM-R. An identical official tokenizer mapping is strong base-model evidence, but future training runs must preserve training_manifest.json for complete upstream-weight and data provenance.",
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)} for path in files],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
