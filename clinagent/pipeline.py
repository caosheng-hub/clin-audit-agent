from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

from clinagent.generator.injector import inject_anomalies
from clinagent.generator.protocol import build_trial, render_protocol
from clinagent.generator.sdtm import generate_clean_data, write_domain_csvs
from clinagent.rules.evaluator import evaluate
from clinagent.rules.executor import RuleExecutor
from clinagent.schema import Anomaly, GroundTruthAnomaly, Rule


def generate_datasets(
    data_root: Path,
    trials: int,
    subjects: int,
    seed: int,
) -> list[str]:
    if subjects < 25:
        raise ValueError(
            "subjects must be >= 25 because the built-in injection suite uses S001-S025"
        )
    data_root.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    for index in range(1, trials + 1):
        trial = build_trial(index)
        trial_dir = data_root / trial.trial_id
        trial_dir.mkdir(parents=True, exist_ok=True)

        (trial_dir / "protocol.md").write_text(
            render_protocol(trial), encoding="utf-8"
        )
        (trial_dir / "rules.json").write_text(
            json.dumps(
                [rule.model_dump(mode="json") for rule in trial.rules],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        clean = generate_clean_data(
            trial, subjects, random.Random(seed * 1000 + index)
        )
        write_domain_csvs(clean, trial_dir / "clean")

        injected, truth = inject_anomalies(
            trial, clean, random.Random(seed * 2000 + index)
        )
        write_domain_csvs(injected, trial_dir / "injected")
        (trial_dir / "ground_truth.json").write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in truth],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        meta = {
            "trial_id": trial.trial_id,
            "title": trial.title,
            "indication": trial.indication,
            "phase": trial.phase,
            "age_min": trial.age_min,
            "age_max": trial.age_max,
            "bmi_min": trial.bmi_min,
            "alt_max": trial.alt_max,
            "hgb_min": trial.hgb_min,
            "creat_max": trial.creat_max,
            "visits": [
                {
                    "code": visit.code,
                    "name": visit.name,
                    "day": visit.day,
                    "window": visit.window,
                }
                for visit in trial.visits
            ],
            "prohibited_cm": trial.prohibited_cm,
            "rules": len(trial.rules),
            "subjects": subjects,
            "injected_anomalies": len(truth),
        }
        (trial_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        generated.append(trial.trial_id)

    return generated


def load_rules(trial_dir: Path) -> list[Rule]:
    raw = json.loads((trial_dir / "rules.json").read_text(encoding="utf-8"))
    return [Rule.model_validate(item) for item in raw]


def load_truth(trial_dir: Path) -> list[GroundTruthAnomaly]:
    raw = json.loads(
        (trial_dir / "ground_truth.json").read_text(encoding="utf-8")
    )
    return [GroundTruthAnomaly.model_validate(item) for item in raw]


def run_check(
    trial_dir: Path, dataset: str
) -> tuple[list[Anomaly], dict[str, float]]:
    if dataset not in {"clean", "injected"}:
        raise ValueError("dataset must be 'clean' or 'injected'")
    data_dir = trial_dir / dataset
    rules = load_rules(trial_dir)
    with RuleExecutor(data_dir) as executor:
        anomalies = executor.run_rules(rules)
        timings = dict(executor.timings)
    return anomalies, timings


def _overall_metrics(trial_results: dict[str, dict]) -> dict:
    tp = sum(item["metrics"]["tp"] for item in trial_results.values())
    fp = sum(item["metrics"]["fp"] for item in trial_results.values())
    fn = sum(item["metrics"]["fn"] for item in trial_results.values())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "predicted": sum(
            item["metrics"]["predicted"] for item in trial_results.values()
        ),
        "truth": sum(item["metrics"]["truth"] for item in trial_results.values()),
        "clean_false_positives": sum(
            item["clean_anomalies"] for item in trial_results.values()
        ),
    }


def _render_markdown(result: dict) -> str:
    overall = result["overall"]
    lines = [
        "# ClinAudit Agent — P0 评测报告",
        "",
        f"- 生成时间：{result['generated_at']}",
        f"- 方案数：{len(result['trials'])}",
        f"- 规则总数：{sum(item['rules'] for item in result['trials'].values())}",
        f"- 受试者总数：{sum(item['subjects'] for item in result['trials'].values())}",
        "",
        "## 总体指标",
        "",
        "| 指标 | 值 |",
        "|---|---|",
        f"| Precision | {overall['precision']:.4f} |",
        f"| Recall | {overall['recall']:.4f} |",
        f"| F1 | {overall['f1']:.4f} |",
        f"| TP / FP / FN | {overall['tp']} / {overall['fp']} / {overall['fn']} |",
        f"| 干净数据误报 | {overall['clean_false_positives']} |",
        "",
        "## 分方案结果",
        "",
        "| 方案 | 规则数 | 受试者 | 注入异常 | 检出 | FP | FN | Precision | Recall | F1 | 干净数据误报 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for trial_id, item in result["trials"].items():
        metrics = item["metrics"]
        lines.append(
            f"| {trial_id} | {item['rules']} | {item['subjects']} | "
            f"{metrics['truth']} | {metrics['tp']} | {metrics['fp']} | "
            f"{metrics['fn']} | {metrics['precision']:.4f} | "
            f"{metrics['recall']:.4f} | {metrics['f1']:.4f} | "
            f"{item['clean_anomalies']} |"
        )

    for trial_id, item in result["trials"].items():
        lines.extend(
            [
                "",
                f"## {trial_id} 分异常类型",
                "",
                "| 异常类型 | 总数 | 检出 | Recall |",
                "|---|---|---|---|",
            ]
        )
        for anomaly_type, bucket in item["metrics"]["per_type"].items():
            lines.append(
                f"| {anomaly_type} | {bucket['total']} | "
                f"{bucket['matched']} | {bucket['recall']:.4f} |"
            )

    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- P0 使用方案生成器内置的 gold rules，目标是验证规则编译、SQL 执行、异常注入和评测闭环。",
            "- 这里的 100% 左右指标不代表大模型抽取效果；LLM 规则抽取的 Precision/Recall F1 将在 P1 单独报告。",
            "- 干净数据误报为 0 是规则引擎正确性的前置条件。",
            "- 所有数据均为合成数据，不含任何真实患者信息。",
        ]
    )
    return "\n".join(lines) + "\n"


