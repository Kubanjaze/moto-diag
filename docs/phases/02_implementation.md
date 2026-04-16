# MotoDiag Phase 02 — Configuration System

**Version:** 1.0 | **Tier:** Micro | **Date:** 2026-04-15

## Goal
Extend the Phase 01 config scaffold into a full configuration system with environment profiles (dev/prod), config validation, data directory auto-creation, and a CLI `config` command to inspect/set values.

CLI: `motodiag config show` / `motodiag config get <key>` / `motodiag config paths`

Outputs: Enhanced config module, config CLI subcommand, config tests

## Logic
1. Extend `core/config.py` Settings with additional fields and validators
2. Add environment profiles (dev/test/prod) via MOTODIAG_ENV
3. Add data directory auto-creation on startup
4. Add `config` CLI subcommand to show/get/validate settings
5. Add config tests

## Key Concepts
- pydantic-settings with field validators
- Environment-based profiles
- Path validation and auto-creation
- Click subcommand group for config management

## Verification Checklist
- [ ] `motodiag config show` displays all settings
- [ ] `motodiag config paths` shows data/output dirs with existence check
- [ ] Config loads from .env file
- [ ] Data directories auto-created on first access
- [ ] Tests pass

## Risks
- .env file not found on fresh clone — handled by defaults
