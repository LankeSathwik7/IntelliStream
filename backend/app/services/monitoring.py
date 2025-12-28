"""Monitoring and observability using Axiom."""

import time
from typing import Dict, Optional, Any
from datetime import datetime
from functools import wraps
import httpx
from app.config import settings


class AxiomClient:
    """Send logs and metrics to Axiom."""

    def __init__(self):
        self.api_url = "https://api.axiom.co/v1/datasets"
        self.token = settings.axiom_token
        self.dataset = settings.axiom_dataset
        self.org_id = settings.axiom_org_id
        self._enabled = bool(self.token and self.dataset)

    def is_configured(self) -> bool:
        return self._enabled

    async def ingest(self, events: list) -> bool:
        """Ingest events to Axiom."""
        if not self._enabled:
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.api_url}/{self.dataset}/ingest",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                    },
                    json=events
                )
                return response.status_code == 200

        except Exception as e:
            print(f"Axiom ingest error: {e}")
            return False

    async def log(
        self,
        level: str,
        message: str,
        **extra
    ) -> bool:
        """Send a log event to Axiom."""
        event = {
            "_time": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "service": "intellistream",
            **extra
        }
        return await self.ingest([event])


class MetricsCollector:
    """Collect and send metrics to Axiom."""

    def __init__(self):
        self.axiom = AxiomClient()
        self.metrics_buffer: list = []
        self.buffer_size = 10  # Flush after 10 events

    async def record(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict] = None
    ):
        """Record a metric."""
        event = {
            "_time": datetime.utcnow().isoformat(),
            "type": "metric",
            "name": metric_name,
            "value": value,
            "tags": tags or {},
            "service": "intellistream"
        }

        self.metrics_buffer.append(event)

        if len(self.metrics_buffer) >= self.buffer_size:
            await self.flush()

    async def flush(self):
        """Flush metrics buffer to Axiom."""
        if not self.metrics_buffer:
            return

        events = self.metrics_buffer.copy()
        self.metrics_buffer.clear()

        await self.axiom.ingest(events)

    async def record_latency(
        self,
        operation: str,
        latency_ms: float,
        success: bool = True
    ):
        """Record operation latency."""
        await self.record(
            metric_name="latency",
            value=latency_ms,
            tags={
                "operation": operation,
                "success": success
            }
        )

    async def record_agent_execution(
        self,
        agent_name: str,
        action: str,
        latency_ms: float,
        success: bool = True,
        extra: Optional[Dict] = None
    ):
        """Record agent execution metrics."""
        event = {
            "_time": datetime.utcnow().isoformat(),
            "type": "agent_trace",
            "agent": agent_name,
            "action": action,
            "latency_ms": latency_ms,
            "success": success,
            "service": "intellistream",
            **(extra or {})
        }

        self.metrics_buffer.append(event)

        if len(self.metrics_buffer) >= self.buffer_size:
            await self.flush()


class RequestLogger:
    """Log HTTP requests for observability."""

    def __init__(self):
        self.axiom = AxiomClient()

    async def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
        user_id: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Log an HTTP request."""
        event = {
            "_time": datetime.utcnow().isoformat(),
            "type": "request",
            "method": method,
            "path": path,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "user_id": user_id,
            "error": error,
            "service": "intellistream"
        }

        await self.axiom.ingest([event])


# Helper decorator for timing operations
def track_time(operation_name: str):
    """Decorator to track execution time of async functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                latency = (time.time() - start) * 1000
                await metrics_collector.record_latency(
                    operation_name,
                    latency,
                    success=True
                )
                return result
            except Exception as e:
                latency = (time.time() - start) * 1000
                await metrics_collector.record_latency(
                    operation_name,
                    latency,
                    success=False
                )
                raise

        return wrapper
    return decorator


# Singleton instances
axiom_client = AxiomClient()
metrics_collector = MetricsCollector()
request_logger = RequestLogger()


# Simple logging functions
async def log_info(message: str, **extra):
    await axiom_client.log("info", message, **extra)


async def log_warning(message: str, **extra):
    await axiom_client.log("warning", message, **extra)


async def log_error(message: str, **extra):
    await axiom_client.log("error", message, **extra)
