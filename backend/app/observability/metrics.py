"""Metrics collection with Prometheus-compatible implementation."""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import threading


class MetricType(Enum):
    """Type of metric."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """Container for metric values with labels."""

    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Counter:
    """
    Counter metric that can only increase.

    Useful for counting requests, errors, etc.
    """

    def __init__(self, name: str, description: str, label_names: List[str] = None):
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self._values: Dict[str, float] = {}
        self._lock = threading.Lock()

    def _make_key(self, labels: Dict[str, str]) -> str:
        """Create key from labels."""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def inc(self, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Increment the counter."""
        labels = labels or {}
        key = self._make_key(labels)

        with self._lock:
            self._values[key] = self._values.get(key, 0) + value

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value."""
        labels = labels or {}
        key = self._make_key(labels)
        return self._values.get(key, 0)

    def collect(self) -> List[MetricValue]:
        """Collect all metric values."""
        with self._lock:
            return [
                MetricValue(value=v, labels=dict(pair.split("=") for pair in k.split(",") if pair))
                for k, v in self._values.items()
            ]


class Gauge:
    """
    Gauge metric that can go up and down.

    Useful for current values like queue size, memory usage.
    """

    def __init__(self, name: str, description: str, label_names: List[str] = None):
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self._values: Dict[str, float] = {}
        self._lock = threading.Lock()

    def _make_key(self, labels: Dict[str, str]) -> str:
        """Create key from labels."""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Set gauge value."""
        labels = labels or {}
        key = self._make_key(labels)

        with self._lock:
            self._values[key] = value

    def inc(self, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Increment gauge."""
        labels = labels or {}
        key = self._make_key(labels)

        with self._lock:
            self._values[key] = self._values.get(key, 0) + value

    def dec(self, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Decrement gauge."""
        self.inc(-value, labels)

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value."""
        labels = labels or {}
        key = self._make_key(labels)
        return self._values.get(key, 0)

    def collect(self) -> List[MetricValue]:
        """Collect all metric values."""
        with self._lock:
            return [
                MetricValue(value=v, labels=dict(pair.split("=") for pair in k.split(",") if pair))
                for k, v in self._values.items()
            ]


class Histogram:
    """
    Histogram metric for measuring distributions.

    Useful for request latencies, response sizes.
    """

    DEFAULT_BUCKETS = (
        0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0
    )

    def __init__(
        self,
        name: str,
        description: str,
        label_names: List[str] = None,
        buckets: tuple = None
    ):
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._observations: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def _make_key(self, labels: Dict[str, str]) -> str:
        """Create key from labels."""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Record an observation."""
        labels = labels or {}
        key = self._make_key(labels)

        with self._lock:
            if key not in self._observations:
                self._observations[key] = []
            self._observations[key].append(value)

    def time(self, labels: Optional[Dict[str, str]] = None):
        """Context manager to time operations."""
        return HistogramTimer(self, labels)

    def get_stats(self, labels: Optional[Dict[str, str]] = None) -> Dict:
        """Get histogram statistics."""
        labels = labels or {}
        key = self._make_key(labels)

        with self._lock:
            observations = self._observations.get(key, [])

        if not observations:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}

        return {
            "count": len(observations),
            "sum": sum(observations),
            "avg": sum(observations) / len(observations),
            "min": min(observations),
            "max": max(observations),
            "p50": self._percentile(observations, 50),
            "p95": self._percentile(observations, 95),
            "p99": self._percentile(observations, 99),
        }

    def _percentile(self, data: List[float], p: float) -> float:
        """Calculate percentile."""
        if not data:
            return 0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


class HistogramTimer:
    """Context manager for timing histogram observations."""

    def __init__(self, histogram: Histogram, labels: Optional[Dict[str, str]] = None):
        self.histogram = histogram
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.histogram.observe(duration, self.labels)


class MetricsRegistry:
    """
    Registry for all metrics.

    Provides centralized management and export.
    """

    def __init__(self):
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def counter(
        self,
        name: str,
        description: str,
        label_names: List[str] = None
    ) -> Counter:
        """Create or get a counter metric."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Counter(name, description, label_names)
            return self._metrics[name]

    def gauge(
        self,
        name: str,
        description: str,
        label_names: List[str] = None
    ) -> Gauge:
        """Create or get a gauge metric."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Gauge(name, description, label_names)
            return self._metrics[name]

    def histogram(
        self,
        name: str,
        description: str,
        label_names: List[str] = None,
        buckets: tuple = None
    ) -> Histogram:
        """Create or get a histogram metric."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Histogram(name, description, label_names, buckets)
            return self._metrics[name]

    def collect_all(self) -> Dict[str, Any]:
        """Collect all metrics."""
        result = {}

        with self._lock:
            for name, metric in self._metrics.items():
                if isinstance(metric, Counter):
                    result[name] = {"type": "counter", "values": metric.collect()}
                elif isinstance(metric, Gauge):
                    result[name] = {"type": "gauge", "values": metric.collect()}
                elif isinstance(metric, Histogram):
                    result[name] = {"type": "histogram", "stats": metric.get_stats()}

        return result

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        with self._lock:
            for name, metric in self._metrics.items():
                lines.append(f"# HELP {name} {metric.description}")

                if isinstance(metric, Counter):
                    lines.append(f"# TYPE {name} counter")
                    for mv in metric.collect():
                        labels = ",".join(f'{k}="{v}"' for k, v in mv.labels.items())
                        label_str = "{" + labels + "}" if labels else ""
                        lines.append(f"{name}{label_str} {mv.value}")

                elif isinstance(metric, Gauge):
                    lines.append(f"# TYPE {name} gauge")
                    for mv in metric.collect():
                        labels = ",".join(f'{k}="{v}"' for k, v in mv.labels.items())
                        label_str = "{" + labels + "}" if labels else ""
                        lines.append(f"{name}{label_str} {mv.value}")

                elif isinstance(metric, Histogram):
                    lines.append(f"# TYPE {name} histogram")
                    stats = metric.get_stats()
                    lines.append(f"{name}_count {stats['count']}")
                    lines.append(f"{name}_sum {stats['sum']}")

        return "\n".join(lines)


# Global registry
_registry = MetricsRegistry()


def setup_metrics() -> MetricsRegistry:
    """Setup metrics collection."""
    return _registry


def get_registry() -> MetricsRegistry:
    """Get the global metrics registry."""
    return _registry


# Convenience functions
def counter(name: str, description: str, label_names: List[str] = None) -> Counter:
    """Create or get a counter metric."""
    return _registry.counter(name, description, label_names)


def gauge(name: str, description: str, label_names: List[str] = None) -> Gauge:
    """Create or get a gauge metric."""
    return _registry.gauge(name, description, label_names)


def histogram(
    name: str,
    description: str,
    label_names: List[str] = None,
    buckets: tuple = None
) -> Histogram:
    """Create or get a histogram metric."""
    return _registry.histogram(name, description, label_names, buckets)


# Pre-defined application metrics
request_counter = counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

request_latency = histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

active_requests = gauge(
    "http_requests_active",
    "Number of active HTTP requests",
    ["endpoint"]
)

agent_execution_time = histogram(
    "agent_execution_duration_seconds",
    "Agent execution time in seconds",
    ["agent_name"]
)

rag_retrieval_count = counter(
    "rag_documents_retrieved_total",
    "Total documents retrieved from RAG",
    ["source"]
)

llm_tokens = counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["model", "type"]
)

cache_operations = counter(
    "cache_operations_total",
    "Cache operations",
    ["operation", "result"]
)
