# Исследовательская система клинической валидации интегрального индекса здоровья HEALTH_ID

**УКЗ-16** — Phase 1 (1C + 2B)

Research use only. Модуль **не ставит диагноз** и **не передаёт индивидуальный HEALTH_ID работодателю**.

## Возможности Phase 1

- Версионированный движок `research-v0.2` (hBody 0.60 / hMental 0.25 / hSocial 0.15, без перенормировки весов)
- Приём ПрМО через mock-адаптер ЕЦОЗ + quality gates
- Персональные коридоры без leakage текущей точки
- Acute / persistence (уникальные даты) / chronic только из EMR
- Explanation contract + clinical review (pending/confirmed/rejected)
- Model card, журнал версий, drift alert без auto-update
- FastAPI: evaluate / timeline / review / model-card

## Быстрый старт

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -e ".[dev]"
pytest
uvicorn ukz16.api.main:app --reload
```

API keys (header `X-API-Key`):

| Role | Key |
|------|-----|
| researcher | `researcher-key` |
| medical_worker | `medical-key` |
| auditor | `auditor-key` |

Пример (маршрут ТЗ §14):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/health-id/evaluations ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: researcher-key" ^
  -H "Idempotency-Key: demo-1" ^
  -d @samples/prmo_ok.json
```

Legacy aliases `/v1/evaluate` и др. сохранены как deprecated.

PostgreSQL (опционально): `docker compose up -d db` и `UKZ16_DATABASE_URL=postgresql+psycopg://ukz16:ukz16@localhost:5432/ukz16`.

## Документация

- [Intended use](docs/intended_use.md)
- [Data dictionary](docs/data_dictionary.md)
- [Formula candidates](docs/formula_candidates.md)
- [Missing/quality policy](docs/missing_quality_policy.md)
- [Model card](docs/model_card.md)
- Validation: [R0](docs/validation/R0_protocol.md) … [R4](docs/validation/R4_clinical_utility.md)

## Phase 2

См. [docs/phase2_ops.md](docs/phase2_ops.md) и [docs/roadmap_next.md](docs/roadmap_next.md): ECOZ HTTP/fixture ingest, OIDC hybrid auth, Vault KV overlays, HMAC/Cosign signing, experimental HRV, OTEL. Dev stubs: `docker compose up vault keycloak`.

## Phase 3 / R2–R4 (synthetic scaffolds)

```bash
python scripts/generate_r2_synthetic_cohort.py
ukz16-r2 --cohort samples/validation/r2_synthetic_cohort.jsonl --out reports/r2_synthetic

python scripts/generate_r3_r4_synthetic.py
ukz16-r3 freeze --out reports/r3/model_freeze.json --site SITE-EXT-1 --site SITE-EXT-2
ukz16-r3 run --cohort samples/validation/r3_synthetic_multisite.jsonl --freeze reports/r3/model_freeze.json --out reports/r3
ukz16-r4 --log samples/validation/r4_synthetic_review_log.jsonl --out reports/r4
```

Протоколы: [R2](docs/validation/R2_retrospective.md) · [R3](docs/validation/R3_external_prospective.md) · [R4](docs/validation/R4_clinical_utility.md).  
Synthetic ≠ clinical claim. Реальная когорта пока недоступна.

## CI

GitHub Actions: `.github/workflows/ci.yml` — `pytest` на Python 3.12.
