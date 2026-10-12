# Multi-stage Dockerfile for Identity Lifecycle Platform
# Security Hardening:
# - Multi-stage build to discard build tools and caches
# - Runs as an unprivileged, non-root user
# - Explicit permissions and minimal attack surface

# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Minimal runtime image
FROM python:3.12-slim AS runtime

# Create dedicated non-root user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -m appuser

WORKDIR /app

# Copy installed python libraries from builder stage
COPY --from=builder /install /usr/local

# Copy application source code and OPA policies
COPY src /app/src
COPY policies /app/policies

# Set non-root ownership
RUN chown -R appuser:appgroup /app

# Switch to unprivileged non-root user
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

EXPOSE 8000

# Default command runs the API
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
