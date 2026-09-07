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

# `api` is required to serve HTTP. `vision` (Pillow) is required for
# the work-order photo endpoints — without it the API starts fine and
# only photo processing fails, with a message naming the missing extra.
# `push` carries the APNs dependencies; drop it if you do not send
# notifications.
COPY --from=builder /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl[api,vision,push] \
    && rm -rf /tmp/*.whl

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
