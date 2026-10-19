from __future__ import annotations

import re
from typing import Any

from clinagent.schema import CheckType, Rule


TABLE_COLUMNS: dict[str, set[str]] = {
    "dm": {"SUBJID", "AGE", "SEX", "BMI", "RFSTDTC", "RFENDTC"},
    "ex": {"SUBJID", "EXTRT", "EXDOSE", "EXSTDTC", "EXENDTC"},
    "ae": {
        "SUBJID",
        "AETERM",
        "AESTDTC",
        "AEENDTC",
        "AESEV",
        "AESER",
        "AEREL",
        "AEACN",
        "AEOUT",
    },
    "lb": {"SUBJID", "LBTESTCD", "LBTEST", "LBORRES", "LBORRESU", "LBDTC"},
    "vs": {"SUBJID", "VSTESTCD", "VSORRES", "VSORRESU", "VSDTC"},
    "cm": {"SUBJID", "CMTRT", "CMSTDTC", "CMENDTC", "CMINDC"},
    "sv": {"SUBJID", "VISIT", "VISITNUM", "SVSTDTC"},
}

_ALLOWED_PARAMS: dict[CheckType, set[str]] = {
    CheckType.RANGE: {"min", "max", "filter"},
    CheckType.REQUIRED: set(),
    CheckType.DATE_ORDER: {"left_field", "op", "right"},
    CheckType.VISIT_WINDOW: {"visit", "anchor", "target_day", "minus", "plus"},
    CheckType.CONSISTENCY: {
        "if_field",
        "if_value",
        "then_field",
        "then_value",
        "then_in",
    },
    CheckType.CONMED_PROHIBITED: {"values"},
}


def _ident(name: str) -> str:
    if not isinstance(name, str) or not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*", name
    ):
        raise ValueError(f"invalid SQL identifier: {name!r}")
    return name


def _col(table: str, name: str) -> str:
    column = _ident(name).upper()
    if column not in TABLE_COLUMNS[table]:
        raise ValueError(
            f"column {column!r} is not allowed for table {table!r}"
        )
    return column


