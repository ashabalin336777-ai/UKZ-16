# Formula Candidates — research-v0.1 (scaffold 2B)

> **Важно:** веса и субформулы ниже — **исследовательский scaffold**, не клинически утверждённые константы. Любой перенос в практику требует валидации R1–R4.

## Интегральный индекс

\[
HEALTH\_ID = 0.60 \cdot hBody + 0.25 \cdot hMental + 0.15 \cdot hSocial
\]

Считается только при политике `allow_weighted_partial` и наличии достаточных компонент; иначе `partial` / `not_calculable` без импутации.

## hBody (scaffold)

Нормализованный балл 0–1 из доступных измеренных витальных (АД, пульс) и, при наличии роста/веса, BMI-прокси.

- Нет `height_cm` или `weight_kg` → поля BMI/АП: `not_calculable: missing_height_weight`
- Полный адаптационный потенциал Баевского — **не рассчитывается** без измеренных роста/веса
- Неизвестные единицы / битый протокол → component blocked

## hMental (scaffold)

- Без валидированной психометрии → `not_calculable: no_validated_psychometrics`
- Голос / SVS — **вне Phase 1**, всегда experimental (не реализовано)

## hSocial (scaffold)

- Без утверждённых метрик → `not_calculable: no_validated_social_metrics`
- Посещаемость ≠ мотивация

## Персональные коридоры

Baseline строится только по **предыдущим** уникальным датам с `quality=ok`. Текущая точка **исключается**.

## Persistence

Считается по **уникальным календарным датам** отклонений, не по числу попыток в один день.
