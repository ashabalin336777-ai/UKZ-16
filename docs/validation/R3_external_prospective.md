# R3 — External Prospective Validation

## Цель

Подтвердить переносимость frozen-модели на внешнюю площадку/ПАК без обновления модели.

## Реализация

| Компонент | Путь |
|-----------|------|
| Freeze | `ukz16.validation.r3.freeze` / `ukz16-r3 freeze` |
| Runner | `ukz16.validation.r3.runner` / `ukz16-r3 run` |
| Synthetic multi-site cohort | `samples/validation/r3_synthetic_multisite.jsonl` |

## Запуск (synthetic)

```bash
python scripts/generate_r3_r4_synthetic.py
ukz16-r3 freeze --out reports/r3/model_freeze.json --site SITE-EXT-1 --site SITE-EXT-2
ukz16-r3 run --cohort samples/validation/r3_synthetic_multisite.jsonl --freeze reports/r3/model_freeze.json --out reports/r3
```

## Обязательные шлюзы ТЗ

1. Model freeze **до** enrollment (hash + version).
2. Нет auto-update.
3. Consent / privacy на внешней площадке.
4. Независимый reference standard.
5. Отчёт transportability by site/device.

Synthetic прогон доказывает только готовность пайплайна, не clinical claim.
