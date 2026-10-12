# Model package schema — research-v0.2

Supersedes `research-v0.1`. The v0.1 package stays in the repo unchanged and is not the runtime default.

## Rules fixed in this version

- No weight renormalization. HEALTH_ID is the exact sum `0.60·hBody + 0.25·hMental + 0.15·hSocial` only when all three components are `derived`.
- Any missing index component → `health_id.value = null`.
- BMI and Baevsky AP are separate indicators. They do not enter hBody or HEALTH_ID.
- Without measured height and weight, BMI and AP are `missing` with reason `missing_height_weight`.
- Component status vocabulary: `measured | derived | experimental | missing`.

## Files

- `model.yaml` — weights, policies, indicators, thresholds
- `normals.yaml` — population reference bands (research)
- `SCHEMA.md` — this file
