from __future__ import annotations

import copy
import random
from datetime import date, timedelta

from clinagent.generator.protocol import Trial
from clinagent.schema import GroundTruthAnomaly


def inject_anomalies(
    trial: Trial,
    clean: dict[str, list[dict[str, str]]],
    rng: random.Random,
) -> tuple[dict[str, list[dict[str, str]]], list[GroundTruthAnomaly]]:
    data = copy.deepcopy(clean)
    truth: list[GroundTruthAnomaly] = []

    def dm_row(subject_id: str) -> dict[str, str]:
        return next(row for row in data["dm"] if row["SUBJID"] == subject_id)

    def ae_row(subject_id: str) -> dict[str, str]:
        rows = [row for row in data["ae"] if row["SUBJID"] == subject_id]
        return rows[rng.randrange(len(rows))]

    def lb_row(subject_id: str, test_code: str) -> dict[str, str]:
        return next(
            row
            for row in data["lb"]
            if row["SUBJID"] == subject_id and row["LBTESTCD"] == test_code
        )

    def vs_row(subject_id: str, test_code: str) -> dict[str, str]:
        return next(
            row
            for row in data["vs"]
            if row["SUBJID"] == subject_id and row["VSTESTCD"] == test_code
        )

    def cm_row(subject_id: str) -> dict[str, str]:
        return next(row for row in data["cm"] if row["SUBJID"] == subject_id)

    def ex_row(subject_id: str) -> dict[str, str]:
        return next(row for row in data["ex"] if row["SUBJID"] == subject_id)

    def sv_row(subject_id: str, visit: str) -> dict[str, str]:
        return next(
            row
            for row in data["sv"]
            if row["SUBJID"] == subject_id and row["VISIT"] == visit
        )

    def record(
        code: str,
        subject_id: str,
        expected: str,
        actual: str,
    ) -> None:
        rule = trial.rule_by_code(code)
        truth.append(
            GroundTruthAnomaly(
                anomaly_id=f"{rule.rule_id}:{subject_id}:{len(truth) + 1:02d}",
                subject_id=subject_id,
                rule_id=rule.rule_id,
                domain=rule.domain,
                field=rule.field,
                expected=expected,
                actual=actual,
                severity=rule.severity,
                anomaly_type=code,
            )
        )

    def safe_ae(row: dict[str, str]) -> dict[str, str]:
        first_dose = dm_row(row["SUBJID"])["RFSTDTC"]
        row.update(
            {
                "AETERM": "头痛",
                "AESTDTC": first_dose,
                "AEENDTC": first_dose,
                "AESEV": "MILD",
                "AESER": "N",
                "AEREL": "NOT RELATED",
                "AEACN": "NONE",
                "AEOUT": "RECOVERED",
            }
        )
        return row

    def first_dose_date(subject_id: str) -> date:
        return date.fromisoformat(dm_row(subject_id)["RFSTDTC"])

    # Eligibility and required demographics.
    row = dm_row("S001")
    row["AGE"] = str(trial.age_min - 1)
    record("AGE_RANGE", "S001", f"{trial.age_min}~{trial.age_max}", row["AGE"])

    row = dm_row("S002")
    row["AGE"] = str(trial.age_max + 1)
    record("AGE_RANGE", "S002", f"{trial.age_min}~{trial.age_max}", row["AGE"])

    row = dm_row("S003")
    row["BMI"] = str(trial.bmi_min - 1)
    record("BMI_RANGE", "S003", f">={trial.bmi_min:g}", row["BMI"])

    row = dm_row("S004")
    row["AGE"] = ""
    record("AGE_REQUIRED", "S004", "非空", "NULL/empty")

    row = dm_row("S005")
    row["BMI"] = ""
    record("BMI_REQUIRED", "S005", "非空", "NULL/empty")

    row = dm_row("S006")
    row["SEX"] = ""
    record("SEX_REQUIRED", "S006", "非空", "NULL/empty")

    row = dm_row("S007")
    row["RFSTDTC"] = ""
    record("RFSTDTC_REQUIRED", "S007", "非空", "NULL/empty")

    # Visit windows.
    for subject_id, visit_code, offset in [
        ("S008", "V1", -2),
        ("S009", "V2", 22),
        ("S010", "V3", 20),
        ("S011", "V4", 67),
    ]:
        visit = next(v for v in trial.visits if v.code == visit_code)
        row = sv_row(subject_id, visit_code)
        row["SVSTDTC"] = (
            first_dose_date(subject_id) + timedelta(days=offset)
        ).isoformat()
        record(
            f"VISIT_{visit_code}_WINDOW",
            subject_id,
            f"{visit_code} day {visit.day} (±{visit.window})",
            f"day {offset}",
        )

    # Vital signs.
    row = vs_row("S012", "SYSBP")
    row["VSORRES"] = str(trial.sysbp_max + 10)
    record(
        "SYSBP_RANGE",
        "S012",
        f"{trial.sysbp_min}~{trial.sysbp_max}",
        row["VSORRES"],
    )

    row = vs_row("S013", "DIABP")
    row["VSORRES"] = str(trial.diabp_min - 10)
    record(
        "DIABP_RANGE",
        "S013",
        f"{trial.diabp_min}~{trial.diabp_max}",
        row["VSORRES"],
    )

    row = vs_row("S014", "SYSBP")
    row["VSORRES"] = ""
    record("VSORRES_REQUIRED", "S014", "非空", "NULL/empty")

    # Adverse events.
    row = safe_ae(ae_row("S015"))
    row["AESEV"] = ""
    record("AESEV_REQUIRED", "S015", "非空", "NULL/empty")

    row = safe_ae(ae_row("S016"))
    row["AETERM"] = ""
    record("AETERM_REQUIRED", "S016", "非空", "NULL/empty")

    row = safe_ae(ae_row("S017"))
    row["AESTDTC"] = ""
    record("AESTDTC_REQUIRED", "S017", "非空", "NULL/empty")

    row = safe_ae(ae_row("S018"))
    first_dose = first_dose_date("S018")
    row["AESTDTC"] = (first_dose - timedelta(days=5)).isoformat()
    row["AEENDTC"] = (first_dose + timedelta(days=5)).isoformat()
    record(
        "AESTDTC_AFTER_DOSE",
        "S018",
        "AESTDTC >= RFSTDTC",
        f"AESTDTC={row['AESTDTC']}, RFSTDTC={first_dose.isoformat()}",
    )

    row = safe_ae(ae_row("S019"))
    start = first_dose_date("S019") + timedelta(days=5)
    row["AESTDTC"] = start.isoformat()
    row["AEENDTC"] = (start - timedelta(days=2)).isoformat()
    record(
        "AEENDTC_ORDER",
        "S019",
        "AEENDTC >= AESTDTC",
        f"AESTDTC={row['AESTDTC']}, AEENDTC={row['AEENDTC']}",
    )

    row = safe_ae(ae_row("S020"))
    row["AEACN"] = "DRUG WITHDRAWN"
    row["AESER"] = "N"
    row["AESEV"] = "MILD"
    row["AEOUT"] = "RECOVERED"
    record(
        "AE_WITHDRAW_SAE",
        "S020",
        "AEACN=DRUG WITHDRAWN -> AESER=Y",
        f"AEACN={row['AEACN']}, AESER={row['AESER']}",
    )

    row = safe_ae(ae_row("S021"))
    row["AESER"] = "Y"
    row["AESEV"] = "MILD"
    row["AEACN"] = "NONE"
    row["AEOUT"] = "RECOVERED"
    record(
        "AE_SAE_SEVERITY",
        "S021",
        "AESER=Y -> AESEV in (SEVERE, LIFE-THREATENING)",
        f"AESER={row['AESER']}, AESEV={row['AESEV']}",
    )

    row = safe_ae(ae_row("S022"))
    row["AEOUT"] = "FATAL"
    row["AESER"] = "N"
    row["AESEV"] = "MILD"
    row["AEACN"] = "NONE"
    record(
        "AE_FATAL_SAE",
        "S022",
        "AEOUT=FATAL -> AESER=Y",
        f"AEOUT={row['AEOUT']}, AESER={row['AESER']}",
    )

    # Laboratory values.
    row = lb_row("S023", "ALT")
    row["LBORRES"] = str(int(trial.alt_max) + 20)
    record("ALT_RANGE", "S023", f"<={trial.alt_max:g}", row["LBORRES"])

    row = lb_row("S024", "HGB")
    row["LBORRES"] = str(int(trial.hgb_min) - 10)
    record("HGB_RANGE", "S024", f">={trial.hgb_min:g}", row["LBORRES"])

    row = lb_row("S025", "CREA")
    row["LBORRES"] = str(int(trial.creat_max) + 20)
    record("CREA_RANGE", "S025", f"<={trial.creat_max:g}", row["LBORRES"])

    row = lb_row("S001", "CREA")
    row["LBORRES"] = ""
    record("LBORRES_REQUIRED", "S001", "非空", "NULL/empty")

    # Concomitant medication.
    prohibited = trial.prohibited_cm[0]
    first_dose = first_dose_date("S002")
    data["cm"].append(
        {
            "SUBJID": "S002",
            "CMTRT": prohibited,
            "CMSTDTC": first_dose.isoformat(),
            "CMENDTC": (first_dose + timedelta(days=10)).isoformat(),
            "CMINDC": "合并疾病",
        }
    )
    record("CM_PROHIBITED", "S002", "不在禁用清单", prohibited)

    row = cm_row("S003")
    row["CMTRT"] = ""
    record("CMTRT_REQUIRED", "S003", "非空", "NULL/empty")

    row = cm_row("S004")
    row["CMSTDTC"] = ""
    record("CMSTDTC_REQUIRED", "S004", "非空", "NULL/empty")

    # Exposure.
    row = ex_row("S005")
    row["EXTRT"] = ""
    record("EXTRT_REQUIRED", "S005", "非空", "NULL/empty")

    row = ex_row("S006")
    row["EXSTDTC"] = ""
    record("EXSTDTC_REQUIRED", "S006", "非空", "NULL/empty")

    row = ex_row("S008")
    row["EXENDTC"] = (
        date.fromisoformat(row["EXSTDTC"]) - timedelta(days=2)
    ).isoformat()
    record(
        "EXENDTC_ORDER",
        "S008",
        "EXENDTC >= EXSTDTC",
        f"EXSTDTC={row['EXSTDTC']}, EXENDTC={row['EXENDTC']}",
    )

    # Visit-level required fields.
    row = sv_row("S012", "V4")
    row["SVSTDTC"] = ""
    record("SVSTDTC_REQUIRED", "S012", "非空", "NULL/empty")

    row = sv_row("S013", "V4")
    row["VISIT"] = ""
    record("VISIT_REQUIRED", "S013", "非空", "NULL/empty")

    return data, truth
