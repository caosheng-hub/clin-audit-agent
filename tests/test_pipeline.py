from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from clinagent.generator.injector import inject_anomalies
from clinagent.generator.protocol import build_trial, render_protocol
from clinagent.generator.sdtm import generate_clean_data, write_domain_csvs
from clinagent.pipeline import generate_datasets, run_evaluation
from clinagent.rules.compiler import compile_rule, validate_rule
from clinagent.rules.evaluator import evaluate
from clinagent.rules.executor import RuleExecutor
from clinagent.schema import CheckType, Rule, Severity


def make_rule(**overrides) -> Rule:
    base = Rule(
        rule_id="T-1",
        trial_id="T",
        code="TEST_RULE",
        domain="AE",
        field="AESEV",
        check_type=CheckType.REQUIRED,
        params={},
        severity=Severity.MAJOR,
        description="test rule",
        section_id="1.1",
        section_title="test",
        quote="test rule",
    )
    return base.model_copy(update=overrides)


@pytest.mark.parametrize("trial_index", [1, 2])
def test_rule_quotes_are_traceable_to_protocol(trial_index: int) -> None:
    trial = build_trial(trial_index)
    protocol = render_protocol(trial)

    assert len(trial.rules) == 33
    assert {rule.check_type for rule in trial.rules} == set(CheckType)
    for rule in trial.rules:
        assert rule.quote in protocol
        assert rule.section_id in protocol


def test_clean_data_has_no_anomalies(tmp_path: Path) -> None:
    trial = build_trial(1)
    clean = generate_clean_data(trial, 25, random.Random(1))
    write_domain_csvs(clean, tmp_path)

    with RuleExecutor(tmp_path) as executor:
        anomalies = executor.run_rules(trial.rules)

    assert anomalies == []


def test_injected_anomalies_are_detected_with_evidence(tmp_path: Path) -> None:
    trial = build_trial(1)
    clean = generate_clean_data(trial, 25, random.Random(1))
    injected, truth = inject_anomalies(trial, clean, random.Random(2))
    assert len(truth) == 34
    write_domain_csvs(injected, tmp_path)

    with RuleExecutor(tmp_path) as executor:
        predicted = executor.run_rules(trial.rules)

    metrics = evaluate(predicted, truth)
    assert metrics["precision"] >= 0.95
    assert metrics["recall"] >= 0.95
    assert metrics["f1"] >= 0.95
    assert all(item.evidence for item in predicted)


def test_end_to_end_pipeline_is_deterministic(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    report_root = tmp_path / "reports"

    generated = generate_datasets(data_root, trials=2, subjects=25, seed=42)
    result = run_evaluation(data_root, report_root)
    overall = result["overall"]

    assert generated == ["TRIAL-001", "TRIAL-002"]
    assert overall["truth"] == 68
    assert overall["tp"] == 68
    assert overall["fp"] == 0
    assert overall["fn"] == 0
    assert overall["clean_false_positives"] == 0
    assert overall["precision"] == overall["recall"] == overall["f1"] == 1.0

    report = (report_root / "evaluation.md").read_text(encoding="utf-8")
    assert "gold rules" in report
    assert "LLM" in report

    trial_result = json.loads(
        (report_root / "TRIAL-001_anomalies.json").read_text(encoding="utf-8")
    )
    assert len(trial_result["injected"]) == 34
    assert trial_result["clean"] == []


def test_compiler_rejects_unknown_column() -> None:
    rule = make_rule(
        check_type=CheckType.RANGE,
        field="NOT_A_COLUMN",
        params={"min": 1},
    )
    with pytest.raises(ValueError, match="not allowed"):
        compile_rule(rule)


def test_compiler_rejects_sql_in_identifier() -> None:
    rule = make_rule(field="AESEV; DROP TABLE ae")
    with pytest.raises(ValueError, match="invalid SQL identifier"):
        compile_rule(rule)


def test_compiler_escapes_string_literals() -> None:
    rule = make_rule(
        check_type=CheckType.CONSISTENCY,
        field="AESER",
        params={
            "if_field": "AEACN",
            "if_value": "Y' OR 1=1 --",
            "then_field": "AESER",
            "then_value": "Y",
        },
    )
    sql = compile_rule(rule)
    assert "'Y'' OR 1=1 --'" in sql


def test_compiler_rejects_unsupported_params() -> None:
    rule = make_rule(
        check_type=CheckType.RANGE,
        field="AGE",
        domain="DM",
        params={"min": 1, "unexpected": True},
    )
    with pytest.raises(ValueError, match="unsupported params"):
        compile_rule(rule)


def test_visit_window_requires_rfstdtc_anchor() -> None:
    rule = make_rule(
        domain="SV",
        field="SVSTDTC",
        check_type=CheckType.VISIT_WINDOW,
        params={
            "visit": "V2",
            "anchor": "EXSTDTC",
            "target_day": 14,
            "minus": 3,
            "plus": 3,
        },
    )
    with pytest.raises(ValueError, match="RFSTDTC"):
        validate_rule(rule)


def test_executor_reports_missing_domain_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="missing domain file"):
        RuleExecutor(tmp_path)


def test_generator_rejects_too_few_subjects(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="subjects must be >= 25"):
        generate_datasets(tmp_path, trials=1, subjects=24, seed=42)
