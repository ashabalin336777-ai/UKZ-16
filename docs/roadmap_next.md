# Roadmap after Phase 1

## Phase 1 — done

Research MVP + TZ formula alignment (`research-v0.2`), quality gates, corridors, review, governance stubs, A16 tests.

## Phase 1.5 — done (API / acceptance hardening)

1. TZ §14 routes under `/api/v1/health-id/...` (legacy `/v1/...` kept as deprecated aliases).
2. `Idempotency-Key`, `X-Request-Id`, versioned model-card, `/validation/metrics`.
3. Drift alert can block evaluation (`423`); resolve endpoint unlocks.
4. A16 acceptance protocol: `docs/validation/A16_acceptance_protocol.md`.

## Phase 2 — engineering (done for research contour)

See `docs/phase2_ops.md`.

1. **ЕЦОЗ adapter** — `HttpEcozAdapter` + mapper + `ingest/{encounter_id}`; modes mock/fixture/http.
2. **AuthN/AuthZ** — OIDC/JWT (Keycloak JWKS) + hybrid API-key fallback. Compose Keycloak stub.
3. **Vault** — KV v2 client + `UKZ16_VAULT_SECRET_MAP` overrides; env fallback; `scripts/seed_vault_dev.py`.
4. **Artifact signing** — HMAC `package.sig`; Cosign digest bridge (`signing_mode=cosign`).
5. **Experimental signals** — HRV / rPPG / voice_SVS research extractors (weight 0, never HEALTH_ID/hMental).
6. **Observability** — No-PHI log filter + optional OTEL FastAPI instrumentation (`[otel]` extra).
7. **R0/R1 report** — `ukz16-r1` writes A16 checklist + optional pytest freeze (`reports/r1`).

## Phase 3 — validation

1. **R1 analytical — tooling done:** `ukz16-r1` (+ golden/property pytest). Signed acceptance still human.
2. **R2 scaffold — done:** `ukz16-r2`, synthetic cohort. Real DB_UAI_2026 blocked until data available.
3. **R3 scaffold — done:** model freeze + multi-site transportability runner `ukz16-r3`. Synthetic external sites only.
4. **R4 scaffold — done:** review-log utility metrics `ukz16-r4` (override, time-to-review, net benefit, safety).
5. **Blocked on data/ops:** real R2/R3 cohorts, clinician R4 study, production Keycloak/Vault/MFA/TLS.

## Hard rules (не снимать)

- Нет скрытой импутации.
- Нет диагноза / допуска / лечения из модуля.
- Нет передачи индивидуального HEALTH_ID работодателю.
- Chronic только из EMR/MIS.
- Drift → alert, не auto-update.
