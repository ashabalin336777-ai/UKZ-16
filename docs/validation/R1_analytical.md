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

```bash
ukz16-r1 --out reports/r1
```

Пишет `r1_report.json` + `r1_report.md` (R0 artifacts, A16 checklist, pytest).  
Результаты аналитики = прогон `pytest` (golden + property). См. `tests/`.  
Это не клиническая валидность и не подписанная приёмка без человека.
