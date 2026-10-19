from __future__ import annotations

import time
from pathlib import Path

import duckdb

from clinagent.rules.compiler import TABLE_COLUMNS, compile_rule
from clinagent.schema import Anomaly, Rule


class RuleExecutor:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.con = duckdb.connect(database=":memory:")
        self.timings: dict[str, float] = {}
        for table in TABLE_COLUMNS:
            path = self.data_dir / f"{table}.csv"
            if not path.exists():
                raise FileNotFoundError(f"missing domain file: {path}")
            escaped = path.as_posix().replace("'", "''")
            self.con.execute(
                f"CREATE OR REPLACE VIEW {table} AS "
                f"SELECT * FROM read_csv_auto('{escaped}', header=true)"
            )

    def run_rules(self, rules: list[Rule]) -> list[Anomaly]:
        found: dict[tuple[str, str], Anomaly] = {}
        for rule in rules:
            sql = compile_rule(rule)
            started = time.perf_counter()
            try:
                rows = self.con.execute(sql).fetchall()
            except Exception as exc:
                raise RuntimeError(
                    f"rule {rule.rule_id} failed: {exc}\nSQL:\n{sql}"
                ) from exc
            self.timings[rule.rule_id] = time.perf_counter() - started

            for row in rows:
                subject_id = row[0]
                if subject_id is None:
                    continue
                key = (str(subject_id), rule.rule_id)
                if key in found:
                    continue
                found[key] = Anomaly(
                    anomaly_id=f"{rule.rule_id}:{subject_id}",
                    subject_id=str(subject_id),
                    rule_id=rule.rule_id,
                    domain=rule.domain.upper(),
                    field=rule.field,
                    expected=str(row[3]) if row[3] is not None else "",
                    actual=str(row[4]) if row[4] is not None else "",
                    severity=rule.severity,
                    check_type=rule.check_type,
                    evidence=str(row[5]) if row[5] is not None else "",
                )
        return sorted(found.values(), key=lambda item: (item.subject_id, item.rule_id))

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> "RuleExecutor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
