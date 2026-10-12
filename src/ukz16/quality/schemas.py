from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import DataFrame, Series


class PrMOVitalsSchema(pa.DataFrameModel):
    """Typed checks for tabular vital extracts (research scaffold)."""

    worker_id: Series[str] = pa.Field(nullable=False)
    encounter_id: Series[str] = pa.Field(nullable=False)
    bp_systolic_mmhg: Series[float] = pa.Field(ge=60, le=260, nullable=True)
    bp_diastolic_mmhg: Series[float] = pa.Field(ge=30, le=160, nullable=True)
    pulse_bpm: Series[float] = pa.Field(ge=30, le=220, nullable=True)
    height_cm: Series[float] = pa.Field(ge=100, le=250, nullable=True)
    weight_kg: Series[float] = pa.Field(ge=30, le=300, nullable=True)

    class Config:
        coerce = True
        strict = False


def vitals_frame_from_payload(payload_dict: dict) -> DataFrame[PrMOVitalsSchema]:
    vitals = payload_dict.get("vitals") or {}
    row = {
        "worker_id": payload_dict["worker_id"],
        "encounter_id": payload_dict["encounter_id"],
        "bp_systolic_mmhg": vitals.get("bp_systolic_mmhg"),
        "bp_diastolic_mmhg": vitals.get("bp_diastolic_mmhg"),
        "pulse_bpm": vitals.get("pulse_bpm"),
        "height_cm": vitals.get("height_cm"),
        "weight_kg": vitals.get("weight_kg"),
    }
    df = pd.DataFrame([row])
    return PrMOVitalsSchema.validate(df)
