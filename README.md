# УКЗ-16 — исследовательская валидация HEALTH_ID

**Research use only.** Модуль **не ставит диагноз**, **не выдаёт допуск к работе** и **не передаёт индивидуальный HEALTH_ID работодателю**.

Репозиторий: [ashabalin336777-ai/UKZ-16](https://github.com/ashabalin336777-ai/UKZ-16)  
Активная модель: `research-v0.2` (веса 0.60 / 0.25 / 0.15, без перенормировки)

---

## Статус поставки

| Фаза | Статус |
|------|--------|
| Phase 1 — движок + A16 | done |
| Phase 1.5 — API ТЗ §14 | done |
| Phase 2 — ops (ЕЦОЗ, OIDC, Vault, Cosign, experimental) | done |
| Phase 2.5 — data lanes, guidance, bench, e2e | done |
| Phase 3 — клиническая валидация на реальных данных | **blocked** (нужна когорта / площадки) |

Synthetic R1–R4 ≠ clinical claim.

---

## Документы для стейкхолдеров

| Аудитория | Документ |
|-----------|----------|
| Тимлид | [Чек-лист: сделано / осталось](docs/stakeholder/teamlead_checklist.md) |
| Заказчик | [Архитектура и стек](docs/stakeholder/customer_architecture.md) |
| Заказчик | [Вопросы для снятия блокеров](docs/stakeholder/customer_questions.md) |
| Команда | [Roadmap](docs/roadmap_next.md) · [Phase 2 ops](docs/phase2_ops.md) · [Phase 2.5](docs/phase25_data_plane.md) |

---

## Что умеет система

- Версионированный HEALTH_ID + explanation contract + clinical review
- Quality gates, персональные коридоры, acute / persistence / chronic-from-EMR
- Ingest ЕЦОЗ: mock / fixture / HTTP
- Auth: API-key (dev) + OIDC/JWT (Keycloak-ready)
- Vault overlays, HMAC / Cosign signing, OTEL optional
- Experimental HRV / rPPG / voice_SVS (не входят в индекс)
- Data lanes raw → normalized → research → audit + псевдонимизация
- CLI валидации: `ukz16-r1` … `ukz16-r4`, `ukz16-bench`

---

## Быстрый старт

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
uvicorn ukz16.api.main:app --reload
```

Ключи API (`X-API-Key`):

| Role | Key |
|------|-----|
| researcher | `researcher-key` |
| medical_worker | `medical-key` |
| auditor | `auditor-key` |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/health-id/evaluations ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: researcher-key" ^
  -H "Idempotency-Key: demo-1" ^
  -d @samples/prmo_ok.json
```

PostgreSQL + stubs:

```bash
docker compose up -d db vault keycloak
# опционально: python scripts/seed_vault_dev.py
```

Полный synthetic прогон:

```bash
python scripts/run_synthetic_e2e.py
```

---

## Документация продукта

- [Intended use](docs/intended_use.md)
- [Data dictionary](docs/data_dictionary.md)
- [Formula candidates](docs/formula_candidates.md)
- [Missing/quality policy](docs/missing_quality_policy.md)
- [Model card](docs/model_card.md)
- [TZ cross-review](docs/tz_cross_review.md)
- Validation: [R0](docs/validation/R0_protocol.md) · [R1](docs/validation/R1_analytical.md) · [R2](docs/validation/R2_retrospective.md) · [R3](docs/validation/R3_external_prospective.md) · [R4](docs/validation/R4_clinical_utility.md) · [A16](docs/validation/A16_acceptance_protocol.md)

---

## CI

GitHub Actions (`.github/workflows/ci.yml`) — `pytest` на Python 3.12.
