# УКЗ-16 — исследовательская валидация HEALTH_ID

**Research use only.** Модуль **не ставит диагноз**, **не выдаёт допуск к работе** и **не передаёт индивидуальный HEALTH_ID работодателю**.

Репозиторий: [ashabalin336777-ai/UKZ-16](https://github.com/ashabalin336777-ai/UKZ-16)  
Активная модель: `research-v0.2` (веса 0.60 / 0.25 / 0.15, без перенормировки)

Сделан исследовательский контур HEALTH_ID: движок и API по ТЗ, ops и data lanes, пилот на 2147 осмотрах заказчика и synthetic R2–R4. **Этап сейчас — research ready (Phase 1–2.5 + пилот).** Клиническая валидация (Phase 3) ждёт реальных рост/вес/психометрии/EMR, площадок, врачей и подписей — не доработки кода.

---

## Этапы (кратко)

| Фаза | Что это | Статус |
|------|---------|--------|
| **Phase 1** | Движок HEALTH_ID по ТЗ (формула, качество, коридор) | **done** |
| **Phase 1.5** | API, idempotency, drift, A16 tooling | **done** |
| **Phase 2** | ЕЦОЗ, auth, Vault, Cosign, experimental HRV/rPPG/voice | **done** (research) |
| **Phase 2.5** | Lanes, псевдонимы, guidance, bench, synthetic e2e | **done** |
| **Пилот заказчика** | CSV Drive → UKZ-16, сверка hBody | **done** (engineering) |
| **Synthetic R2–R4** | Дозаполнение полей → полный пайплайн валидации | **done** (`clinical_claim=false`) |
| **Phase 3 — R0** | Правила / протокол | документ есть; **подпись человека** — нет |
| **Phase 3 — R1** | Аналитическая приёмка | tooling **done**; акт — нет |
| **Phase 3 — R2** | Ретроспектива на реальной когорте | runner **done**; реальных данных полного контракта — нет |
| **Phase 3 — R3** | Внешние площадки | runner **done**; 1 реальный сайт — мало |
| **Phase 3 — R4** | Врачи: review / override / safety | runner **done**; клиницистов — нет |
| **Phase 4** | Боевой prod (MFA, TLS, SLA) | **не начат** |

Synthetic / enriched R1–R4 ≠ clinical claim. Без fill: HEALTH_ID `null` по ТЗ. С fill: HEALTH_ID calculable + engineering metrics.

Открытый чек-лист: [GitHub #8](https://github.com/ashabalin336777-ai/UKZ-16/issues/8).

---

## Документы для стейкхолдеров

| Аудитория | Документ |
|-----------|----------|
| Тимлид | [Чек-лист](docs/stakeholder/teamlead_checklist.md) · [Issues #1–#8](https://github.com/ashabalin336777-ai/UKZ-16/issues/8) |
| Заказчик | [Презентация (HTML)](docs/stakeholder/customer_brief.html) · [Демо-экран](docs/demo/index.html) |
| Заказчик | [Вопросы (блокеры Phase 3)](docs/stakeholder/customer_questions.md) |
| Заказчик | [Архитектура и стек](docs/stakeholder/customer_architecture.md) |
| Данные | [Инвентаризация Drive](docs/stakeholder/customer_dataset_inventory.md) |
| Данные | [Пилот CSV](docs/stakeholder/customer_pilot.md) · [Enriched R2–R4](docs/stakeholder/customer_enriched_validation.md) |
| Команда | [Roadmap](docs/roadmap_next.md) · [Phase 2](docs/phase2_ops.md) · [Phase 2.5](docs/phase25_data_plane.md) |

**Показ заказчику (15 мин):** открыть `docs/stakeholder/customer_brief.html` (стрелки ←→) → `docs/demo/index.html` (3 сценария). Бейдж на экране: Research only · не диагноз · не допуск.

---

## Что умеет система

- Версионированный HEALTH_ID + explanation contract + clinical review
- Quality gates: отбракованное поле не входит в ИМТ/АП; hBody блокируется только по своим входам
- Персональный коридор по hBody (robust z, `mad_floor` 0.02)
- Психометрия только PHQ-9 / GAD-7 / WHO-5; chronic только из EMR
- Ingest ЕЦОЗ: mock / fixture / HTTP; auth API-key + OIDC
- Vault overlays, HMAC / Cosign, OTEL optional
- Experimental HRV / rPPG / voice_SVS (не в индекс)
- Data lanes raw → normalized → research → audit
- CLI: `ukz16-r1` … `ukz16-r4`, `ukz16-bench`
- Customer CSV mapper + `WorkerSequence` (единая история коридора)

---

## Как проверить

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/run_synthetic_e2e.py
ukz16-r1 --out reports/r1 --skip-pytest

# при локальной копии Drive CSV:
python scripts/import_customer_exams.py
python scripts/run_customer_enriched_validation.py
```

API:

```bash
uvicorn ukz16.api.main:app --reload
curl -X POST http://127.0.0.1:8000/api/v1/health-id/evaluations ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: researcher-key" ^
  -H "Idempotency-Key: demo-1" ^
  -d @samples/prmo_ok.json
```

| Role | Key |
|------|-----|
| researcher | `researcher-key` |
| medical_worker | `medical-key` |
| auditor | `auditor-key` |

```bash
docker compose up -d db vault keycloak
# опционально: python scripts/seed_vault_dev.py
```

---

## Документация продукта

- [Intended use](docs/intended_use.md) · [Data dictionary](docs/data_dictionary.md) · [Formula](docs/formula_candidates.md)
- [Missing/quality](docs/missing_quality_policy.md) · [Model card](docs/model_card.md) · [TZ cross-review](docs/tz_cross_review.md)
- Validation: [R0](docs/validation/R0_protocol.md) · [R1](docs/validation/R1_analytical.md) · [R2](docs/validation/R2_retrospective.md) · [R3](docs/validation/R3_external_prospective.md) · [R4](docs/validation/R4_clinical_utility.md) · [A16](docs/validation/A16_acceptance_protocol.md)

---

## CI

GitHub Actions (`.github/workflows/ci.yml`) — `pytest` на Python 3.12 (60+ tests).
