"""Observability module with OpenTelemetry integration."""

from app.observability.tracing import (
    setup_tracing,
    get_tracer,
    trace_async,
    trace_sync,
    add_span_attributes,
    record_exception,
)
from app.observability.metrics import (
    setup_metrics,
    counter,
    histogram,
    gauge,
    MetricsRegistry,
)
from app.observability.logging import (
    setup_structured_logging,
    get_logger,
    log_with_context,
    LogLevel,
)

__all__ = [
    "setup_tracing",
    "get_tracer",
    "trace_async",
    "trace_sync",
    "add_span_attributes",
    "record_exception",
    "setup_metrics",
    "counter",
    "histogram",
    "gauge",
    "MetricsRegistry",
    "setup_structured_logging",
    "get_logger",
    "log_with_context",
    "LogLevel",
]