def _literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def _fmt_number(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _select(
    subject_expr: str,
    domain: str,
    field: str,
    expected: str,
    actual_expr: str,
    evidence_expr: str,
    from_clause: str,
    where_clause: str,
) -> str:
    return (
        "SELECT DISTINCT\n"
        f"  {subject_expr} AS subject_id,\n"
        f"  {_literal(domain)} AS domain,\n"
        f"  {_literal(field)} AS field,\n"
        f"  {_literal(expected)} AS expected,\n"
        f"  {actual_expr} AS actual,\n"
        f"  {evidence_expr} AS evidence\n"
        f"FROM {from_clause}\n"
        f"WHERE {where_clause}"
    )


def validate_rule(rule: Rule) -> None:
    table = rule.domain.lower()
    if table not in TABLE_COLUMNS:
        raise ValueError(f"unknown domain: {rule.domain!r}")
    if rule.field is not None:
        _col(table, rule.field)

    params = rule.params
    unknown = set(params) - _ALLOWED_PARAMS[rule.check_type]
    if unknown:
        raise ValueError(
            f"unsupported params for {rule.check_type.value}: {sorted(unknown)}"
        )

    if rule.check_type is CheckType.RANGE:
        if rule.field is None:
            raise ValueError("range rule requires a field")
        if params.get("min") is None and params.get("max") is None:
            raise ValueError("range rule requires min or max")
        for key, value in (params.get("filter") or {}).items():
            _col(table, key)
            if not isinstance(value, (str, int, float)):
                raise ValueError(f"invalid filter value for {key!r}")

    elif rule.check_type is CheckType.REQUIRED:
        if rule.field is None:
            raise ValueError("required rule requires a field")

    elif rule.check_type is CheckType.DATE_ORDER:
        _col(table, params["left_field"])
        if params["op"] not in {">=", "<=", ">", "<"}:
            raise ValueError(f"unsupported date operator: {params['op']!r}")
        right = params.get("right")
        if not isinstance(right, dict) or "source" not in right or "field" not in right:
            raise ValueError("date_order requires right.source and right.field")
        if right["source"] == "same":
            _col(table, right["field"])
        elif right["source"] == "dm":
            _col("dm", right["field"])
        else:
            raise ValueError(f"unsupported right.source: {right['source']!r}")

    elif rule.check_type is CheckType.VISIT_WINDOW:
        if table != "sv":
            raise ValueError("visit_window rules must use the SV domain")
        _col(table, "VISIT")
        _col(table, "SVSTDTC")
        if params.get("anchor") != "RFSTDTC":
            raise ValueError("only RFSTDTC is supported as visit anchor")
        _col("dm", "RFSTDTC")
        for key in ("target_day", "minus", "plus"):
            if not isinstance(params.get(key), (int, float)):
                raise ValueError(f"visit_window requires numeric {key}")
        if params["minus"] < 0 or params["plus"] < 0:
            raise ValueError("visit window bounds must be non-negative")

    elif rule.check_type is CheckType.CONSISTENCY:
        _col(table, params["if_field"])
        _col(table, params["then_field"])
        if "then_in" in params:
            values = params["then_in"]
            if not isinstance(values, list) or not values:
                raise ValueError("then_in must be a non-empty list")
        elif "then_value" not in params:
            raise ValueError("consistency rule requires then_value or then_in")

    elif rule.check_type is CheckType.CONMED_PROHIBITED:
        if rule.field is None:
            raise ValueError("conmed_prohibited rule requires a field")
        values = params.get("values")
        if not isinstance(values, list) or not values:
            raise ValueError("conmed_prohibited requires a non-empty values list")


def _compile_range(rule: Rule) -> str:
    table = rule.domain.lower()
    field = _col(table, rule.field or "")
    params = rule.params

    conditions: list[str] = []
    expected_parts: list[str] = []
    if params.get("min") is not None:
        conditions.append(
            f"TRY_CAST({field} AS DOUBLE) < {_literal(params['min'])}"
        )
        expected_parts.append(f">={_fmt_number(params['min'])}")
    if params.get("max") is not None:
        conditions.append(
            f"TRY_CAST({field} AS DOUBLE) > {_literal(params['max'])}"
        )
        expected_parts.append(f"<={_fmt_number(params['max'])}")

    where = "(" + " OR ".join(conditions) + ")"
    for key, value in (params.get("filter") or {}).items():
        where += f" AND {_col(table, key)} = {_literal(value)}"
    where += " AND SUBJID IS NOT NULL"

    actual = f"COALESCE(CAST({field} AS VARCHAR), 'NULL')"
    evidence = (
        f"{_literal(field + '=')} || COALESCE(CAST({field} AS VARCHAR), 'NULL')"
    )
    return _select(
        "SUBJID",
        rule.domain.upper(),
        field,
        " and ".join(expected_parts),
        actual,
        evidence,
        table,
        where,
    )


def _compile_required(rule: Rule) -> str:
    table = rule.domain.lower()
    field = _col(table, rule.field or "")
    where = f"({field} IS NULL OR TRIM(CAST({field} AS VARCHAR)) = '')"
    actual = f"COALESCE(CAST({field} AS VARCHAR), 'NULL')"
    evidence = (
        f"{_literal(field + '=')} || COALESCE(CAST({field} AS VARCHAR), 'NULL')"
    )
    return _select(
        "SUBJID",
        rule.domain.upper(),
        field,
        "非空",
        actual,
        evidence,
        table,
        where,
    )


def _compile_date_order(rule: Rule) -> str:
    table = rule.domain.lower()
    params = rule.params
    left = _col(table, params["left_field"])
    op = params["op"]
    violation = {">=": "<", "<=": ">", ">": "<=", "<": ">="}[op]
    right = params["right"]

    if right["source"] == "same":
        right_col = _col(table, right["field"])
        from_clause = table
        subject_expr = "SUBJID"
        left_expr = left
        right_expr = right_col
    else:
        right_col = _col("dm", right["field"])
        from_clause = f"{table} AS x JOIN dm AS d USING (SUBJID)"
        subject_expr = "x.SUBJID"
        left_expr = f"x.{left}"
        right_expr = f"d.{right_col}"

    where = (
        f"TRY_CAST({left_expr} AS DATE) {violation} "
        f"TRY_CAST({right_expr} AS DATE)"
        f" AND {left_expr} IS NOT NULL AND {right_expr} IS NOT NULL"
    )
    actual = (
        f"{_literal(left + '=')} || COALESCE(CAST({left_expr} AS VARCHAR), 'NULL')"
        f" || ', ' || {_literal(right_col + '=')}"
        f" || COALESCE(CAST({right_expr} AS VARCHAR), 'NULL')"
    )
    return _select(
        subject_expr,
        rule.domain.upper(),
        left,
        f"{left} {op} {right_col}",
        actual,
        actual,
        from_clause,
        where,
    )


def _compile_visit_window(rule: Rule) -> str:
    params = rule.params
    visit = params["visit"]
    target = params["target_day"]
    minus = params["minus"]
    plus = params["plus"]
    diff = (
        "date_diff('day', TRY_CAST(d.RFSTDTC AS DATE), "
        "TRY_CAST(x.SVSTDTC AS DATE))"
    )
    where = (
        f"x.VISIT = {_literal(visit)}"
        " AND x.SVSTDTC IS NOT NULL AND d.RFSTDTC IS NOT NULL"
        f" AND (({diff} - ({_literal(target)})) < {_literal(-minus)}"
        f" OR ({diff} - ({_literal(target)})) > {_literal(plus)})"
    )
    actual = f"'day ' || COALESCE(CAST({diff} AS VARCHAR), 'NULL')"
    evidence = (
        f"{_literal('VISIT=')} || COALESCE(CAST(x.VISIT AS VARCHAR), 'NULL')"
        f" || ', ' || {_literal('SVSTDTC=')}"
        " || COALESCE(CAST(x.SVSTDTC AS VARCHAR), 'NULL')"
        f" || ', ' || {_literal('RFSTDTC=')}"
        " || COALESCE(CAST(d.RFSTDTC AS VARCHAR), 'NULL')"
    )
    return _select(
        "x.SUBJID",
        "SV",
        "SVSTDTC",
        f"{visit} day {_fmt_number(target)} (-{_fmt_number(minus)}/+{_fmt_number(plus)})",
        actual,
        evidence,
        "sv AS x JOIN dm AS d USING (SUBJID)",
        where,
    )


def _compile_consistency(rule: Rule) -> str:
    table = rule.domain.lower()
    params = rule.params
    if_field = _col(table, params["if_field"])
    then_field = _col(table, params["then_field"])
    if_value = params["if_value"]
    where = f"{if_field} = {_literal(if_value)}"

    if "then_in" in params:
        values = params["then_in"]
        value_sql = ", ".join(_literal(value) for value in values)
        where += f" AND ({then_field} IS NULL OR {then_field} NOT IN ({value_sql}))"
        expected = (
            f"if {if_field}={if_value} then {then_field} in "
            f"[{', '.join(str(value) for value in values)}]"
        )
    else:
        then_value = params["then_value"]
        where += (
            f" AND ({then_field} IS NULL OR "
            f"{then_field} <> {_literal(then_value)})"
        )
        expected = (
            f"if {if_field}={if_value} then {then_field}={then_value}"
        )

    actual = (
        f"{_literal(if_field + '=')} || COALESCE(CAST({if_field} AS VARCHAR), 'NULL')"
        f" || ', ' || {_literal(then_field + '=')}"
        f" || COALESCE(CAST({then_field} AS VARCHAR), 'NULL')"
    )
    return _select(
        "SUBJID",
        rule.domain.upper(),
        then_field,
        expected,
        actual,
        actual,
        table,
        where,
    )


def _compile_conmed(rule: Rule) -> str:
    table = rule.domain.lower()
    field = _col(table, rule.field or "")
    values = rule.params["values"]
    value_sql = ", ".join(_literal(value) for value in values)
    where = f"{field} IN ({value_sql}) AND SUBJID IS NOT NULL"
    actual = f"COALESCE(CAST({field} AS VARCHAR), 'NULL')"
    evidence = (
        f"{_literal(field + '=')} || COALESCE(CAST({field} AS VARCHAR), 'NULL')"
    )
    return _select(
        "SUBJID",
        rule.domain.upper(),
        field,
        "not in [" + ", ".join(str(value) for value in values) + "]",
        actual,
        evidence,
        table,
        where,
    )


def compile_rule(rule: Rule) -> str:
    validate_rule(rule)
    if rule.check_type is CheckType.RANGE:
        return _compile_range(rule)
    if rule.check_type is CheckType.REQUIRED:
        return _compile_required(rule)
    if rule.check_type is CheckType.DATE_ORDER:
        return _compile_date_order(rule)
    if rule.check_type is CheckType.VISIT_WINDOW:
        return _compile_visit_window(rule)
    if rule.check_type is CheckType.CONSISTENCY:
        return _compile_consistency(rule)
    if rule.check_type is CheckType.CONMED_PROHIBITED:
        return _compile_conmed(rule)
    raise ValueError(f"unsupported check type: {rule.check_type!r}")
