# Missing & Quality Policy — research-v0.1

## Принципы

1. **Нет скрытой импутации** средним, нулём или «типичным» значением.
2. Недостаточность данных → `not_calculable` / `partial` / block component с явной `reason`.
3. Качество сигнала и протокол проверяются **до** расчёта.
4. Дубликаты и повторные попытки одного дня не улучшают completeness и не увеличивают persistence.

## Правила пропусков

| Условие | Результат |
|---------|-----------|
| Нет height или weight | BMI/АП not_calculable: `missing_height_weight` |
| Нет validated psychometrics | hMental not_calculable: `no_validated_psychometrics` |
| Нет validated social metrics | hSocial not_calculable: `no_validated_social_metrics` |
| Нет consent_research | отказ ingest: `consent_required` |
| Unknown unit | block component: `unknown_unit` |
| Broken / unknown protocol | block: `bad_protocol` |
| Out-of-range vital (hard) | block field: `out_of_range` |

## Quality statuses

- `ok` — прошло гейты
- `degraded` — допустимо с пометкой, вклад в uncertainty
- `reject` — поле/компонент заблокирован

## Safe refusal

При критическом отказе качества или отсутствии согласия модуль возвращает explanation contract со `status=not_calculable` и **не** вычисляет фиктивный HEALTH_ID.
