"""MotoDiag — AI-powered motorcycle diagnostic tool."""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

__app_name__ = "motodiag"

# Phase 208: the version is declared ONCE, in pyproject.toml, and read
# back from installed package metadata. It used to be a literal here as
# well, which drifted to five minor versions behind the real one —
# `motodiag --version`, `/v1/version` and the OpenAPI `version` field
# all reported 0.1.0 against a 0.6.0 package. A version number that lies
# is worse than no version number: it sends a bug report to the wrong
# release. The fallback covers a source tree that was never installed,
# where metadata genuinely does not exist.
try:
    __version__ = _pkg_version(__app_name__)
except PackageNotFoundError:  # pragma: no cover — uninstalled source tree
    __version__ = "0.0.0+unknown"
