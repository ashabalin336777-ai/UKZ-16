# A16 Acceptance Protocol — mapping to automated tests

Этап: аналитическая приёмка исследовательского контура (`research-v0.2`).  
Клиническая приёмка R2–R4 этим протоколом не закрывается.

| ID | Критерий ТЗ | Автотест / артефакт | Статус |
|----|-------------|---------------------|--------|
| A16-01 | Воспроизводимость | `tests/golden/test_a16_acceptance.py::test_a16_deterministic_same_inputs_same_hash_and_trace`, `tests/property/test_determinism.py` | covered |
| A16-02 | Нет роста/веса → ИМТ и АП `missing_height_weight` | `test_a16_missing_height_weight` | covered |
| A16-03 | Нет психометрики → hMental missing; SVS experimental | `test_a16_no_psychometrics_hmental_not_calculable` (SVS placeholder `experimental`, не в hMental) | covered |
| A16-04 | Повторы одного дня не умножают persistence | `test_a16_same_day_repeats_do_not_increase_persistence` | covered |
| A16-05 | Future leakage ловится тестом | `test_a16_future_leakage_and_patient_split` | covered (helper, не ML-pipeline) |
| A16-06 | Worker не в train/test одновременно | тот же тест `patient_level_split_ok` | covered (helper) |
| A16-07 | Объяснимость: components, quality, completeness, uncertainty, evidence | `test_a16_output_contract_fields` | covered |
| A16-08 | В ИС УКЗ нет индивидуальных HEALTH_ID | `test_a16_api_employer_export_forbidden` | partial (API deny; нет enterprise-контура) |
| A16-09 | Нет диагноза/допуска; human review | `diagnosis_claim=false`, `test_a16_review_pending_confirmed_rejected` | covered |
| A16-10 | Drift → alert, без auto-update; может блокировать расчёт | `test_a16_drift_blocks_evaluation` | covered |
| A16-11 | Unknown unit / bad protocol блокируют | `test_a16_unknown_unit_and_bad_protocol_block` | covered |
| A16-12 | ИБ: роли, MFA, шифрование, backup, согласие, псевдонимизация | API-key roles + consent gate; MFA/encryption/backup — вне Phase 1 | partial |

## Прогон

```bash
pytest -q
```

Критерий перехода к подписанной R1-приёмке: все `covered` зелёные; `partial` закрыты отдельным планом или приняты как residual risk в R0.
