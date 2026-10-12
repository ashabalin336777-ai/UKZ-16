# Model Card — HEALTH_ID research-v0.2

## Model details

- **Name:** HEALTH_ID
- **Version:** research-v0.2
- **Supersedes:** research-v0.1 (archived, not the runtime default)
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
- ИМТ и АП Баевского не входят в HEALTH_ID. Без роста и веса их статус `missing` / `missing_height_weight`.
- Неполные компоненты не перенормируются: итог остаётся null.
- Нет experimental signals (HRV/rPPG/voice) в этой версии.
- Нет боевой интеграции ЕЦОЗ.

## Drift & updates

Drift alerts без auto-update. Смена версии — только через явный model package и журнал версий.
