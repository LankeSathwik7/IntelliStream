"""Structured logging with context propagation."""

import json
import sys
import time
import logging
from typing import Dict, Any, Optional
from enum import Enum
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from functools import wraps


# Context variables for log correlation
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


class LogLevel(Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEvent:
    """Structured log event."""

    level: str
    message: str
    timestamp: float = field(default_factory=time.time)
    logger: str = "intellistream"

    # Context
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    trace_id: Optional[str] = None

    # Additional fields
    extra: Dict[str, Any] = field(default_factory=dict)

    # Error info
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp,
            "logger": self.logger,
        }

        if self.request_id:
            result["request_id"] = self.request_id
        if self.user_id:
            result["user_id"] = self.user_id
        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.extra:
            result.update(self.extra)
        if self.error_type:
            result["error"] = {
                "type": self.error_type,
                "message": self.error_message,
                "stack_trace": self.stack_trace,
            }

        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class StructuredLogger:
    """
    Structured logger with JSON output and context propagation.

    Designed for cloud-native environments (ELK, Datadog, Axiom).
    """

    def __init__(
        self,
        name: str = "intellistream",
        level: LogLevel = LogLevel.INFO,
        json_output: bool = True,
    ):
        self.name = name
        self.level = level
        self.json_output = json_output
        self._handlers = []

    def _should_log(self, level: LogLevel) -> bool:
        """Check if level should be logged."""
        levels = list(LogLevel)
        return levels.index(level) >= levels.index(self.level)

    def _get_context(self) -> Dict:
        """Get current context."""
        return {
            "request_id": _request_id.get(),
            "user_id": _user_id.get(),
            "trace_id": _trace_id.get(),
        }

    def _emit(self, event: LogEvent):
        """Emit log event."""
        if self.json_output:
            output = event.to_json()
        else:
            # Human-readable format
            ctx = []
            if event.request_id:
                ctx.append(f"req={event.request_id[:8]}")
            if event.user_id:
                ctx.append(f"user={event.user_id[:8]}")

            ctx_str = f"[{' '.join(ctx)}] " if ctx else ""
            output = f"{event.level} | {ctx_str}{event.message}"

            if event.extra:
                output += f" | {event.extra}"

        # Write to stdout
        print(output, file=sys.stdout, flush=True)

        # Call handlers
        for handler in self._handlers:
            try:
                handler(event)
            except Exception:
                pass

    def add_handler(self, handler):
        """Add a log handler."""
        self._handlers.append(handler)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        if self._should_log(LogLevel.DEBUG):
            context = self._get_context()
            event = LogEvent(
                level="DEBUG",
                message=message,
                logger=self.name,
                request_id=context["request_id"],
                user_id=context["user_id"],
                trace_id=context["trace_id"],
                extra=kwargs
            )
            self._emit(event)

    def info(self, message: str, **kwargs):
        """Log info message."""
        if self._should_log(LogLevel.INFO):
            context = self._get_context()
            event = LogEvent(
                level="INFO",
                message=message,
                logger=self.name,
                request_id=context["request_id"],
                user_id=context["user_id"],
                trace_id=context["trace_id"],
                extra=kwargs
            )
            self._emit(event)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        if self._should_log(LogLevel.WARNING):
            context = self._get_context()
            event = LogEvent(
                level="WARNING",
                message=message,
                logger=self.name,
                request_id=context["request_id"],
                user_id=context["user_id"],
                trace_id=context["trace_id"],
                extra=kwargs
            )
            self._emit(event)

    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message."""
        if self._should_log(LogLevel.ERROR):
            import traceback

            context = self._get_context()
            event = LogEvent(
                level="ERROR",
                message=message,
                logger=self.name,
                request_id=context["request_id"],
                user_id=context["user_id"],
                trace_id=context["trace_id"],
                extra=kwargs
            )

            if exception:
                event.error_type = type(exception).__name__
                event.error_message = str(exception)
                event.stack_trace = traceback.format_exc()

            self._emit(event)

    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log critical message."""
        if self._should_log(LogLevel.CRITICAL):
            import traceback

            context = self._get_context()
            event = LogEvent(
                level="CRITICAL",
                message=message,
                logger=self.name,
                request_id=context["request_id"],
                user_id=context["user_id"],
                trace_id=context["trace_id"],
                extra=kwargs
            )

            if exception:
                event.error_type = type(exception).__name__
                event.error_message = str(exception)
                event.stack_trace = traceback.format_exc()

            self._emit(event)


# Global logger instance
_logger: Optional[StructuredLogger] = None


def setup_structured_logging(
    name: str = "intellistream",
    level: LogLevel = LogLevel.INFO,
    json_output: bool = True,
) -> StructuredLogger:
    """
    Setup structured logging.

    Args:
        name: Logger name
        level: Minimum log level
        json_output: Use JSON format

    Returns:
        Configured logger
    """
    global _logger
    _logger = StructuredLogger(name, level, json_output)
    return _logger


def get_logger() -> StructuredLogger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = StructuredLogger()
    return _logger


def set_request_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None,
):
    """Set logging context for current request."""
    if request_id:
        _request_id.set(request_id)
    if user_id:
        _user_id.set(user_id)
    if trace_id:
        _trace_id.set(trace_id)


def clear_request_context():
    """Clear logging context."""
    _request_id.set(None)
    _user_id.set(None)
    _trace_id.set(None)


def log_with_context(
    level: LogLevel,
    message: str,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs
):
    """Log with explicit context."""
    logger = get_logger()

    # Temporarily set context
    old_request_id = _request_id.get()
    old_user_id = _user_id.get()

    if request_id:
        _request_id.set(request_id)
    if user_id:
        _user_id.set(user_id)

    try:
        if level == LogLevel.DEBUG:
            logger.debug(message, **kwargs)
        elif level == LogLevel.INFO:
            logger.info(message, **kwargs)
        elif level == LogLevel.WARNING:
            logger.warning(message, **kwargs)
        elif level == LogLevel.ERROR:
            logger.error(message, **kwargs)
        elif level == LogLevel.CRITICAL:
            logger.critical(message, **kwargs)
    finally:
        # Restore context
        _request_id.set(old_request_id)
        _user_id.set(old_user_id)


class LoggingMiddleware:
    """
    Middleware for automatic request logging.

    Logs request start/end with timing and context.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import uuid

        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        set_request_context(request_id=request_id)

        logger = get_logger()
        start_time = time.time()

        # Get request info
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        logger.info(
            f"Request started: {method} {path}",
            method=method,
            path=path,
        )

        # Track response status
        response_status = 0

        async def send_wrapper(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)

        except Exception as e:
            logger.error(
                f"Request failed: {method} {path}",
                exception=e,
                method=method,
                path=path,
            )
            raise

        finally:
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Request completed: {method} {path} {response_status}",
                method=method,
                path=path,
                status=response_status,
                duration_ms=round(duration_ms, 2),
            )
            clear_request_context()
