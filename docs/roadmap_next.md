# Roadmap after Phase 1

## Phase 1 — done

Research MVP + TZ formula alignment (`research-v0.2`), quality gates, corridors, review, governance stubs, A16 tests.

## Phase 1.5 — done (API / acceptance hardening)

1. TZ §14 routes under `/api/v1/health-id/...` (legacy `/v1/...` kept as deprecated aliases).
2. `Idempotency-Key`, `X-Request-Id`, versioned model-card, `/validation/metrics`.
3. Drift alert can block evaluation (`423`); resolve endpoint unlocks.
4. A16 acceptance protocol: `docs/validation/A16_acceptance_protocol.md`.

## Phase 2 — engineering (in progress / scaffolded)

See `docs/phase2_ops.md`.

1. **ЕЦОЗ adapter** — `HttpEcozAdapter` + mapper + `ingest/{encounter_id}`; modes mock/fixture/http.
2. **AuthN/AuthZ** — OIDC/JWT (Keycloak JWKS) + hybrid API-key fallback. Vault — next ops step.
3. **Artifact signing** — HMAC package.sig now; Sigstore/Cosign production bridge next.
4. **Experimental signals** — HRV/rPPG/voice_SVS slots (`experimental`, weight 0). Real NeuroKit2/openSMILE next.
5. **Observability** — No-PHI log filter + optional OTEL FastAPI instrumentation (`[otel]` extra).

## Phase 3 — validation

1. **R2 scaffold — done:** `ukz16-r2`, synthetic cohort. Real DB_UAI_2026 blocked until data available.
2. **R3 scaffold — done:** model freeze + multi-site transportability runner `ukz16-r3`. Synthetic external sites only.
3. **R4 scaffold — done:** review-log utility metrics `ukz16-r4` (override, time-to-review, net benefit, safety).
4. **Blocked on data/ops:** real R2/R3 cohorts, clinician R4 study, Keycloak/Vault production wiring.

## Hard rules (не снимать)

- Нет скрытой импутации.
- Нет диагноза / допуска / лечения из модуля.
- Нет передачи индивидуального HEALTH_ID работодателю.
- Chronic только из EMR/MIS.
- Drift → alert, не auto-update.
