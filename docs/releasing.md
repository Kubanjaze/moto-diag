# Releasing MotoDiag

Backend and mobile release separately and are not version-locked. The
mobile app pins an OpenAPI snapshot, so a backend contract change means
a mobile release too — see the compatibility note at the bottom.

## Backend

### 1. Version

`pyproject.toml` is the **only** place the version is written. Since
Phase 208, `motodiag.__version__`, `Settings.version`, `/v1/version` and
the OpenAPI document all read it back from installed package metadata.
Do not add a second literal — that is exactly how `--version` came to
report 0.1.0 against a 0.6.0 package for five minor releases.

```bash
# edit pyproject.toml: version = "0.7.0"
pip install -e ".[dev]"     # refresh the installed metadata
motodiag --version          # must print the new number
```

### 2. Green before you build

```bash
pytest -q                                   # full suite
python scripts/check_f9_patterns.py --all   # drift lint
```

`tests/test_phase209_packaging.py` is the one that matters here: it
builds a wheel, installs it into a throwaway venv with no extras, and
runs the CLI. Do not release with it deselected — it is the only test
that exercises the artefact rather than the source tree.

### 3. Build

```bash
rm -rf dist build
python -m build
ls dist/
```

### 4. Verify the artefact by hand

Automated coverage exists, but look at it once per release:

```bash
python3 -m venv /tmp/verify && /tmp/verify/bin/pip install dist/*.whl
/tmp/verify/bin/motodiag --version
/tmp/verify/bin/motodiag db init          # must print "Loaded ..." lines
/tmp/verify/bin/motodiag code P0115       # must NOT say "No DB entry"
```

The knowledge base ships inside the wheel. A `db init` that reports
success without `Loaded` lines means the seed data did not make it in,
and the release is empty of the thing people install it for.

### 5. Publish

```bash
pip install twine
twine check dist/*
twine upload dist/*
```

### 6. Tag

```bash
git tag -a v0.7.0 -m "MotoDiag 0.7.0"
git push origin v0.7.0
```

### 7. Container

> Unverified — the image has never been built. See F76.

```bash
docker build -t motodiag:0.7.0 .
docker run --rm -p 8000:8000 motodiag:0.7.0
curl localhost:8000/healthz
```

## Mobile (iOS)

The runbook is [`docs/testflight.md`](../../moto-diag-mobile/docs/testflight.md)
in the mobile repo; store metadata is
[`docs/app-store-listing.md`](../../moto-diag-mobile/docs/app-store-listing.md).

Real blockers, as of Phase 209:

1. **No privacy policy URL.** Required for submission; does not exist.
2. **No demo server for App Review.** The app is a client and cannot be
   exercised without a backend. Same host decision as F64.
3. **No screenshots captured.**
4. **The TestFlight upload needs Apple credentials** that only the
   account holder has. The `.ipa` builds; nobody has uploaded one.

**Android / Play Store is not a supported path.** Android source is
present and has built historically, but nothing has been run on it since
iOS became the shipped target, and the New-Architecture build flag there
is untested (Phase 208). Treat a Play Store release as unscoped work,
not a checklist item.

## Backend ↔ mobile compatibility

The app talks to the backend through a **committed OpenAPI snapshot**
(`api-schema/openapi.json`) and TypeScript types generated from it. A
backend release that changes a route or model requires:

```bash
# backend running
node scripts/refresh-api-schema.js
npm run generate-api-types
npx tsc --noEmit
```

This has drifted twice, both times because the backend was fixed and
the generated artefacts were not. `/v1/version` reports both the package
version and the schema version, which is the fastest way to tell what a
deployment is actually running.

## The order that matters

Ship the backend first. The app degrades against an older backend
(missing routes surface as typed errors) but an app released against a
backend that has not deployed yet is broken for everyone who updates.
