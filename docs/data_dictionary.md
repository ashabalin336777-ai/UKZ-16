# Data Dictionary — ПрМО / HEALTH_ID

Все идентификаторы работников — **псевдонимы**. Реальные PHI в репозиторий и логи не помещаются.

## PrMOIngest (вход)

| Поле | Тип | Обязательность | Описание |
|------|-----|----------------|----------|
| `worker_id` | string | required | Псевдоним работника |
| `encounter_id` | string | required | Идентификатор осмотра |
| `measured_at` | datetime (ISO-8601) | required | Время измерения |
| `source_system` | string | required | Источник (например `ECOZ_MOCK`) |
| `consent_research` | bool | required | Согласие на исследовательский контур |
| `protocol_id` | string | required | Идентификатор протокола измерений |
| `protocol_version` | string | required | Версия протокола |
| `vitals` | object | required | Витальные показатели |
| `context` | object | optional | Контекст (смена, площадка, поза) |
| `psychometrics` | object | optional | Валидированная психометрия |
| `social_metrics` | object | optional | Метрики для hSocial (research) |
| `emr_flags` | object | optional | Флаги из МИС/ЭМК |
| `provenance` | object | required | Происхождение и устройство |

### vitals

| Поле | Единицы | Примечание |
|------|---------|------------|
| `height_cm` | cm | без значения BMI/АП not_calculable |
| `weight_kg` | kg | без значения BMI/АП not_calculable |
| `bp_systolic_mmhg` | mmHg | |
| `bp_diastolic_mmhg` | mmHg | |
| `pulse_bpm` | bpm | |
| `temperature_c` | °C | optional |
| `spo2_pct` | % | optional |

### psychometrics (validated only)

| Поле | Описание |
|------|----------|
| `instrument` | PHQ-9 / GAD-7 / WHO-5 и т.п. |
| `score` | Числовой балл |
| `scored_at` | Дата оценки |
| `validated` | true только для утверждённого протокола |

### emr_flags

| Поле | Описание |
|------|----------|
| `clinically_confirmed_chronic` | bool — хроническое состояние **только** из МИС/ЭМК |
| `chronic_condition_codes` | list[string] — коды (research labels, не диагноз модуля) |

### provenance

| Поле | Описание |
|------|----------|
| `device_id` | Устройство / канал ввода |
| `operator_id` | Псевдоним оператора |
| `input_ids` | Список идентификаторов исходных измерений |
| `unit_system` | `SI_medical` ожидается |

## Evaluation (выход) — см. explanation contract

См. Pydantic-модели в `src/ukz16/domain/contracts.py`.
