from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.helpers import make_prmo
from ukz16.engine.calculator import evaluate_health_id
from ukz16.governance.model_registry import load_model_package
from ukz16.quality.gates import run_quality_gates


@given(
    pulse=st.floats(min_value=40, max_value=180, allow_nan=False, allow_infinity=False),
    sbp=st.floats(min_value=80, max_value=200, allow_nan=False, allow_infinity=False),
    dbp=st.floats(min_value=40, max_value=120, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=30, deadline=None)
def test_property_deterministic_evaluation(pulse: float, sbp: float, dbp: float):
    model = load_model_package()
    payload = make_prmo(encounter_id="HYP-1", pulse=pulse, sbp=sbp, dbp=dbp)
    q = run_quality_gates(payload, model)
    a = evaluate_health_id(payload, q, model)
    b = evaluate_health_id(payload, q, model)
    assert a.health_id.value == b.health_id.value
    assert a.evidence.input_hash == b.evidence.input_hash
    assert a.evidence.contribution_trace == b.evidence.contribution_trace
    assert a.diagnosis_claim is False
