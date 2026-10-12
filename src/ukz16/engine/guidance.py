from __future__ import annotations

from ukz16.domain.contracts import ClinicalGuidance, EvaluationResult
from ukz16.domain.enums import ComponentStatus, HealthIdStatus


def build_guidance(result: EvaluationResult) -> ClinicalGuidance:
    """F16-05 research guidance: alternative explanation + suggested next step.

    Never suggests diagnosis, fitness-for-work, or treatment.
    """
    codes: list[str] = []
    alts: list[str] = []
    steps: list[str] = []

    if result.health_id.status == HealthIdStatus.NOT_CALCULABLE:
        reason = result.health_id.reason or "insufficient_data"
        codes.append("not_calculable")
        alts.append(f"Индекс не рассчитан: {reason}. Это отсутствие данных/качества, не диагноз.")
        if "missing" in reason or "insufficient" in reason:
            steps.append("Повторить измерение по протоколу с полным набором обязательных полей.")
        if "consent" in reason:
            steps.append("Проверить research consent перед повторным ingest.")
        if "unit" in reason or "protocol" in reason:
            steps.append("Исправить unit_system / protocol_id согласно model package.")

    missing = [c.name for c in result.components if c.status == ComponentStatus.MISSING]
    if missing:
        codes.append("missing_components")
        alts.append("Отсутствуют компоненты: " + ", ".join(missing) + ".")
        if "hMental" in missing:
            steps.append("При наличии согласия собрать валидированную психометрику; без неё hMental остаётся missing.")
        if "bmi" in missing or "ap_baevsky" in missing:
            steps.append("Зафиксировать рост и вес (не предсказывать ИМТ).")

    experimental = [c for c in result.components if c.status == ComponentStatus.EXPERIMENTAL and c.value is not None]
    if experimental:
        codes.append("experimental_present")
        alts.append(
            "Сигналы "
            + ", ".join(c.name for c in experimental)
            + " носят experimental-статус и не входят в HEALTH_ID / hMental."
        )
        steps.append("Не интерпретировать HRV/rPPG/voice_SVS как клиническое решение.")

    if result.acute_state and result.acute_state.is_acute:
        codes.append("acute_flags")
        alts.append(
            "Есть acute-флаги исследовательского контура: "
            + ", ".join(result.acute_state.flags or ["unspecified"])
            + ". Это не допуск/отвод."
        )
        steps.append("Передать кейс медицинскому работнику на clinical-review (pending → confirmed/rejected).")

    if result.personal_deviation and result.personal_deviation.outside_corridor:
        codes.append("personal_corridor")
        alts.append("Значение вне персонального коридора (research signal), не клинический вердикт.")
        steps.append("Сверить качество сигнала и историю уникальных дат persistence.")

    if result.uncertainty.score is not None and result.uncertainty.score >= 0.3:
        codes.append("high_uncertainty")
        alts.append(f"Неопределённость повышена (score={result.uncertainty.score}).")
        steps.append("Дозаполнить required fields до повторного расчёта.")

    if not alts:
        alts.append("Расчёт выполнен в research-режиме; explanation contract в evidence/components.")
    if not steps:
        steps.append("При необходимости оформить clinical-review; индивидуальный HEALTH_ID работодателю не передавать.")

    # Deduplicate preserving order
    steps = list(dict.fromkeys(steps))
    return ClinicalGuidance(
        alternative_explanation=" ".join(alts),
        suggested_next_step=" ".join(steps),
        codes=codes,
    )
