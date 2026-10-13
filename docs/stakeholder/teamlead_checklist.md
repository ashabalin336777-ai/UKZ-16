# Чек-лист для тимлида — УКЗ-16 / HEALTH_ID

Дата среза: 2026-10-13. Репозиторий: [UKZ-16](https://github.com/ashabalin336777-ai/UKZ-16). Модель: `research-v0.2`.  
Сводка открытых пунктов: [issue #8](https://github.com/ashabalin336777-ai/UKZ-16/issues/8) (метка `checklist`).

## Статус одной фразой

**Research ready (Phase 1–2.5 + пилот заказчика + synthetic R2–R4).** Клинический claim не заявлен. Phase 3 на реальных данных и Phase 4 (prod) ждут внешних входов.

---

## Карта фаз

| Фаза | Смысл | Статус |
|------|-------|--------|
| Phase 1 | Движок HEALTH_ID по ТЗ | done |
| Phase 1.5 | API, A16 tooling | done |
| Phase 2 | ЕЦОЗ / auth / Vault / Cosign / experimental | done (research) |
| Phase 2.5 | Lanes, bench, synthetic e2e | done |
| Пилот CSV | 2147 осмотров заказчика | done (engineering) |
| Synthetic R2–R4 | Дозаполнение → пайплайн валидации | done (`clinical_claim=false`) |
| Phase 3 R0–R1 | Протокол + аналитическая приёмка | tooling done; **подписи нет** |
| Phase 3 R2–R4 | Реальная когорта / сайты / врачи | runners done; **данные/люди нет** |
| Phase 4 | Боевой prod (MFA, TLS, SLA) | не начат |

---

## Сделано (можно принимать как research delivery)

### Движок и контракт ТЗ
- [x] HEALTH_ID: веса 0.60 / 0.25 / 0.15, **без перенормировки**
- [x] Статусы: `measured | derived | experimental | missing`
- [x] `bmi`, `ap_baevsky`; без роста/веса → `missing_height_weight`
- [x] Нет скрытой импутации; chronic только из EMR
- [x] Коридор без leakage; persistence по уникальным датам
- [x] `WorkerSequence` — единая история для пилота / R2 / R4
- [x] `diagnosis_claim=false`, employer export → 403 + audit

### API / governance / ops / data plane
- [x] `/api/v1/health-id/...`, idempotency, review, model card, drift 423
- [x] A16 mapping + `ukz16-r1`
- [x] ЕЦОЗ mock/fixture/HTTP; API-key + OIDC stub; Vault; Cosign bridge
- [x] Experimental HRV / rPPG / voice_SVS (не в индекс)
- [x] Lanes raw→audit, псевдонимизация, guidance F16-05, `ukz16-bench`
- [x] `scripts/run_synthetic_e2e.py`
- [x] CI: pytest 3.12 (**60+** tests)

### Данные заказчика (engineering)
- [x] Drive inventory — [customer_dataset_inventory.md](customer_dataset_inventory.md)
- [x] Пилот CSV — [customer_pilot.md](customer_pilot.md) (HEALTH_ID null на 2147; hBody r≈0.74)
- [x] Synthetic enrichment + R2→R3→R4 — [customer_enriched_validation.md](customer_enriched_validation.md)

---

## Осталось (GitHub Issues)

### Phase 3 — клиника
- [ ] [#1](https://github.com/ashabalin336777-ai/UKZ-16/issues/1) — реальные рост/вес, психометрия, EMR, формулы proxy
- [ ] [#2](https://github.com/ashabalin336777-ai/UKZ-16/issues/2) — когорта R2 + data use agreement
- [ ] [#3](https://github.com/ashabalin336777-ai/UKZ-16/issues/3) — внешние сайты R3
- [ ] [#4](https://github.com/ashabalin336777-ai/UKZ-16/issues/4) — клиницисты R4
- [ ] [#5](https://github.com/ashabalin336777-ai/UKZ-16/issues/5) — подписи R0/SAP и A16

### Интеграции + Phase 4 prod
- [ ] [#6](https://github.com/ashabalin336777-ai/UKZ-16/issues/6) — боевой ЕЦОЗ, устройства, судьба HRV/rPPG/voice
- [ ] [#7](https://github.com/ashabalin336777-ai/UKZ-16/issues/7) — Keycloak/MFA, Vault, TLS, Cosign, staging SLA, владелец модели

Вопросы заказчику: [customer_questions.md](customer_questions.md).

---

## Как проверить delivery

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/run_synthetic_e2e.py
ukz16-r1 --out reports/r1 --skip-pytest

# при наличии data/customer_drive/.../health_id_per_exam.csv:
python scripts/import_customer_exams.py
python scripts/run_customer_enriched_validation.py
```

Критерий research ready: pytest зелёный, synthetic e2e отрабатывает, клинический claim **не** формулируется.
