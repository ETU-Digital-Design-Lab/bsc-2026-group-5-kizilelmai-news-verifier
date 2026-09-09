#!/usr/bin/env python3
"""Audit a claim-level evaluation set before it is cited in a paper.

This script validates the *record keeping* needed for a multi-annotator gold
set.  It deliberately cannot certify that people performed the annotations;
that requires the study's consent/recruitment and provenance records.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_CLAIM_COLUMNS = {"claim_id", "text", "gold_label"}
REQUIRED_ANNOTATION_COLUMNS = {"claim_id", "annotator_pseudo_id", "decision", "timestamp", "guideline_version"}
VALID_LABELS = {"0", "1"}


def krippendorff_alpha(item_labels: list[list[str]]) -> float | None:
    """Nominal alpha using coincidence weights; excludes singly rated items."""
    items = [labels for labels in item_labels if len(labels) >= 2]
    totals = Counter(label for labels in items for label in labels)
    n = sum(totals.values())
    if n < 2:
        return None
    observed = sum((len(labels) ** 2 - sum(v * v for v in Counter(labels).values()))
                   / (len(labels) - 1) for labels in items) / n
    expected = (n * n - sum(v * v for v in totals.values())) / (n * (n - 1))
    return 1 - observed / expected if expected else None


def valid_timestamp(value: str) -> bool:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.tzinfo is not None and dt <= datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return False


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path}: CSV header is missing.")
        return [{key.strip(): (value or "").strip() for key, value in row.items()} for row in reader]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fleiss_kappa(item_labels: list[list[str]]) -> float | None:
    """Compute Fleiss' kappa for complete, equally rated binary items."""
    if not item_labels:
        return None
    n_raters = len(item_labels[0])
    if n_raters < 2 or any(len(labels) != n_raters for labels in item_labels):
        return None

    totals = Counter(label for labels in item_labels for label in labels)
    n_items = len(item_labels)
    p_bar = sum(
        (sum(count * count for count in Counter(labels).values()) - n_raters)
        / (n_raters * (n_raters - 1))
        for labels in item_labels
    ) / n_items
    p_expected = sum((count / (n_items * n_raters)) ** 2 for count in totals.values())
    if p_expected == 1:
        return None
    return (p_bar - p_expected) / (1 - p_expected)


