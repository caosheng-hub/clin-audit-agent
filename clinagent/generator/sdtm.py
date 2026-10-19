from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from clinagent.generator.protocol import Trial


DOMAIN_COLUMNS: dict[str, list[str]] = {
    "dm": ["SUBJID", "AGE", "SEX", "BMI", "RFSTDTC", "RFENDTC"],
    "ex": ["SUBJID", "EXTRT", "EXDOSE", "EXSTDTC", "EXENDTC"],
    "ae": [
        "SUBJID",
        "AETERM",
        "AESTDTC",
        "AEENDTC",
        "AESEV",
        "AESER",
        "AEREL",
        "AEACN",
        "AEOUT",
    ],
    "lb": ["SUBJID", "LBTESTCD", "LBTEST", "LBORRES", "LBORRESU", "LBDTC"],
    "vs": ["SUBJID", "VSTESTCD", "VSORRES", "VSORRESU", "VSDTC"],
    "cm": ["SUBJID", "CMTRT", "CMSTDTC", "CMENDTC", "CMINDC"],
    "sv": ["SUBJID", "VISIT", "VISITNUM", "SVSTDTC"],
}

COMMON_CM = ["阿司匹林", "二甲双胍", "氨氯地平", "辛伐他汀", "奥美拉唑"]
AE_TERMS = ["头痛", "恶心", "皮疹", "乏力", "腹泻", "发热", "咳嗽", "转氨酶升高"]


def _iso(value: date) -> str:
    return value.isoformat()


def generate_clean_data(
    trial: Trial, n_subjects: int, rng: random.Random
) -> dict[str, list[dict[str, str]]]:
    data: dict[str, list[dict[str, str]]] = {
        domain: [] for domain in DOMAIN_COLUMNS
    }
    base = date(2025, 1, 6)
    allowed_cm = [name for name in COMMON_CM if name not in trial.prohibited_cm]

    for number in range(1, n_subjects + 1):
        subject_id = f"S{number:03d}"
        first_dose = base + timedelta(days=rng.randint(0, 150))
        last_dose = first_dose + timedelta(days=56 + rng.randint(0, 5))
        age = rng.randint(trial.age_min, trial.age_max)
        bmi = round(rng.uniform(trial.bmi_min + 0.5, 29.5), 1)
        sex = rng.choice(["M", "F"])

        data["dm"].append(
            {
                "SUBJID": subject_id,
                "AGE": str(age),
                "SEX": sex,
                "BMI": str(bmi),
                "RFSTDTC": _iso(first_dose),
                "RFENDTC": _iso(last_dose),
            }
        )
        data["ex"].append(
            {
                "SUBJID": subject_id,
                "EXTRT": "研究药物 A",
                "EXDOSE": "100",
                "EXSTDTC": _iso(first_dose),
                "EXENDTC": _iso(last_dose),
            }
        )

        for visit in trial.visits:
            offset = visit.day + rng.randint(-visit.window, visit.window)
            visit_date = first_dose + timedelta(days=offset)
            data["sv"].append(
                {
                    "SUBJID": subject_id,
                    "VISIT": visit.code,
                    "VISITNUM": str(int(visit.code[1:])),
                    "SVSTDTC": _iso(visit_date),
                }
            )

            alt = rng.randint(10, int(trial.alt_max) - 10)
            hgb = rng.randint(int(trial.hgb_min) + 5, 160)
            crea = rng.randint(50, int(trial.creat_max) - 10)
            for test_code, test_name, result, unit in [
                ("ALT", "丙氨酸氨基转移酶", alt, "U/L"),
                ("HGB", "血红蛋白", hgb, "g/L"),
                ("CREA", "肌酐", crea, "μmol/L"),
            ]:
                data["lb"].append(
                    {
                        "SUBJID": subject_id,
                        "LBTESTCD": test_code,
                        "LBTEST": test_name,
                        "LBORRES": str(result),
                        "LBORRESU": unit,
                        "LBDTC": _iso(visit_date),
                    }
                )

            sysbp = rng.randint(trial.sysbp_min, trial.sysbp_max)
            diabp = rng.randint(trial.diabp_min, trial.diabp_max)
            for test_code, result in [("SYSBP", sysbp), ("DIABP", diabp)]:
                data["vs"].append(
                    {
                        "SUBJID": subject_id,
                        "VSTESTCD": test_code,
                        "VSORRES": str(result),
                        "VSORRESU": "mmHg",
                        "VSDTC": _iso(visit_date),
                    }
                )

        for _ in range(rng.randint(1, 3)):
            start = first_dose + timedelta(days=rng.randint(0, 40))
            end = start + timedelta(days=rng.randint(1, 15))
            severity = rng.choice(
                ["MILD", "MODERATE", "SEVERE", "LIFE-THREATENING"]
            )
            serious = "N"
            if severity in {"SEVERE", "LIFE-THREATENING"}:
                serious = rng.choice(["Y", "N"])

            outcome = rng.choice(
                ["RECOVERED", "RECOVERING", "NOT RECOVERED", "FATAL"]
            )
            if outcome == "FATAL":
                serious = "Y"
                severity = rng.choice(["SEVERE", "LIFE-THREATENING"])

            action = rng.choice(
                ["NONE", "DOSE REDUCED", "DOSE INTERRUPTED", "DRUG WITHDRAWN"]
            )
            if action == "DRUG WITHDRAWN":
                serious = "Y"
                if severity not in {"SEVERE", "LIFE-THREATENING"}:
                    severity = "SEVERE"

            if serious == "Y" and severity not in {
                "SEVERE",
                "LIFE-THREATENING",
            }:
                severity = "SEVERE"

            data["ae"].append(
                {
                    "SUBJID": subject_id,
                    "AETERM": rng.choice(AE_TERMS),
                    "AESTDTC": _iso(start),
                    "AEENDTC": _iso(end),
                    "AESEV": severity,
                    "AESER": serious,
                    "AEREL": rng.choice(
                        ["RELATED", "NOT RELATED", "POSSIBLY RELATED"]
                    ),
                    "AEACN": action,
                    "AEOUT": outcome,
                }
            )

        for _ in range(rng.randint(1, 3)):
            cm_start = first_dose + timedelta(days=rng.randint(-10, 30))
            cm_end = cm_start + timedelta(days=rng.randint(1, 30))
            data["cm"].append(
                {
                    "SUBJID": subject_id,
                    "CMTRT": rng.choice(allowed_cm),
                    "CMSTDTC": _iso(cm_start),
                    "CMENDTC": _iso(cm_end),
                    "CMINDC": "合并疾病",
                }
            )

    return data


def write_domain_csvs(
    data: dict[str, list[dict[str, str]]], out_dir: Path
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for domain, columns in DOMAIN_COLUMNS.items():
        path = out_dir / f"{domain}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for row in data[domain]:
                writer.writerow({column: row.get(column, "") for column in columns})
