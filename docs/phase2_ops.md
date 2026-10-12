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

## 2. Auth (Keycloak-ready)

```bash
UKZ16_AUTH_MODE=hybrid   # bearer JWT preferred, API key fallback
UKZ16_OIDC_ISSUER=https://keycloak.example/realms/ukz16
UKZ16_OIDC_AUDIENCE=ukz16-api
UKZ16_OIDC_JWKS_URL=https://keycloak.example/realms/ukz16/protocol/openid-connect/certs
UKZ16_OIDC_ROLE_CLAIM=realm_access.roles
```

Roles: `researcher`, `medical_worker`, `auditor`.

## 3. Model package signing

Research HMAC (bridge to Sigstore/Cosign later):

```bash
UKZ16_MODEL_SIGNING_SECRET=***
UKZ16_REQUIRE_SIGNED_MODEL=false
```

`POST /api/v1/health-id/models/{version}/sign`  
`GET /api/v1/health-id/models/{version}/signature`

## 4. Experimental signals

HRV / rPPG / voice_SVS always `experimental`, weight 0, never enter hMental or HEALTH_ID. Real NeuroKit2/openSMILE pipelines replace `ukz16.experimental.signals`.

## 5. Observability

```bash
UKZ16_OTEL_ENABLED=true
UKZ16_OTEL_SERVICE_NAME=ukz16-api
UKZ16_OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
pip install -e ".[otel]"
```

PHI field names are filtered from `ukz16` technical logs.
