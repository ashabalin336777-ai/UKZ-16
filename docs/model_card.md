# Model Card — HEALTH_ID research-v0.1

## Model details

- **Name:** HEALTH_ID
- **Version:** research-v0.1
- **Type:** Rule-based composite index (scaffold)
- **Weights:** hBody 0.60 / hMental 0.25 / hSocial 0.15
- **Owner:** УКЗ-16 research team
- **Intended use:** research only (see `docs/intended_use.md`)

## Training data

Не применимо: детерминированные правила, не ML-обучение. Synthetic fixtures для тестов — без PHI.

## Evaluation data

Golden tests A16 (deterministic). R2–R4 — шаблоны протоколов, клинические данные не включены.

## Ethical considerations

- Не ставит диагноз.
- Индивидуальный HEALTH_ID не передаётся работодателю.
- Human clinical review обязателен для клинической интерпретации сигнала.

## Limitations

- Субформулы — заглушки до утверждения.
- Нет experimental signals (HRV/rPPG/voice) в этой версии.
- Нет боевой интеграции ЕЦОЗ.

## Drift & updates

Drift alerts без auto-update. Смена версии — только через явный model package и журнал версий.
