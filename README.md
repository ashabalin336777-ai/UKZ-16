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

Пример:

```bash
curl -X POST http://127.0.0.1:8000/v1/evaluate ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: researcher-key" ^
  -d @samples/prmo_ok.json
```

PostgreSQL (опционально): `docker compose up -d db` и `UKZ16_DATABASE_URL=postgresql+psycopg://ukz16:ukz16@localhost:5432/ukz16`.

## Документация

- [Intended use](docs/intended_use.md)
- [Data dictionary](docs/data_dictionary.md)
- [Formula candidates](docs/formula_candidates.md)
- [Missing/quality policy](docs/missing_quality_policy.md)
- [Model card](docs/model_card.md)
- Validation: [R0](docs/validation/R0_protocol.md) … [R4](docs/validation/R4_clinical_utility.md)

## Вне Phase 1 / дальше

См. [docs/roadmap_next.md](docs/roadmap_next.md): ЕЦОЗ-адаптер, Keycloak/Vault/Sigstore, experimental HRV/rPPG/voice, R2–R4.

## CI

GitHub Actions: `.github/workflows/ci.yml` — `pytest` на Python 3.12.
