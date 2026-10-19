from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from clinagent.llm.provider import load_llm_config, get_provider
from clinagent.pipeline import (
    generate_datasets,
    run_check,
    run_evaluation,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = ROOT / "data" / "synthetic"
REPORT_DIR = ROOT / "reports"
CONFIG_PATH = ROOT / "config" / "settings.yaml"


def cmd_generate(args: argparse.Namespace) -> None:
    trial_ids = generate_datasets(
        DATA_ROOT, args.trials, args.subjects, args.seed
    )
    print(f"generated {len(trial_ids)} trials under {DATA_ROOT}")
    for trial_id in trial_ids:
        trial_dir = DATA_ROOT / trial_id
        meta = json.loads(
            (trial_dir / "meta.json").read_text(encoding="utf-8")
        )
        print(
            f"  {trial_id}: rules={meta['rules']}, "
            f"subjects={meta['subjects']}, "
            f"injected={meta['injected_anomalies']}"
        )


def cmd_check(args: argparse.Namespace) -> None:
    trial_dir = DATA_ROOT / args.trial
    if not trial_dir.exists():
        raise SystemExit(f"trial not found: {trial_dir}")
    anomalies, timings = run_check(trial_dir, args.dataset)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"{args.trial}_{args.dataset}_anomalies.json"
    out_path.write_text(
        json.dumps(
            [item.model_dump(mode="json") for item in anomalies],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"dataset={args.dataset}, anomalies={len(anomalies)}")
    print(f"written: {out_path}")
    if anomalies:
        print("")
        print(f"{'subject':<10}{'rule_id':<48}{'field':<14}actual")
        for item in anomalies[:15]:
            print(
                f"{item.subject_id:<10}{item.rule_id:<48}"
                f"{str(item.field):<14}{item.actual}"
            )
        if len(anomalies) > 15:
            print(f"... {len(anomalies) - 15} more")
    total_ms = sum(timings.values()) * 1000
    print(f"rule execution total: {total_ms:.1f} ms")


def cmd_evaluate(args: argparse.Namespace) -> None:
    if not DATA_ROOT.exists():
        raise SystemExit(
            f"no generated data under {DATA_ROOT}; run `generate` first"
        )
    result = run_evaluation(DATA_ROOT, REPORT_DIR)
    overall = result["overall"]
    print("evaluation complete")
    print(
        f"  precision={overall['precision']:.4f} "
        f"recall={overall['recall']:.4f} f1={overall['f1']:.4f}"
    )
    print(
        f"  tp={overall['tp']} fp={overall['fp']} fn={overall['fn']} "
        f"clean_fp={overall['clean_false_positives']}"
    )
    print(f"  report: {REPORT_DIR / 'evaluation.md'}")


def cmd_all(args: argparse.Namespace) -> None:
    generate_datasets(DATA_ROOT, args.trials, args.subjects, args.seed)
    result = run_evaluation(DATA_ROOT, REPORT_DIR)
    overall = result["overall"]
    print("")
    print("P0 pipeline complete")
    print(
        f"  precision={overall['precision']:.4f} "
        f"recall={overall['recall']:.4f} f1={overall['f1']:.4f}"
    )
    print(
        f"  clean_false_positives={overall['clean_false_positives']}"
    )
    print(f"  report: {REPORT_DIR / 'evaluation.md'}")


def cmd_llm_check(args: argparse.Namespace) -> None:
    config = load_llm_config(CONFIG_PATH)
    provider = get_provider(config)
    schema = {
        "type": "object",
        "properties": {"status": {"type": "string"}},
        "required": ["status"],
    }
    started = time.perf_counter()
    try:
        output = provider.chat(
            '只输出 JSON：{"status":"ok"}',
            system="你是严格的 JSON 输出器，不要输出任何解释。",
            json_schema=schema,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    elapsed = time.perf_counter() - started
    print(f"provider={config.provider} model={config.model}")
    print(f"elapsed={elapsed:.2f}s")
    print(f"output={output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clinagent", description="ClinAudit Agent (synthetic P0)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="generate synthetic data")
    generate.add_argument("--trials", type=int, default=2)
    generate.add_argument("--subjects", type=int, default=25)
    generate.add_argument("--seed", type=int, default=42)
    generate.set_defaults(func=cmd_generate)

    check = subparsers.add_parser("check", help="run rules on one trial")
    check.add_argument("--trial", required=True)
    check.add_argument(
        "--dataset", choices=["clean", "injected"], default="injected"
    )
    check.set_defaults(func=cmd_check)

    evaluate = subparsers.add_parser("evaluate", help="evaluate all trials")
    evaluate.set_defaults(func=cmd_evaluate)

    all_cmd = subparsers.add_parser("all", help="generate and evaluate")
    all_cmd.add_argument("--trials", type=int, default=2)
    all_cmd.add_argument("--subjects", type=int, default=25)
    all_cmd.add_argument("--seed", type=int, default=42)
    all_cmd.set_defaults(func=cmd_all)

    llm_check = subparsers.add_parser(
        "llm-check", help="check local Ollama connectivity"
    )
    llm_check.set_defaults(func=cmd_llm_check)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
