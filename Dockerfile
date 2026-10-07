# syntax=docker/dockerfile:1
# Human-readable tag + immutable multi-platform digest.
# The digest prevents the base image from silently changing underneath this build.
ARG PYTHON_BASE=python:3.12.15-slim-trixie@sha256:ddb0207ae1f0356c2b724d740769b0c5f5f51cc54a0525178f721825f78fe74c

FROM ${PYTHON_BASE} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements-runtime.txt ./

# Install only runtime dependencies into a separate prefix so test/security
# tooling never needs to enter the final image.
RUN python -m pip install --upgrade pip \
    && python -m pip install --prefix=/install -r requirements-runtime.txt

FROM ${PYTHON_BASE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Stable, non-root numeric identity for the application process.
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --create-home --home-dir /home/app \
       --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder /install/ /usr/local/
COPY --chown=10001:10001 app ./app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
