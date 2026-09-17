# MotoDiag API container (Phase 209).
#
# Multi-stage: the wheel is built in a throwaway layer so no build
# toolchain, source tree or test suite reaches the runtime image.
#
# NOT YET BUILT OR RUN. Docker was unavailable on the machine this was
# written on, so `docker build` has never executed against this file.
# What IS verified, outside a container: the wheel installs with the
# `api` extra into a clean environment, `motodiag serve` starts from it,
# and `/healthz` and `/v1/version` both answer 200 — the same commands
# this image runs. Treat the container mechanics (layer copy, user, volume,
# healthcheck wiring) as unreviewed until someone builds it. See F76.
#
# Phase 209B changed three things below, and verified what it could without
# Docker: the shell-glob fix (reproduced and fixed under /bin/sh), the
# `server` extra (a clean-wheel test installs it and renders a PDF), and
# ffmpeg (NOT verified -- there is no Docker here).

# ---------- build ----------
FROM python:3.13-slim AS builder

WORKDIR /build
RUN pip install --no-cache-dir build

# Copy only what the wheel needs. `src/` carries the packaged seed data
# (~1.5 MB of DTCs and known issues) since Phase 209 — the knowledge
# base is part of the package, not a mounted volume.
COPY pyproject.toml MANIFEST.in README.md LICENSE ./
COPY src/ ./src/

RUN python -m build --wheel --outdir /dist

# ---------- runtime ----------
FROM python:3.13-slim AS runtime

# ffmpeg is a system binary pip can't provide. Without it every video
# upload returns 503 -- the vision sweep and Ask are both dead. Added by
# Phase 209B and exactly as unverified as the rest of this file.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# `server` is the whole server: api + ai + vision + push + reports. This line used to
# say [api,vision,push] and left out `ai`, so the container could not call
# Claude or Whisper at all.
#
# The wheel path is resolved BEFORE the extras are appended. The previous
# form, `pip install /tmp/*.whl[api,vision,push]`, never worked: to /bin/sh
# the brackets are a glob character class, so the pattern matched nothing and
# went through literally, and pip rejected the `*` ("Invalid wheel filename").
# Reproduced under /bin/sh without Docker by Phase 209B. `docker build` had
# never been run, so nobody had seen it fail.
COPY --from=builder /dist/*.whl /tmp/
RUN set -eu; whl="$(ls /tmp/*.whl)"; \
    pip install --no-cache-dir "${whl}[server]"; \
    rm -f /tmp/*.whl

# Non-root. The data directory is created and owned before the drop, so
# the volume mount lands somewhere writable.
RUN useradd --create-home --uid 10001 motodiag \
    && mkdir -p /var/lib/motodiag \
    && chown -R motodiag:motodiag /var/lib/motodiag
USER motodiag

# Explicit, not the platform default: inside a container "the user's
# data directory" should be the mounted volume, and nothing else.
ENV MOTODIAG_DB_PATH=/var/lib/motodiag/motodiag.db \
    MOTODIAG_API_HOST=0.0.0.0 \
    MOTODIAG_API_PORT=8000 \
    PYTHONUNBUFFERED=1

VOLUME ["/var/lib/motodiag"]
EXPOSE 8000

# `motodiag serve` applies pending migrations before binding, so a fresh
# volume is initialised on first boot without a separate entrypoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"

CMD ["motodiag", "serve"]
