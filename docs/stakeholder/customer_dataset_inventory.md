# Инвентаризация датасета заказчика (Drive)

Источник: [Google Drive УКЗ-16](https://drive.google.com/drive/folders/1CndIUnFec3-94ke-wOEgbviMu2XkqzuL)  
Срез анализа: 2026-10-13. Локальная копия документов/CSV: `data/customer_drive/` (**не в git**).  
Видео целиком не скачивались (объём большой); индексы видео учтены.

---

## Структура папки

| Папка / файл | Содержание |
|--------------|------------|
| `01_видео` | **2178** видео ПрМО (`{object_id}_{tab}_…mp4`), **21** табельный номер |
| `01_видео_исключено_77777` | **19** исключённых роликов (tab `77777`) |
| `02_видео_вне_индекса` | **101** видео вне CSV-индекса |
| `03_индексы_CSV` | **Основной tabular dataset** |
| `04_документы` | ТЗ, стратегия, аудит ЕЦОЗ/УКЗ, карта параметров |
| `05_перечень_и_словарь` | Перечень данных + словарь терминов |
| `06_эталонные_фото` | Эталонные кадры |
| `07_материалы_проверки_HEALTH_ID` | Отчёты коррекции / rPPG-калибровки (txt/pages) |
| `08_новые_материалы_Drive` | Доп. методические материалы |
| `09_НИР_кандидаты_Drive` | Кандидаты НИР |
| `MANIFEST*.csv`, `ОТЧЁТ.md`, `ОБНОВЛЕНИЕ_*.md` | Манифест выгрузки |

---

## Что есть в таблицах (ключевой файл)

Файл: `03_индексы_CSV/health_id_per_exam.csv`

| Метрика | Значение |
|---------|----------|
| Осмотров | **2147** |
| Сотрудников (anon) | **22** |
| Период | 2025-03-25 → 2026-03-25 |
| Площадка | 1 организация (Чебоксарский речной порт) |
| Тип осмотра | предрейсовый ≈ 2133, послерейсовый 11 |
| Полнота АД/пульс | ≈ 99.8% |
| Температура | 100% |
| Алкоголь | 100% (все 0 в этой выгрузке) |

### Поля, которые уже есть

- Идентификаторы: `object_id`, `exam_anon_id`, `employee_anon_id`, `exam_dt`
- Витальные: `sbp`, `dbp`, `pulse`, `temperature`, `alcohol`
- Жалобы (категория): `complaints_category`
- Решение медика (класс допуска): `result_medic_class` / журнал `admission`
- Контекст: `organization`, `terminal`, `exam_type`
- История: `history_rows_count`, `gap_days`, `regularity_score`, trend/stability scores
- **Готовые proxy-индексы заказчика:** `hBody_ID`, `hMental_ID_proxy`, `hSocial_Health_ID_proxy`, `HEALTH_ID`, blind-варианты, `risk_bucket`
- Видео-индексы: `videos_index_full.csv` / `objects_status_full.csv` (~2147 объектов с видео)

Дополнительно: `journal_anonymized.csv` (~2367 строк, 21 сотрудник) — журнал с АД/пульс/темп/анамнез/допуск.

Отчёт `07_.../health_id_chron.txt`: формула УКЗ-2 (scores + trend), коррекция острых отклонений, калибровка по **5** rPPG GT-точкам (MAE 4.08→0.58 на этой калибровке).

Корневой `ОТЧЁТ.md` (2026-10-12): сверка количеств journal/health_id/videos — **OK**; не найдены `СВОДНЫЙ ПАКЕТ НИР.docx` и файл «21 вопрос стажёров». `ОБНОВЛЕНИЕ_2026-10-12.md` явно фиксирует: HEALTH_ID только research, не допуск/диагноз.

---

## Чего не хватает для полного контракта UKZ-16 (`PrMOIngest`)

| Нужно для модуля | В датасете | Влияние |
|------------------|------------|---------|
| `height_cm` / `weight_kg` | **нет** | BMI и `ap_baevsky` → `missing`; полный hBody ТЗ не закрыть |
| Валидированная психометрика (PHQ/GAD/…) | **нет** (есть только `hMental_ID_proxy`) | hMental в нашем движке → `missing` / HEALTH_ID not_calculable |
| `social_metrics` (engagement и т.п.) | **нет** (есть proxy `hSocial_Health_ID_proxy`) | hSocial → missing |
| EMR chronic flags/codes | **нет** | chronic_from_emr пустой |
| `consent_research`, `protocol_id/version` | **нет в CSV** | нужно задать research defaults при импорте |
| `provenance.device_id`, unit_system | частично (terminal / video path) | собрать при маппере |
| Клинический GT для R4 review | только admission + 5 rPPG GT | R4 полноценно не закрыть |
| Многосайтовость (R3) | **1 сайт** | R3 transportability пока нельзя |

---

## Что уже можно использовать для проверки проекта

### 1. Сейчас (без дозапросов) — **можно**

1. **Импорт-маппер** CSV → `PrMOIngest` (vitals: SBP/DBP/pulse/temp; worker/encounter/time).  
2. **Прогон движка UKZ-16** на 2147 осмотрах: quality gates, persistence/corridor на 20+ сотрудниках с длинной историей.  
3. **Сравнение** нашего `hBody`/статусов с заказчиковыми `hBody_ID` / `HEALTH_ID` / `risk_bucket` (корреляции, расхождения на острых АД/ЧСС).  
4. **Smoke R2-подобный** retrospective на синтетическом таргете = заказчиковый `HEALTH_ID` или `result_medic_class` (**не клинический claim**, только engineering check).  
5. **Experimental rPPG**: выборка видео по индексу + 5 GT из отчёта коррекции (не полный pipeline).  
6. Проверка запретов: не экспортировать individual HEALTH_ID; admission из журнала **не** трактовать как диагноз модуля.

### 2. Частично — нужно уточнение у заказчика

- Как именно считаются `hMental_ID_proxy` / `hSocial_Health_ID_proxy` (формула, входы).  
- Можно ли получить рост/вес / психометрику / EMR chronic для тех же `employee_anon_id`.  
- Права и способ доступа к видео для массового rPPG (сейчас индексы есть, полный dump не качали).

### 3. Пока нельзя заявлять

- Клиническая валидность R2–R4.  
- Полный HEALTH_ID по ТЗ (нужны все три компоненты без proxy-подмены).  
- Внешняя транспортабельность R3.  
- SLA / production readiness.

---

## Рекомендуемый следующий шаг инженерии

1. Скрипт `scripts/import_customer_exams.py`: CSV → JSONL `PrMOIngest` + прогон `evaluate_health_id`.  
2. Отчёт сравнения с колонками заказчика (`reports/customer_pilot/`).  
3. В чек-лист тимлида: запрос роста/веса, психометрии, EMR и расшифровки proxy-формул.

Hard rules: research use only; не использовать `admission` / `result_medic_class` как выход HEALTH_ID-модуля для допуска.
