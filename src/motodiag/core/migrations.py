"""Schema migration framework for MotoDiag.

Phase 110: Reusable forward-only migration system with rollback support.
All subsequent retrofit phases (111-120) and future expansion tracks append
to MIGRATIONS. Each migration runs in a transaction; on failure the schema
version is not bumped.

Design:
- Forward-only in production (new DB gets all migrations, existing DB
  applies only missing ones)
- Rollback supported for testing and emergency recovery
- Each migration has a unique integer version matching schema_version table
- Migration 001 corresponds to initial schema (tracked in database.py)
- Migration 002 corresponds to pricing tables added later
- Migration 003+ are retrofit-era additions
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from motodiag.core.config import get_settings
from motodiag.core.database import get_connection


class Migration(BaseModel):
    """A single schema migration.

    upgrade_sql runs when applying the migration (forward).
    rollback_sql runs when reverting (used for testing, emergency recovery).
    Both should be idempotent where possible.
    """
    version: int = Field(..., description="Unique monotonic version number matching schema_version table")
    name: str = Field(..., description="Short slug describing the migration")
    description: str = Field(..., description="Human-readable explanation of what this migrates")
    upgrade_sql: str = Field(..., description="SQL to apply the migration")
    rollback_sql: str = Field(default="", description="SQL to revert the migration (optional but recommended)")


# --- Migration registry ---
# Retrofit phases append entries here. Do NOT delete or reorder — migrations
# are applied in version order, and existing DBs rely on consistent history.

MIGRATIONS: list[Migration] = [
    # Migration 003 — Phase 110: vehicle registry expansion
    Migration(
        version=3,
        name="vehicle_powertrain_expansion",
        description=(
            "Phase 110: Add powertrain (ICE/electric/hybrid), engine_type "
            "(4-stroke/2-stroke/electric/hybrid/desmo), battery_chemistry, "
            "motor_kw, and bms_present columns to vehicles table. Existing "
            "rows get ICE/4-stroke defaults."
        ),
        upgrade_sql="""
            ALTER TABLE vehicles ADD COLUMN powertrain TEXT DEFAULT 'ice';
            ALTER TABLE vehicles ADD COLUMN engine_type TEXT DEFAULT 'four_stroke';
            ALTER TABLE vehicles ADD COLUMN battery_chemistry TEXT;
            ALTER TABLE vehicles ADD COLUMN motor_kw REAL;
            ALTER TABLE vehicles ADD COLUMN bms_present INTEGER DEFAULT 0;
        """,
        rollback_sql="""
            -- SQLite does not support DROP COLUMN directly pre-3.35.
            -- Use CREATE-COPY-DROP-RENAME pattern. For rollback testing only.
            CREATE TABLE vehicles_rollback AS
                SELECT id, make, model, year, engine_cc, vin, protocol, notes
                FROM vehicles;
            DROP TABLE vehicles;
            ALTER TABLE vehicles_rollback RENAME TO vehicles;
        """,
    ),
    # Migration 004 — Phase 111: knowledge base schema expansion
    Migration(
        version=4,
        name="dtc_category_expansion",
        description=(
            "Phase 111: Add dtc_category column to dtc_codes for expanded "
            "taxonomy (HV battery, motor, regen, TPMS, emissions, etc.). "
            "Create dtc_category_meta table for category descriptions + "
            "applicable powertrains. Existing DTC rows default to 'unknown' "
            "until explicitly classified."
        ),
        upgrade_sql="""
            ALTER TABLE dtc_codes ADD COLUMN dtc_category TEXT DEFAULT 'unknown';

            CREATE TABLE IF NOT EXISTS dtc_category_meta (
                category TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                applicable_powertrains TEXT NOT NULL,
                severity_default TEXT NOT NULL DEFAULT 'medium'
            );

            INSERT OR IGNORE INTO dtc_category_meta (category, description, applicable_powertrains, severity_default) VALUES
                ('engine', 'Engine management faults (misfire, timing, sensors)', '["ice","hybrid"]', 'high'),
                ('fuel', 'Fuel delivery faults (pump, injectors, pressure)', '["ice","hybrid"]', 'high'),
                ('ignition', 'Ignition system faults (coils, plugs, pickup)', '["ice","hybrid"]', 'high'),
                ('emissions', 'Emissions system faults (O2, EVAP, PAIR, cat)', '["ice","hybrid"]', 'medium'),
                ('transmission', 'Transmission/clutch faults', '["ice","hybrid","electric"]', 'high'),
                ('cooling', 'Cooling system faults (thermostat, fan, coolant)', '["ice","hybrid","electric"]', 'high'),
                ('exhaust', 'Exhaust system faults (O2, catalyst, SAI)', '["ice","hybrid"]', 'medium'),
                ('abs', 'ABS and wheel speed sensor faults', '["ice","hybrid","electric"]', 'critical'),
                ('airbag', 'Airbag system faults', '["ice","hybrid","electric"]', 'critical'),
                ('immobilizer', 'Anti-theft/immobilizer (HISS, KIPASS)', '["ice","hybrid","electric"]', 'medium'),
                ('body', 'Body electrical and accessories', '["ice","hybrid","electric"]', 'low'),
                ('network', 'CAN/K-line communication faults', '["ice","hybrid","electric"]', 'high'),
                ('tpms', 'Tire pressure monitoring', '["ice","hybrid","electric"]', 'medium'),
                ('hv_battery', 'High-voltage battery pack and BMS faults', '["electric","hybrid"]', 'critical'),
                ('motor', 'Electric motor controller faults (IGBT, phase)', '["electric","hybrid"]', 'critical'),
                ('regen', 'Regenerative braking system faults', '["electric","hybrid"]', 'high'),
                ('charging_port', 'DC/AC charging port faults', '["electric","hybrid"]', 'high'),
                ('thermal', 'Battery/motor thermal management', '["electric","hybrid"]', 'high'),
                ('inverter', 'DC-to-AC inverter faults', '["electric","hybrid"]', 'critical'),
                ('unknown', 'Unclassified DTC', '["ice","hybrid","electric"]', 'medium');
        """,
        rollback_sql="""
            CREATE TABLE dtc_codes_rollback AS
                SELECT id, code, description, category, severity, make, common_causes, fix_summary
                FROM dtc_codes;
            DROP TABLE dtc_codes;
            CREATE TABLE dtc_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                make TEXT,
                common_causes TEXT,
                fix_summary TEXT,
                UNIQUE(code, make)
            );
            INSERT INTO dtc_codes (id, code, description, category, severity, make, common_causes, fix_summary)
                SELECT id, code, description, category, severity, make, common_causes, fix_summary FROM dtc_codes_rollback;
            DROP TABLE dtc_codes_rollback;
            DROP TABLE IF EXISTS dtc_category_meta;
        """,
    ),
    # Migration 005 — Phase 112: user/auth layer introduction
    Migration(
        version=5,
        name="auth_layer_introduction",
        description=(
            "Phase 112: Create users, roles, permissions, user_roles, "
            "role_permissions tables. Seed 'system' user (id=1), 4 roles "
            "(owner/tech/service_writer/apprentice), 12 base permissions. "
            "Add user_id FK to diagnostic_sessions and repair_plans; "
            "created_by_user_id FK to known_issues. Existing rows default "
            "to system user (id=1) to preserve referential integrity."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT,
                full_name TEXT,
                password_hash TEXT,
                tier TEXT NOT NULL DEFAULT 'individual',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, role_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id INTEGER NOT NULL,
                permission_id INTEGER NOT NULL,
                PRIMARY KEY (role_id, permission_id),
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            );

            -- Seed "system" user (id=1) to own all pre-retrofit data
            INSERT OR IGNORE INTO users (id, username, email, full_name, password_hash, tier, is_active)
                VALUES (1, 'system', NULL, 'System (pre-retrofit data owner)', NULL, 'company', 1);

            -- Seed 4 baseline roles
            INSERT OR IGNORE INTO roles (name, description) VALUES
                ('owner', 'Shop owner — full administrative access'),
                ('tech', 'Certified mechanic — diagnose, repair, document'),
                ('service_writer', 'Customer-facing staff — scheduling, invoicing, communication'),
                ('apprentice', 'Learning mechanic — limited write access, read-mostly');

            -- Seed 12 baseline permissions
            INSERT OR IGNORE INTO permissions (name, description) VALUES
                ('read_garage', 'View vehicles in the garage'),
                ('write_garage', 'Add, edit, or remove vehicles'),
                ('read_session', 'View diagnostic sessions'),
                ('write_session', 'Create or modify diagnostic sessions'),
                ('run_diagnose', 'Execute AI-assisted diagnostic workflows'),
                ('read_repair_plan', 'View repair plans and cost estimates'),
                ('write_repair_plan', 'Create or modify repair plans'),
                ('export_report', 'Export diagnostic reports to PDF/HTML'),
                ('share_report', 'Share reports externally with customers'),
                ('manage_users', 'Create, edit, or deactivate user accounts'),
                ('manage_billing', 'View and modify billing / subscription settings'),
                ('manage_shop', 'Shop-level admin (work orders, scheduling, analytics)');

            -- Seed default role-permission mappings
            -- OWNER: all 12 permissions
            INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                SELECT (SELECT id FROM roles WHERE name='owner'), p.id FROM permissions p;
            -- TECH: read/write garage + session + diagnose + read/write repair plan + export
            INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                SELECT (SELECT id FROM roles WHERE name='tech'), p.id FROM permissions p
                WHERE p.name IN ('read_garage','write_garage','read_session','write_session',
                                 'run_diagnose','read_repair_plan','write_repair_plan','export_report');
            -- SERVICE_WRITER: read garage/session, write repair plan, export/share, manage shop
            INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                SELECT (SELECT id FROM roles WHERE name='service_writer'), p.id FROM permissions p
                WHERE p.name IN ('read_garage','read_session','read_repair_plan',
                                 'write_repair_plan','export_report','share_report','manage_shop');
            -- APPRENTICE: read-mostly plus supervised diagnose
            INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                SELECT (SELECT id FROM roles WHERE name='apprentice'), p.id FROM permissions p
                WHERE p.name IN ('read_garage','read_session','read_repair_plan','run_diagnose');

            -- Retrofit user_id columns onto existing tables
            ALTER TABLE diagnostic_sessions ADD COLUMN user_id INTEGER DEFAULT 1;
            ALTER TABLE repair_plans ADD COLUMN user_id INTEGER DEFAULT 1;
            ALTER TABLE known_issues ADD COLUMN created_by_user_id INTEGER DEFAULT 1;
        """,
        rollback_sql="""
            -- Rollback 005: drop auth tables only. Keeping the new user_id
            -- columns on existing tables is harmless (they're nullable-with-default
            -- and unused). Full column removal would require CREATE-COPY-DROP-RENAME
            -- and is not needed for testing; auth tables gone is sufficient to prove
            -- the auth layer can be dismantled without data loss in the core tables.
            DROP TABLE IF EXISTS role_permissions;
            DROP TABLE IF EXISTS user_roles;
            DROP TABLE IF EXISTS permissions;
            DROP TABLE IF EXISTS roles;
            DROP TABLE IF EXISTS users;
        """,
    ),
    # Migration 006 — Phase 113: CRM foundation
    Migration(
        version=6,
        name="crm_foundation",
        description=(
            "Phase 113: Create customers + customer_bikes tables. Seed "
            "'unassigned' placeholder customer (id=1) owned by system user. "
            "Add customer_id FK onto vehicles; existing rows default to "
            "unassigned placeholder (id=1)."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER NOT NULL DEFAULT 1,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                notes TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
            );

            CREATE INDEX IF NOT EXISTS idx_customers_owner ON customers(owner_user_id);
            CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);
            CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);

            CREATE TABLE IF NOT EXISTS customer_bikes (
                customer_id INTEGER NOT NULL,
                vehicle_id INTEGER NOT NULL,
                relationship TEXT NOT NULL DEFAULT 'owner',
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                PRIMARY KEY (customer_id, vehicle_id, relationship),
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_customer_bikes_vehicle ON customer_bikes(vehicle_id);

            -- Seed placeholder "unassigned" customer (id=1) owned by system user
            INSERT OR IGNORE INTO customers (id, owner_user_id, name, email, is_active)
                VALUES (1, 1, 'Unassigned', NULL, 1);

            -- Retrofit customer_id onto vehicles
            ALTER TABLE vehicles ADD COLUMN customer_id INTEGER DEFAULT 1;
        """,
        rollback_sql="""
            -- Drop CRM tables; customer_id column on vehicles left in place (harmless).
            DROP TABLE IF EXISTS customer_bikes;
            DROP TABLE IF EXISTS customers;
        """,
    ),
    # Migration 007 — Phase 114: workflow template substrate
    Migration(
        version=7,
        name="workflow_template_substrate",
        description=(
            "Phase 114: Create workflow_templates + checklist_items tables. "
            "Seed 2 built-in templates (generic PPI + generic winterization) "
            "with 5 + 4 starter checklist items. Track N phases 259-272 "
            "populate the remaining 11 workflow categories with full content."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS workflow_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                applicable_powertrains TEXT NOT NULL DEFAULT '["ice","electric","hybrid"]',
                estimated_duration_minutes INTEGER,
                required_tier TEXT NOT NULL DEFAULT 'individual',
                created_by_user_id INTEGER NOT NULL DEFAULT 1,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
            );

            CREATE INDEX IF NOT EXISTS idx_templates_category ON workflow_templates(category);
            CREATE INDEX IF NOT EXISTS idx_templates_slug ON workflow_templates(slug);

            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                sequence_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                instruction_text TEXT NOT NULL,
                expected_pass TEXT,
                expected_fail TEXT,
                diagnosis_if_fail TEXT,
                required INTEGER NOT NULL DEFAULT 1,
                tools_needed TEXT NOT NULL DEFAULT '[]',
                estimated_minutes INTEGER,
                FOREIGN KEY (template_id) REFERENCES workflow_templates(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_checklist_template ON checklist_items(template_id);

            -- Seed 2 built-in templates
            INSERT OR IGNORE INTO workflow_templates
                (slug, name, description, category, applicable_powertrains,
                 estimated_duration_minutes, required_tier, created_by_user_id)
                VALUES
                ('generic_ppi_v1', 'Generic Pre-Purchase Inspection',
                 'Quick pre-purchase inspection covering engine, chassis, fluids, electrical. Track N phase 259 expands with engine-specific content.',
                 'ppi', '["ice","electric","hybrid"]', 60, 'individual', 1),
                ('generic_winterization_v1', 'Generic Winterization Protocol',
                 'Seasonal storage: fuel stabilization, battery tender, oil change, storage position. Track N phase 264 expands.',
                 'winterization', '["ice","hybrid"]', 45, 'individual', 1);

            -- Seed starter checklist for PPI (5 items)
            INSERT OR IGNORE INTO checklist_items
                (template_id, sequence_number, title, instruction_text, expected_pass, expected_fail, required, tools_needed, estimated_minutes)
                VALUES
                ((SELECT id FROM workflow_templates WHERE slug='generic_ppi_v1'), 1,
                 'VIN verification',
                 'Read VIN from frame and match to title/registration. Photograph if discrepancy.',
                 'VIN matches title and frame/bike year',
                 'VIN mismatch, altered, or missing',
                 1, '["flashlight","magnifying glass"]', 5),
                ((SELECT id FROM workflow_templates WHERE slug='generic_ppi_v1'), 2,
                 'Frame inspection',
                 'Inspect frame for cracks, welds, straightness. Check neck bearings for play.',
                 'Frame straight, no cracks, no aftermarket welds',
                 'Cracks, repairs, or bent frame',
                 1, '["flashlight","straight edge"]', 10),
                ((SELECT id FROM workflow_templates WHERE slug='generic_ppi_v1'), 3,
                 'Engine compression test',
                 'Warm engine, remove spark plug, crank and read compression gauge. Repeat all cylinders.',
                 'Within 10% across cylinders, within OEM spec',
                 'Low or highly variable compression',
                 1, '["compression gauge","spark plug socket"]', 15),
                ((SELECT id FROM workflow_templates WHERE slug='generic_ppi_v1'), 4,
                 'Fluid inspection',
                 'Check oil color/level, coolant color/level, brake fluid, fork oil condition.',
                 'All fluids fresh, correct color, at correct level',
                 'Milky oil, rusty coolant, dark brake fluid',
                 1, '["flashlight","rag"]', 10),
                ((SELECT id FROM workflow_templates WHERE slug='generic_ppi_v1'), 5,
                 'Brake and tire condition',
                 'Measure pad thickness, rotor thickness, tire tread depth, DOT date. Check for age cracking.',
                 'Pads >3mm, rotors >min spec, tires <5 years old, adequate tread',
                 'Below spec or aged out',
                 1, '["pad depth gauge","tread depth gauge","caliper"]', 10);

            -- Seed starter checklist for winterization (4 items)
            INSERT OR IGNORE INTO checklist_items
                (template_id, sequence_number, title, instruction_text, expected_pass, expected_fail, required, tools_needed, estimated_minutes)
                VALUES
                ((SELECT id FROM workflow_templates WHERE slug='generic_winterization_v1'), 1,
                 'Add fuel stabilizer',
                 'Add Sta-Bil or equivalent to fuel tank per manufacturer ratio. Run engine 5 minutes to circulate.',
                 'Stabilizer circulated through fuel system',
                 'Engine not run after adding — stabilizer did not reach carbs/injectors',
                 1, '["fuel stabilizer"]', 10),
                ((SELECT id FROM workflow_templates WHERE slug='generic_winterization_v1'), 2,
                 'Oil change',
                 'Change engine oil and filter with recommended winter weight (typically 10W-40).',
                 'Fresh oil and filter, correct fill level',
                 'Dirty oil left in engine over winter',
                 1, '["drain pan","oil filter wrench","torque wrench"]', 15),
                ((SELECT id FROM workflow_templates WHERE slug='generic_winterization_v1'), 3,
                 'Connect battery tender',
                 'Disconnect negative terminal, clean terminals, connect battery tender per manufacturer instructions.',
                 'Battery on tender, reading float voltage (13.2V-13.6V)',
                 'Battery left disconnected with no maintenance',
                 1, '["battery tender","wire brush"]', 5),
                ((SELECT id FROM workflow_templates WHERE slug='generic_winterization_v1'), 4,
                 'Storage position and cover',
                 'Move to storage, put on centerstand/jackstand to unload suspension, cover with breathable cover.',
                 'Bike stable, weight off tires, cover breathable',
                 'On sidestand with tires loaded, plastic tarp cover',
                 1, '["jack stand","breathable cover"]', 10);
        """,
        rollback_sql="""
            DROP TABLE IF EXISTS checklist_items;
            DROP TABLE IF EXISTS workflow_templates;
        """,
    ),
    # Migration 008 — Phase 115: i18n translations substrate
    Migration(
        version=8,
        name="i18n_translations_substrate",
        description=(
            "Phase 115: Create translations table with composite PK "
            "(locale, namespace, key) + value + optional context. Seeds ~40 "
            "baseline English strings across 4 namespaces (cli, ui, "
            "diagnostics, workflow). Track Q phases 308-310 populate Spanish, "
            "French, German. Additional locales (ja/it/pt) reserved."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS translations (
                locale TEXT NOT NULL,
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                context TEXT,
                PRIMARY KEY (locale, namespace, key)
            );

            CREATE INDEX IF NOT EXISTS idx_translations_locale ON translations(locale);
            CREATE INDEX IF NOT EXISTS idx_translations_ns_key ON translations(namespace, key);

            -- Seed baseline English (en) strings across 4 namespaces

            -- cli namespace (11 strings): welcome, help/version, command prompts
            INSERT OR IGNORE INTO translations (locale, namespace, key, value, context) VALUES
                ('en', 'cli', 'welcome', 'Welcome to MotoDiag', 'shown on interactive shell start'),
                ('en', 'cli', 'version_info', 'MotoDiag v{version}', 'shown for --version flag'),
                ('en', 'cli', 'help_usage', 'Usage: motodiag [OPTIONS] COMMAND [ARGS]...', NULL),
                ('en', 'cli', 'command_diagnose', 'Run AI-assisted diagnostic workflow', NULL),
                ('en', 'cli', 'command_garage', 'Manage your vehicle garage', NULL),
                ('en', 'cli', 'command_report', 'Export or share diagnostic reports', NULL),
                ('en', 'cli', 'command_customer', 'Manage customer records', NULL),
                ('en', 'cli', 'prompt_confirm', 'Are you sure? [y/N]', NULL),
                ('en', 'cli', 'prompt_vehicle_id', 'Enter vehicle ID:', NULL),
                ('en', 'cli', 'exit_goodbye', 'Goodbye!', NULL),
                ('en', 'cli', 'unknown_command', 'Unknown command: {cmd}', NULL);

            -- ui namespace (12 strings): buttons, status labels, common actions
            INSERT OR IGNORE INTO translations (locale, namespace, key, value, context) VALUES
                ('en', 'ui', 'button_save', 'Save', NULL),
                ('en', 'ui', 'button_cancel', 'Cancel', NULL),
                ('en', 'ui', 'button_delete', 'Delete', NULL),
                ('en', 'ui', 'button_edit', 'Edit', NULL),
                ('en', 'ui', 'button_next', 'Next', NULL),
                ('en', 'ui', 'button_back', 'Back', NULL),
                ('en', 'ui', 'loading', 'Loading...', 'progress indicator'),
                ('en', 'ui', 'error_generic', 'Something went wrong. Please try again.', NULL),
                ('en', 'ui', 'error_not_found', 'Not found', NULL),
                ('en', 'ui', 'error_permission', 'You do not have permission for this action', NULL),
                ('en', 'ui', 'success_saved', 'Saved successfully', NULL),
                ('en', 'ui', 'success_deleted', 'Deleted successfully', NULL);

            -- diagnostics namespace (11 strings): severity, confidence, session state
            INSERT OR IGNORE INTO translations (locale, namespace, key, value, context) VALUES
                ('en', 'diagnostics', 'severity_critical', 'Critical', 'severity label — immediate safety risk'),
                ('en', 'diagnostics', 'severity_high', 'High', 'severity label — major drivability issue'),
                ('en', 'diagnostics', 'severity_medium', 'Medium', NULL),
                ('en', 'diagnostics', 'severity_low', 'Low', 'severity label — cosmetic or minor'),
                ('en', 'diagnostics', 'confidence_high', 'High confidence', 'AI confidence tier'),
                ('en', 'diagnostics', 'confidence_medium', 'Medium confidence', NULL),
                ('en', 'diagnostics', 'confidence_low', 'Low confidence', NULL),
                ('en', 'diagnostics', 'session_open', 'Open', 'session status'),
                ('en', 'diagnostics', 'session_closed', 'Closed', 'session status'),
                ('en', 'diagnostics', 'no_dtc_found', 'No fault codes detected', NULL),
                ('en', 'diagnostics', 'analysis_in_progress', 'Analyzing symptoms...', NULL);

            -- workflow namespace (11 strings): checklist states, template labels
            INSERT OR IGNORE INTO translations (locale, namespace, key, value, context) VALUES
                ('en', 'workflow', 'step_pass', 'Pass', 'checklist item result'),
                ('en', 'workflow', 'step_fail', 'Fail', 'checklist item result'),
                ('en', 'workflow', 'step_skip', 'Skip', 'checklist item result'),
                ('en', 'workflow', 'step_unclear', 'Unclear', 'checklist item result — inconclusive'),
                ('en', 'workflow', 'template_ppi', 'Pre-Purchase Inspection', NULL),
                ('en', 'workflow', 'template_winterization', 'Winterization', NULL),
                ('en', 'workflow', 'checklist_complete', 'Checklist complete', NULL),
                ('en', 'workflow', 'checklist_progress', '{done} of {total} items complete', 'progress label'),
                ('en', 'workflow', 'required_step', 'Required', 'marks a step as mandatory'),
                ('en', 'workflow', 'optional_step', 'Optional', NULL),
                ('en', 'workflow', 'estimated_minutes', 'Estimated: {minutes} min', NULL);
        """,
        rollback_sql="""
            DROP TABLE IF EXISTS translations;
        """,
    ),
]


def get_current_version(db_path: Optional[str] = None) -> int:
    """Return the highest applied schema version, or 0 if the DB is fresh."""
    path = db_path or get_settings().db_path
    if not Path(path).exists():
        return 0

    with get_connection(path) as conn:
        try:
            cursor = conn.execute("SELECT MAX(version) FROM schema_version")
            row = cursor.fetchone()
            if row and row[0] is not None:
                return int(row[0])
        except Exception:
            # schema_version table may not exist on a very fresh DB
            return 0
    return 0


def get_applied_migrations(db_path: Optional[str] = None) -> list[int]:
    """Return a sorted list of all applied schema version numbers."""
    path = db_path or get_settings().db_path
    if not Path(path).exists():
        return []

    with get_connection(path) as conn:
        try:
            cursor = conn.execute("SELECT version FROM schema_version ORDER BY version")
            return [int(row[0]) for row in cursor.fetchall()]
        except Exception:
            return []


def get_pending_migrations(db_path: Optional[str] = None) -> list[Migration]:
    """Return migrations with a version higher than the current applied max."""
    current = get_current_version(db_path)
    return [m for m in MIGRATIONS if m.version > current]


def apply_migration(migration: Migration, db_path: Optional[str] = None) -> None:
    """Apply a single migration transactionally.

    On failure, the transaction rolls back and schema_version is not updated.
    """
    path = db_path or get_settings().db_path

    with get_connection(path) as conn:
        # Execute the upgrade SQL (may be multi-statement)
        conn.executescript(migration.upgrade_sql)

        # Record the migration in schema_version
        conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (migration.version,),
        )


def apply_pending_migrations(db_path: Optional[str] = None) -> list[int]:
    """Apply all pending migrations in version order. Returns applied versions."""
    pending = get_pending_migrations(db_path)
    applied: list[int] = []

    for migration in sorted(pending, key=lambda m: m.version):
        apply_migration(migration, db_path)
        applied.append(migration.version)

    return applied


def rollback_migration(migration: Migration, db_path: Optional[str] = None) -> None:
    """Roll back a single migration using its rollback_sql.

    Mainly for testing and emergency recovery. Not used in normal operation.
    """
    if not migration.rollback_sql.strip():
        raise ValueError(
            f"Migration {migration.version} ({migration.name}) has no rollback_sql defined"
        )

    path = db_path or get_settings().db_path

    with get_connection(path) as conn:
        conn.executescript(migration.rollback_sql)
        # Remove from schema_version
        conn.execute(
            "DELETE FROM schema_version WHERE version = ?",
            (migration.version,),
        )


def rollback_to_version(target_version: int, db_path: Optional[str] = None) -> list[int]:
    """Roll back migrations until the DB is at target_version.

    Rolls back in reverse version order. For testing and recovery.
    """
    applied = get_applied_migrations(db_path)
    to_rollback = sorted([v for v in applied if v > target_version], reverse=True)

    rolled_back: list[int] = []
    for version in to_rollback:
        migration = next((m for m in MIGRATIONS if m.version == version), None)
        if migration is None:
            raise ValueError(f"No migration definition found for version {version}")
        rollback_migration(migration, db_path)
        rolled_back.append(version)

    return rolled_back


def get_migration_by_version(version: int) -> Optional[Migration]:
    """Look up a migration by version number."""
    return next((m for m in MIGRATIONS if m.version == version), None)
