from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from clinagent.schema import CheckType, Rule, Severity


INDICATIONS = [
    "2 型糖尿病",
    "非小细胞肺癌",
    "类风湿关节炎",
    "高血压",
    "慢性肾脏病",
    "溃疡性结肠炎",
]


@dataclass(frozen=True)
class Visit:
    code: str
    name: str
    day: int
    window: int


@dataclass
class Clause:
    section_id: str
    section_title: str
    text: str
    rule: Rule | None = None


@dataclass
class Trial:
    trial_id: str
    title: str
    indication: str
    phase: str
    age_min: int
    age_max: int
    bmi_min: float
    alt_max: float
    hgb_min: float
    creat_max: float
    sysbp_min: int
    sysbp_max: int
    diabp_min: int
    diabp_max: int
    visits: list[Visit]
    prohibited_cm: list[str]
    clauses: list[Clause]

    @property
    def rules(self) -> list[Rule]:
        return [clause.rule for clause in self.clauses if clause.rule is not None]

    def rule_by_code(self, code: str) -> Rule:
        for rule in self.rules:
            if rule.code == code:
                return rule
        raise KeyError(f"rule code not found in {self.trial_id}: {code}")


def build_trial(index: int) -> Trial:
    rng = random.Random(4200 + index)
    trial_id = f"TRIAL-{index:03d}"
    indication = INDICATIONS[(index - 1) % len(INDICATIONS)]
    phase = rng.choice(["II", "III"])
    age_min = 18
    age_max = rng.choice([70, 75, 80])
    bmi_min = rng.choice([18.0, 18.5, 19.0])
    alt_max = rng.choice([100.0, 120.0, 150.0])
    hgb_min = rng.choice([90.0, 100.0, 110.0])
    creat_max = rng.choice([133.0, 150.0])
    sysbp_min, sysbp_max = 90, 160
    diabp_min, diabp_max = 50, 100
    visits = [
        Visit("V1", "筛选期", -7, 2),
        Visit("V2", "第 2 次访视", 14, 3),
        Visit("V3", "第 3 次访视", 28, 3),
        Visit("V4", "研究结束访视", 56, 5),
    ]
    prohibited_cm = rng.choice(
        [["华法林"], ["利伐沙班"], ["华法林", "利伐沙班"]]
    )
    title = (
        f"{indication}受试者中评估研究药物安全性及有效性的"
        f"随机、双盲、安慰剂对照 {phase} 期临床研究"
    )

    clauses: list[Clause] = []
    counter = 0

    def add(
        section_id: str,
        section_title: str,
        text: str,
        *,
        domain: str | None = None,
        field: str | None = None,
        check_type: CheckType | None = None,
        params: dict[str, Any] | None = None,
        severity: Severity = Severity.MAJOR,
        code: str | None = None,
    ) -> None:
        nonlocal counter
        rule = None
        if check_type is not None:
            if not domain or not code:
                raise ValueError("domain and code are required when creating a rule")
            counter += 1
            rule = Rule(
                rule_id=f"{trial_id}-{code}-{counter:02d}",
                trial_id=trial_id,
                code=code,
                domain=domain,
                field=field,
                check_type=check_type,
                params=params or {},
                severity=severity,
                description=text,
                section_id=section_id,
                section_title=section_title,
                quote=text,
            )
        clauses.append(Clause(section_id, section_title, text, rule))

    add("1.1", "研究目的", "评价研究药物在目标适应症受试者中的安全性和耐受性。")
    add(
        "2.1",
        "研究设计",
        "本研究采用随机、双盲、安慰剂对照设计，计划入组约 200 例受试者。",
    )

    add(
        "3.1",
        "入选标准",
        f"年龄在 {age_min} 至 {age_max} 周岁之间（含边界）。",
        domain="DM",
        field="AGE",
        check_type=CheckType.RANGE,
        params={"min": age_min, "max": age_max},
        severity=Severity.CRITICAL,
        code="AGE_RANGE",
    )
    add(
        "3.1",
        "入选标准",
        f"筛选时体质指数（BMI）不得低于 {bmi_min:g} kg/m²。",
        domain="DM",
        field="BMI",
        check_type=CheckType.RANGE,
        params={"min": bmi_min},
        severity=Severity.CRITICAL,
        code="BMI_RANGE",
    )
    add("3.1", "入选标准", "受试者已签署知情同意书。")
    add(
        "3.1",
        "入选标准",
        "年龄（AGE）为必填字段。",
        domain="DM",
        field="AGE",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="AGE_REQUIRED",
    )
    add(
        "3.1",
        "入选标准",
        "体质指数（BMI）为必填字段。",
        domain="DM",
        field="BMI",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="BMI_REQUIRED",
    )
    add(
        "3.1",
        "入选标准",
        "受试者性别（SEX）为必填字段。",
        domain="DM",
        field="SEX",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="SEX_REQUIRED",
    )
    add(
        "3.1",
        "入选标准",
        "首次给药日期（RFSTDTC）为必填字段。",
        domain="DM",
        field="RFSTDTC",
        check_type=CheckType.REQUIRED,
        severity=Severity.CRITICAL,
        code="RFSTDTC_REQUIRED",
    )
    add("3.2", "排除标准", "已知对研究药物或其辅料过敏者不得入选。")

    for visit in visits:
        if visit.day < 0:
            text = (
                f"访视 {visit.code}（{visit.name}）计划于首次给药前第 "
                f"{abs(visit.day)} 天进行，允许窗口为 ±{visit.window} 天。"
            )
        else:
            text = (
                f"访视 {visit.code}（{visit.name}）计划于首次给药后第 "
                f"{visit.day} 天进行，允许窗口为 ±{visit.window} 天。"
            )
        add(
            "4.1",
            "访视计划",
            text,
            domain="SV",
            field="SVSTDTC",
            check_type=CheckType.VISIT_WINDOW,
            params={
                "visit": visit.code,
                "anchor": "RFSTDTC",
                "target_day": visit.day,
                "minus": visit.window,
                "plus": visit.window,
            },
            severity=Severity.MAJOR,
            code=f"VISIT_{visit.code}_WINDOW",
        )

    add(
        "5.1",
        "生命体征",
        f"收缩压（SYSBP）应在 {sysbp_min} 至 {sysbp_max} mmHg 之间。",
        domain="VS",
        field="VSORRES",
        check_type=CheckType.RANGE,
        params={"filter": {"VSTESTCD": "SYSBP"}, "min": sysbp_min, "max": sysbp_max},
        severity=Severity.MAJOR,
        code="SYSBP_RANGE",
    )
    add(
        "5.1",
        "生命体征",
        f"舒张压（DIABP）应在 {diabp_min} 至 {diabp_max} mmHg 之间。",
        domain="VS",
        field="VSORRES",
        check_type=CheckType.RANGE,
        params={"filter": {"VSTESTCD": "DIABP"}, "min": diabp_min, "max": diabp_max},
        severity=Severity.MAJOR,
        code="DIABP_RANGE",
    )
    add(
        "5.1",
        "生命体征",
        "生命体征结果（VSORRES）为必填字段。",
        domain="VS",
        field="VSORRES",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="VSORRES_REQUIRED",
    )

    add(
        "6.1",
        "不良事件",
        "所有不良事件必须记录严重程度（AESEV），该字段不得为空。",
        domain="AE",
        field="AESEV",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="AESEV_REQUIRED",
    )
    add(
        "6.1",
        "不良事件",
        "不良事件名称（AETERM）为必填字段。",
        domain="AE",
        field="AETERM",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="AETERM_REQUIRED",
    )
    add(
        "6.1",
        "不良事件",
        "不良事件开始日期（AESTDTC）为必填字段。",
        domain="AE",
        field="AESTDTC",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="AESTDTC_REQUIRED",
    )
    add(
        "6.1",
        "不良事件",
        "不良事件开始日期（AESTDTC）不得早于首次给药日期（RFSTDTC）。",
        domain="AE",
        field="AESTDTC",
        check_type=CheckType.DATE_ORDER,
        params={
            "left_field": "AESTDTC",
            "op": ">=",
            "right": {"source": "dm", "field": "RFSTDTC"},
        },
        severity=Severity.MAJOR,
        code="AESTDTC_AFTER_DOSE",
    )
    add(
        "6.1",
        "不良事件",
        "不良事件结束日期（AEENDTC）不得早于开始日期（AESTDTC）。",
        domain="AE",
        field="AEENDTC",
        check_type=CheckType.DATE_ORDER,
        params={
            "left_field": "AEENDTC",
            "op": ">=",
            "right": {"source": "same", "field": "AESTDTC"},
        },
        severity=Severity.MAJOR,
        code="AEENDTC_ORDER",
    )
    add(
        "6.1",
        "不良事件",
        "若不良事件导致研究药物永久停用（AEACN 为 DRUG WITHDRAWN），"
        "则必须标记为严重不良事件（AESER 为 Y）。",
        domain="AE",
        field="AESER",
        check_type=CheckType.CONSISTENCY,
        params={
            "if_field": "AEACN",
            "if_value": "DRUG WITHDRAWN",
            "then_field": "AESER",
            "then_value": "Y",
        },
        severity=Severity.CRITICAL,
        code="AE_WITHDRAW_SAE",
    )
    add(
        "6.1",
        "不良事件",
        "若不良事件被标记为严重不良事件（AESER 为 Y），则严重程度（AESEV）"
        "必须为 SEVERE 或 LIFE-THREATENING。",
        domain="AE",
        field="AESEV",
        check_type=CheckType.CONSISTENCY,
        params={
            "if_field": "AESER",
            "if_value": "Y",
            "then_field": "AESEV",
            "then_in": ["SEVERE", "LIFE-THREATENING"],
        },
        severity=Severity.CRITICAL,
        code="AE_SAE_SEVERITY",
    )
    add(
        "6.1",
        "不良事件",
        "若不良事件转归为死亡（AEOUT 为 FATAL），则必须标记为严重不良事件（AESER 为 Y）。",
        domain="AE",
        field="AESER",
        check_type=CheckType.CONSISTENCY,
        params={
            "if_field": "AEOUT",
            "if_value": "FATAL",
            "then_field": "AESER",
            "then_value": "Y",
        },
        severity=Severity.CRITICAL,
        code="AE_FATAL_SAE",
    )

    add(
        "6.2",
        "实验室检查",
        f"丙氨酸氨基转移酶（ALT）检测值不得超过 {alt_max:g} U/L。",
        domain="LB",
        field="LBORRES",
        check_type=CheckType.RANGE,
        params={"filter": {"LBTESTCD": "ALT"}, "max": alt_max},
        severity=Severity.MAJOR,
        code="ALT_RANGE",
    )
    add(
        "6.2",
        "实验室检查",
        f"血红蛋白（HGB）检测值不得低于 {hgb_min:g} g/L。",
        domain="LB",
        field="LBORRES",
        check_type=CheckType.RANGE,
        params={"filter": {"LBTESTCD": "HGB"}, "min": hgb_min},
        severity=Severity.MAJOR,
        code="HGB_RANGE",
    )
    add(
        "6.2",
        "实验室检查",
        f"肌酐（CREA）检测值不得超过 {creat_max:g} μmol/L。",
        domain="LB",
        field="LBORRES",
        check_type=CheckType.RANGE,
        params={"filter": {"LBTESTCD": "CREA"}, "max": creat_max},
        severity=Severity.MAJOR,
        code="CREA_RANGE",
    )
    add(
        "6.2",
        "实验室检查",
        "实验室检查结果（LBORRES）为必填字段。",
        domain="LB",
        field="LBORRES",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="LBORRES_REQUIRED",
    )

    prohibited_text = "、".join(prohibited_cm)
    add(
        "6.3",
        "合并用药",
        f"研究期间禁止合并使用以下药物：{prohibited_text}。",
        domain="CM",
        field="CMTRT",
        check_type=CheckType.CONMED_PROHIBITED,
        params={"values": prohibited_cm},
        severity=Severity.CRITICAL,
        code="CM_PROHIBITED",
    )
    add(
        "6.3",
        "合并用药",
        "合并用药名称（CMTRT）为必填字段。",
        domain="CM",
        field="CMTRT",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="CMTRT_REQUIRED",
    )
    add(
        "6.3",
        "合并用药",
        "合并用药开始日期（CMSTDTC）为必填字段。",
        domain="CM",
        field="CMSTDTC",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="CMSTDTC_REQUIRED",
    )

    add(
        "7.1",
        "数据管理",
        "访视日期（SVSTDTC）为必填字段。",
        domain="SV",
        field="SVSTDTC",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="SVSTDTC_REQUIRED",
    )
    add(
        "7.1",
        "数据管理",
        "访视名称（VISIT）为必填字段。",
        domain="SV",
        field="VISIT",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="VISIT_REQUIRED",
    )

    add(
        "7.2",
        "给药记录",
        "研究药物名称（EXTRT）为必填字段。",
        domain="EX",
        field="EXTRT",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="EXTRT_REQUIRED",
    )
    add(
        "7.2",
        "给药记录",
        "研究药物首次给药日期（EXSTDTC）为必填字段。",
        domain="EX",
        field="EXSTDTC",
        check_type=CheckType.REQUIRED,
        severity=Severity.MAJOR,
        code="EXSTDTC_REQUIRED",
    )
    add(
        "7.2",
        "给药记录",
        "研究药物给药结束日期（EXENDTC）不得早于开始日期（EXSTDTC）。",
        domain="EX",
        field="EXENDTC",
        check_type=CheckType.DATE_ORDER,
        params={
            "left_field": "EXENDTC",
            "op": ">=",
            "right": {"source": "same", "field": "EXSTDTC"},
        },
        severity=Severity.MAJOR,
        code="EXENDTC_ORDER",
    )

    return Trial(
        trial_id=trial_id,
        title=title,
        indication=indication,
        phase=phase,
        age_min=age_min,
        age_max=age_max,
        bmi_min=bmi_min,
        alt_max=alt_max,
        hgb_min=hgb_min,
        creat_max=creat_max,
        sysbp_min=sysbp_min,
        sysbp_max=sysbp_max,
        diabp_min=diabp_min,
        diabp_max=diabp_max,
        visits=visits,
        prohibited_cm=prohibited_cm,
        clauses=clauses,
    )


def render_protocol(trial: Trial) -> str:
    lines = [
        f"# {trial.title}",
        "",
        f"**方案编号：** {trial.trial_id}",
        f"**适应症：** {trial.indication}",
        f"**研究分期：** {trial.phase} 期",
        "",
        "> 本文件为合成数据，仅用于方法验证，不含任何真实患者信息。",
        "",
    ]
    current_section: str | None = None
    for clause in trial.clauses:
        if clause.section_id != current_section:
            lines.extend(
                ["", f"## {clause.section_id} {clause.section_title}", ""]
            )
            current_section = clause.section_id
        lines.append(f"- {clause.text}")
    return "\n".join(lines).rstrip() + "\n"
