# Пилот на данных заказчика (engineering only)

Дата: 2026-10-13. Модель: `research-v0.2`.  
**clinical_claim = false** — это не R2/R3/R4 и не клиническая валидность.

Команда:

```bash
python scripts/import_customer_exams.py
# артефакты (gitignored): reports/customer_pilot/
```

Источник: `data/customer_drive/03_индексы_CSV/health_id_per_exam.csv` (2147 осмотров / 22 сотрудника / 1 сайт).

---

## Сверка с ТЗ (факт пилота)

| Правило ТЗ | Результат на CSV |
|------------|------------------|
| Нет всех трёх компонент → `health_id.value = null`, без перенормировки | **2147 / 2147** `not_calculable` (`insufficient_components:hMental,hSocial`) |
| hBody из АД/пульса | **2143** `derived`, **4** `missing` (`quality_blocked` — отбраковка vitals) |
| BMI / АП без роста/веса → `missing_height_weight` | **2147** BMI missing; АП — `missing_height_weight` |
| Proxy заказчика не подставляются в индекс | Да: `hMental_ID_proxy` / `hSocial_…` / `HEALTH_ID` только в side-car |
| Admission / `result_medic_class` ≠ выход модуля | Да |
| `diagnosis_claim=false`, employer export запрещён | Да |

Completeness типично **0.4286** (3/7: АД+пульс; нет роста/веса/психометрии/social).

---

## Сравнение hBody (UKZ×100 vs `hBody_ID` заказчика)

| Метрика | Значение |
|---------|----------|
| Paired n | 2143 |
| Pearson r | **0.736** |
| Spearman ρ | **0.762** |
| MAE | 17.8 |
| RMSE | 20.0 |
| UKZ mean×100 | 69.1 |
| Customer mean | 86.8 |

Корреляция умеренно-высокая: оба индекса реагируют на АД/пульс. Абсолютный сдвиг ожидаем — у заказчика УКЗ-2 (scores + trend/stability), у нас scaffold `hBody_vitals_v0` (дистанция до ref 70/120/80). Это **не** калибровка и **не** clinical claim.

Коридор (по UKZ hBody): outside **189**; once ≥3 уникальных дат отклонения накопилось — `is_persistent` на последующих осмотрах (**1551**), по правилу persistence из ТЗ.

---

## Что остаётся для клинической валидации

1. Дозапрос: рост/вес, PHQ/GAD/WHO-5, EMR chronic, расшифровка proxy.  
2. Data use agreement + когорта R2.  
3. ≥2 внешних сайта (R3).  
4. Клиницисты R4 + подписи R0/SAP/A16.

Маппер: `src/ukz16/ingest/customer_csv.py`. Тесты: `tests/unit/test_customer_csv.py`.
