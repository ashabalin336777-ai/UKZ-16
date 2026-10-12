# Архитектура и стек — для заказчика (кратко)

**Проект:** УКЗ-16 — исследовательская система клинической валидации индекса **HEALTH_ID**  
**Назначение:** воспроизводимый расчёт и валидация на данных ПрМО.  
**Важно:** research use only — модуль **не ставит диагноз**, **не выдаёт допуск**, **не передаёт индивидуальный HEALTH_ID работодателю**.

---

## Зачем система

1. Принять измерение (ПрМО) из ЕЦОЗ/МИС или стенда.  
2. Проверить качество и протокол.  
3. Посчитать версионированный HEALTH_ID с объяснением для врача.  
4. Дать human review и аудит.  
5. Готовить отчёты валидации R0–R4 (сейчас — на синтетике; клиника — после реальных данных).

---

## Архитектура (логические блоки)

```
ЕЦОЗ / МИС / fixtures
        │
        ▼
   Ingest adapter          ← mock | file fixture | HTTP
        │
        ▼
   Quality gates           ← согласие, единицы, протокол, полнота
        │
        ▼
   HEALTH_ID engine        ← model package research-v0.2
   (hBody / hMental / hSocial + bmi / AP; experimental отдельно)
        │
        ├── API (FastAPI)  ← researcher / medical_worker / auditor
        ├── Clinical review
        ├── Governance     ← model card, drift, подпись пакета
        └── Data lanes     ← raw → normalized → research → audit
```

**Контуры данных**

| Контур | Смысл |
|--------|--------|
| Operational | рабочие ID, расчёт, review |
| Research | псевдонимизированные снимки для анализа |
| Audit | факты доступа/событий без значений виталов |
| Employer | **закрыт** для индивидуального HEALTH_ID |

**Экспериментальные сигналы** (HRV, rPPG, voice/SVS) считаются отдельно, вес 0, в индекс и hMental **не входят**.

---

## Стек технологий

| Слой | Технологии |
|------|------------|
| Язык / API | Python 3.12, FastAPI, Pydantic, Uvicorn |
| Данные | PostgreSQL (prod-like), SQLite (dev/tests), SQLAlchemy, Alembic |
| Auth | API-keys (dev) + OIDC/JWT (Keycloak JWKS) |
| Secrets | HashiCorp Vault KV v2 (env fallback) |
| Signing | HMAC package.sig; мост Cosign/Sigstore |
| Observability | structured logs + No-PHI filter; optional OpenTelemetry |
| Валидация | pytest, Hypothesis; CLI `ukz16-r1`…`r4`, `ukz16-bench` |
| Packaging | Docker Compose (API, Postgres, Vault stub, Keycloak stub) |
| CI | GitHub Actions |

---

## Что уже есть vs что требует заказчика

| Уже в репозитории | Нужно от площадки / заказчика |
|-------------------|-------------------------------|
| Движок, API, тесты, synthetic R1–R4 | Реальная когорта и согласия |
| Адаптер ЕЦОЗ (контракт) | Доступ к стенду/бою ЕЦОЗ |
| Keycloak/Vault stubs | Production IAM, MFA, TLS, backup |
| Research/audit lanes | Политика хранения и сроки |
| Model package v0.2 | Утверждение формул и норм после R2–R4 |

Подробный список вопросов — в [customer_questions.md](customer_questions.md).  
Чек-лист для команды — в [teamlead_checklist.md](teamlead_checklist.md).
