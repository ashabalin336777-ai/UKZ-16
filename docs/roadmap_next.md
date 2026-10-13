# Roadmap УКЗ-16

**Сейчас:** research ready (Phase 1–2.5 + customer pilot + synthetic R2–R4).  
**Дальше:** реальная Phase 3 (R0–R4 с подписями и данными площадки), затем Phase 4 prod.

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

## Phase 2.5 — research data plane & readiness (done)

See `docs/phase25_data_plane.md`.

1. **Lanes** — raw / normalized / research / audit snapshots (`lane_records`).
2. **Pseudonymization** — HMAC subject/encounter pseudo ids (`UKZ16_PSEUDONYM_PEPPER`).
3. **Guidance F16-05** — `EvaluationResult.guidance` (alternative explanation + next step, no diagnosis).
4. **Bench** — `ukz16-bench` synthetic p50/p95/p99 (`sla_claim=false`).
5. **E2E demo** — `scripts/run_synthetic_e2e.py` (R1→R4+bench).
6. **Employer deny audit** — blocked export writes `employer_export_denied`.

## Phase 3 — validation (blocked on real inputs)

1. **R1 analytical — tooling done:** `ukz16-r1` (+ golden/property pytest). Signed acceptance still human.
2. **R2 scaffold — done:** `ukz16-r2`, synthetic cohort. Real cohort blocked until data available.
3. **R3 scaffold — done:** model freeze + multi-site transportability runner `ukz16-r3`. Synthetic external sites only.
4. **R4 scaffold — done:** review-log utility metrics `ukz16-r4`.
5. **Customer CSV pilot (engineering):** `scripts/import_customer_exams.py` — 2147 exams, TZ null HEALTH_ID confirmed; see [customer_pilot.md](stakeholder/customer_pilot.md).
6. **Synthetic enrichment path (engineering):** customer vitals + generated height/weight/psychometrics/EMR/sites → R2/R3/R4 via `scripts/run_customer_enriched_validation.py` — see [customer_enriched_validation.md](stakeholder/customer_enriched_validation.md).
7. **Blocked for clinical claim:** real height/weight/psychometrics/EMR from site, signed R0/SAP/A16, real multi-site + clinicians, production Keycloak/Vault/MFA/TLS.

См. [teamlead_checklist.md](stakeholder/teamlead_checklist.md) и [customer_questions.md](stakeholder/customer_questions.md).

## Hard rules (не снимать)

- Нет скрытой импутации.
- Нет диагноза / допуска / лечения из модуля.
- Нет передачи индивидуального HEALTH_ID работодателю.
- Chronic только из EMR/MIS.
- Drift → alert, не auto-update.
