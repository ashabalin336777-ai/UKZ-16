# Phase 2.5 — Research data plane & readiness

Цель: закрыть TZ-пробелы, которые можно сделать **без реальной когорты**: схемы контуров, псевдонимизация, guidance F16-05, синтетический latency bench, e2e demo.

## 1. Data lanes

На каждый evaluate пишутся 4 снимка (`lane_records`, `UKZ16_PERSIST_LANES=true`):

| Lane | Содержимое |
|------|------------|
| `raw` | исходный envelope |
| `normalized` | валидированный PrMO + quality |
| `research` | `subject_pseudo_id` + vitals/components (не для работодателя) |
| `audit` | actor/request/model/status **без** значений виталов и HEALTH_ID |

## 2. Pseudonymization

```bash
UKZ16_PSEUDONYM_PEPPER=***
# или Vault map: pseudonym_pepper:ukz16/privacy#pepper
```

HMAC-SHA256 → `sub_<32 hex>`. Operational `worker_id` в API/таблицах сохраняется; research/audit используют pseudo id.

## 3. Guidance (F16-05)

`EvaluationResult.guidance`:

- `alternative_explanation` — почему индекс/компонент неполный или flagged
- `suggested_next_step` — research next action
- **никогда** не ставит диагноз / допуск / лечение

## 4. Bench (не SLA)

```bash
ukz16-bench --out reports/bench --n 200
```

p50/p95/p99 CPU-path. `sla_claim=false`.

## 5. Synthetic e2e

```bash
python scripts/run_synthetic_e2e.py
```

R1 checklist → R2 → R3 → R4 → bench под `reports/e2e/`.
