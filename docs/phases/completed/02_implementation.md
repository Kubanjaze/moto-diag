# MotoDiag Phase 02 — Configuration System

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-04-15

## Goal
Extend the Phase 01 config scaffold into a full configuration system with environment profiles (dev/test/prod), config field validation, data directory auto-creation, cached singleton settings, and a CLI `config` subcommand group to inspect settings and paths.

CLI: `motodiag config show` / `motodiag config paths` / `motodiag config init`

Outputs: Enhanced `core/config.py`, config CLI subcommands, 13 tests

## Logic
1. Extended `core/config.py` Settings with new fields: `env` (Environment enum), `data_dir`, `output_dir`, `ai_temperature`, `connection_timeout`, `log_level`, `log_file`
2. Added `Environment` enum (dev/test/prod) selectable via `MOTODIAG_ENV`
3. Added field validators for `max_tokens` (100–8192), `ai_temperature` (0.0–1.0), `baud_rate` (valid serial rates only)
4. Added `ensure_directories()` — creates all data subdirs (dtc_codes, vehicles, knowledge, output) if missing
5. Added `reset_settings()` — clears `@lru_cache` for testing
6. Added helper methods: `get_data_path(*parts)`, `get_output_path(*parts)` for relative path construction
7. Added `config` CLI subcommand group with 3 commands:
   - `config show` — displays all settings in a Rich table (API key masked)
   - `config paths` — shows data/output dirs with existence check
   - `config init` — creates all required directories

## Key Concepts
- `pydantic` `@field_validator` with `@classmethod` for Settings validation
- `functools.lru_cache(maxsize=1)` for singleton Settings
- `Environment(str, Enum)` for typed profile switching
- `click.group()` nesting for `motodiag config <subcommand>`
- `Rich` Table rendering with masked sensitive values

## Verification Checklist
- [x] `motodiag config show` displays all settings with API key masked
- [x] `motodiag config paths` shows data/output dirs with existence check
- [x] `motodiag config init` creates missing directories
- [x] Config loads from .env file via pydantic-settings
- [x] Data directories auto-created via `ensure_directories()`
- [x] Invalid max_tokens / temperature / baud_rate raise ValidationError
- [x] 13 tests pass in 0.31s

## Risks
- ~~.env file not found on fresh clone~~ — handled by defaults, all fields have sensible defaults
- No risks materialized

## Results
| Metric | Value |
|--------|-------|
| New config fields | 7 (env, data_dir, output_dir, ai_temperature, connection_timeout, log_level, log_file) |
| Validators | 3 (max_tokens, ai_temperature, baud_rate) |
| CLI commands added | 3 (config show, config paths, config init) |
| Tests | 13 |
| Test time | 0.31s |

Config system is production-ready with validation, environment profiles, and CLI inspection.
