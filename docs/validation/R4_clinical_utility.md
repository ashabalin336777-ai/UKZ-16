# R4 — Clinical Utility

## Цель

Оценить пользу human-AI team: explanation + clinical review без автоматической постановки диагноза.

## Реализация

| Компонент | Путь |
|-----------|------|
| Review log loader | `ukz16.validation.r4.logs` |
| Metrics | override rate, time-to-review, net benefit, safety |
| CLI | `ukz16-r4` |
| Synthetic log | `samples/validation/r4_synthetic_review_log.jsonl` |

## Запуск (synthetic)

```bash
python scripts/generate_r3_r4_synthetic.py
ukz16-r4 --log samples/validation/r4_synthetic_review_log.jsonl --out reports/r4
```

## Метрики

- Override rate
- Mean time-to-review
- Decision distribution (`confirmed/rejected/escalated/no_action`)
- Net benefit (model vs treat-all vs treat-none)
- Harm flags / missed positives without alert
- `diagnosis_auto_assigned = false` всегда

## Шлюз

Operational claim только после prospective clinician study и утверждения intended use. Synthetic ≠ R4 pass.
