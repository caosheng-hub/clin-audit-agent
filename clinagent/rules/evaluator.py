from __future__ import annotations

from clinagent.schema import Anomaly, GroundTruthAnomaly


def _round(value: float) -> float:
    return round(value, 4)


def evaluate(
    predicted: list[Anomaly], truth: list[GroundTruthAnomaly]
) -> dict:
    predictions = {(item.subject_id, item.rule_id): item for item in predicted}
    expected = {(item.subject_id, item.rule_id): item for item in truth}

    true_positive = set(predictions) & set(expected)
    false_positive = set(predictions) - set(expected)
    false_negative = set(expected) - set(predictions)

    precision = len(true_positive) / len(predictions) if predictions else 0.0
    recall = len(true_positive) / len(expected) if expected else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    per_type: dict[str, dict[str, float | int]] = {}
    for key, item in expected.items():
        bucket = per_type.setdefault(
            item.anomaly_type, {"total": 0, "matched": 0}
        )
        bucket["total"] += 1
        if key in predictions:
            bucket["matched"] += 1
    for bucket in per_type.values():
        total = int(bucket["total"])
        matched = int(bucket["matched"])
        bucket["recall"] = _round(matched / total) if total else 0.0

    return {
        "precision": _round(precision),
        "recall": _round(recall),
        "f1": _round(f1),
        "tp": len(true_positive),
        "fp": len(false_positive),
        "fn": len(false_negative),
        "predicted": len(predictions),
        "truth": len(expected),
        "per_type": dict(sorted(per_type.items())),
        "false_positives": [
            {
                "subject_id": predictions[key].subject_id,
                "rule_id": predictions[key].rule_id,
                "field": predictions[key].field,
                "actual": predictions[key].actual,
            }
            for key in sorted(false_positive)
        ],
        "false_negatives": [
            {
                "subject_id": expected[key].subject_id,
                "rule_id": expected[key].rule_id,
                "anomaly_type": expected[key].anomaly_type,
                "expected": expected[key].expected,
            }
            for key in sorted(false_negative)
        ],
    }