def run_evaluation(data_root: Path, report_dir: Path) -> dict:
    report_dir.mkdir(parents=True, exist_ok=True)
    trial_dirs = sorted(path for path in data_root.iterdir() if path.is_dir())
    if not trial_dirs:
        raise FileNotFoundError(f"no trials found under {data_root}")

    trial_results: dict[str, dict] = {}
    for trial_dir in trial_dirs:
        rules = load_rules(trial_dir)
        truth = load_truth(trial_dir)
        meta = json.loads(
            (trial_dir / "meta.json").read_text(encoding="utf-8")
        )

        clean_anomalies, _ = run_check(trial_dir, "clean")
        injected_anomalies, timings = run_check(trial_dir, "injected")
        metrics = evaluate(injected_anomalies, truth)

        trial_results[trial_dir.name] = {
            "rules": len(rules),
            "subjects": int(meta["subjects"]),
            "clean_anomalies": len(clean_anomalies),
            "metrics": metrics,
            "timings": timings,
        }

        (report_dir / f"{trial_dir.name}_anomalies.json").write_text(
            json.dumps(
                {
                    "trial_id": trial_dir.name,
                    "injected": [
                        item.model_dump(mode="json")
                        for item in injected_anomalies
                    ],
                    "clean": [
                        item.model_dump(mode="json") for item in clean_anomalies
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    overall = _overall_metrics(trial_results)
    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "note": (
            "P0 uses generator-provided gold rules to validate the rule engine; "
            "LLM rule extraction is evaluated separately in P1."
        ),
        "overall": overall,
        "trials": trial_results,
    }
    (report_dir / "evaluation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (report_dir / "evaluation.md").write_text(
        _render_markdown(result), encoding="utf-8"
    )
    return result
