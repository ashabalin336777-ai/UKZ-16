from __future__ import annotations

from pathlib import Path
from typing import Any


R0_ARTIFACTS: list[dict[str, str]] = [
    {"path": "docs/intended_use.md", "title": "Intended use"},
    {"path": "docs/data_dictionary.md", "title": "Data dictionary"},
    {"path": "docs/formula_candidates.md", "title": "Formula candidates"},
    {"path": "docs/missing_quality_policy.md", "title": "Missing/quality policy"},
    {"path": "docs/model_card.md", "title": "Model card"},
    {"path": "docs/validation/R0_protocol.md", "title": "R0 protocol"},
    {"path": "docs/validation/A16_acceptance_protocol.md", "title": "A16 protocol"},
    {"path": "models/health_id/research-v0.2/model.yaml", "title": "Active model package"},
]

A16_ITEMS: list[dict[str, Any]] = [
    {
        "id": "A16-01",
        "criterion": "Воспроизводимость",
        "artifact": "tests/golden/test_a16_acceptance.py::test_a16_deterministic_same_inputs_same_hash_and_trace",
        "status": "covered",
    },
    {
        "id": "A16-02",
        "criterion": "Нет роста/веса → missing_height_weight",
        "artifact": "test_a16_missing_height_weight",
        "status": "covered",
    },
    {
        "id": "A16-03",
        "criterion": "Нет психометрики → hMental missing; SVS experimental",
        "artifact": "test_a16_no_psychometrics_hmental_not_calculable",
        "status": "covered",
    },
    {
        "id": "A16-04",
        "criterion": "Same-day repeats не умножают persistence",
        "artifact": "test_a16_same_day_repeats_do_not_increase_persistence",
        "status": "covered",
    },
    {
        "id": "A16-05",
        "criterion": "Future leakage ловится тестом",
        "artifact": "test_a16_future_leakage_and_patient_split",
        "status": "covered",
    },
    {
        "id": "A16-06",
        "criterion": "Worker не в train/test одновременно",
        "artifact": "test_a16_future_leakage_and_patient_split",
        "status": "covered",
    },
    {
        "id": "A16-07",
        "criterion": "Объяснимость output contract",
        "artifact": "test_a16_output_contract_fields",
        "status": "covered",
    },
    {
        "id": "A16-08",
        "criterion": "Нет индивидуальных HEALTH_ID работодателю",
        "artifact": "test_a16_api_employer_export_forbidden",
        "status": "partial",
        "notes": "API deny; enterprise contour out of scope",
    },
    {
        "id": "A16-09",
        "criterion": "Нет диагноза/допуска; human review",
        "artifact": "test_a16_review_pending_confirmed_rejected",
        "status": "covered",
    },
    {
        "id": "A16-10",
        "criterion": "Drift → alert, может блокировать расчёт",
        "artifact": "test_a16_drift_blocks_evaluation",
        "status": "covered",
    },
    {
        "id": "A16-11",
        "criterion": "Unknown unit / bad protocol блокируют",
        "artifact": "test_a16_unknown_unit_and_bad_protocol_block",
        "status": "covered",
    },
    {
        "id": "A16-12",
        "criterion": "ИБ: роли, MFA, шифрование, backup, согласие",
        "artifact": "API roles + consent gate",
        "status": "partial",
        "notes": "MFA/encryption/backup outside research Phase 1–2",
    },
]


def evaluate_r0_artifacts(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in R0_ARTIFACTS:
        path = root / item["path"]
        rows.append(
            {
                "path": item["path"],
                "title": item["title"],
                "present": path.is_file(),
            }
        )
    return rows
