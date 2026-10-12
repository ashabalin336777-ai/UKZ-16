from __future__ import annotations

import logging
from typing import Any

from ukz16.config import get_settings

logger = logging.getLogger("ukz16")


class NoPhiFilter(logging.Filter):
    """Drop log records that look like they contain PHI field names."""

    BLOCKED = (
        "health_id.value",
        "bp_systolic",
        "bp_diastolic",
        "pulse_bpm",
        "height_cm",
        "weight_kg",
        "psychometrics",
        "diagnosis",
        "svs",
    )

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        msg = str(record.getMessage()).lower()
        return not any(token in msg for token in self.BLOCKED)


def setup_telemetry(app: Any | None = None) -> dict[str, Any]:
    """Configure logging/OTEL without PHI in technical logs.

    When otel_enabled=false, only installs NoPhiFilter on ukz16 logger.
    """
    settings = get_settings()
    handler = logging.StreamHandler()
    handler.addFilter(NoPhiFilter())
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    status = {"otel_enabled": False, "phi_filter": True, "service_name": settings.otel_service_name}
    if not settings.otel_enabled:
        return status

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        resource = Resource.create({"service.name": settings.otel_service_name})
        provider = TracerProvider(resource=resource)
        # Default to console exporter in research; OTLP wired when endpoint set
        if settings.otel_exporter_otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter: Any = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        else:
            exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        if app is not None:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz")

        status["otel_enabled"] = True
        status["exporter"] = "otlp" if settings.otel_exporter_otlp_endpoint else "console"
    except Exception as exc:  # pragma: no cover - optional dependency path
        logger.warning("otel_setup_failed reason=%s", type(exc).__name__)
        status["otel_enabled"] = False
        status["error"] = type(exc).__name__
    return status
