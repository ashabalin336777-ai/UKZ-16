# Model package schema — research-v0.1

## Files

- `model.yaml` — weights, policies, thresholds, scoring scaffold
- `normals.yaml` — population reference bands (research)
- `SCHEMA.md` — this file

## Immutability

Изменение любого файла = новая версия (`research-v0.2`, …). Хеш package фиксируется в evaluation evidence.

## Loading

`ukz16.governance.model_registry.load_model_package(version)`
