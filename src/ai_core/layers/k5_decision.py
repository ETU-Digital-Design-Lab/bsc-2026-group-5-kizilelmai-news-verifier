"""Evidence-only selective decision policy.

This module deliberately does *not* accept a retrieved record's verdict label.
A corpus label can be useful for training or for a retrieval baseline, but using
it at inference turns an evidence verifier into nearest-record label propagation.
The only inputs here are claim--evidence inference scores and evidence quality
metadata. Thresholds are selected on a held-out development set, never on the
reported test set (see ``scripts/evaluation/fit_selective_policy.py``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

from src.ai_core.layers.constants import STATUS_APPROVE, STATUS_REJECT, STATUS_RETURN
from src.ai_core.layers.k4_nli import IDX_CONTRADICTION, IDX_ENTAILMENT, IDX_NEUTRAL


@dataclass(frozen=True)
class PolicyConfig:
    """Operating point exported by the held-out-development fitting script."""

    min_evidence_strength: float = 0.55
    min_nli_probability: float = 0.50
    min_nli_margin: float = 0.12
    max_risk: float = 0.55
    top_k: int = 3

    @classmethod
    def from_mapping(cls, value: Optional[Mapping[str, Any]]) -> "PolicyConfig":
        if not value:
            return cls()
        names = {field: value[field] for field in cls.__dataclass_fields__ if field in value}
        return cls(**names)


def _clip(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _normalised_weights(evidence: Iterable[Mapping[str, Any]]) -> List[float]:
    """Weight relevance and authority without allowing either to decide a label."""
    raw = []
    for item in evidence:
        relevance = 0.65 * _clip(item.get("sig_rerank")) + 0.35 * _clip(item.get("sim"))
        raw.append(max(0.01, relevance * (0.75 + 0.25 * _clip(item.get("authority", 0.60)))))
    total = sum(raw)
    return [weight / total for weight in raw] if total else []


def aggregate_evidence(
    evidence: Iterable[Mapping[str, Any]], *, critical_mismatch: bool = False,
) -> Dict[str, float]:
    """Aggregate NLI from several independently retrieved evidence passages.

    ``critical_mismatch`` is only a tie-breaker for a detected number/date/entity
    discrepancy in an otherwise relevant passage. It cannot create a verdict
    without an NLI-supported, sufficiently strong evidence set.
    """
    rows = list(evidence)
    weights = _normalised_weights(rows)
    if not rows or not weights:
        return {"entailment": 0.0, "contradiction": 0.0, "neutral": 1.0,
                "strength": 0.0, "n_sources": 0.0}

    entailment = contradiction = neutral = strength = 0.0
    for row, weight in zip(rows, weights):
        probs = row.get("nli_probs") or []
        entailment += weight * _clip(probs[IDX_ENTAILMENT] if len(probs) > IDX_ENTAILMENT else 0.0)
        neutral += weight * _clip(probs[IDX_NEUTRAL] if len(probs) > IDX_NEUTRAL else 1.0)
        contradiction += weight * _clip(probs[IDX_CONTRADICTION] if len(probs) > IDX_CONTRADICTION else 0.0)
        strength += weight * (0.65 * _clip(row.get("sig_rerank")) +
                              0.20 * _clip(row.get("sim")) +
                              0.15 * _clip(row.get("authority", 0.60)))

    if critical_mismatch and strength >= 0.55:
        contradiction = min(1.0, contradiction + 0.08 * (1.0 - contradiction))

    return {"entailment": entailment, "contradiction": contradiction,
            "neutral": neutral, "strength": strength, "n_sources": float(len(rows))}


def make_evidence_decision(
    evidence: Iterable[Mapping[str, Any]], *, critical_mismatch: bool = False,
    policy: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a selective verdict from evidence, without consulting corpus labels."""
    config = PolicyConfig.from_mapping(policy)
    rows = list(evidence)[:config.top_k]
    scores = aggregate_evidence(rows, critical_mismatch=critical_mismatch)
    support, refute = scores["entailment"], scores["contradiction"]
    strongest = max(support, refute)
    margin = abs(support - refute)
    confidence = scores["strength"] * strongest * (1.0 - 0.35 * scores["neutral"])
    risk = 1.0 - confidence

    insufficient = (
        scores["n_sources"] == 0 or scores["strength"] < config.min_evidence_strength
        or strongest < config.min_nli_probability or margin < config.min_nli_margin
        or risk > config.max_risk
    )
    if insufficient:
        return {"status": STATUS_RETURN, "confidence": round(confidence * 100),
                "risk": round(risk * 100), "reason": "insufficient_evidence_or_policy_risk",
                "evidence": scores, "nli_margin": margin}

    status = STATUS_APPROVE if support > refute else STATUS_REJECT
    return {"status": status, "confidence": round(confidence * 100),
            "risk": round(risk * 100), "reason": "aggregated_nli_evidence",
            "evidence": scores, "nli_margin": margin}


# Compatibility wrapper. ``db_label`` is intentionally ignored; it remains only
# to avoid silently breaking external callers that used the old function.
def make_decision(nli_probs: List[float], sim_score: float, db_label: Optional[int] = None,
                  sig_rerank: float = 0.0, **_: Any) -> Dict[str, Any]:
    return make_evidence_decision([{"nli_probs": nli_probs, "sim": sim_score,
                                    "sig_rerank": sig_rerank, "authority": 0.60}])
