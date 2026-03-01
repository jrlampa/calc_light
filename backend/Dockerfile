# ── STAGE 1: Dependencies ────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system deps needed to compile any C extensions
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Install Python deps into a prefix so they can be COPY'd cleanly
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── STAGE 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runner

# Non-root user for security
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Bring installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source (no test files, no scripts)
COPY app/ ./app/

# Database directory — mounted at runtime
RUN mkdir -p /database && chown app:app /database

USER app

EXPOSE 8000

# Use gunicorn for production resilience; uvicorn workers for async support
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
