"""Distributed tracing with OpenTelemetry-compatible implementation."""

import asyncio
import time
import uuid
from typing import Optional, Dict, Any, Callable, List
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
from contextvars import ContextVar


# Context variables for trace propagation
_current_span: ContextVar[Optional["Span"]] = ContextVar("current_span", default=None)
_current_trace: ContextVar[Optional[str]] = ContextVar("current_trace", default=None)


class SpanKind(Enum):
    """Type of span."""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(Enum):
    """Span status."""

    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanEvent:
    """Event within a span."""

    name: str
    timestamp: float
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """
    Trace span representing a unit of work.

    Compatible with OpenTelemetry span structure.
    """

    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    kind: SpanKind = SpanKind.INTERNAL
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    _token: Optional[Any] = None

    def set_attribute(self, key: str, value: Any):
        """Set a span attribute."""
        self.attributes[key] = value

    def set_status(self, status: SpanStatus, description: Optional[str] = None):
        """Set span status."""
        self.status = status
        if description:
            self.attributes["status_description"] = description

    def add_event(self, name: str, attributes: Optional[Dict] = None):
        """Add an event to the span."""
        self.events.append(SpanEvent(
            name=name,
            timestamp=time.time(),
            attributes=attributes or {}
        ))

    def record_exception(self, exception: Exception):
        """Record an exception event."""
        self.add_event("exception", {
            "exception.type": type(exception).__name__,
            "exception.message": str(exception),
        })
        self.set_status(SpanStatus.ERROR, str(exception))

    def end(self):
        """End the span."""
        self.end_time = time.time()
        if self.status == SpanStatus.UNSET:
            self.status = SpanStatus.OK

    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    def to_dict(self) -> Dict:
        """Convert span to dictionary for export."""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "attributes": self.attributes,
            "events": [
                {"name": e.name, "timestamp": e.timestamp, "attributes": e.attributes}
                for e in self.events
            ]
        }


class SpanExporter:
    """Base class for span exporters."""

    async def export(self, spans: List[Span]):
        """Export spans to backend."""
        raise NotImplementedError


class ConsoleExporter(SpanExporter):
    """Export spans to console for debugging."""

    async def export(self, spans: List[Span]):
        """Print spans to console."""
        for span in spans:
            print(f"[TRACE] {span.name} ({span.duration_ms:.2f}ms) - {span.status.value}")
            if span.attributes:
                for k, v in span.attributes.items():
                    print(f"  {k}: {v}")


class AxiomExporter(SpanExporter):
    """Export spans to Axiom."""

    def __init__(self, token: str, org_id: str, dataset: str):
        self.token = token
        self.org_id = org_id
        self.dataset = dataset
        self.endpoint = f"https://api.axiom.co/v1/datasets/{dataset}/ingest"

    async def export(self, spans: List[Span]):
        """Export spans to Axiom."""
        if not self.token:
            return

        import httpx

        events = [
            {
                "_time": span.start_time,
                "type": "trace",
                **span.to_dict()
            }
            for span in spans
        ]

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.endpoint,
                    json=events,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                    }
                )
        except Exception as e:
            print(f"Failed to export traces to Axiom: {e}")


class Tracer:
    """
    Tracer for creating and managing spans.

    Provides OpenTelemetry-compatible API for distributed tracing.
    """

    def __init__(self, service_name: str, exporters: Optional[List[SpanExporter]] = None):
        self.service_name = service_name
        self.exporters = exporters or []
        self._spans: List[Span] = []
        self._batch_size = 100
        self._flush_interval = 10.0  # seconds

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict] = None,
    ) -> Span:
        """
        Start a new span.

        Args:
            name: Span name
            kind: Span kind
            attributes: Initial attributes

        Returns:
            New span
        """
        # Get or create trace ID
        trace_id = _current_trace.get()
        if not trace_id:
            trace_id = str(uuid.uuid4())
            _current_trace.set(trace_id)

        # Get parent span
        parent = _current_span.get()
        parent_span_id = parent.span_id if parent else None

        # Create span
        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=str(uuid.uuid4())[:16],
            parent_span_id=parent_span_id,
            kind=kind,
            attributes=attributes or {},
        )

        # Set as current span
        span._token = _current_span.set(span)

        # Add service name
        span.set_attribute("service.name", self.service_name)

        return span

    def end_span(self, span: Span):
        """End a span and queue for export."""
        span.end()

        # Restore previous span
        if span._token:
            _current_span.reset(span._token)

        # Add to batch
        self._spans.append(span)

        # Flush if batch is full
        if len(self._spans) >= self._batch_size:
            asyncio.create_task(self.flush())

    async def flush(self):
        """Flush pending spans to exporters."""
        if not self._spans:
            return

        spans = self._spans.copy()
        self._spans.clear()

        for exporter in self.exporters:
            try:
                await exporter.export(spans)
            except Exception as e:
                print(f"Exporter failed: {e}")

    def get_current_span(self) -> Optional[Span]:
        """Get the current active span."""
        return _current_span.get()


# Global tracer instance
_tracer: Optional[Tracer] = None


def setup_tracing(
    service_name: str = "intellistream",
    axiom_token: Optional[str] = None,
    axiom_org_id: Optional[str] = None,
    axiom_dataset: str = "intellistream-traces",
    console_export: bool = False,
) -> Tracer:
    """
    Setup distributed tracing.

    Args:
        service_name: Name of the service
        axiom_token: Axiom API token
        axiom_org_id: Axiom organization ID
        axiom_dataset: Axiom dataset name
        console_export: Enable console export for debugging

    Returns:
        Configured tracer
    """
    global _tracer

    exporters = []

    if console_export:
        exporters.append(ConsoleExporter())

    if axiom_token and axiom_org_id:
        exporters.append(AxiomExporter(axiom_token, axiom_org_id, axiom_dataset))

    _tracer = Tracer(service_name, exporters)
    return _tracer


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer("intellistream")
    return _tracer


def add_span_attributes(attributes: Dict[str, Any]):
    """Add attributes to the current span."""
    span = _current_span.get()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, value)


def record_exception(exception: Exception):
    """Record an exception on the current span."""
    span = _current_span.get()
    if span:
        span.record_exception(exception)


def trace_async(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict] = None,
) -> Callable:
    """
    Decorator to trace async functions.

    Usage:
        @trace_async("my-operation")
        async def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            span = tracer.start_span(span_name, kind, attributes)

            try:
                result = await func(*args, **kwargs)
                span.set_status(SpanStatus.OK)
                return result

            except Exception as e:
                span.record_exception(e)
                raise

            finally:
                tracer.end_span(span)

        return wrapper

    return decorator


def trace_sync(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict] = None,
) -> Callable:
    """
    Decorator to trace sync functions.

    Usage:
        @trace_sync("my-operation")
        def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            span = tracer.start_span(span_name, kind, attributes)

            try:
                result = func(*args, **kwargs)
                span.set_status(SpanStatus.OK)
                return result

            except Exception as e:
                span.record_exception(e)
                raise

            finally:
                tracer.end_span(span)

        return wrapper

    return decorator
