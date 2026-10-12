# Roadmap after Phase 1

## Phase 1 — done

Research MVP + TZ formula alignment (`research-v0.2`), quality gates, corridors, review, governance stubs, A16 tests.

## Phase 1.5 — done (API / acceptance hardening)

1. TZ §14 routes under `/api/v1/health-id/...` (legacy `/v1/...` kept as deprecated aliases).
2. `Idempotency-Key`, `X-Request-Id`, versioned model-card, `/validation/metrics`.
3. Drift alert can block evaluation (`423`); resolve endpoint unlocks.
4. A16 acceptance protocol: `docs/validation/A16_acceptance_protocol.md`.

## Phase 2 — next engineering

1. **ЕЦОЗ adapter** — реальный клиент МИС за контрактом `IngestAdapter` (без изменения explanation contract).
2. **AuthN/AuthZ** — Keycloak / OIDC вместо API keys; Vault для секретов.
3. **Artifact signing** — Sigstore/Cosign для model package releases.
4. **Experimental signals** (отдельный контур): HRV (NeuroKit2), rPPG; voice/SVS placeholder уже `experimental` и не входит в hMental — нужна реальная feature pipeline.
5. **Observability** — OpenTelemetry без PHI в логах.

## Phase 3 — validation

1. Заполнить и исполнить R2 на ретроспективной когорте (group holdout, calibration).
2. R3 внешняя проспективная площадка.
3. R4 clinical utility (human-AI team, net benefit).

## Hard rules (не снимать)

- Нет скрытой импутации.
- Нет диагноза / допуска / лечения из модуля.
- Нет передачи индивидуального HEALTH_ID работодателю.
- Chronic только из EMR/MIS.
- Drift → alert, не auto-update.
