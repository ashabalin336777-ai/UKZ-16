# Чек-лист для тимлида — УКЗ-16 / HEALTH_ID

Дата среза: 2026-10-13. Репозиторий: [UKZ-16](https://github.com/ashabalin336777-ai/UKZ-16). Модель: `research-v0.2`.

## Статус

Исследовательский контур **инженерно готов** (Phase 1 → 2.5). Клиническая валидность **не заявлена**. Переход к Phase 3 на реальных данных заблокирован внешними входами.

---

## Сделано (можно принимать как research delivery)

### Движок и контракт ТЗ
- [x] HEALTH_ID: веса 0.60 / 0.25 / 0.15, **без перенормировки**
- [x] Статусы компонент: `measured | derived | experimental | missing`
- [x] Отдельные `bmi`, `ap_baevsky`; без роста/веса → `missing_height_weight`
- [x] Нет скрытой импутации; chronic только из EMR/MIS
- [x] Коридор без leakage текущей точки; persistence по уникальным датам
- [x] `diagnosis_claim=false`, employer export → 403 + audit

### API / governance
- [x] Маршруты `/api/v1/health-id/...` (ТЗ §14), idempotency, request-id
- [x] Clinical review pending/confirmed/rejected
- [x] Model card, версии моделей, drift alert (блок 423, без auto-update)
- [x] A16 acceptance mapping + `ukz16-r1` отчёт

### Phase 2 ops
- [x] ЕЦОЗ: mock / fixture / HTTP adapter
- [x] Auth: API-key + OIDC/JWT (Keycloak-ready), compose stub
- [x] Vault KV overlays + seed script
- [x] HMAC signing + Cosign digest bridge
- [x] Experimental HRV / rPPG / voice_SVS (weight 0, не в индекс)
- [x] OTEL optional, No-PHI log filter

### Phase 2.5 data plane
- [x] Lanes: raw / normalized / research / audit
- [x] Псевдонимизация research/audit
- [x] Guidance F16-05 (не диагноз)
- [x] `ukz16-bench` (synthetic p95, без SLA claim)
- [x] `scripts/run_synthetic_e2e.py` (R1→R4+bench)

### Валидация (scaffolds)
- [x] R0 docs + R1 tooling
- [x] R2 / R3 / R4 runners на **синтетике**
- [x] CI: pytest Python 3.12 (50+ tests)

---

## Осталось — только с реальными данными / prod-ops

### Данные и клиника
- [x] Частичный датасет Drive получен — см. [customer_dataset_inventory.md](customer_dataset_inventory.md) (2147 осмотров / 22 сотрудника, 1 сайт)
- [ ] Дозапрос: рост/вес, психометрика, EMR chronic, расшифровка proxy hMental/hSocial
- [ ] Реальная когорта R2 полного объёма + data use agreement
- [ ] Внешние сайты R3 + freeze до enrollment
- [ ] Клиницисты R4: review log, override, time-to-review, net benefit / safety
- [ ] Подписанная приёмка R0/SAP и A16 (человек, не только CI)
- [ ] Пилот на текущем CSV: импорт → прогон UKZ-16 → сравнение с `HEALTH_ID` заказчика

### Интеграции
- [ ] Боевой контур ЕЦОЗ/МИС (контракт полей, токены, стенд)
- [ ] Справочник устройств / единиц / протоколов с площадки
- [ ] Решание: HRV/rPPG/voice — остаются experimental или входят в отдельный протокол

### Production security / ops
- [ ] Keycloak (realm, роли, MFA) — не stub
- [ ] Vault production + ротация секретов
- [ ] TLS/mTLS, шифрование at-rest, backup/restore drill
- [ ] Cosign/Sigstore с реальными ключами (не только digest bridge)
- [ ] Staging p95 / 99.5% на реальном трафике (bench ≠ SLA)

### Организационное
- [ ] Назначить владельца model package и процесс смены версии
- [ ] Согласовать контуры: кто видит research vs audit vs employer aggregates
- [ ] План residual risk по A16-08 / A16-12 (enterprise / MFA)

---

## Как быстро проверить текущий delivery

```bash
pip install -e ".[dev]"
pytest -q
python scripts/run_synthetic_e2e.py
ukz16-r1 --out reports/r1 --skip-pytest
```

Критерий «research ready»: pytest зелёный, e2e synthetic отрабатывает, клинический claim **не** формулируется.
