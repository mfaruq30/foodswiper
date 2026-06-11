# Cloud Run container for the Munch recommendation service.
#
# Why Cloud Run: its always-free tier (2M requests/month, no expiry) is the
# only verified $0 home for this service in 2026 — Fly.io and Railway, named
# in the original spec, no longer have free tiers (docs/DECISIONS.md D-002).
FROM python:3.12-slim

WORKDIR /srv

# Install the package itself (hatchling build) — no requirements.txt drift.
COPY pyproject.toml ./
COPY app ./app
COPY evalharness ./evalharness
RUN pip install --no-cache-dir .

# Cloud Run injects $PORT; 8080 is the convention for local `docker run`.
ENV PORT=8080

# One uvicorn worker: Cloud Run scales horizontally with instances, not
# in-process workers, and the free tier bills per instance-time.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