def audit_dataset(dataset_dir: Path) -> dict[str, Any]:
    claims_path = dataset_dir / "claims_annotated.csv"
    round1_path = dataset_dir / "annotation_round1.csv"
    round2_path = dataset_dir / "annotation_round2.csv"
    report_path = dataset_dir / "iaa_report.json"
    manifest_path = dataset_dir / "annotation_manifest.json"

    errors: list[str] = []
    warnings: list[str] = []
    for path in (claims_path, round1_path):
        if not path.is_file():
            errors.append(f"Required file is missing: {path.name}")
    if errors:
        return {"status": "FAIL", "errors": errors, "warnings": warnings}

    claims = read_csv(claims_path)
    annotations = read_csv(round1_path)
    claim_columns = set(claims[0]) if claims else set()
    annotation_columns = set(annotations[0]) if annotations else set()
    missing_claim_columns = sorted(REQUIRED_CLAIM_COLUMNS - claim_columns)
    missing_annotation_columns = sorted(REQUIRED_ANNOTATION_COLUMNS - annotation_columns)
    if missing_claim_columns:
        errors.append(f"claims_annotated.csv missing columns: {', '.join(missing_claim_columns)}")
    if missing_annotation_columns:
        errors.append(f"annotation_round1.csv missing columns: {', '.join(missing_annotation_columns)}")

    # Legacy columns remain readable for diagnostics; they cannot satisfy strict provenance.
    for row in annotations:
        row["annotator"] = row.get("annotator_pseudo_id", row.get("annotator", ""))
        row["label"] = row.get("decision", row.get("label", ""))
        row["label"] = {"DOĞRU": "1", "YALAN": "0"}.get(row["label"], row["label"])
    if len(claims) != 500:
        errors.append(f"This protocol requires exactly 500 claims; found {len(claims)}.")
    if len(annotations) != 1500:
        errors.append(f"This protocol requires exactly 1500 first-round decisions; found {len(annotations)}.")
    bad_timestamps = sum(not valid_timestamp(row.get("timestamp", "")) for row in annotations)
    missing_guidelines = sum(not row.get("guideline_version", "").strip() for row in annotations)
    if bad_timestamps:
        errors.append(f"Missing/invalid/timezone-free/future first-round timestamps: {bad_timestamps}")
    if missing_guidelines:
        errors.append(f"First-round decisions without guideline_version: {missing_guidelines}")

    claim_ids = [row.get("claim_id", "") for row in claims]
    claim_id_counts = Counter(claim_ids)
    duplicate_claim_ids = sorted(claim_id for claim_id, count in claim_id_counts.items() if count > 1 or not claim_id)
    if duplicate_claim_ids:
        errors.append(f"Duplicate or empty claim IDs: {len(duplicate_claim_ids)}")
    duplicate_texts = sum(1 for _, count in Counter(row.get("text", "") for row in claims).items() if count > 1)
    if duplicate_texts:
        warnings.append(f"Duplicate claim texts: {duplicate_texts}")

    invalid_gold_labels = [row.get("claim_id", "") for row in claims if row.get("gold_label") not in VALID_LABELS]
    invalid_annotation_labels = [row.get("claim_id", "") for row in annotations if row.get("label") not in VALID_LABELS]
    if invalid_gold_labels:
        errors.append(f"Invalid final labels: {len(invalid_gold_labels)}")
    if invalid_annotation_labels:
        errors.append(f"Invalid individual labels: {len(invalid_annotation_labels)}")

    annotations_by_claim: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in annotations:
        annotations_by_claim[row.get("claim_id", "")].append(row)
    annotators = sorted({row.get("annotator", "") for row in annotations if row.get("annotator", "")})
    expected_annotators = set(annotators)
    if len(expected_annotators) != 3:
        errors.append(f"Exactly 3 pseudonymous annotators are required; found {len(expected_annotators)}.")
    unknown_annotation_claims = sorted(set(annotations_by_claim) - set(claim_ids))
    if unknown_annotation_claims:
        errors.append(f"Annotations reference unknown claims: {len(unknown_annotation_claims)}")

    incomplete_claims: list[str] = []
    duplicate_decisions: list[str] = []
    incomplete_complete_labels: list[list[str]] = []
    disagreements: list[str] = []
    majority_mismatches: list[str] = []
    for claim in claims:
        claim_id = claim.get("claim_id", "")
        rows = annotations_by_claim.get(claim_id, [])
        per_annotator = Counter(row.get("annotator", "") for row in rows)
        if set(per_annotator) != expected_annotators or any(count != 1 for count in per_annotator.values()):
            incomplete_claims.append(claim_id)
            if any(count > 1 for count in per_annotator.values()):
                duplicate_decisions.append(claim_id)
            continue
        labels = [row["label"] for row in rows]
        incomplete_complete_labels.append(labels)
        if len(set(labels)) > 1:
            disagreements.append(claim_id)
        majority = Counter(labels).most_common(1)[0][0]
        if claim.get("gold_label") != majority:
            majority_mismatches.append(claim_id)

    if incomplete_claims:
        errors.append(
            f"Claims without one first-round decision from every annotator: {len(incomplete_claims)}"
        )
    if duplicate_decisions:
        errors.append(f"Claims with duplicate first-round decisions: {len(duplicate_decisions)}")
    round2 = read_csv(round2_path) if round2_path.is_file() else []
    round2_claim_ids = sorted({row.get("claim_id", "") for row in round2 if row.get("claim_id", "")})
    if disagreements and not round2:
        warnings.append("First-round disagreements exist but annotation_round2.csv is missing.")
    # Adjudication may validly override majority, but only with a separate timed rationale.
    resolved = set()
    for row in round2:
        cid = row.get("claim_id", "")
        claim = next((c for c in claims if c["claim_id"] == cid), None)
        decision = {"DOĞRU": "1", "YALAN": "0"}.get(row.get("decision"), row.get("decision", row.get("final_label")))
        if (claim and decision == claim["gold_label"] and row.get("rationale")
                and row.get("annotator_pseudo_id") and row.get("guideline_version")
                and valid_timestamp(row.get("timestamp", ""))):
            resolved.add(cid)
    unrecorded_adjudications = sorted((set(disagreements) | set(majority_mismatches)) - resolved)
    if unrecorded_adjudications:
        errors.append(f"Disputes/majority overrides without timed separate adjudication and rationale: {len(unrecorded_adjudications)}")

    kappa = fleiss_kappa(incomplete_complete_labels)
    declared_report: dict[str, Any] = {}
    if report_path.is_file():
        with report_path.open("r", encoding="utf-8") as handle:
            declared_report = json.load(handle)
        declared_kappa = declared_report.get(
            "iaa_fleiss_kappa_first_round_complete_items",
            declared_report.get("iaa_fleiss_kappa"),
        )
        if kappa is not None and declared_kappa is not None and abs(float(declared_kappa) - kappa) > 0.0001:
            errors.append(
                f"Declared Fleiss kappa ({declared_kappa}) does not match first-round records ({kappa:.4f})."
            )
        declared_n = declared_report.get("final_claims", declared_report.get("n_claims"))
        if declared_n is not None and int(declared_n) != len(claims):
            errors.append(f"Declared claim count ({declared_n}) does not match claims file ({len(claims)}).")
    else:
        warnings.append("iaa_report.json is missing.")

    if not manifest_path.is_file():
        errors.append(
            "annotation_manifest.json is missing; human provenance (protocol, dates, consent/ethics, and source records) is not documented."
        )
    else:
        try:
            protocol = json.loads(manifest_path.read_text(encoding="utf-8"))
            if protocol.get("DO_NOT_PUBLISH_UNTIL_COMPLETED", True) is not False:
                errors.append("Annotation manifest is still a template/unapproved factual record.")
            for key in ("claim_freeze_date", "claim_sampling_frame", "annotation_guide_version", "annotation_window", "ethics_and_consent", "adjudication"):
                if not protocol.get(key):
                    errors.append(f"Annotation manifest missing: {key}")
            blinding = protocol.get("blinding", {})
            for key in ("annotators_blinded_to_system_predictions", "annotators_blinded_to_each_other_first_round_labels",
                        "published_verdict_visible", "source_url_visible"):
                if type(blinding.get(key)) is not bool:
                    errors.append(f"Annotation manifest must record true/false: blinding.{key}")
            if not blinding.get("procedure"):
                errors.append("Annotation manifest must describe exactly what annotators saw.")
            declared_annotators = {a.get("pseudonymous_id") for a in protocol.get("annotators", [])}
            if declared_annotators != expected_annotators:
                errors.append("Manifest annotators differ from the first-round records.")
            for raw_path in (round1_path, round2_path):
                if not raw_path.is_file() or protocol.get("raw_export_hashes", {}).get(raw_path.name) != sha256(raw_path):
                    errors.append(f"Missing/mismatched manifest raw export SHA-256: {raw_path.name}")
            guideline_files = protocol.get("guideline_files", {})
            for version in {r.get("guideline_version", "") for r in annotations} - {""}:
                item = guideline_files.get(version, {})
                guide = dataset_dir / item.get("path", "")
                if not guide.is_file() or sha256(guide) != item.get("sha256"):
                    errors.append(f"Missing/mismatched archived guideline: {version}")
        except (ValueError, TypeError, AttributeError) as exc:
            errors.append(f"Invalid annotation manifest: {type(exc).__name__}")

    file_hashes = {
        path.name: sha256(path)
        for path in (claims_path, round1_path, round2_path, report_path)
        if path.is_file()
    }
    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_dir": str(dataset_dir),
        "counts": {
            "final_claims": len(claims),
            "first_round_decisions": len(annotations),
            "annotators_observed": annotators,
            "complete_first_round_claims": len(incomplete_complete_labels),
            "incomplete_first_round_claims": len(incomplete_claims),
            "first_round_disagreements": len(disagreements),
            "round2_claims": len(round2_claim_ids),
        },
        "iaa": {
            "fleiss_kappa_first_round_complete_items": round(kappa, 6) if kappa is not None else None,
            "krippendorff_alpha_nominal_complete_items": krippendorff_alpha(incomplete_complete_labels),
            "items_used": len(incomplete_complete_labels),
            "full_500_iaa_available": len(incomplete_complete_labels) == 500 and not errors,
            "scope": "Record-only diagnostic on complete first-round items; human independence not established.",
            "declared_fleiss_kappa": declared_report.get(
                "iaa_fleiss_kappa_first_round_complete_items",
                declared_report.get("iaa_fleiss_kappa"),
            ),
        },
        "errors": errors,
        "warnings": warnings,
        "examples": {
            "missing_first_round_ids": incomplete_claims[:20],
            "disagreement_ids": disagreements[:20],
            "majority_mismatch_ids": majority_mismatches[:20],
        },
        "file_sha256": file_hashes,
        "all_incomplete_claim_ids": incomplete_claims,
        "publication_note": (
            "PASS only verifies the completeness and internal consistency of the supplied files. "
            "It does not prove that annotations were performed by humans."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a multi-annotator claim evaluation dataset.")
    parser.add_argument("--dataset-dir", type=Path, default=Path("data/gold_500"))
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON report path.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when the audit fails.")
    args = parser.parse_args()

    report = audit_dataset(args.dataset_dir)
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    print(encoded)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    return 2 if args.strict and report["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
