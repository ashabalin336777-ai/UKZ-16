# Roadmap after Phase 1

## Phase 1 — done

Research MVP: engine `research-v0.1`, quality gates, corridors, review, governance stubs, API, A16 tests.

## Phase 2 — next engineering

1. **ЕЦОЗ adapter** — реальный клиент МИС за контрактом `IngestAdapter` (без изменения explanation contract).
2. **AuthN/AuthZ** — Keycloak / OIDC вместо API keys; Vault для секретов.
3. **Artifact signing** — Sigstore/Cosign для model package releases.
4. **Experimental signals** (отдельный контур): HRV (NeuroKit2), rPPG, voice/SVS — только `status=experimental`, не в hMental.
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
