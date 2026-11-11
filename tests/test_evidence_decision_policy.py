from src.ai_core.layers.k5_decision import make_decision, make_evidence_decision


def evidence(nli_probs):
    return {"nli_probs": nli_probs, "sim": .95, "sig_rerank": .95, "authority": .95}


def test_support_requires_nli_evidence_not_a_record_label():
    supported = make_evidence_decision([evidence([.95, .02, .03])])
    assert supported["status"] == "ONAY"

    # The deprecated label argument cannot change the compatibility wrapper's
    # result. This protects against re-introducing nearest-record propagation.
    with_true_label = make_decision([.95, .02, .03], .95, db_label=1, sig_rerank=.95)
    with_false_label = make_decision([.95, .02, .03], .95, db_label=0, sig_rerank=.95)
    assert with_true_label == with_false_label


def test_contradiction_is_a_first_class_outcome():
    result = make_evidence_decision([evidence([.03, .02, .95])])
    assert result["status"] == "RED"


def test_retrieval_strength_cannot_override_neutral_nli():
    result = make_evidence_decision([evidence([.05, .90, .05])])
    assert result["status"] == "RET"


def test_conflicting_evidence_abstains():
    result = make_evidence_decision([
        evidence([.88, .04, .08]), evidence([.08, .04, .88]),
    ])
    assert result["status"] == "RET"
