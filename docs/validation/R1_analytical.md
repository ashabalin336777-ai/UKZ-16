# R1 — Analytical Correctness

## Цель

Доказать детерминизм, корректность единиц, missing/quality gates, absence of leakage и полноту explanation contract на synthetic данных.

## Проверки

- Одинаковые inputs + model_version → одинаковый result/trace
- Unit conversion / unknown unit
- Missing height/weight → not_calculable
- No psychometrics → hMental not_calculable
- Same-day repeats → persistence по уникальным датам
- Current point excluded from baseline
- No diagnosis claims
- Review pending/confirmed/rejected

## Отчёт

Результаты = прогон `pytest` (golden + property). См. `tests/`.
