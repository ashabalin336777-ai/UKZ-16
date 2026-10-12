# Phase 2 operations

## 1. ECOZ ingest

```bash
# mock (default)
UKZ16_INGEST_MODE=mock

# file fixtures
UKZ16_INGEST_MODE=fixture
UKZ16_ECOZ_FIXTURES_DIR=samples/ecoz

# live MIS
UKZ16_INGEST_MODE=http
UKZ16_ECOZ_BASE_URL=https://ecoz.example/api
UKZ16_ECOZ_TOKEN=***
```

`POST /api/v1/health-id/ingest/{encounter_id}` pulls from the configured adapter and evaluates.

Token may also come from Vault (`ecoz_token` in `UKZ16_VAULT_SECRET_MAP`).

## 2. Auth (Keycloak-ready)

```bash
UKZ16_AUTH_MODE=hybrid   # bearer JWT preferred, API key fallback
UKZ16_OIDC_ISSUER=https://keycloak.example/realms/ukz16
UKZ16_OIDC_AUDIENCE=ukz16-api
UKZ16_OIDC_JWKS_URL=https://keycloak.example/realms/ukz16/protocol/openid-connect/certs
UKZ16_OIDC_ROLE_CLAIM=realm_access.roles
```

Roles: `researcher`, `medical_worker`, `auditor`.

Local stub: `docker compose up keycloak` → http://localhost:8081 (admin/admin). Create realm `ukz16` and client `ukz16-api`.

## 3. Vault secrets

```bash
UKZ16_VAULT_ADDR=http://127.0.0.1:8200
UKZ16_VAULT_TOKEN=ukz16-dev-root
UKZ16_VAULT_MOUNT=secret
UKZ16_VAULT_PATH=ukz16
UKZ16_VAULT_SECRET_MAP=ecoz_token:ukz16/ecoz#token,model_signing_secret:ukz16/signing#hmac
```

Dev Vault: `docker compose up vault` (root token `ukz16-dev-root`). Example seed:

```bash
export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=ukz16-dev-root
vault kv put secret/ukz16/ecoz token=dev-ecoz-token
vault kv put secret/ukz16/signing hmac=dev-hmac-secret
```

Without Vault, env vars (`UKZ16_ECOZ_TOKEN`, `UKZ16_MODEL_SIGNING_SECRET`) remain the fallback.

## 4. Model package signing

HMAC (default) or Cosign digest bridge:

```bash
UKZ16_SIGNING_MODE=hmac          # or cosign
UKZ16_MODEL_SIGNING_SECRET=***   # hmac mode / Vault map
UKZ16_REQUIRE_SIGNED_MODEL=false
```

- HMAC: writes `package.sig`
- Cosign: writes `package.digest` + `COSIGN.md`; sign/verify with `cosign sign-blob` / `verify-blob` and `package.sig.bundle`

`POST /api/v1/health-id/models/{version}/sign`  
`GET /api/v1/health-id/models/{version}/signature`

## 5. Experimental signals

HRV / rPPG / voice_SVS always `experimental`, weight 0, never enter hMental or HEALTH_ID.

Pass optional `experimental_signals` on ingest:

```json
{
  "experimental_signals": {
    "hrv": {
      "consent_scope": "research_hrv",
      "nn_intervals_ms": [800, 820, 790, 810],
      "protocol_version": "hrv-r0",
      "device_id": "PPG-1"
    },
    "rppg": {
      "consent_scope": "research_rppg",
      "signal": [0.1, 0.2, 0.15],
      "sampling_rate": 30,
      "device_id": "CAM-1"
    },
    "voice": {
      "consent_scope": "research_voice",
      "f0_hz": 155,
      "jitter_pct": 0.8,
      "shimmer_pct": 2.0,
      "hnr_db": 18
    }
  }
}
```

- HRV: NN intervals or optional NeuroKit2 (`pip install -e ".[hrv]"`, `use_neurokit` + `signal`)
- rPPG: waveform peaks or `bpm_estimate`
- voice_SVS: acoustic scalars or external `svs_score` (openSMILE upstream; not bundled)

## 5b. Vault seed (dev)

```bash
docker compose up -d vault
python scripts/seed_vault_dev.py
```

## 5c. R0/R1 analytical report

```bash
ukz16-r1 --out reports/r1
# checklist only:
ukz16-r1 --out reports/r1 --skip-pytest
```

## 6. Observability

```bash
UKZ16_OTEL_ENABLED=true
UKZ16_OTEL_SERVICE_NAME=ukz16-api
UKZ16_OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
pip install -e ".[otel]"
```

PHI field names are filtered from `ukz16` technical logs.
