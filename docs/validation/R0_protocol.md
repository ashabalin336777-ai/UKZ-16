# R0 — Analytical / Protocol Freeze

## Цель

Зафиксировать intended use, словарь данных, политики missing/quality, кандидатов формул и риск-реестр **до** клинической валидации.

## Артефакты

- [x] intended_use.md
- [x] data_dictionary.md
- [x] formula_candidates.md
- [x] missing_quality_policy.md
- [x] model_card.md
- [x] model package `models/health_id/research-v0.1/`

## Критерии прохождения R0

1. Research use only задокументирован.
2. Запрет передачи работодателю зафиксирован.
3. Нет скрытой импутации в политике.
4. Chronic только из EMR/MIS.
5. Версия модели неизменяема без нового package.
