# R2 — Retrospective Validation

## Цель

Ретроспективная валидация HEALTH_ID против **независимого** reference standard с temporal split и group holdout по работнику.

## Реализация в репозитории

| Компонент | Путь |
|-----------|------|
| Cohort loader | `src/ukz16/validation/r2/cohort.py` |
| Splits | `src/ukz16/validation/r2/splits.py` |
| Metrics | `src/ukz16/validation/r2/metrics.py` |
| Runner | `src/ukz16/validation/r2/runner.py` |
| CLI | `ukz16-r2` |
| Synthetic cohort (no PHI) | `samples/validation/r2_synthetic_cohort.jsonl` |

## Формат когорты (JSONL)

Каждая строка:

```json
{
  "row_id": "...",
  "payload": { "...PrMOIngest..." },
  "reference": { "label": 0, "source": "independent_adjudication_v1" },
  "subgroup": { "site_id": "SITE-A", "sex": "F" }
}
```

`reference.label` — независимая метка 0/1. Нельзя строить label из той же формулы HEALTH_ID.

## Запуск

```bash
python scripts/generate_r2_synthetic_cohort.py
ukz16-r2 --cohort samples/validation/r2_synthetic_cohort.jsonl --out reports/r2_synthetic --split both
```

Отчёты: `reports/r2_synthetic/r2_report.json`, `r2_report.md`.

## Метрики

- Brier + bootstrap 95% CI
- ECE (calibration bins)
- Confusion / FN at pre-set threshold
- Abstention rate (`health_id.value is null`)
- Subgroup slices: site_id, sex
- Guards: no worker overlap train/test; no auto model update

## Шлюз перехода

R2 **не считается пройденным** на synthetic cohort. Для claim нужны:

1. Независимый clinical reference / adjudication
2. Pre-registered thresholds in SAP
3. Real PrMO extract (например DB_UAI_2026) без PHI в git
4. Подписи медицинского руководителя и статистика

## Запреты

- Один работник в train и test
- Future feature leakage
- Заявление диагностической точности без reference standard
