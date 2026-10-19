# ClinAudit Agent — P0 评测报告

- 生成时间：2026-10-19T20:52:06
- 方案数：2
- 规则总数：66
- 受试者总数：50

## 总体指标

| 指标 | 值 |
|---|---|
| Precision | 1.0000 |
| Recall | 1.0000 |
| F1 | 1.0000 |
| TP / FP / FN | 68 / 0 / 0 |
| 干净数据误报 | 0 |

## 分方案结果

| 方案 | 规则数 | 受试者 | 注入异常 | 检出 | FP | FN | Precision | Recall | F1 | 干净数据误报 |
|---|---|---|---|---|---|---|---|---|---|---|
| TRIAL-001 | 33 | 25 | 34 | 34 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 0 |
| TRIAL-002 | 33 | 25 | 34 | 34 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 0 |

## TRIAL-001 分异常类型

| 异常类型 | 总数 | 检出 | Recall |
|---|---|---|---|
| AEENDTC_ORDER | 1 | 1 | 1.0000 |
| AESEV_REQUIRED | 1 | 1 | 1.0000 |
| AESTDTC_AFTER_DOSE | 1 | 1 | 1.0000 |
| AESTDTC_REQUIRED | 1 | 1 | 1.0000 |
| AETERM_REQUIRED | 1 | 1 | 1.0000 |
| AE_FATAL_SAE | 1 | 1 | 1.0000 |
| AE_SAE_SEVERITY | 1 | 1 | 1.0000 |
| AE_WITHDRAW_SAE | 1 | 1 | 1.0000 |
| AGE_RANGE | 2 | 2 | 1.0000 |
| AGE_REQUIRED | 1 | 1 | 1.0000 |
| ALT_RANGE | 1 | 1 | 1.0000 |
| BMI_RANGE | 1 | 1 | 1.0000 |
| BMI_REQUIRED | 1 | 1 | 1.0000 |
| CMSTDTC_REQUIRED | 1 | 1 | 1.0000 |
| CMTRT_REQUIRED | 1 | 1 | 1.0000 |
| CM_PROHIBITED | 1 | 1 | 1.0000 |
| CREA_RANGE | 1 | 1 | 1.0000 |
| DIABP_RANGE | 1 | 1 | 1.0000 |
| EXENDTC_ORDER | 1 | 1 | 1.0000 |
| EXSTDTC_REQUIRED | 1 | 1 | 1.0000 |
| EXTRT_REQUIRED | 1 | 1 | 1.0000 |
| HGB_RANGE | 1 | 1 | 1.0000 |
| LBORRES_REQUIRED | 1 | 1 | 1.0000 |
| RFSTDTC_REQUIRED | 1 | 1 | 1.0000 |
| SEX_REQUIRED | 1 | 1 | 1.0000 |
| SVSTDTC_REQUIRED | 1 | 1 | 1.0000 |
| SYSBP_RANGE | 1 | 1 | 1.0000 |
| VISIT_REQUIRED | 1 | 1 | 1.0000 |
| VISIT_V1_WINDOW | 1 | 1 | 1.0000 |
| VISIT_V2_WINDOW | 1 | 1 | 1.0000 |
| VISIT_V3_WINDOW | 1 | 1 | 1.0000 |
| VISIT_V4_WINDOW | 1 | 1 | 1.0000 |
| VSORRES_REQUIRED | 1 | 1 | 1.0000 |

## TRIAL-002 分异常类型

| 异常类型 | 总数 | 检出 | Recall |
|---|---|---|---|
| AEENDTC_ORDER | 1 | 1 | 1.0000 |
| AESEV_REQUIRED | 1 | 1 | 1.0000 |
| AESTDTC_AFTER_DOSE | 1 | 1 | 1.0000 |
| AESTDTC_REQUIRED | 1 | 1 | 1.0000 |
| AETERM_REQUIRED | 1 | 1 | 1.0000 |
| AE_FATAL_SAE | 1 | 1 | 1.0000 |
| AE_SAE_SEVERITY | 1 | 1 | 1.0000 |
| AE_WITHDRAW_SAE | 1 | 1 | 1.0000 |
| AGE_RANGE | 2 | 2 | 1.0000 |
| AGE_REQUIRED | 1 | 1 | 1.0000 |
| ALT_RANGE | 1 | 1 | 1.0000 |
| BMI_RANGE | 1 | 1 | 1.0000 |
| BMI_REQUIRED | 1 | 1 | 1.0000 |
| CMSTDTC_REQUIRED | 1 | 1 | 1.0000 |
| CMTRT_REQUIRED | 1 | 1 | 1.0000 |
| CM_PROHIBITED | 1 | 1 | 1.0000 |
| CREA_RANGE | 1 | 1 | 1.0000 |
| DIABP_RANGE | 1 | 1 | 1.0000 |
| EXENDTC_ORDER | 1 | 1 | 1.0000 |
| EXSTDTC_REQUIRED | 1 | 1 | 1.0000 |
| EXTRT_REQUIRED | 1 | 1 | 1.0000 |
| HGB_RANGE | 1 | 1 | 1.0000 |
| LBORRES_REQUIRED | 1 | 1 | 1.0000 |
| RFSTDTC_REQUIRED | 1 | 1 | 1.0000 |
| SEX_REQUIRED | 1 | 1 | 1.0000 |
| SVSTDTC_REQUIRED | 1 | 1 | 1.0000 |
| SYSBP_RANGE | 1 | 1 | 1.0000 |
| VISIT_REQUIRED | 1 | 1 | 1.0000 |
| VISIT_V1_WINDOW | 1 | 1 | 1.0000 |
| VISIT_V2_WINDOW | 1 | 1 | 1.0000 |
| VISIT_V3_WINDOW | 1 | 1 | 1.0000 |
| VISIT_V4_WINDOW | 1 | 1 | 1.0000 |
| VSORRES_REQUIRED | 1 | 1 | 1.0000 |

## 说明

- P0 使用方案生成器内置的 gold rules，目标是验证规则编译、SQL 执行、异常注入和评测闭环。
- 这里的 100% 左右指标不代表大模型抽取效果；LLM 规则抽取的 Precision/Recall F1 将在 P1 单独报告。
- 干净数据误报为 0 是规则引擎正确性的前置条件。
- 所有数据均为合成数据，不含任何真实患者信息。
