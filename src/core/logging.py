"""Structured JSON logging with security redaction and correlation ID propagation.

Design Requirements:
- Do NOT log tokens, passwords, authorization headers, or sensitive personal data.
- Attach correlation ID to all log events for distributed tracing across API and Pub/Sub workers.
- Format output as machine-readable JSON suitable for Google Cloud Logging / Splunk.
"""

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variable for distributed request correlation ID
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Patterns for sensitive field detection
SENSITIVE_KEY_PATTERNS = [
    re.compile(r"pass(word)?", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"auth(orization)?", re.IGNORECASE),
    re.compile(r"bearer", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"ssn", re.IGNORECASE),
]

REDACTED_VALUE = "[REDACTED_SENSITIVE_DATA]"


def sanitize_data(data: Any) -> Any:
    """Recursively scrub sensitive keys and token-like patterns from dictionaries/lists."""
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if any(pattern.search(str(key)) for pattern in SENSITIVE_KEY_PATTERNS):
                sanitized[key] = REDACTED_VALUE
            else:
                sanitized[key] = sanitize_data(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, str):
        # Redact JWT token strings (header.payload.signature pattern)
        if re.match(r"^eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}$", data):
            return "[REDACTED_JWT_TOKEN]"
        return data
    return data


class StructuredJsonFormatter(logging.Formatter):
    """Custom logging formatter that produces Google Cloud Logging compatible JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_ctx.get() or getattr(record, "correlation_id", None) or "none",
            "sourceLocation": {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            },
        }

        # Include additional structured attributes passed in extra={}
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_entry["details"] = sanitize_data(record.extra_fields)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure root logger with JSON output and sensitive data sanitization."""
    logger = logging.getLogger("identity_orchestrator")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Avoid duplicate handlers if re-initialized
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get named logger inheriting structured JSON configuration."""
    if name:
        return logging.getLogger(f"identity_orchestrator.{name}")
    return logger
