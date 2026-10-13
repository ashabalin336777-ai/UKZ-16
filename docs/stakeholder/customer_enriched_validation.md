# Обогащённая когорта + R2→R3→R4 (synthetic fill)

Дата: 2026-10-13. Модель: `research-v0.2`.  
**clinical_claim = false**

Реальные виталы из Drive CSV + **синтетические** рост/вес, психометрия (PHQ-9/GAD-7/WHO-5), social, EMR, 3 сайта. Это разблокирует engineering-прогон полного контракта `PrMOIngest`, но **не** заменяет клинические данные заказчика.

```bash
python scripts/run_customer_enriched_validation.py
# или по шагам:
python scripts/generate_customer_enriched_cohort.py
ukz16-r2 --cohort reports/customer_enriched/r2_cohort.jsonl --out reports/customer_enriched/r2
ukz16-r3 freeze --out reports/customer_enriched/r3/model_freeze.json --site SITE-A --site SITE-B --site SITE-C
ukz16-r3 run --cohort reports/customer_enriched/r3_cohort.jsonl --freeze reports/customer_enriched/r3/model_freeze.json --out reports/customer_enriched/r3
ukz16-r4 --log reports/customer_enriched/r4_review_log.jsonl --out reports/customer_enriched/r4
```

---

## Что сгенерировано

| Поле | Источник |
|------|----------|
| АД / пульс / температура | customer CSV |
| `height_cm` / `weight_kg` / `age_years` | synthetic (детерминированно по worker) |
| PHQ-9 / GAD-7 / WHO-5 + `scored_at` | synthetic (стресс от виталов) |
| `social_metrics.engagement_score` | synthetic |
| EMR chronic flags | synthetic (~12% workers) |
| `site_id` SITE-A/B/C | synthetic round-robin |
| R2 label | customer `risk_bucket`/`result_medic_class` + SBP/pulse rules (**не** из UKZ HEALTH_ID) |

Worker id в samples: `W-ENR-xx` (remap). Полные когорты: `reports/customer_enriched/` (gitignored). Smoke: `samples/validation/customer_enriched_*_smoke.jsonl`.

---

## Результат прогона (срез)

| Этап | Факт |
|------|------|
| HEALTH_ID | calculable (50/50 smoke OK; abstention ~0.2% на полном R3) |
| R2 group holdout | n_test=567, Brier≈0.144, sens@0.5≈0.32, spec≈0.98 |
| R3 freeze | ok, 3 сайта, Brier≈0.149 |
| R4 | 608 cases, override_rate≈0.39, harm_flags=0 |

Метрики — **scaffold / engineering**; порог 0.5 и синтетические labels не калиброваны под клинику.

---

## Что это не закрывает

- Реальный рост/вес/психометрию/EMR с площадки  
- Подписанный R0/SAP/A16  
- Clinical claim, допуск, диагноз  

Код: `src/ukz16/ingest/synthetic_enrichment.py`, `scripts/generate_customer_enriched_cohort.py`.
