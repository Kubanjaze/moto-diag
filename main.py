"""MotoDiag — main entry point (CLI fallback)."""

import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="motodiag",
        description="MotoDiag — AI-powered motorcycle diagnostic tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version", action="store_true", help="Show version and exit"
    )
    parser.add_argument(
        "--info", action="store_true", help="Show system info"
    )
    args = parser.parse_args()

    from motodiag import __version__

    if args.version:
        print(f"motodiag v{__version__}")
        return

    if args.info:
        # Quick import check for all packages
        packages = [
            "motodiag.core",
            "motodiag.core.config",
            "motodiag.core.models",
            "motodiag.vehicles",
            "motodiag.knowledge",
            "motodiag.engine",
            "motodiag.cli",
            "motodiag.hardware",
            "motodiag.advanced",
            "motodiag.api",
        ]
        print(f"motodiag v{__version__}")
        print(f"Python {sys.version}")
        print()
        for pkg in packages:
            try:
                __import__(pkg)
                print(f"  ✓ {pkg}")
            except ImportError as e:
                print(f"  ✗ {pkg} — {e}")
        return

    # Default: launch Click CLI
    from motodiag.cli.main import cli
    cli()


if __name__ == "__main__":
    main()
