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
    post_apply: str = Field(
        default="",
        description=(
            "Optional 'module:function' run after upgrade_sql, inside the same "
            "transaction, receiving the open connection. Phase 244F: a backfill "
            "that needs real parsing cannot be expressed in SQL, and doing it "
            "outside the migration would leave a window where the schema exists "
            "and the data behind it does not."
        ),
    )


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
    # Migration 009 — Phase 116: feedback/learning hooks substrate
    Migration(
        version=9,
        name="feedback_learning_hooks",
        description=(
            "Phase 116: Create diagnostic_feedback and session_overrides "
            "tables. Feedback records post-diagnosis truth (what the "
            "mechanic actually found) vs AI output, with outcome enum "
            "(correct/partially_correct/incorrect/inconclusive). Overrides "
            "log field-level disagreements on diagnostic sessions. Track R "
            "phases 318-327 consume this via FeedbackReader read-only hook."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS diagnostic_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                submitted_by_user_id INTEGER NOT NULL DEFAULT 1,
                ai_suggested_diagnosis TEXT,
                ai_confidence REAL,
                actual_diagnosis TEXT,
                actual_fix TEXT,
                outcome TEXT NOT NULL,
                mechanic_notes TEXT,
                parts_used TEXT NOT NULL DEFAULT '[]',
                actual_labor_hours REAL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (submitted_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
            );

            CREATE INDEX IF NOT EXISTS idx_feedback_session ON diagnostic_feedback(session_id);
            CREATE INDEX IF NOT EXISTS idx_feedback_outcome ON diagnostic_feedback(outcome);

            CREATE TABLE IF NOT EXISTS session_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                ai_value TEXT,
                override_value TEXT,
                overridden_by_user_id INTEGER NOT NULL DEFAULT 1,
                reason TEXT,
                overridden_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (overridden_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
            );

            CREATE INDEX IF NOT EXISTS idx_overrides_session ON session_overrides(session_id);
            CREATE INDEX IF NOT EXISTS idx_overrides_field ON session_overrides(field_name);
        """,
        rollback_sql="""
            DROP TABLE IF EXISTS session_overrides;
            DROP TABLE IF EXISTS diagnostic_feedback;
        """,
    ),
    # Migration 010 — Phase 117: reference data tables
    Migration(
        version=10,
        name="reference_data_tables",
        description=(
            "Phase 117: Create 4 empty reference tables — manual_references "
            "(Clymer/Haynes/OEM citations), parts_diagrams (exploded views, "
            "schematics, wiring, assembly), failure_photos (failure-mode "
            "photo library), video_tutorials (YouTube/Vimeo/internal "
            "tutorials). Year-range targeting via year_start/year_end "
            "reuses the known_issues pattern. Track P phases 293-302 "
            "populate content on top of this substrate."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS manual_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                publisher TEXT,
                isbn TEXT,
                make TEXT,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                page_count INTEGER,
                section_titles TEXT NOT NULL DEFAULT '[]',
                url TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_manuals_make_model ON manual_references(make, model);
            CREATE INDEX IF NOT EXISTS idx_manuals_source ON manual_references(source);

            CREATE TABLE IF NOT EXISTS parts_diagrams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                make TEXT,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                diagram_type TEXT NOT NULL,
                section TEXT,
                title TEXT NOT NULL,
                image_ref TEXT NOT NULL,
                source_manual_id INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_manual_id) REFERENCES manual_references(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_diagrams_make_model ON parts_diagrams(make, model);
            CREATE INDEX IF NOT EXISTS idx_diagrams_type ON parts_diagrams(diagram_type);

            CREATE TABLE IF NOT EXISTS failure_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                failure_category TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                part_affected TEXT,
                image_ref TEXT NOT NULL,
                submitted_by_user_id INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (submitted_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
            );

            CREATE INDEX IF NOT EXISTS idx_photos_make_model ON failure_photos(make, model);
            CREATE INDEX IF NOT EXISTS idx_photos_category ON failure_photos(failure_category);

            CREATE TABLE IF NOT EXISTS video_tutorials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                source TEXT NOT NULL,
                source_video_id TEXT,
                url TEXT,
                duration_seconds INTEGER,
                make TEXT,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                skill_level TEXT NOT NULL DEFAULT 'intermediate',
                topic_tags TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_videos_make_model ON video_tutorials(make, model);
            CREATE INDEX IF NOT EXISTS idx_videos_source ON video_tutorials(source);
        """,
        rollback_sql="""
            DROP TABLE IF EXISTS parts_diagrams;
            DROP TABLE IF EXISTS video_tutorials;
            DROP TABLE IF EXISTS failure_photos;
            DROP TABLE IF EXISTS manual_references;
        """,
    ),
    # Migration 011 — Phase 118: billing/accounting/inventory/scheduling substrate
    Migration(
        version=11,
        name="ops_substrate",
        description=(
            "Phase 118: Create 9 business-ops tables across 4 domains — "
            "billing (subscriptions, payments), accounting (invoices, "
            "invoice_line_items), inventory (inventory_items, vendors), "
            "warranty/recalls (recalls, warranties), scheduling "
            "(appointments). Schema + minimal CRUD substrate only. Track O "
            "phases 273-289 wire up Stripe + QuickBooks + calendar sync, "
            "Track S phases 328-329 build the customer billing portal."
        ),
        upgrade_sql="""
            -- Billing: subscriptions
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tier TEXT NOT NULL DEFAULT 'individual',
                status TEXT NOT NULL DEFAULT 'trialing',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ends_at TIMESTAMP,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
            CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);

            -- Billing: payments
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subscription_id INTEGER,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                status TEXT NOT NULL DEFAULT 'pending',
                stripe_payment_intent_id TEXT UNIQUE,
                payment_method TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
            CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

            -- Accounting: invoices
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                repair_plan_id INTEGER,
                invoice_number TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'draft',
                subtotal REAL NOT NULL DEFAULT 0.0,
                tax_amount REAL NOT NULL DEFAULT 0.0,
                total REAL NOT NULL DEFAULT 0.0,
                currency TEXT NOT NULL DEFAULT 'USD',
                issued_at TIMESTAMP,
                due_at TIMESTAMP,
                paid_at TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (repair_plan_id) REFERENCES repair_plans(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
            CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);

            -- Accounting: invoice line items
            CREATE TABLE IF NOT EXISTS invoice_line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                description TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 1.0,
                unit_price REAL NOT NULL DEFAULT 0.0,
                line_total REAL NOT NULL DEFAULT 0.0,
                source_repair_plan_item_id INTEGER,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                FOREIGN KEY (source_repair_plan_item_id) REFERENCES repair_plan_items(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_line_items(invoice_id);

            -- Inventory: vendors (created before inventory_items for FK)
            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                contact_name TEXT,
                email TEXT,
                phone TEXT,
                website TEXT,
                address TEXT,
                payment_terms TEXT,
                notes TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_vendors_active ON vendors(is_active);

            -- Inventory: items
            CREATE TABLE IF NOT EXISTS inventory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                make TEXT,
                model_applicable TEXT NOT NULL DEFAULT '[]',
                quantity_on_hand INTEGER NOT NULL DEFAULT 0,
                reorder_point INTEGER NOT NULL DEFAULT 0,
                unit_cost REAL DEFAULT 0.0,
                unit_price REAL DEFAULT 0.0,
                vendor_id INTEGER,
                location TEXT,
                last_counted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory_items(sku);
            CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory_items(category);

            -- Recalls
            CREATE TABLE IF NOT EXISTS recalls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_number TEXT NOT NULL UNIQUE,
                make TEXT NOT NULL,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                description TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                remedy TEXT,
                notification_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_recalls_make_model ON recalls(make, model);

            -- Warranties
            CREATE TABLE IF NOT EXISTS warranties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                coverage_type TEXT NOT NULL,
                provider TEXT,
                start_date TEXT,
                end_date TEXT,
                mileage_limit INTEGER,
                terms TEXT,
                claim_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_warranties_vehicle ON warranties(vehicle_id);

            -- Scheduling: appointments
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                vehicle_id INTEGER,
                user_id INTEGER,
                appointment_type TEXT NOT NULL DEFAULT 'service',
                status TEXT NOT NULL DEFAULT 'scheduled',
                scheduled_start TEXT NOT NULL,
                scheduled_end TEXT NOT NULL,
                actual_start TEXT,
                actual_end TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_appointments_customer ON appointments(customer_id);
            CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
            CREATE INDEX IF NOT EXISTS idx_appointments_scheduled_start ON appointments(scheduled_start);
        """,
        rollback_sql="""
            -- Rollback in FK-safe order (children first, parents last)
            DROP TABLE IF EXISTS appointments;
            DROP TABLE IF EXISTS warranties;
            DROP TABLE IF EXISTS recalls;
            DROP TABLE IF EXISTS inventory_items;
            DROP TABLE IF EXISTS vendors;
            DROP TABLE IF EXISTS invoice_line_items;
            DROP TABLE IF EXISTS invoices;
            DROP TABLE IF EXISTS payments;
            DROP TABLE IF EXISTS subscriptions;
        """,
    ),
    # Migration 012 — Phase 119: photo annotation layer
    Migration(
        version=12,
        name="photo_annotation_layer",
        description=(
            "Phase 119: Create photo_annotations table for coordinate-based "
            "shape annotations (circles, rectangles, arrows, text labels) "
            "on arbitrary images. Coords normalized 0.0–1.0 so annotations "
            "survive image resize. Optional FK to failure_photos (CASCADE) "
            "for DB-linked annotations; opaque image_ref lets annotations "
            "attach to any image. Track Q phase 307 renders the canvas overlay."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS photo_annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_ref TEXT NOT NULL,
                failure_photo_id INTEGER,
                shape TEXT NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                width REAL,
                height REAL,
                text TEXT,
                color TEXT NOT NULL DEFAULT '#FF0000',
                stroke_width INTEGER NOT NULL DEFAULT 2,
                label TEXT,
                created_by_user_id INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (failure_photo_id) REFERENCES failure_photos(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
            );

            CREATE INDEX IF NOT EXISTS idx_photo_ann_image ON photo_annotations(image_ref);
            CREATE INDEX IF NOT EXISTS idx_photo_ann_photo ON photo_annotations(failure_photo_id);
            CREATE INDEX IF NOT EXISTS idx_photo_ann_user ON photo_annotations(created_by_user_id);
        """,
        rollback_sql="""
            DROP TABLE IF EXISTS photo_annotations;
        """,
    ),
    # Migration 013 — Phase 122: intake usage log (photo bike ID quota tracking)
    Migration(
        version=13,
        name="intake_usage_log",
        description=(
            "Phase 122: Create intake_usage_log table for tracking photo-based "
            "vehicle identification usage per user per month. Supports quota "
            "enforcement (individual 20/mo, shop 200/mo, company unlimited), "
            "sha256 image cache lookup, and cost tracking. Image bytes never "
            "persist — only the preprocessed-bytes sha256 hash."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS intake_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                model_used TEXT,
                confidence REAL,
                image_hash TEXT,
                tokens_input INTEGER NOT NULL DEFAULT 0,
                tokens_output INTEGER NOT NULL DEFAULT 0,
                cost_cents INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_intake_user ON intake_usage_log(user_id);
            CREATE INDEX IF NOT EXISTS idx_intake_user_time ON intake_usage_log(user_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_intake_image_hash ON intake_usage_log(image_hash);
        """,
        rollback_sql="""
            DROP TABLE IF EXISTS intake_usage_log;
        """,
    ),
    # Migration 014 — Phase 127: session history browser notes column
    Migration(
        version=14,
        name="session_notes_column",
        description=(
            "Phase 127: Add nullable `notes` TEXT column to diagnostic_sessions "
            "to support append-only post-hoc annotations (reopen + annotate "
            "workflow). Existing rows get NULL. No index — free-text search "
            "uses LIKE; Phase 128's knowledge browser may add FTS5 later. "
            "Follows the same pattern as migration 005's user_id retrofit column."
        ),
        upgrade_sql="""
            ALTER TABLE diagnostic_sessions ADD COLUMN notes TEXT;
        """,
        rollback_sql="""
            -- Rollback 014: SQLite does not support ALTER TABLE DROP COLUMN
            -- on versions prior to 3.35. The `notes` column is retained (same
            -- pattern as migration 005's user_id retrofit columns). It is
            -- nullable with no default, so leaving it in place is harmless.
            -- Full removal would require CREATE-COPY-DROP-RENAME which is not
            -- needed for rollback testing; the column is effectively inert.
        """,
    ),
    # Migration 015 — Phase 131: AI response cache table (offline mode + caching)
    Migration(
        version=15,
        name="ai_response_cache",
        description=(
            "Phase 131: Create ai_response_cache table to support transparent "
            "caching of AI responses (DiagnosticClient.diagnose + "
            "FaultCodeInterpreter.interpret) and offline mode. Cache key is "
            "SHA256 of canonical-JSON inputs (kind-prefixed). Cache entries "
            "live forever until explicit purge via `motodiag cache purge "
            "--older-than N` or `motodiag cache clear`. Two indexes: "
            "cache_key (for lookup) and created_at (for purge-older-than "
            "queries). hit_count + last_used_at let shop owners see which "
            "cached queries are actually paying off via `motodiag cache stats`."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS ai_response_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                kind TEXT NOT NULL,
                model_used TEXT,
                response_json TEXT NOT NULL,
                tokens_input INTEGER DEFAULT 0,
                tokens_output INTEGER DEFAULT 0,
                cost_cents INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP,
                hit_count INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_ai_cache_key ON ai_response_cache(cache_key);
            CREATE INDEX IF NOT EXISTS idx_ai_cache_created ON ai_response_cache(created_at);
        """,
        rollback_sql="""
            DROP TABLE IF EXISTS ai_response_cache;
        """,
    ),
    # Migration 016 — Phase 142: sensor recordings + samples substrate
    Migration(
        version=16,
        name="sensor_recordings",
        description=(
            "Phase 142: Create sensor_recordings (session metadata) and "
            "sensor_samples (individual PID readings) tables supporting "
            "`motodiag hardware log start/stop/list/show/replay/diff/export/"
            "prune`. Designed for the SQLite + JSONL split policy: under "
            "1000 rows per recording stays in SQLite with file_ref NULL; "
            "above the threshold spills to ~/.motodiag/recordings/<uuid>.jsonl "
            "and sensor_samples retains every 100th reading as a sparse "
            "summary (file_ref stores the sidecar filename). "
            "sensor_recordings.vehicle_id is NULLABLE for dealer-lot scenarios "
            "(pre-sale diagnostic without a garage entry yet) and uses ON "
            "DELETE SET NULL so deleting a vehicle does not cascade-destroy "
            "its recording history. sensor_samples.recording_id uses ON "
            "DELETE CASCADE so removing a recording cleanly removes its "
            "SQLite rows. pid_hex is stored as the Phase 141 SensorReading "
            "format `\"0x0C\"` (with `0x` prefix, uppercase hex byte) to "
            "keep one canonical string representation across the codebase. "
            "Four indexes support the dominant query shapes: list by "
            "vehicle, list by recency, time-ordered playback, and per-PID "
            "diff joins."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS sensor_recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                session_label TEXT,
                started_at TIMESTAMP NOT NULL,
                stopped_at TIMESTAMP,
                protocol_name TEXT NOT NULL,
                pids_csv TEXT NOT NULL,
                notes TEXT,
                sample_count INTEGER NOT NULL DEFAULT 0,
                max_hz REAL,
                min_hz REAL,
                file_ref TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_recordings_vehicle
                ON sensor_recordings(vehicle_id);
            CREATE INDEX IF NOT EXISTS idx_recordings_started
                ON sensor_recordings(started_at);

            CREATE TABLE IF NOT EXISTS sensor_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id INTEGER NOT NULL,
                captured_at TIMESTAMP NOT NULL,
                pid_hex TEXT NOT NULL,
                value REAL,
                raw INTEGER,
                unit TEXT,
                FOREIGN KEY (recording_id) REFERENCES sensor_recordings(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_samples_recording_time
                ON sensor_samples(recording_id, captured_at);
            CREATE INDEX IF NOT EXISTS idx_samples_recording_pid
                ON sensor_samples(recording_id, pid_hex);
        """,
        rollback_sql="""
            -- Child table first to respect FK ordering even under PRAGMA
            -- foreign_keys=ON semantics during rollback tests.
            DROP TABLE IF EXISTS sensor_samples;
            DROP TABLE IF EXISTS sensor_recordings;
        """,
    ),
    # Migration 017 — Phase 145: adapter compatibility database
    Migration(
        version=17,
        name="adapter_compatibility",
        description=(
            "Phase 145: Create three-table adapter compatibility knowledge "
            "base supporting `motodiag hardware compat "
            "{list,recommend,check,show,note add,note list,seed}`. "
            "obd_adapters catalogs 20-25 real-world OBD adapters across "
            "five price tiers (generic ELM327 clones through OEM dealer "
            "tools) with chipset, transport, supported protocols, "
            "bidirectional/Mode22 flags, and reliability 1-5. "
            "adapter_compatibility stores (adapter, make, model-pattern, "
            "year-range) → status rows using SQL LIKE patterns so one "
            "entry can cover a model family (`'CBR%'`). compat_notes is "
            "the free-text mechanic knowledge layer — quirks, "
            "workarounds, known-failures, tips — scoped per (adapter, "
            "make) with `'*'` as the any-make wildcard. Three CHECK "
            "constraints (reliability 1-5, price >= 0, bit-flags 0/1) "
            "+ two enum CHECKs (status, note_type). FK cascades: "
            "compat_notes + adapter_compatibility child-delete when "
            "adapter_id is removed; submitted_by_user_id → users SET "
            "DEFAULT so removing a user preserves the note attributed "
            "to system user id=1. Six indexes support the dominant "
            "query shapes: slug lookup, chipset filter, make+model-"
            "pattern match, make+year range, adapter join, and note "
            "lookup by (adapter, make)."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS obd_adapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                chipset TEXT NOT NULL,
                transport TEXT NOT NULL,
                price_usd_cents INTEGER NOT NULL DEFAULT 0,
                purchase_url TEXT,
                supported_protocols_csv TEXT NOT NULL,
                supports_bidirectional INTEGER NOT NULL DEFAULT 0,
                supports_mode22 INTEGER NOT NULL DEFAULT 0,
                reliability_1to5 INTEGER NOT NULL DEFAULT 3,
                known_issues TEXT,
                notes TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (reliability_1to5 BETWEEN 1 AND 5),
                CHECK (price_usd_cents >= 0),
                CHECK (supports_bidirectional IN (0, 1)),
                CHECK (supports_mode22 IN (0, 1))
            );

            CREATE INDEX IF NOT EXISTS idx_obd_adapters_slug
                ON obd_adapters(slug);
            CREATE INDEX IF NOT EXISTS idx_obd_adapters_chipset
                ON obd_adapters(chipset);

            CREATE TABLE IF NOT EXISTS adapter_compatibility (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adapter_id INTEGER NOT NULL,
                vehicle_make TEXT NOT NULL,
                vehicle_model_pattern TEXT NOT NULL,
                year_min INTEGER,
                year_max INTEGER,
                status TEXT NOT NULL,
                notes TEXT,
                verified_by TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (adapter_id) REFERENCES obd_adapters(id) ON DELETE CASCADE,
                CHECK (status IN ('full','partial','read-only','incompatible'))
            );

            CREATE INDEX IF NOT EXISTS idx_compat_make_model
                ON adapter_compatibility(vehicle_make, vehicle_model_pattern);
            CREATE INDEX IF NOT EXISTS idx_compat_make_year
                ON adapter_compatibility(vehicle_make, year_min, year_max);
            CREATE INDEX IF NOT EXISTS idx_compat_adapter
                ON adapter_compatibility(adapter_id);

            CREATE TABLE IF NOT EXISTS compat_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adapter_id INTEGER NOT NULL,
                vehicle_make TEXT NOT NULL,
                note_type TEXT NOT NULL,
                body TEXT NOT NULL,
                source_url TEXT,
                submitted_by_user_id INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (adapter_id) REFERENCES obd_adapters(id) ON DELETE CASCADE,
                FOREIGN KEY (submitted_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT,
                CHECK (note_type IN ('quirk','workaround','known-failure','tip'))
            );

            CREATE INDEX IF NOT EXISTS idx_compat_notes_adapter_make
                ON compat_notes(adapter_id, vehicle_make);
        """,
        rollback_sql="""
            -- Child-first drop order respects FK (compat_notes and
            -- adapter_compatibility both reference obd_adapters).
            DROP TABLE IF EXISTS compat_notes;
            DROP TABLE IF EXISTS adapter_compatibility;
            DROP TABLE IF EXISTS obd_adapters;
        """,
    ),
    # Migration 018 — Phase 150: fleet management
    Migration(
        version=18,
        name="fleet_management",
        description=(
            "Phase 150: Create two-table fleet management system. "
            "`fleets` catalogs named groupings of bikes (rental fleets, "
            "demo lineups, race teams) scoped per-owner via UNIQUE "
            "(owner_user_id, name). `fleet_bikes` is the many-to-many "
            "junction between fleets and vehicles, carrying a per-"
            "assignment `role` (rental/demo/race/customer) and "
            "`added_at` timestamp. FK CASCADE on both sides of the "
            "junction: deleting a fleet drops its junction rows but "
            "leaves vehicles intact (bikes survive fleet dissolution "
            "— non-negotiable spec #3); deleting a vehicle drops its "
            "junction rows but leaves fleets intact. `owner_user_id` "
            "→ users.id ON DELETE SET DEFAULT so removing a user "
            "reassigns their fleets to the system user (id=1), "
            "mirroring the Phase 112/145 retrofit pattern. Two indexes "
            "support the dominant query shapes: lookup fleets by "
            "(owner, name) and reverse-lookup `list_fleets_for_bike`."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS fleets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                owner_user_id INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET DEFAULT,
                UNIQUE (owner_user_id, name)
            );

            CREATE INDEX IF NOT EXISTS idx_fleets_owner_name
                ON fleets(owner_user_id, name);

            CREATE TABLE IF NOT EXISTS fleet_bikes (
                fleet_id INTEGER NOT NULL,
                vehicle_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'customer',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (fleet_id, vehicle_id),
                FOREIGN KEY (fleet_id) REFERENCES fleets(id) ON DELETE CASCADE,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
                CHECK (role IN ('rental','demo','race','customer'))
            );

            CREATE INDEX IF NOT EXISTS idx_fleet_bikes_vehicle
                ON fleet_bikes(vehicle_id);
        """,
        rollback_sql="""
            -- Child-first drop order respects FK (fleet_bikes references
            -- fleets and vehicles).
            DROP TABLE IF EXISTS fleet_bikes;
            DROP TABLE IF EXISTS fleets;
        """,
    ),
    # Migration 019 — Phase 151: service-interval scheduling
    Migration(
        version=19,
        name="service_interval_scheduling",
        description=(
            "Phase 151: Create a two-table service-interval scheduling "
            "system layered over the vehicles registry. "
            "`service_intervals` carries per-bike maintenance schedules "
            "(oil change, valve check, chain lube, etc.) keyed by "
            "(vehicle_id, item_slug) UNIQUE, with FK CASCADE on "
            "vehicle_id so deleting a bike drops its schedule. Dual-"
            "axis due: every_miles OR every_months may be set (CHECK "
            "ensures at least one is non-NULL), and last_done_* + "
            "next_due_* track the most recent completion plus the "
            "computed next-due point. "
            "`service_interval_templates` is a global seed catalog — "
            "OEM-recommended intervals per (make, model_pattern). Both "
            "'harley-davidson' + SQL LIKE 'Sportster%' model patterns "
            "and universal '*'/'%' wildcards are supported so a single "
            "template can cover a whole make or the entire fleet. "
            "Three indexes support the dominant query shapes: "
            "`idx_svc_int_vehicle` for per-bike schedule loads, "
            "`idx_svc_int_next_due` for ORDER BY next_due_at sweeps, "
            "and `idx_svc_tpl_make_model` for template lookups. "
            "Phase 152 will add `vehicles.mileage` + `service_history` "
            "— this phase's record_completion reads/writes them via "
            "try/except so the soft-dep is free when 152 lands."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS service_intervals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                item_slug TEXT NOT NULL,
                description TEXT NOT NULL,
                every_miles INTEGER,
                every_months INTEGER,
                last_done_miles INTEGER,
                last_done_at TEXT,
                next_due_miles INTEGER,
                next_due_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
                UNIQUE (vehicle_id, item_slug),
                CHECK (every_miles IS NOT NULL OR every_months IS NOT NULL)
            );

            CREATE INDEX IF NOT EXISTS idx_svc_int_vehicle
                ON service_intervals(vehicle_id);
            CREATE INDEX IF NOT EXISTS idx_svc_int_next_due
                ON service_intervals(next_due_at);

            CREATE TABLE IF NOT EXISTS service_interval_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                make TEXT NOT NULL,
                model_pattern TEXT NOT NULL,
                item_slug TEXT NOT NULL,
                description TEXT NOT NULL,
                every_miles INTEGER,
                every_months INTEGER,
                notes TEXT,
                CHECK (every_miles IS NOT NULL OR every_months IS NOT NULL),
                UNIQUE (make, model_pattern, item_slug)
            );

            CREATE INDEX IF NOT EXISTS idx_svc_tpl_make_model
                ON service_interval_templates(make, model_pattern);
        """,
        rollback_sql="""
            -- Child-first drop order respects FK (service_intervals
            -- references vehicles). No cross-table FK between the two
            -- 019 tables, so order between them is only stylistic.
            DROP TABLE IF EXISTS service_intervals;
            DROP TABLE IF EXISTS service_interval_templates;
        """,
    ),
    # Migration 020 — Phase 152: service history tracking + vehicles.mileage
    Migration(
        version=20,
        name="service_history_tracking",
        description=(
            "Phase 152: Add `vehicles.mileage` INTEGER NULL column as "
            "the persistent source-of-truth for per-bike odometer "
            "readings. Create `service_history` table — one row per "
            "completed service event across the 11-value event_type "
            "vocabulary (oil-change, tire, valve-adjust, brake, "
            "diagnostic, recall, chain, coolant, air-filter, "
            "spark-plug, custom). Each event stores at_miles + at_date "
            "(ISO-8601), optional notes, cost_cents, mechanic_user_id "
            "FK, and a comma-separated parts_csv. A CHECK constraint "
            "enforces the event_type enum; the set is mirrored in the "
            "Pydantic `ServiceEvent.event_type: Literal[...]` so the "
            "model and DB can't drift without touching both. FK "
            "cascades: vehicle_id → vehicles(id) ON DELETE CASCADE "
            "(service history dies with its bike — non-negotiable "
            "spec #4); mechanic_user_id → users(id) ON DELETE SET "
            "NULL (history survives mechanic removal, loses "
            "attribution only — mirrors the Phase 112/145/150 user-"
            "deletion preservation pattern). Three indexes support "
            "the dominant query shapes: per-bike timeline "
            "`(vehicle_id, at_date DESC)`, per-type cross-bike "
            "filters `(event_type, at_date DESC)`, and a global "
            "recent-events feed `(at_date DESC)`. Rollback drops "
            "service_history + its indexes but leaves vehicles.mileage "
            "in place — SQLite pre-3.35 lacks native DROP COLUMN and "
            "the CREATE-COPY-DROP-RENAME dance would churn every "
            "existing row for a nullable column that causes no harm. "
            "The predictor gains a +0.05 confidence bonus when "
            "`vehicle['mileage_source'] == 'db'` — the CLI sets this "
            "flag when the bike's stored mileage is used without a "
            "--current-miles override, telling the scorer that the "
            "reading came from a logged service event rather than a "
            "user-asserted value."
        ),
        upgrade_sql="""
            ALTER TABLE vehicles ADD COLUMN mileage INTEGER;

            CREATE TABLE IF NOT EXISTS service_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                at_miles INTEGER,
                at_date TEXT NOT NULL,
                notes TEXT,
                cost_cents INTEGER,
                mechanic_user_id INTEGER,
                parts_csv TEXT,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
                FOREIGN KEY (mechanic_user_id) REFERENCES users(id) ON DELETE SET NULL,
                CHECK (event_type IN (
                    'oil-change','tire','valve-adjust','brake',
                    'diagnostic','recall','chain','coolant',
                    'air-filter','spark-plug','custom'
                ))
            );

            CREATE INDEX IF NOT EXISTS idx_service_history_vehicle
                ON service_history(vehicle_id, at_date DESC);
            CREATE INDEX IF NOT EXISTS idx_service_history_type
                ON service_history(event_type, at_date DESC);
            CREATE INDEX IF NOT EXISTS idx_service_history_date
                ON service_history(at_date DESC);
        """,
        rollback_sql="""
            -- vehicles.mileage stays in place: SQLite pre-3.35 lacks
            -- native DROP COLUMN; the nullable leftover is inert.
            DROP INDEX IF EXISTS idx_service_history_vehicle;
            DROP INDEX IF EXISTS idx_service_history_type;
            DROP INDEX IF EXISTS idx_service_history_date;
            DROP TABLE IF EXISTS service_history;
        """,
    ),
    # Migration 021 — Phase 153: parts cross-reference
    Migration(
        version=21,
        name="parts_cross_reference",
        description=(
            "Phase 153: Create a two-table OEM ↔ aftermarket parts "
            "cross-reference system. `parts` catalogs individual parts "
            "(both OEM and aftermarket) keyed by a UNIQUE `slug` so "
            "re-seeding is idempotent. Each row carries the "
            "manufacturer-side identity (`oem_part_number`, `brand`), "
            "the mechanic-facing descriptor (`description`, `category`), "
            "the bike scope (`make` lowercased on insert, "
            "`model_pattern` using SQL LIKE wildcards so one row can "
            "cover 'CBR%' or 'Sportster%' families, plus optional "
            "`year_min`/`year_max`), economic metadata "
            "(`typical_cost_cents` CHECK ≥ 0, `purchase_url`), and "
            "provenance (`notes`, `verified_by`). "
            "`parts_xref` is the many-to-many join between OEM and "
            "aftermarket parts, carrying a curated `equivalence_rating` "
            "1-5 (5=drop-in, 4=minor notes, 3=functional-equiv-with-"
            "tweak, 2=partial, 1=related) along with optional `notes` "
            "and `source_url`. UNIQUE(oem_part_id, aftermarket_part_id) "
            "de-dupes cross-references so loaders can INSERT OR IGNORE "
            "on the natural key for idempotent re-seeding. A CHECK "
            "constraint `oem_part_id != aftermarket_part_id` blocks "
            "self-reference. FK cascades: both xref sides → parts(id) "
            "ON DELETE CASCADE so removing a part drops its "
            "cross-references automatically; submitted_by_user_id → "
            "users(id) ON DELETE SET DEFAULT preserves xrefs attributed "
            "to the system user id=1 when the submitter is removed "
            "(mirrors the Phase 112/145/150/152 user-deletion "
            "preservation pattern). Four indexes support the dominant "
            "query shapes: `idx_parts_oem` (lookup by OEM part "
            "number), `idx_parts_make_cat` (list-for-bike queries), "
            "`idx_parts_slug` (slug lookups), and `idx_xref_oem` "
            "(reverse traversal from one OEM to its aftermarket "
            "alternatives)."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                oem_part_number TEXT,
                brand TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                make TEXT NOT NULL,
                model_pattern TEXT NOT NULL,
                year_min INTEGER,
                year_max INTEGER,
                typical_cost_cents INTEGER NOT NULL DEFAULT 0,
                purchase_url TEXT,
                notes TEXT,
                verified_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (typical_cost_cents >= 0)
            );

            CREATE INDEX IF NOT EXISTS idx_parts_oem
                ON parts(oem_part_number);
            CREATE INDEX IF NOT EXISTS idx_parts_make_cat
                ON parts(make, category);
            CREATE INDEX IF NOT EXISTS idx_parts_slug
                ON parts(slug);

            CREATE TABLE IF NOT EXISTS parts_xref (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oem_part_id INTEGER NOT NULL,
                aftermarket_part_id INTEGER NOT NULL,
                equivalence_rating INTEGER NOT NULL DEFAULT 3,
                notes TEXT,
                source_url TEXT,
                submitted_by_user_id INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (oem_part_id) REFERENCES parts(id) ON DELETE CASCADE,
                FOREIGN KEY (aftermarket_part_id) REFERENCES parts(id) ON DELETE CASCADE,
                FOREIGN KEY (submitted_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT,
                UNIQUE (oem_part_id, aftermarket_part_id),
                CHECK (equivalence_rating BETWEEN 1 AND 5),
                CHECK (oem_part_id != aftermarket_part_id)
            );

            CREATE INDEX IF NOT EXISTS idx_xref_oem
                ON parts_xref(oem_part_id);
        """,
        rollback_sql="""
            -- Child-first drop order respects FK (parts_xref references
            -- parts on both sides).
            DROP TABLE IF EXISTS parts_xref;
            DROP TABLE IF EXISTS parts;
        """,
    ),
    # Migration 022 — Phase 154: technical service bulletins (TSBs)
    Migration(
        version=22,
        name="technical_service_bulletins",
        description=(
            "Phase 154: Create the `technical_service_bulletins` table "
            "catalogging OEM-issued Technical Service Bulletins — "
            "official fixes for known issues, distinct from Phase 155 "
            "federal safety recalls and Phase 08 forum-consensus "
            "`known_issues`. Keyed by UNIQUE `tsb_number` (HD 'M-1287', "
            "Honda 'MC-19-123', Yamaha 'TB-2019-045') so re-seeding is "
            "idempotent via INSERT OR IGNORE. `make` stores lowercased, "
            "`model_pattern` uses SQL LIKE wildcards so a single row can "
            "cover 'Dyna%' or 'CBR600%' families, with optional "
            "`year_min`/`year_max` bounds. `severity` CHECK in "
            "(critical, high, medium, low) mirrors the knowledge-base "
            "severity ladder. `source_url` tracks the public citation "
            "(service.h-d.com, powersports.honda.com, forum archives); "
            "`verified_by` captures the provenance chain. Three indexes "
            "support the dominant query shapes: `idx_tsb_make_model` "
            "(list-for-bike), `idx_tsb_number` (show by tsb_number), "
            "and `idx_tsb_issued` DESC (recent-first list + by-make "
            "queries). No FK to other tables — TSBs are a standalone "
            "provenance layer referenced by id/number strings only."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS technical_service_bulletins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tsb_number TEXT NOT NULL UNIQUE,
                make TEXT NOT NULL,
                model_pattern TEXT NOT NULL,
                year_min INTEGER,
                year_max INTEGER,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                fix_procedure TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                issued_date TEXT NOT NULL,
                source_url TEXT,
                verified_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (severity IN ('critical', 'high', 'medium', 'low'))
            );

            CREATE INDEX IF NOT EXISTS idx_tsb_make_model
                ON technical_service_bulletins(make, model_pattern);
            CREATE INDEX IF NOT EXISTS idx_tsb_number
                ON technical_service_bulletins(tsb_number);
            CREATE INDEX IF NOT EXISTS idx_tsb_issued
                ON technical_service_bulletins(issued_date DESC);
        """,
        rollback_sql="""
            DROP TABLE IF EXISTS technical_service_bulletins;
        """,
    ),
    # Migration 023 — Phase 155: NHTSA safety recall extension
    Migration(
        version=23,
        name="recalls_nhtsa_extension",
        description=(
            "Phase 155: EXTEND the Phase 118 `recalls` substrate (schema-"
            "only, zero data) into a working NHTSA safety-recall lookup. "
            "Distinct from Phase 154 TSBs (manufacturer non-safety) — "
            "recalls are federal-mandate-to-fix, free to the owner, and "
            "trump forum consensus. "
            "ALTER TABLE (SQLite-safe) adds three columns: `nhtsa_id TEXT` "
            "stores the opaque NHTSA campaign identifier (22V123000 "
            "pattern); `vin_range TEXT` is either NULL (all-VIN campaign) "
            "or a JSON list of [prefix_start, prefix_end] tuples for "
            "partial-VIN scoped recalls; `open INTEGER NOT NULL DEFAULT "
            "1` tracks whether the campaign is still outstanding (the "
            "NOT NULL + default preserves pre-existing Phase 118 NULL "
            "rows — they retrofit to open=1 on the ALTER). "
            "Since SQLite ALTER cannot add a UNIQUE constraint, "
            "`idx_recalls_nhtsa_id` is declared as a partial UNIQUE INDEX "
            "WHERE nhtsa_id IS NOT NULL — two rows with NULL nhtsa_id "
            "(Phase 118 substrate) coexist; two non-NULL matching rows "
            "raise IntegrityError. `idx_recalls_open` supports the "
            "dominant filter (most list_ queries scope to open=1). "
            "The new `recall_resolutions` table records per-vehicle "
            "resolutions: UNIQUE(vehicle_id, recall_id) makes "
            "`mark_resolved` idempotent, FK CASCADE on vehicle + recall "
            "deletes drops resolutions automatically, FK SET NULL on "
            "the optional resolved_by_user_id preserves resolution "
            "history when a user is removed (mirrors Phase 112/150/152 "
            "user-deletion preservation pattern). Two indexes support "
            "the dominant queries: `idx_recall_res_vehicle` "
            "(list_open_for_bike LEFT JOIN) and `idx_recall_res_recall` "
            "(by-campaign rollup)."
        ),
        upgrade_sql="""
            -- ALTER recalls table: add NHTSA-ID, VIN range, open-status columns.
            -- SQLite ALTER cannot add UNIQUE; we follow with a partial
            -- UNIQUE INDEX that only enforces non-NULL rows (Phase 118
            -- substrate rows with NULL nhtsa_id remain valid).
            ALTER TABLE recalls ADD COLUMN nhtsa_id TEXT;
            ALTER TABLE recalls ADD COLUMN vin_range TEXT;
            ALTER TABLE recalls ADD COLUMN open INTEGER NOT NULL DEFAULT 1;

            CREATE UNIQUE INDEX IF NOT EXISTS idx_recalls_nhtsa_id
                ON recalls(nhtsa_id) WHERE nhtsa_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_recalls_open
                ON recalls(open);

            -- New table: recall_resolutions tracks per-vehicle closure.
            CREATE TABLE IF NOT EXISTS recall_resolutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                recall_id INTEGER NOT NULL,
                resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_by_user_id INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
                FOREIGN KEY (recall_id) REFERENCES recalls(id) ON DELETE CASCADE,
                FOREIGN KEY (resolved_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
                UNIQUE (vehicle_id, recall_id)
            );

            CREATE INDEX IF NOT EXISTS idx_recall_res_vehicle
                ON recall_resolutions(vehicle_id);
            CREATE INDEX IF NOT EXISTS idx_recall_res_recall
                ON recall_resolutions(recall_id);
        """,
        rollback_sql="""
            -- Child-first drop order (recall_resolutions has FKs to
            -- recalls and vehicles; recalls is parent). Drop the
            -- resolutions table + its indexes, then drop the partial
            -- UNIQUE INDEX and the open index. SQLite pre-3.35 cannot
            -- DROP COLUMN via ALTER — the nhtsa_id / vin_range / open
            -- columns are left in place on rollback. This is a
            -- documented limitation: callers needing a strict schema-
            -- only rollback should rebuild via CREATE-COPY-DROP-RENAME
            -- against the Phase 118 recalls shape.
            DROP INDEX IF EXISTS idx_recall_res_vehicle;
            DROP INDEX IF EXISTS idx_recall_res_recall;
            DROP TABLE IF EXISTS recall_resolutions;
            DROP INDEX IF EXISTS idx_recalls_nhtsa_id;
            DROP INDEX IF EXISTS idx_recalls_open;
        """,
    ),
    # Migration 024 — Phase 157: performance baselining
    Migration(
        version=24,
        name="performance_baselines",
        description=(
            "Phase 157: Two-table split — `performance_baselines` holds the "
            "aggregated expected-range band (min / median / max) for each "
            "(make, model_pattern SQL LIKE, optional year_min / year_max, "
            "canonical pid_hex `0x05`, operating_state in "
            "{idle, 2500rpm, redline}) tuple, while `baseline_exemplars` "
            "records provenance: which sensor recordings mechanics flagged "
            "as known-healthy and thus fed the aggregates. The split "
            "mirrors Phase 145 `obd_adapters`/`compat_notes` and Phase "
            "153 `parts`/`parts_xref`: aggregate rows stay cheap to query "
            "while raw exemplars preserve the audit trail. "
            "`performance_baselines` CHECK constraints: `operating_state` "
            "IN ('idle','2500rpm','redline'), `confidence_1to5` BETWEEN "
            "1 AND 5, and `expected_min <= expected_median <= "
            "expected_max` (band sanity — a rebuild producing a "
            "degenerate band fails fast rather than silently persisting "
            "bad data). `sample_count` DEFAULT 0 so INSERT OR IGNORE "
            "stubs don't NULL-out the raw count; `last_rebuilt_at` "
            "defaults to CURRENT_TIMESTAMP so stale rows are easy to "
            "spot. `baseline_exemplars` UNIQUE(recording_id) enforces "
            "idempotent `flag_recording_as_healthy` — re-flagging the "
            "same recording is a no-op via INSERT OR IGNORE. FK cascades "
            "match Phase 142 / Phase 112 conventions: vehicle_id → "
            "vehicles(id) ON DELETE SET NULL (exemplar survives when the "
            "bike is deleted, loses its back-reference only); "
            "recording_id → sensor_recordings(id) ON DELETE CASCADE "
            "(exemplar dies with its underlying recording — without the "
            "raw data the flag is meaningless); flagged_by_user_id → "
            "users(id) ON DELETE SET DEFAULT (preserves attribution to "
            "the system user id=1 when a mechanic account is removed). "
            "Two indexes support dominant query shapes: "
            "`idx_baselines_lookup` on (make, model_pattern, pid_hex, "
            "operating_state) covers `get_baseline` exactly, and "
            "`idx_exemplars_vehicle` covers the 'which recordings for "
            "bike #N count as healthy?' reverse lookup. Rollback drops "
            "baseline_exemplars first (child) then performance_baselines "
            "(parent) to respect the FK."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS performance_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                make TEXT NOT NULL,
                model_pattern TEXT NOT NULL,
                year_min INTEGER,
                year_max INTEGER,
                pid_hex TEXT NOT NULL,
                operating_state TEXT NOT NULL,
                expected_min REAL NOT NULL,
                expected_max REAL NOT NULL,
                expected_median REAL NOT NULL,
                sample_count INTEGER NOT NULL DEFAULT 0,
                last_rebuilt_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confidence_1to5 INTEGER NOT NULL DEFAULT 1,
                CHECK (operating_state IN ('idle', '2500rpm', 'redline')),
                CHECK (confidence_1to5 BETWEEN 1 AND 5),
                CHECK (expected_min <= expected_median
                       AND expected_median <= expected_max)
            );

            CREATE INDEX IF NOT EXISTS idx_baselines_lookup
                ON performance_baselines(
                    make, model_pattern, pid_hex, operating_state
                );

            CREATE TABLE IF NOT EXISTS baseline_exemplars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                recording_id INTEGER NOT NULL UNIQUE,
                flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                flagged_by_user_id INTEGER DEFAULT 1,
                FOREIGN KEY (vehicle_id)
                    REFERENCES vehicles(id) ON DELETE SET NULL,
                FOREIGN KEY (recording_id)
                    REFERENCES sensor_recordings(id) ON DELETE CASCADE,
                FOREIGN KEY (flagged_by_user_id)
                    REFERENCES users(id) ON DELETE SET DEFAULT
            );

            CREATE INDEX IF NOT EXISTS idx_exemplars_vehicle
                ON baseline_exemplars(vehicle_id);
        """,
        rollback_sql="""
            -- Child-first drop respects the recording_id FK.
            DROP INDEX IF EXISTS idx_exemplars_vehicle;
            DROP TABLE IF EXISTS baseline_exemplars;
            DROP INDEX IF EXISTS idx_baselines_lookup;
            DROP TABLE IF EXISTS performance_baselines;
        """,
    ),
    # Migration 025 — Phase 160: shop profile + multi-bike intake (Track G)
    Migration(
        version=25,
        name="shops_and_intake_visits",
        description=(
            "Phase 160: First Track G phase. Opens shop management with the "
            "narrowest possible slice — register a shop profile and log bike "
            "arrivals as intake_visits rows. Explicitly reuses Phase 113's "
            "customers + customer_bikes (migration 006) rather than "
            "duplicating CRM state. Two tables: `shops` (profile: name, "
            "address, contact, hours_json, tax_id, scoped UNIQUE(owner, "
            "name) per the fleets pattern from migration 018) and "
            "`intake_visits` (arrival event linking shop_id + customer_id + "
            "vehicle_id at intake_at with reported_problems freetext + "
            "guarded status lifecycle `open -> closed | cancelled -> "
            "(reopen) -> open`). FK asymmetry is deliberate: shop_id "
            "CASCADE (shop deletion is rare, explicit, confirmed — "
            "cascading keeps history tidy), customer_id + vehicle_id "
            "RESTRICT (prevents accidental history erasure via unrelated "
            "deletes — mechanics deactivate customers rather than "
            "deleting them). Three indexes cover the dominant access "
            "patterns: (shop_id, status) for the daily open-queue query, "
            "(vehicle_id) for 'is this bike already checked in?' duplicate-"
            "intake prevention, and (customer_id) for 'show me this "
            "customer's visit history.' mileage_at_intake nullable "
            "because walk-in carb rebuilds on bikes with broken speedos "
            "happen — and intake_visits is an at-arrival snapshot, not "
            "a service record (the Phase 152 monotonic-mileage rules "
            "apply to service_history, not to intake). Rollback drops "
            "intake_visits first (child of shops) then shops."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS shops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER NOT NULL DEFAULT 1,
                name TEXT NOT NULL,
                address TEXT,
                city TEXT,
                state TEXT,
                zip TEXT,
                phone TEXT,
                email TEXT,
                tax_id TEXT,
                hours_json TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET DEFAULT,
                UNIQUE (owner_user_id, name)
            );
            CREATE INDEX IF NOT EXISTS idx_shops_owner_name
                ON shops(owner_user_id, name);

            CREATE TABLE IF NOT EXISTS intake_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                vehicle_id INTEGER NOT NULL,
                intake_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                mileage_at_intake INTEGER,
                reported_problems TEXT,
                intake_user_id INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','closed','cancelled')),
                closed_at TIMESTAMP,
                close_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE CASCADE,
                FOREIGN KEY (customer_id)
                    REFERENCES customers(id) ON DELETE RESTRICT,
                FOREIGN KEY (vehicle_id)
                    REFERENCES vehicles(id) ON DELETE RESTRICT,
                FOREIGN KEY (intake_user_id)
                    REFERENCES users(id) ON DELETE SET DEFAULT
            );
            CREATE INDEX IF NOT EXISTS idx_intake_shop_status
                ON intake_visits(shop_id, status);
            CREATE INDEX IF NOT EXISTS idx_intake_vehicle
                ON intake_visits(vehicle_id);
            CREATE INDEX IF NOT EXISTS idx_intake_customer
                ON intake_visits(customer_id);
        """,
        rollback_sql="""
            -- Child-first drop respects the shop_id FK.
            DROP INDEX IF EXISTS idx_intake_customer;
            DROP INDEX IF EXISTS idx_intake_vehicle;
            DROP INDEX IF EXISTS idx_intake_shop_status;
            DROP TABLE IF EXISTS intake_visits;
            DROP INDEX IF EXISTS idx_shops_owner_name;
            DROP TABLE IF EXISTS shops;
        """,
    ),
    # Migration 026 — Phase 161: work orders (Track G, continues)
    Migration(
        version=26,
        name="work_orders",
        description=(
            "Phase 161: Second Track G phase. Creates `work_orders` — the "
            "mechanic's unit of work on a specific bike. Attaches to "
            "Phase 160 `intake_visits` via nullable `intake_visit_id` FK "
            "(SET NULL on intake delete; work history survives an "
            "accidental intake wipe). Denormalizes `shop_id` + "
            "`vehicle_id` + `customer_id` onto the work order itself so "
            "dominant queries — 'list work orders for shop X', 'list "
            "work orders for bike Y', 'list work orders for customer "
            "Z' — are single-index lookups rather than JOINs. FK "
            "asymmetry mirrors Phase 160: shop_id CASCADE (rare, "
            "explicit, confirmed), vehicle_id + customer_id RESTRICT "
            "(prevent accidental history erasure), "
            "assigned_mechanic_user_id SET NULL (orphaned WOs remain "
            "re-assignable when a mechanic account is removed in Phase "
            "172), created_by_user_id SET DEFAULT (fallback to system "
            "user id=1 per Phase 112 pattern). Status CHECK enforces "
            "('draft','open','in_progress','on_hold','completed',"
            "'cancelled'); priority CHECK enforces BETWEEN 1 AND 5 "
            "(grid-sortable mechanic-settable integer; AI-overridable "
            "in Phase 163 only when confidence exceeds a threshold). "
            "Timestamp columns `opened_at` + `started_at` + "
            "`completed_at` + `closed_at` populate as the order moves "
            "through the lifecycle; `on_hold_reason` + "
            "`cancellation_reason` carry freetext. Four indexes cover "
            "the dominant access patterns: (shop_id, status) for the "
            "daily open-queue query, (vehicle_id) for 'show me this "
            "bike's work history', (customer_id) for per-customer "
            "roll-ups, (intake_visit_id) for 1:N intake→WOs lookups. "
            "Rollback drops indexes then DROP TABLE work_orders."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS work_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                intake_visit_id INTEGER,
                vehicle_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                priority INTEGER NOT NULL DEFAULT 3
                    CHECK (priority BETWEEN 1 AND 5),
                estimated_hours REAL,
                actual_hours REAL,
                estimated_parts_cost_cents INTEGER,
                assigned_mechanic_user_id INTEGER,
                created_by_user_id INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN (
                        'draft','open','in_progress',
                        'on_hold','completed','cancelled'
                    )),
                on_hold_reason TEXT,
                cancellation_reason TEXT,
                opened_at TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                closed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE CASCADE,
                FOREIGN KEY (intake_visit_id)
                    REFERENCES intake_visits(id) ON DELETE SET NULL,
                FOREIGN KEY (vehicle_id)
                    REFERENCES vehicles(id) ON DELETE RESTRICT,
                FOREIGN KEY (customer_id)
                    REFERENCES customers(id) ON DELETE RESTRICT,
                FOREIGN KEY (assigned_mechanic_user_id)
                    REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (created_by_user_id)
                    REFERENCES users(id) ON DELETE SET DEFAULT
            );
            CREATE INDEX IF NOT EXISTS idx_wo_shop_status
                ON work_orders(shop_id, status);
            CREATE INDEX IF NOT EXISTS idx_wo_vehicle
                ON work_orders(vehicle_id);
            CREATE INDEX IF NOT EXISTS idx_wo_customer
                ON work_orders(customer_id);
            CREATE INDEX IF NOT EXISTS idx_wo_intake_visit
                ON work_orders(intake_visit_id);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_wo_intake_visit;
            DROP INDEX IF EXISTS idx_wo_customer;
            DROP INDEX IF EXISTS idx_wo_vehicle;
            DROP INDEX IF EXISTS idx_wo_shop_status;
            DROP TABLE IF EXISTS work_orders;
        """,
    ),
    # Migration 027 — Phase 162: structured issue logging + categorization (Track G)
    Migration(
        version=27,
        name="issues",
        description=(
            "Phase 162: Third Track G phase. Promotes Phase 161 "
            "work_orders.reported_problems freetext into a structured, "
            "categorized, severity-scored `issues` list. Each issue "
            "attaches to a work_orders row via work_order_id FK CASCADE "
            "(issue exists only in WO context), carries title + "
            "description + 12-category taxonomy + 4-tier severity + "
            "guarded `open → resolved | duplicate | wont_fix → "
            "(reopen) → open` lifecycle, and optionally cross-references "
            "a dtc_codes.code (TEXT, soft-validated to survive seed "
            "reloads) and a symptoms.id (hard FK SET NULL). "
            "Self-referencing duplicate_of_issue_id FK with SET NULL on "
            "canonical delete preserves the duplicate row even when "
            "its canonical disappears. Diagnostic_session_id FK SET NULL "
            "links back to Phase 07 sessions opportunistically. "
            "Reported_by_user_id FK SET DEFAULT (Phase 112 system user "
            "fallback). Five indexes cover the dominant queries: "
            "(work_order_id, status) for per-WO filtered lists, "
            "(category) for shop-wide category roll-ups, (severity) for "
            "critical-first sorts, (reported_at) for time-range filters, "
            "(duplicate_of_issue_id) for canonical-resolution lookups. "
            "**12-category taxonomy** (override from Domain-Researcher "
            "brief — see _research/track_g_workflow_brief.md): existing "
            "engine/fuel_system/electrical/cooling/exhaust/transmission/"
            "other PLUS new brakes/suspension/drivetrain/tires_wheels/"
            "accessories/rider_complaint. Existing 7-value SymptomCategory "
            "enum misfiles ~40-50% of real shop tickets to 'other'; "
            "12 values cover ~95%. Severity reuses Severity minus INFO "
            "(low/medium/high/critical). Status CHECK enforces "
            "open|resolved|duplicate|wont_fix. Rollback drops indexes "
            "reverse-order then DROP TABLE issues."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL DEFAULT 'other'
                    CHECK (category IN (
                        'engine','fuel_system','electrical','cooling',
                        'exhaust','transmission','brakes','suspension',
                        'drivetrain','tires_wheels','accessories',
                        'rider_complaint','other'
                    )),
                severity TEXT NOT NULL DEFAULT 'medium'
                    CHECK (severity IN ('low','medium','high','critical')),
                status TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN (
                        'open','resolved','duplicate','wont_fix'
                    )),
                resolution_notes TEXT,
                reported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                reported_by_user_id INTEGER NOT NULL DEFAULT 1,
                diagnostic_session_id INTEGER,
                linked_dtc_code TEXT,
                linked_symptom_id INTEGER,
                duplicate_of_issue_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (reported_by_user_id)
                    REFERENCES users(id) ON DELETE SET DEFAULT,
                FOREIGN KEY (diagnostic_session_id)
                    REFERENCES diagnostic_sessions(id) ON DELETE SET NULL,
                FOREIGN KEY (linked_symptom_id)
                    REFERENCES symptoms(id) ON DELETE SET NULL,
                FOREIGN KEY (duplicate_of_issue_id)
                    REFERENCES issues(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_issues_wo_status
                ON issues(work_order_id, status);
            CREATE INDEX IF NOT EXISTS idx_issues_category
                ON issues(category);
            CREATE INDEX IF NOT EXISTS idx_issues_severity
                ON issues(severity);
            CREATE INDEX IF NOT EXISTS idx_issues_reported_at
                ON issues(reported_at);
            CREATE INDEX IF NOT EXISTS idx_issues_duplicate_of
                ON issues(duplicate_of_issue_id);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_issues_duplicate_of;
            DROP INDEX IF EXISTS idx_issues_reported_at;
            DROP INDEX IF EXISTS idx_issues_severity;
            DROP INDEX IF EXISTS idx_issues_category;
            DROP INDEX IF EXISTS idx_issues_wo_status;
            DROP TABLE IF EXISTS issues;
        """,
    ),
    # Migration 028 — Phase 164: per-shop tunable triage weights
    Migration(
        version=28,
        name="shops_triage_weights",
        description=(
            "Phase 164: Adds nullable JSON column `triage_weights` to "
            "the shops table for per-shop tunable triage scoring "
            "weights. NULL means use ShopTriageWeights pydantic "
            "defaults (priority_weight=100, wait_weight=1.0, "
            "parts_ready_weight=10, urgent_flag_bonus=500, "
            "skip_penalty=50). Stored as TEXT (SQLite has no native "
            "JSON type); application layer parses via json.loads. "
            "Single ALTER TABLE — no new tables, no new indexes. "
            "Rollback uses the SQLite-portable rename-recreate-copy-"
            "drop pattern (matches Phase 145/150 forward-compat work) "
            "rather than depending on DROP COLUMN (only available "
            "since SQLite 3.35)."
        ),
        upgrade_sql="""
            ALTER TABLE shops ADD COLUMN triage_weights TEXT;
        """,
        rollback_sql="""
            -- SQLite-portable column drop via rebuild.
            CREATE TABLE shops_rollback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER NOT NULL DEFAULT 1,
                name TEXT NOT NULL,
                address TEXT,
                city TEXT,
                state TEXT,
                zip TEXT,
                phone TEXT,
                email TEXT,
                tax_id TEXT,
                hours_json TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET DEFAULT,
                UNIQUE (owner_user_id, name)
            );
            INSERT INTO shops_rollback
                (id, owner_user_id, name, address, city, state, zip,
                 phone, email, tax_id, hours_json, is_active,
                 created_at, updated_at)
            SELECT id, owner_user_id, name, address, city, state, zip,
                   phone, email, tax_id, hours_json, is_active,
                   created_at, updated_at
            FROM shops;
            DROP TABLE shops;
            ALTER TABLE shops_rollback RENAME TO shops;
            CREATE INDEX IF NOT EXISTS idx_shops_owner_name
                ON shops(owner_user_id, name);
        """,
    ),
    # Migration 029 — Phase 165: parts needs aggregation (work_order_parts +
    # parts_requisitions + parts_requisition_items)
    Migration(
        version=29,
        name="parts_needs_aggregation",
        description=(
            "Phase 165: Bridges Phase 153 parts catalog (parts + "
            "parts_xref) to Phase 161 work_orders. Three new tables:\n"
            "1) `work_order_parts` — junction (work_order_id FK CASCADE, "
            "part_id FK RESTRICT) with quantity (>0 CHECK), optional "
            "unit_cost_cents_override (nullable; NULL = use catalog "
            "typical_cost_cents), 5-state lifecycle CHECK IN "
            "('open','ordered','received','installed','cancelled'), "
            "ordered_at/received_at/installed_at timestamps, notes, "
            "created_by_user_id FK SET DEFAULT.\n"
            "2) `parts_requisitions` — immutable shop-scoped consolidated "
            "shopping-list snapshots with shop_id FK CASCADE, generated_at, "
            "wo_id_scope (JSON array of wo_ids OR NULL = all open), "
            "total_distinct_parts/total_quantity/total_estimated_cost_cents "
            "frozen at generation time, notes, generated_by_user_id FK SET "
            "DEFAULT.\n"
            "3) `parts_requisition_items` — frozen per-part snapshot rows "
            "(requisition_id FK CASCADE, part_id FK RESTRICT, total_quantity "
            "CHECK >0, estimated_cost_cents, contributing_wo_ids JSON array).\n"
            "FK asymmetry mirrors Phases 160/161: structural ownership "
            "(WO→lines, requisition→items) cascades; curated reference data "
            "(parts) is RESTRICT-protected so removing a part referenced "
            "anywhere is blocked at the FK layer (preserves cost audit "
            "history). 3 indexes cover dominant access patterns: "
            "idx_wop_wo_status (per-WO active-line lookup), idx_wop_part "
            "(parts-side reverse lookup for catalog hygiene + Phase 166 AI "
            "sourcing aggregation), idx_parts_req_shop_date (shop history "
            "browse). Cost recompute (work_orders.estimated_parts_cost_cents) "
            "ALWAYS routes through Phase 161 update_work_order whitelist — "
            "never raw SQL — preserving the lifecycle guard + audit "
            "integrity Phase 161 established."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS work_order_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1
                    CHECK (quantity > 0),
                unit_cost_cents_override INTEGER
                    CHECK (unit_cost_cents_override IS NULL OR
                           unit_cost_cents_override >= 0),
                status TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','ordered','received',
                                      'installed','cancelled')),
                ordered_at TIMESTAMP,
                received_at TIMESTAMP,
                installed_at TIMESTAMP,
                notes TEXT,
                created_by_user_id INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (part_id)
                    REFERENCES parts(id) ON DELETE RESTRICT,
                FOREIGN KEY (created_by_user_id)
                    REFERENCES users(id) ON DELETE SET DEFAULT
            );
            CREATE TABLE IF NOT EXISTS parts_requisitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                generated_by_user_id INTEGER NOT NULL DEFAULT 1,
                wo_id_scope TEXT,
                total_distinct_parts INTEGER NOT NULL DEFAULT 0,
                total_quantity INTEGER NOT NULL DEFAULT 0,
                total_estimated_cost_cents INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE CASCADE,
                FOREIGN KEY (generated_by_user_id)
                    REFERENCES users(id) ON DELETE SET DEFAULT
            );
            CREATE TABLE IF NOT EXISTS parts_requisition_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisition_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                total_quantity INTEGER NOT NULL CHECK (total_quantity > 0),
                estimated_cost_cents INTEGER NOT NULL DEFAULT 0,
                contributing_wo_ids TEXT NOT NULL,
                FOREIGN KEY (requisition_id)
                    REFERENCES parts_requisitions(id) ON DELETE CASCADE,
                FOREIGN KEY (part_id)
                    REFERENCES parts(id) ON DELETE RESTRICT
            );
            CREATE INDEX IF NOT EXISTS idx_wop_wo_status
                ON work_order_parts(work_order_id, status);
            CREATE INDEX IF NOT EXISTS idx_wop_part
                ON work_order_parts(part_id);
            CREATE INDEX IF NOT EXISTS idx_parts_req_shop_date
                ON parts_requisitions(shop_id, generated_at DESC);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_parts_req_shop_date;
            DROP INDEX IF EXISTS idx_wop_part;
            DROP INDEX IF EXISTS idx_wop_wo_status;
            DROP TABLE IF EXISTS parts_requisition_items;
            DROP TABLE IF EXISTS parts_requisitions;
            DROP TABLE IF EXISTS work_order_parts;
        """,
    ),
    # Migration 030 — Phase 166: AI parts sourcing recommendations
    Migration(
        version=30,
        name="sourcing_recommendations",
        description=(
            "Phase 166: First Track G AI phase to use both ShopAIClient "
            "(Phase 162.5) AND read Phase 165 ConsolidatedPartNeed. "
            "Single small audit table `sourcing_recommendations` "
            "persists every AI sourcing call (synchronous + future "
            "batch path) with full recommendation_json blob for "
            "downstream Phase 169 invoicing + Phase 171 analytics. "
            "Append-only — no deduplication; cache_hit=1 rows persist "
            "alongside cache_miss=0 rows so `shop sourcing budget` can "
            "separate paid impressions from free. FK part_id CASCADE "
            "(recommendation specific to part identity); vehicle_id "
            "SET NULL (recommendation outlives vehicle deletion as a "
            "generic part-level artifact). No FK on requisition_id / "
            "requisition_line_id — Phase 165 owns those ids; storing "
            "advisorily as TEXT-ish ints avoids cross-table coupling. "
            "Two indexes: (part_id, generated_at DESC) for catalog-side "
            "lookups (most recent recommendation for a part); "
            "(requisition_id, requisition_line_id) for batch-result "
            "correlation in Phase 166's optimize_requisition path."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS sourcing_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_id INTEGER NOT NULL,
                vehicle_id INTEGER,
                requisition_id INTEGER,
                requisition_line_id INTEGER,
                quantity INTEGER NOT NULL DEFAULT 1
                    CHECK (quantity > 0),
                tier_preference TEXT NOT NULL DEFAULT 'balanced'
                    CHECK (tier_preference IN
                           ('oem','aftermarket','used','balanced')),
                source_tier TEXT NOT NULL
                    CHECK (source_tier IN
                           ('oem','aftermarket','used','superseded')),
                confidence REAL NOT NULL
                    CHECK (confidence BETWEEN 0.0 AND 1.0),
                estimated_cost_cents INTEGER NOT NULL DEFAULT 0,
                recommendation_json TEXT NOT NULL,
                ai_model TEXT NOT NULL,
                tokens_in INTEGER NOT NULL DEFAULT 0,
                tokens_out INTEGER NOT NULL DEFAULT 0,
                cache_hit INTEGER NOT NULL DEFAULT 0,
                cost_cents INTEGER NOT NULL DEFAULT 0,
                batch_id TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE CASCADE,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sr_part
                ON sourcing_recommendations(part_id, generated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_sr_requisition
                ON sourcing_recommendations(requisition_id, requisition_line_id);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_sr_requisition;
            DROP INDEX IF EXISTS idx_sr_part;
            DROP TABLE IF EXISTS sourcing_recommendations;
        """,
    ),
    # Migration 031 — Phase 167: AI labor time estimation history
    Migration(
        version=31,
        name="labor_estimates",
        description=(
            "Phase 167: AI-driven labor time estimates persisted to a "
            "history table. Each row carries the estimate (base + "
            "adjusted hours + skill/mileage multipliers + confidence + "
            "rationale + breakdown JSON + alternative scenarios) + full "
            "AI audit metadata (model + tokens + cost + cache_hit + "
            "prompt_cache_hit). Append-only; reopened work orders "
            "spawn new estimate rows (history preserved). FK wo_id "
            "CASCADE — estimates follow their work order lifecycle. "
            "Three indexes cover dominant queries: "
            "idx_labor_est_wo (per-WO history list), "
            "idx_labor_est_generated (budget time filter), "
            "idx_labor_est_model (model-comparison audit). "
            "Write-back to work_orders.estimated_hours routes through "
            "Phase 161 update_work_order whitelist — NEVER raw SQL, "
            "enforced by anti-regression grep test mirroring Phase "
            "165's cost-recompute audit guarantee."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS labor_estimates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wo_id INTEGER NOT NULL,
                skill_tier TEXT NOT NULL DEFAULT 'journeyman'
                    CHECK (skill_tier IN
                           ('apprentice', 'journeyman', 'master')),
                base_hours REAL NOT NULL,
                adjusted_hours REAL NOT NULL,
                skill_adjustment REAL NOT NULL DEFAULT 0.0,
                mileage_adjustment REAL NOT NULL DEFAULT 0.0,
                confidence REAL NOT NULL
                    CHECK (confidence BETWEEN 0.0 AND 1.0),
                rationale TEXT NOT NULL,
                breakdown_json TEXT NOT NULL DEFAULT '[]',
                alternatives_json TEXT NOT NULL DEFAULT '[]',
                environment_notes TEXT,
                ai_model TEXT NOT NULL,
                tokens_in INTEGER NOT NULL DEFAULT 0,
                tokens_out INTEGER NOT NULL DEFAULT 0,
                cost_cents INTEGER NOT NULL DEFAULT 0,
                prompt_cache_hit INTEGER NOT NULL DEFAULT 0,
                user_prompt_snapshot TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (wo_id)
                    REFERENCES work_orders(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_labor_est_wo
                ON labor_estimates(wo_id);
            CREATE INDEX IF NOT EXISTS idx_labor_est_generated
                ON labor_estimates(generated_at);
            CREATE INDEX IF NOT EXISTS idx_labor_est_model
                ON labor_estimates(ai_model);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_labor_est_model;
            DROP INDEX IF EXISTS idx_labor_est_generated;
            DROP INDEX IF EXISTS idx_labor_est_wo;
            DROP TABLE IF EXISTS labor_estimates;
        """,
    ),
    # Migration 032 — Phase 168: bay/lift scheduling
    Migration(
        version=32,
        name="bays_and_schedule_slots",
        description=(
            "Phase 168: Physical shop bay/lift scheduling. Two tables: "
            "shop_bays (bay inventory — name, type CHECK IN "
            "('lift','flat','specialty','tire','dyno','wash'), "
            "max_bike_weight_lbs, is_active flag, UNIQUE(shop_id, name)) "
            "and bay_schedule_slots (per-slot reservations — bay_id FK "
            "CASCADE, work_order_id FK SET NULL so utilization history "
            "survives WO deletion, scheduled_start + scheduled_end CHECK "
            "end > start, actual_start + actual_end, status CHECK IN "
            "('planned','active','completed','cancelled','overrun'), "
            "created_by_user_id FK SET DEFAULT). 4 indexes: "
            "idx_bays_shop_active (shop-filtered listings), "
            "idx_slots_bay_start (per-bay chronological queries), "
            "idx_slots_wo (WO->slots reverse lookup), "
            "idx_slots_status_start (active-slot sweep). Overrun "
            "detection: actual_end > scheduled_end + 25% buffer "
            "(OVERRUN_BUFFER_FRACTION module constant)."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS shop_bays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                bay_type TEXT NOT NULL DEFAULT 'lift'
                    CHECK (bay_type IN
                           ('lift','flat','specialty','tire','dyno','wash')),
                is_active INTEGER NOT NULL DEFAULT 1,
                max_bike_weight_lbs INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
                UNIQUE (shop_id, name)
            );
            CREATE TABLE IF NOT EXISTS bay_schedule_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bay_id INTEGER NOT NULL,
                work_order_id INTEGER,
                scheduled_start TIMESTAMP NOT NULL,
                scheduled_end TIMESTAMP NOT NULL,
                actual_start TIMESTAMP,
                actual_end TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'planned'
                    CHECK (status IN
                           ('planned','active','completed',
                            'cancelled','overrun')),
                created_by_user_id INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bay_id) REFERENCES shop_bays(id) ON DELETE CASCADE,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE SET NULL,
                FOREIGN KEY (created_by_user_id)
                    REFERENCES users(id) ON DELETE SET DEFAULT,
                CHECK (scheduled_end > scheduled_start)
            );
            CREATE INDEX IF NOT EXISTS idx_bays_shop_active
                ON shop_bays(shop_id, is_active);
            CREATE INDEX IF NOT EXISTS idx_slots_bay_start
                ON bay_schedule_slots(bay_id, scheduled_start);
            CREATE INDEX IF NOT EXISTS idx_slots_wo
                ON bay_schedule_slots(work_order_id);
            CREATE INDEX IF NOT EXISTS idx_slots_status_start
                ON bay_schedule_slots(status, scheduled_start);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_slots_status_start;
            DROP INDEX IF EXISTS idx_slots_wo;
            DROP INDEX IF EXISTS idx_slots_bay_start;
            DROP INDEX IF EXISTS idx_bays_shop_active;
            DROP TABLE IF EXISTS bay_schedule_slots;
            DROP TABLE IF EXISTS shop_bays;
        """,
    ),
    # Migration 033 — Phase 169: invoices.work_order_id soft FK
    Migration(
        version=33,
        name="invoices_work_order_id",
        description=(
            "Phase 169: Add nullable `work_order_id` column to the "
            "Phase 118 `invoices` table so invoices can reference the "
            "Phase 161 work_order they were generated from. SQLite "
            "ALTER TABLE can't add FK constraints, so this is a soft "
            "reference — repo-layer validates on write; mechanics "
            "don't delete work_orders (Phase 161 cancels instead). "
            "Plus one index for shop-level revenue rollup queries."
        ),
        upgrade_sql="""
            ALTER TABLE invoices ADD COLUMN work_order_id INTEGER;
            CREATE INDEX IF NOT EXISTS idx_invoices_work_order
                ON invoices(work_order_id);
        """,
        rollback_sql="""
            -- SQLite-portable column drop: recreate table without column.
            DROP INDEX IF EXISTS idx_invoices_work_order;
            CREATE TABLE invoices_rollback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                repair_plan_id INTEGER,
                invoice_number TEXT UNIQUE,
                status TEXT DEFAULT 'draft',
                subtotal INTEGER NOT NULL DEFAULT 0,
                tax_amount INTEGER NOT NULL DEFAULT 0,
                total INTEGER NOT NULL DEFAULT 0,
                currency TEXT DEFAULT 'USD',
                issued_at TIMESTAMP,
                due_at TIMESTAMP,
                paid_at TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO invoices_rollback
                (id, customer_id, repair_plan_id, invoice_number, status,
                 subtotal, tax_amount, total, currency, issued_at, due_at,
                 paid_at, notes, created_at, updated_at)
            SELECT id, customer_id, repair_plan_id, invoice_number, status,
                   subtotal, tax_amount, total, currency, issued_at, due_at,
                   paid_at, notes, created_at, updated_at
            FROM invoices;
            DROP TABLE invoices;
            ALTER TABLE invoices_rollback RENAME TO invoices;
        """,
    ),
    # Migration 034 — Phase 170: customer_notifications audit-log table
    Migration(
        version=34,
        name="customer_notifications",
        description=(
            "Phase 170: Create `customer_notifications` — audit-log + "
            "queue for shop-workflow customer messages (WO status, "
            "invoice issued/paid, parts arrived, estimate-ready, "
            "approval-requested). This phase owns templating + "
            "persistence; actual email/SMS transport is deferred to "
            "Track J infrastructure. Lifecycle: pending → "
            "sent|failed|cancelled. Resend creates new pending row "
            "(preserves failure audit). FKs: customer/shop CASCADE, "
            "work_order_id + invoice_id SET NULL so history survives."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS customer_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                shop_id INTEGER NOT NULL,
                work_order_id INTEGER,
                invoice_id INTEGER,
                event TEXT NOT NULL CHECK(event IN (
                    'wo_opened', 'wo_in_progress', 'wo_on_hold',
                    'wo_completed', 'wo_cancelled', 'invoice_issued',
                    'invoice_paid', 'parts_arrived', 'estimate_ready',
                    'approval_requested'
                )),
                channel TEXT NOT NULL CHECK(channel IN (
                    'email', 'sms', 'in_app'
                )),
                recipient TEXT NOT NULL,
                subject TEXT,
                body TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN (
                    'pending', 'sent', 'failed', 'cancelled'
                )),
                failure_reason TEXT,
                triggered_by_user_id INTEGER,
                triggered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (customer_id)
                    REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE CASCADE,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE SET NULL,
                FOREIGN KEY (invoice_id)
                    REFERENCES invoices(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_notif_customer
                ON customer_notifications(customer_id, triggered_at DESC);
            CREATE INDEX IF NOT EXISTS idx_notif_shop_status
                ON customer_notifications(shop_id, status);
            CREATE INDEX IF NOT EXISTS idx_notif_wo
                ON customer_notifications(work_order_id);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_notif_wo;
            DROP INDEX IF EXISTS idx_notif_shop_status;
            DROP INDEX IF EXISTS idx_notif_customer;
            DROP TABLE IF EXISTS customer_notifications;
        """,
    ),
    # Migration 035 — Phase 172: shop-scoped RBAC + WO assignment history
    Migration(
        version=35,
        name="shop_members_and_assignments",
        description=(
            "Phase 172: Create `shop_members` (per-shop role for users; "
            "stacks on Phase 112 global RBAC so a user can own one "
            "shop AND be a tech at another) + `work_order_assignments` "
            "(audit log of WO mechanic reassignments preserving "
            "attribution over the WO lifetime). FKs: user+shop "
            "CASCADE (member deletion follows shop/user deletion); "
            "wo CASCADE for assignments; mechanic SET NULL (preserves "
            "history when a user is deleted)."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS shop_members (
                user_id INTEGER NOT NULL,
                shop_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN (
                    'owner', 'tech', 'service_writer', 'apprentice'
                )),
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1,
                updated_at TIMESTAMP,
                PRIMARY KEY (user_id, shop_id),
                FOREIGN KEY (user_id)
                    REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_shop_members_shop_role
                ON shop_members(shop_id, role, is_active);
            CREATE INDEX IF NOT EXISTS idx_shop_members_user
                ON shop_members(user_id);

            CREATE TABLE IF NOT EXISTS work_order_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER NOT NULL,
                mechanic_user_id INTEGER,
                assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                unassigned_at TIMESTAMP,
                assigned_by_user_id INTEGER,
                reason TEXT,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (mechanic_user_id)
                    REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (assigned_by_user_id)
                    REFERENCES users(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_wo_assignments_wo
                ON work_order_assignments(work_order_id, assigned_at DESC);
            CREATE INDEX IF NOT EXISTS idx_wo_assignments_mechanic
                ON work_order_assignments(mechanic_user_id, assigned_at DESC);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_wo_assignments_mechanic;
            DROP INDEX IF EXISTS idx_wo_assignments_wo;
            DROP TABLE IF EXISTS work_order_assignments;
            DROP INDEX IF EXISTS idx_shop_members_user;
            DROP INDEX IF EXISTS idx_shop_members_shop_role;
            DROP TABLE IF EXISTS shop_members;
        """,
    ),
    # Migration 036 — Phase 173: workflow_rules + workflow_rule_runs
    Migration(
        version=36,
        name="workflow_rules",
        description=(
            "Phase 173: Create `workflow_rules` (JSON-defined "
            "if-this-then-that rules composing Track G primitives) + "
            "`workflow_rule_runs` (audit log of every rule firing, "
            "matched or not — feeds Phase 171 analytics). event_trigger "
            "CHECK restricts to known lifecycle events + 'manual'. "
            "UNIQUE(shop_id, name) prevents duplicate rule names per "
            "shop. FK shop CASCADE; rule CASCADE; wo SET NULL on runs "
            "so audit history survives WO deletion."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS workflow_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                event_trigger TEXT NOT NULL CHECK(event_trigger IN (
                    'wo_opened', 'wo_in_progress', 'wo_completed',
                    'wo_cancelled', 'parts_arrived', 'invoice_issued',
                    'invoice_paid', 'issue_added', 'manual'
                )),
                conditions_json TEXT NOT NULL,
                actions_json TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 100,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_by_user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(shop_id, name),
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_user_id)
                    REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS workflow_rule_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id INTEGER NOT NULL,
                work_order_id INTEGER,
                triggered_event TEXT,
                matched INTEGER NOT NULL,
                actions_log TEXT,
                error TEXT,
                actor_user_id INTEGER,
                fired_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rule_id)
                    REFERENCES workflow_rules(id) ON DELETE CASCADE,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE SET NULL,
                FOREIGN KEY (actor_user_id)
                    REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_rules_shop_active
                ON workflow_rules(shop_id, is_active, event_trigger);
            CREATE INDEX IF NOT EXISTS idx_rule_runs_rule
                ON workflow_rule_runs(rule_id, fired_at DESC);
            CREATE INDEX IF NOT EXISTS idx_rule_runs_wo
                ON workflow_rule_runs(work_order_id, fired_at DESC);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_rule_runs_wo;
            DROP INDEX IF EXISTS idx_rule_runs_rule;
            DROP TABLE IF EXISTS workflow_rule_runs;
            DROP INDEX IF EXISTS idx_rules_shop_active;
            DROP TABLE IF EXISTS workflow_rules;
        """,
    ),
    # Migration 037 — Phase 176: auth + billing substrate
    Migration(
        version=37,
        name="auth_and_billing",
        description=(
            "Phase 176: Create `api_keys` (Stripe-style mdk_live_* "
            "keys, sha256-hashed — plaintext never stored), extend "
            "Phase 118 `subscriptions` with Stripe billing-cycle "
            "columns (period_start/end, cancel_at_period_end, "
            "trial_end, canceled_at, stripe_price_id), and create "
            "`stripe_webhook_events` (idempotent event log keyed by "
            "Stripe event_id). Reuses Phase 118 `subscriptions` "
            "substrate unchanged — matches the Phase 169 pattern "
            "(substrate reuse across phase gaps) applied to the "
            "auth + billing domain. FK user_id CASCADE — when a "
            "user is deleted, their keys + subscriptions disappear "
            "(Stripe customer record lives on at Stripe regardless)."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key_prefix TEXT NOT NULL,
                key_hash TEXT NOT NULL UNIQUE,
                name TEXT,
                last_used_at TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                revoked_at TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_api_keys_user
                ON api_keys(user_id, is_active);
            CREATE INDEX IF NOT EXISTS idx_api_keys_prefix
                ON api_keys(key_prefix);

            -- Extend Phase 118 subscriptions with Stripe billing-cycle
            -- columns (reuse-substrate pattern, not duplication).
            ALTER TABLE subscriptions ADD COLUMN stripe_price_id TEXT;
            ALTER TABLE subscriptions ADD COLUMN current_period_start TIMESTAMP;
            ALTER TABLE subscriptions ADD COLUMN current_period_end TIMESTAMP;
            ALTER TABLE subscriptions ADD COLUMN cancel_at_period_end INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE subscriptions ADD COLUMN canceled_at TIMESTAMP;
            ALTER TABLE subscriptions ADD COLUMN trial_end TIMESTAMP;

            CREATE INDEX IF NOT EXISTS idx_subs_user_status
                ON subscriptions(user_id, status);
            CREATE INDEX IF NOT EXISTS idx_subs_stripe_cust
                ON subscriptions(stripe_customer_id);

            CREATE TABLE IF NOT EXISTS stripe_webhook_events (
                event_id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_webhook_events_type
                ON stripe_webhook_events(type);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_webhook_events_type;
            DROP TABLE IF EXISTS stripe_webhook_events;
            DROP INDEX IF EXISTS idx_subs_stripe_cust;
            DROP INDEX IF EXISTS idx_subs_user_status;

            -- Rollback subscriptions new columns via rename-recreate
            -- (SQLite can't DROP COLUMN reliably on older versions)
            CREATE TABLE subscriptions_rollback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tier TEXT NOT NULL DEFAULT 'individual',
                status TEXT NOT NULL DEFAULT 'trialing',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ends_at TIMESTAMP,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            INSERT INTO subscriptions_rollback
                (id, user_id, tier, status, started_at, ends_at,
                 stripe_customer_id, stripe_subscription_id,
                 created_at, updated_at)
            SELECT id, user_id, tier, status, started_at, ends_at,
                   stripe_customer_id, stripe_subscription_id,
                   created_at, updated_at
            FROM subscriptions;
            DROP TABLE subscriptions;
            ALTER TABLE subscriptions_rollback RENAME TO subscriptions;
            CREATE INDEX IF NOT EXISTS idx_subscriptions_user
                ON subscriptions(user_id);
            CREATE INDEX IF NOT EXISTS idx_subscriptions_status
                ON subscriptions(status);

            DROP INDEX IF EXISTS idx_api_keys_prefix;
            DROP INDEX IF EXISTS idx_api_keys_user;
            DROP TABLE IF EXISTS api_keys;
        """,
    ),
    # Migration 038 — Phase 177: vehicles.owner_user_id retrofit
    Migration(
        version=38,
        name="vehicles_owner_user_id",
        description=(
            "Phase 177: Retrofit owner_user_id column on Phase 04 "
            "vehicles table. Pre-retrofit rows default to system "
            "user (id=1) — invisible via API until an operator "
            "explicitly re-owns them. Matches Phase 112's pattern "
            "of retrofitting user_id columns onto existing tables."
        ),
        upgrade_sql="""
            ALTER TABLE vehicles
                ADD COLUMN owner_user_id INTEGER NOT NULL DEFAULT 1;
            CREATE INDEX IF NOT EXISTS idx_vehicles_owner
                ON vehicles(owner_user_id);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_vehicles_owner;
            -- SQLite pre-3.35 can't DROP COLUMN; use rename-recreate
            -- to restore the pre-Phase-177 shape.
            CREATE TABLE vehicles_rollback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                year INTEGER NOT NULL,
                engine_cc INTEGER,
                vin TEXT,
                protocol TEXT NOT NULL DEFAULT 'none',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                powertrain TEXT DEFAULT 'ice',
                engine_type TEXT DEFAULT 'four_stroke',
                battery_chemistry TEXT,
                motor_kw REAL,
                bms_present INTEGER DEFAULT 0,
                customer_id INTEGER DEFAULT 1,
                mileage INTEGER
            );
            INSERT INTO vehicles_rollback
                (id, make, model, year, engine_cc, vin, protocol,
                 notes, created_at, updated_at,
                 powertrain, engine_type, battery_chemistry,
                 motor_kw, bms_present, customer_id, mileage)
            SELECT
                id, make, model, year, engine_cc, vin, protocol,
                notes, created_at, updated_at,
                powertrain, engine_type, battery_chemistry,
                motor_kw, bms_present, customer_id, mileage
            FROM vehicles;
            DROP TABLE vehicles;
            ALTER TABLE vehicles_rollback RENAME TO vehicles;
            CREATE INDEX IF NOT EXISTS idx_vehicles_make_model
                ON vehicles(make, model);
            CREATE INDEX IF NOT EXISTS idx_vehicles_year
                ON vehicles(year);
        """,
    ),
    # Migration 039 — Phase 191B: video diagnostic capture + AI analysis
    Migration(
        version=39,
        name="videos_table",
        description=(
            "Phase 191B: Add videos table for diagnostic video capture + "
            "Claude Vision AI analysis pipeline. session_id FK with "
            "ON DELETE CASCADE; soft-delete via deleted_at; "
            "analysis_state machine (pending|analyzing|analyzed|"
            "analysis_failed|unsupported); SHA-256 dedup; analysis_findings "
            "stored as JSON serialization of VisualAnalysisResult. "
            "Note: FK targets diagnostic_sessions(id) — the canonical "
            "session table in this codebase (the v1.0.1 plan's `sessions` "
            "shorthand maps to diagnostic_sessions)."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                format TEXT NOT NULL DEFAULT 'mp4',
                codec TEXT NOT NULL DEFAULT 'h264',
                interrupted INTEGER NOT NULL DEFAULT 0,
                file_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                upload_state TEXT NOT NULL DEFAULT 'uploaded',
                analysis_state TEXT NOT NULL DEFAULT 'pending',
                analysis_findings TEXT,
                analyzed_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                deleted_at TEXT,
                FOREIGN KEY (session_id) REFERENCES diagnostic_sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_videos_session
                ON videos(session_id) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_videos_analysis_state
                ON videos(analysis_state)
                WHERE analysis_state IN ('pending', 'analyzing');
            CREATE INDEX IF NOT EXISTS idx_videos_sha256
                ON videos(sha256);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_videos_sha256;
            DROP INDEX IF EXISTS idx_videos_analysis_state;
            DROP INDEX IF EXISTS idx_videos_session;
            DROP TABLE IF EXISTS videos;
        """,
    ),
    # Migration 040 — Phase 192 (Commit 1 scope-add): videos.analyzing_started_at
    Migration(
        version=40,
        name="videos_analyzing_started_at",
        description=(
            "Phase 192 Section D (stuck-in-analyzing detection — 5-min "
            "threshold per plan v1.0.1): add nullable "
            "`analyzing_started_at TEXT` column to the `videos` table "
            "so the mobile diagnostic-report viewer can compute stuck-"
            "duration for each video whose `analysis_state == 'analyzing'`. "
            "\n\n"
            "Nullability contract (Phase 192 Contract A): the column is "
            "added NULL with NO DEFAULT. Existing rows from Phase 191B "
            "(including the 191B smoke-test row + any production rows) "
            "stay with `analyzing_started_at IS NULL`. NO BACKFILL — "
            "we cannot reconstruct a true `analyzing` start time for "
            "rows that transitioned before this migration existed, and "
            "fabricating one (e.g., copying `created_at`) would "
            "mis-classify pre-migration rows in the stuck-detection "
            "logic. Mobile-side stuck-detection (Commit 3 scope) MUST "
            "treat `analysis_state == 'analyzing' AND "
            "analyzing_started_at IS NULL` as PRE-MIGRATION INDETERMINATE "
            "and surface those rows as STUCK IMMEDIATELY rather than "
            "waiting 5 minutes from now (the row may have been stuck "
            "for hours or days before the migration landed)."
            "\n\n"
            "Atomicity contract (Phase 192 Contract B): the "
            "`pending → analyzing` transition is performed by a SINGLE "
            "atomic UPDATE in `motodiag.core.video_repo."
            "update_analysis_state`. Both `analysis_state = 'analyzing'` "
            "AND `analyzing_started_at = <iso-now>` are set in the SAME "
            "SQL statement to eliminate the race window where a row "
            "could sit in `analyzing` with `analyzing_started_at IS "
            "NULL` and trip the pre-migration-indeterminate path "
            "inappropriately. Two-statement implementations are "
            "FORBIDDEN by Contract B; tests in "
            "`tests/test_phase192_analyzing_started_at_atomicity.py` "
            "verify single-UPDATE behavior."
        ),
        upgrade_sql="""
            ALTER TABLE videos ADD COLUMN analyzing_started_at TEXT;
        """,
        rollback_sql="""
            -- SQLite pre-3.35 can't DROP COLUMN; use rename-recreate
            -- to restore the post-migration-039 / pre-migration-040
            -- shape exactly. Mirrors the recreate pattern used in
            -- migrations 003 / 038.
            CREATE TABLE videos_rollback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                format TEXT NOT NULL DEFAULT 'mp4',
                codec TEXT NOT NULL DEFAULT 'h264',
                interrupted INTEGER NOT NULL DEFAULT 0,
                file_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                upload_state TEXT NOT NULL DEFAULT 'uploaded',
                analysis_state TEXT NOT NULL DEFAULT 'pending',
                analysis_findings TEXT,
                analyzed_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                deleted_at TEXT,
                FOREIGN KEY (session_id) REFERENCES diagnostic_sessions(id) ON DELETE CASCADE
            );
            INSERT INTO videos_rollback
                (id, session_id, started_at, duration_ms,
                 width, height, file_size_bytes, format, codec,
                 interrupted, file_path, sha256,
                 upload_state, analysis_state, analysis_findings,
                 analyzed_at, created_at, deleted_at)
            SELECT
                id, session_id, started_at, duration_ms,
                width, height, file_size_bytes, format, codec,
                interrupted, file_path, sha256,
                upload_state, analysis_state, analysis_findings,
                analyzed_at, created_at, deleted_at
            FROM videos;
            DROP TABLE videos;
            ALTER TABLE videos_rollback RENAME TO videos;
            CREATE INDEX IF NOT EXISTS idx_videos_session
                ON videos(session_id) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_videos_analysis_state
                ON videos(analysis_state)
                WHERE analysis_state IN ('pending', 'analyzing');
            CREATE INDEX IF NOT EXISTS idx_videos_sha256
                ON videos(sha256);
        """,
    ),
    # Migration 041 — Phase 194 (Commit 0): work_order_photos substrate
    Migration(
        version=41,
        name="work_order_photos",
        description=(
            "Phase 194 (Commit 0): Add `work_order_photos` table for the "
            "camera/photo integration substrate. Substrate-half of the "
            "194/194B substrate-then-feature pair (194 capture/attach/"
            "display + 194B AI photo analysis). Mechanics tap 'Take "
            "photo' inside a work order, capture, classify, upload — "
            "the photo appears in the WO detail screen as a new section "
            "variant. Paired before/after photos render side-by-side; "
            "general photos in a grid; un-classified photos surface a "
            "'classify later' affordance.\n\n"
            "Schema choices (per Phase 194 v1.0 Section A flexibility): "
            "`work_order_id NOT NULL` + `issue_id` nullable. Mechanic "
            "can photograph WO-overall (intake baseline / insurance "
            "documentation) OR photograph specific issue. UX classifies; "
            "data model accommodates.\n\n"
            "Pairing model (per Section D): `role` enum {before, after, "
            "general, undecided} + `pair_id` self-FK. `undecided` is the "
            "fast-path 'decide later' affordance from the capture-time "
            "4-button picker. `pair_id` ON DELETE SET NULL: deleting one "
            "side of a pair leaves the other standalone (less destructive "
            "than CASCADE).\n\n"
            "Substrate-anticipates-feature (per Section C): "
            "`analysis_state TEXT NULL` + `analysis_findings TEXT (JSON) "
            "NULL` columns ship from this migration even though Phase "
            "194 never writes them. Phase 194B's AI analysis pipeline "
            "fills them. Mirrors Phase 191's videos table preparing for "
            "191B.\n\n"
            "Source provenance forward-look (per Section's source-"
            "agnostic UI commitment): `source TEXT NULL` for future "
            "phases (196 OBD-triggered, 195 voice-narrated) to populate "
            "without schema migration. Phase 194 leaves NULL.\n\n"
            "Image-pipeline normalization (Section K): backend decodes "
            "HEIC → JPEG, normalizes EXIF orientation upright, resizes "
            "to 2048px long-edge, JPEG quality 85. `width` + `height` "
            "stored as the post-normalization pixel dimensions (not "
            "raw camera output) so consumers don't need to re-read "
            "the file to render layout. `file_size_bytes` is the "
            "post-normalization JPEG byte count.\n\n"
            "FK posture: ON DELETE CASCADE for work_order_id (deleting "
            "a WO removes its photos), ON DELETE SET NULL for issue_id "
            "(deleting an issue keeps the photo at WO scope), ON DELETE "
            "SET DEFAULT for uploaded_by_user_id (preserves the photo "
            "if the uploader is removed; default is sentinel)."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS work_order_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER NOT NULL,
                issue_id INTEGER,
                role TEXT NOT NULL DEFAULT 'general'
                    CHECK (role IN ('before', 'after', 'general', 'undecided')),
                pair_id INTEGER,
                file_path TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                uploaded_by_user_id INTEGER NOT NULL,
                analysis_state TEXT,
                analysis_findings TEXT,
                source TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                deleted_at TEXT,
                FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE SET NULL,
                FOREIGN KEY (pair_id) REFERENCES work_order_photos(id) ON DELETE SET NULL,
                FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
            );
            CREATE INDEX IF NOT EXISTS idx_wo_photos_wo
                ON work_order_photos(work_order_id) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_wo_photos_issue
                ON work_order_photos(issue_id) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_wo_photos_pair
                ON work_order_photos(pair_id);
            CREATE INDEX IF NOT EXISTS idx_wo_photos_sha256
                ON work_order_photos(sha256);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_wo_photos_sha256;
            DROP INDEX IF EXISTS idx_wo_photos_pair;
            DROP INDEX IF EXISTS idx_wo_photos_issue;
            DROP INDEX IF EXISTS idx_wo_photos_wo;
            DROP TABLE IF EXISTS work_order_photos;
        """,
    ),
    # Migration 042 — Phase 195 (Commit 0): voice_transcripts + extracted_symptoms substrate
    Migration(
        version=42,
        name="voice_transcripts_and_extracted_symptoms",
        description=(
            "Phase 195 (Commit 0): Add `voice_transcripts` + "
            "`extracted_symptoms` tables for the voice-input substrate. "
            "Substrate-half of the 195/195B substrate-then-feature pair "
            "(195 capture + on-device preview + audio upload + keyword "
            "extraction; 195B cloud Whisper + Claude-rich extraction + "
            "cost monitoring + VAD).\n\n"
            "Schema choices (per Phase 195 v1.0 Section 1 hybrid + "
            "Section 5 60-day audio retention + Section 6 forward-invest "
            "narrow + Section 7 ISO 639-1 with region):\n"
            "- voice_transcripts.work_order_id NOT NULL + issue_id "
            "  nullable (Phase 194 A-flexibility precedent).\n"
            "- audio_path stored canonically; audio bytes pruned by the "
            "  60-day sweep (audio_sweep.prune_old_audio); audio_deleted_at "
            "  TIMESTAMP set when sweep runs (transcripts permanent, audio "
            "  bytes ephemeral).\n"
            "- preview_text + preview_engine populated by mobile from "
            "  on-device STT (iOS Speech / Android SpeechRecognizer).\n"
            "- extraction_state CHECK enum {pending, extracting, "
            "  extracted, extraction_failed}.\n"
            "- language ISO 639-1 with optional region (en-US, es-MX, "
            "  fr-CA) per Section 7 — Whisper + iOS Speech both use "
            "  locale-with-region; storing without region loses "
            "  information.\n"
            "- whisper_transcript / whisper_segments (JSON) / "
            "  whisper_cost_usd_cents / whisper_model — substrate-"
            "  anticipates-feature for Phase 195B (cloud Whisper); "
            "  Phase 195 leaves NULL.\n"
            "- source TEXT NULL forward-invest narrow (Phase 196 OBD "
            "  populates 'obd'; F38 future unify).\n\n"
            "extracted_symptoms is NEW relational shape (Phase 178's "
            "diagnostic_sessions.symptoms is JSON-list and stays JSON-list "
            "in Phase 195; F38 NEW filed at plan-write for future "
            "unification): one row per extracted symptom phrase with "
            "linked_symptom_id FK to symptoms catalog (Phase 178 KB), "
            "category from engine/symptoms.SYMPTOM_CATEGORIES, "
            "extraction_method enum {keyword, claude, manual_edit}, "
            "confidence 0.0-1.0 (keyword=1.0; future Claude=model-"
            "reported), segment_start_ms/end_ms NULL until Phase 195B "
            "Whisper segments populate. confirmed_by_user_id + "
            "confirmed_at track mechanic confirmation via PATCH UI.\n\n"
            "FK posture: voice_transcripts.work_order_id CASCADE "
            "(deleting WO removes transcripts); voice_transcripts.issue_id "
            "SET NULL (deleting issue keeps transcript at WO scope); "
            "voice_transcripts.uploaded_by_user_id SET DEFAULT (preserve "
            "if uploader removed); extracted_symptoms.transcript_id "
            "CASCADE (deleting transcript removes its extracted symptoms); "
            "extracted_symptoms.linked_symptom_id SET NULL (deleting KB "
            "symptom unlinks but keeps the row); "
            "extracted_symptoms.confirmed_by_user_id SET NULL."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS voice_transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER NOT NULL,
                issue_id INTEGER,
                audio_path TEXT NOT NULL,
                audio_size_bytes INTEGER NOT NULL,
                audio_format TEXT NOT NULL DEFAULT 'm4a',
                audio_sha256 TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                sample_rate_hz INTEGER NOT NULL DEFAULT 16000,
                language TEXT NOT NULL DEFAULT 'en-US',
                captured_at TEXT NOT NULL,
                uploaded_by_user_id INTEGER NOT NULL,
                preview_text TEXT,
                preview_engine TEXT,
                extraction_state TEXT NOT NULL DEFAULT 'pending'
                    CHECK (extraction_state IN
                        ('pending', 'extracting', 'extracted',
                         'extraction_failed')),
                extracted_at TEXT,
                whisper_transcript TEXT,
                whisper_segments TEXT,
                whisper_cost_usd_cents INTEGER,
                whisper_model TEXT,
                source TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                audio_deleted_at TEXT,
                deleted_at TEXT,
                FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE SET NULL,
                FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
            );
            CREATE INDEX IF NOT EXISTS idx_voice_transcripts_wo
                ON voice_transcripts(work_order_id) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_voice_transcripts_issue
                ON voice_transcripts(issue_id) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_voice_transcripts_audio_age
                ON voice_transcripts(created_at)
                WHERE audio_deleted_at IS NULL AND deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_voice_transcripts_extraction_state
                ON voice_transcripts(extraction_state)
                WHERE extraction_state IN ('pending', 'extracting');

            CREATE TABLE IF NOT EXISTS extracted_symptoms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transcript_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                category TEXT,
                linked_symptom_id INTEGER,
                confidence REAL NOT NULL DEFAULT 1.0,
                extraction_method TEXT NOT NULL DEFAULT 'keyword'
                    CHECK (extraction_method IN
                        ('keyword', 'claude', 'manual_edit')),
                segment_start_ms INTEGER,
                segment_end_ms INTEGER,
                confirmed_by_user_id INTEGER,
                confirmed_at TEXT,
                source TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                deleted_at TEXT,
                FOREIGN KEY (transcript_id) REFERENCES voice_transcripts(id) ON DELETE CASCADE,
                FOREIGN KEY (linked_symptom_id) REFERENCES symptoms(id) ON DELETE SET NULL,
                FOREIGN KEY (confirmed_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_extracted_symptoms_transcript
                ON extracted_symptoms(transcript_id) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_extracted_symptoms_linked
                ON extracted_symptoms(linked_symptom_id) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_extracted_symptoms_method
                ON extracted_symptoms(extraction_method);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_extracted_symptoms_method;
            DROP INDEX IF EXISTS idx_extracted_symptoms_linked;
            DROP INDEX IF EXISTS idx_extracted_symptoms_transcript;
            DROP TABLE IF EXISTS extracted_symptoms;
            DROP INDEX IF EXISTS idx_voice_transcripts_extraction_state;
            DROP INDEX IF EXISTS idx_voice_transcripts_audio_age;
            DROP INDEX IF EXISTS idx_voice_transcripts_issue;
            DROP INDEX IF EXISTS idx_voice_transcripts_wo;
            DROP TABLE IF EXISTS voice_transcripts;
        """,
    ),
    # Migration 043 — Phase 195B (Commit 0): cost_events ledger
    Migration(
        version=43,
        name="cost_events",
        description=(
            "Phase 195B (Commit 0): Add `cost_events` table — a granular "
            "per-call ledger for cloud-API cost monitoring (Risk 8 from "
            "the Phase 195 pre-plan). One row per OpenAI Whisper "
            "transcription call and per Claude-rich symptom-extraction "
            "call. The `voice_transcripts.whisper_cost_usd_cents` column "
            "(migration 042) holds the per-transcript denormalized "
            "Whisper total; `cost_events` is the itemized ledger that "
            "backs the `motodiag costs report` rollup CLI + the soft "
            "per-shop monthly cap.\n\n"
            "`kind` CHECK enum {whisper, claude_extraction} — Phase 195B "
            "ships both; future cloud-API kinds extend the enum (+ the "
            "matching Pydantic Literal, per F37 Track 1 discipline).\n\n"
            "`transcript_id` FK ON DELETE SET NULL — the ledger row "
            "outlives the transcript it billed for (cost history must "
            "survive transcript deletion for accurate monthly rollups). "
            "`shop_id` denormalized onto the row (not joined through "
            "the transcript) for the same reason + fast per-shop "
            "aggregation. `units_label` / `units_value` are a "
            "kind-polymorphic measure: 'duration_ms' for Whisper "
            "(billed per audio-minute), 'tokens' for Claude (billed "
            "per token). `cost_usd_cents` is the computed charge."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS cost_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL
                    CHECK (kind IN ('whisper', 'claude_extraction')),
                model TEXT NOT NULL,
                transcript_id INTEGER,
                shop_id INTEGER,
                units_label TEXT,
                units_value INTEGER,
                cost_usd_cents INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (transcript_id)
                    REFERENCES voice_transcripts(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_cost_events_created
                ON cost_events(created_at);
            CREATE INDEX IF NOT EXISTS idx_cost_events_shop
                ON cost_events(shop_id);
            CREATE INDEX IF NOT EXISTS idx_cost_events_kind
                ON cost_events(kind);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_cost_events_kind;
            DROP INDEX IF EXISTS idx_cost_events_shop;
            DROP INDEX IF EXISTS idx_cost_events_created;
            DROP TABLE IF EXISTS cost_events;
        """,
    ),
    # Migration 044 — Phase 199: push device-token registry
    Migration(
        version=44,
        name="device_tokens",
        description=(
            "Phase 199: Add `device_tokens` — mechanic-facing push "
            "notification token registry. Invariant: one row per TOKEN "
            "(UNIQUE); re-registration by a different user REBINDS the "
            "row (shared-device reality) rather than duplicating. "
            "Pruned on APNs 410/Unregistered."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS device_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id)
                    ON DELETE CASCADE,
                token TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL DEFAULT 'ios',
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_device_tokens_user
                ON device_tokens(user_id);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_device_tokens_user;
            DROP TABLE IF EXISTS device_tokens;
        """,
    ),
    # Migration 045 — Phase 200: customer-facing report share links
    Migration(
        version=45,
        name="report_shares",
        description=(
            "Phase 200: Add `report_shares` — capability links that let a "
            "bike owner read a customer-preset session report with no "
            "account and no API key. The token IS the authorization, so "
            "the security model is entropy + hard expiry + revocation. "
            "`created_by_user_id` is load-bearing, not audit trim: the "
            "report builder is owner-scoped, so rebuilding the document "
            "for an anonymous viewer requires the user the share was "
            "minted for."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS report_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                session_id INTEGER NOT NULL
                    REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
                created_by_user_id INTEGER NOT NULL
                    REFERENCES users(id) ON DELETE CASCADE,
                preset TEXT NOT NULL DEFAULT 'customer',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                view_count INTEGER NOT NULL DEFAULT 0,
                last_viewed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_report_shares_session
                ON report_shares(session_id);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_report_shares_session;
            DROP TABLE IF EXISTS report_shares;
        """,
    ),
    # Migration 046 — F55: link diagnostic sessions to a customer
    Migration(
        version=46,
        name="session_customer_id",
        description=(
            "F55: Add nullable `diagnostic_sessions.customer_id`. Work "
            "orders, invoices and appointments all carried a customer "
            "since Phase 118/006, but sessions only ever got `user_id` "
            "(the Phase 178 owner retrofit), so the customer-facing "
            "share page (Phase 200) could not name the person it was "
            "prepared for. Backfilled from `vehicles.customer_id`, "
            "SKIPPING the id-1 'Unassigned' sentinel that the Phase 006 "
            "retrofit used as its DEFAULT — backfilling that blindly "
            "would claim every orphan session belongs to a placeholder "
            "customer. Nullable on purpose: a session with no known "
            "customer is a legitimate state (walk-in diagnostics)."
        ),
        upgrade_sql="""
            ALTER TABLE diagnostic_sessions
                ADD COLUMN customer_id INTEGER
                REFERENCES customers(id) ON DELETE SET NULL;

            UPDATE diagnostic_sessions
               SET customer_id = (
                     SELECT v.customer_id FROM vehicles v
                      WHERE v.id = diagnostic_sessions.vehicle_id
                        AND v.customer_id IS NOT NULL
                        AND v.customer_id != 1
                   )
             WHERE vehicle_id IS NOT NULL
               AND customer_id IS NULL;

            CREATE INDEX IF NOT EXISTS idx_sessions_customer
                ON diagnostic_sessions(customer_id);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_sessions_customer;
            ALTER TABLE diagnostic_sessions DROP COLUMN customer_id;
        """,
    ),
    # Migration 047 — Phase 202: per-mechanic labor time entries
    Migration(
        version=47,
        name="work_order_time_entries",
        description=(
            "Phase 202: Add `work_order_time_entries` — the per-mechanic "
            "labor ledger. Time worked was previously UNRECONSTRUCTIBLE: "
            "`start_work` overwrites `work_orders.started_at` on every "
            "start and `pause_work` stamps nothing, so a started/paused/ "
            "resumed job kept one timestamp and no record of the gap. "
            "Closed entries sum into the existing `work_orders."
            "actual_hours` sink that invoicing, reconciliation and "
            "analytics already consume. The partial UNIQUE index "
            "enforces one OPEN entry per mechanic in the database rather "
            "than by convention — an application-level check would race "
            "a double-tap or a second device."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS work_order_time_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                duration_seconds INTEGER,
                source TEXT NOT NULL DEFAULT 'timer'
                    CHECK (source IN ('timer', 'manual')),
                needs_review INTEGER NOT NULL DEFAULT 0,
                note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id)
                    REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_time_entries_wo
                ON work_order_time_entries(work_order_id);
            CREATE INDEX IF NOT EXISTS idx_time_entries_user
                ON work_order_time_entries(user_id, started_at);
            -- One OPEN entry per mechanic, enforced by the database.
            CREATE UNIQUE INDEX IF NOT EXISTS idx_time_entries_one_open
                ON work_order_time_entries(user_id)
                WHERE ended_at IS NULL;
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_time_entries_one_open;
            DROP INDEX IF EXISTS idx_time_entries_user;
            DROP INDEX IF EXISTS idx_time_entries_wo;
            DROP TABLE IF EXISTS work_order_time_entries;
        """,
    ),
    # Migration 048 — field reports for OBD connection failures
    Migration(
        version=48,
        name="obd_failure_reports",
        description=(
            "Owner-facing field telemetry: when a mechanic cannot connect "
            "an OBD adapter, record it and alert the maintainer. Exists "
            "because the BLE transport ships UNVERIFIED against real "
            "hardware (F56) — rather than buy an adapter to test a path "
            "no user can currently reach, the first real failure is made "
            "to reach the maintainer with enough context to reproduce it. "
            "`notified_at` is stamped when the alert goes out so a retry "
            "storm does not become a push storm."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS obd_failure_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL
                    REFERENCES users(id) ON DELETE CASCADE,
                error_kind TEXT NOT NULL,
                transport TEXT,
                device_id TEXT,
                message TEXT,
                app_version TEXT,
                platform TEXT,
                os_version TEXT,
                created_at TEXT NOT NULL,
                notified_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_obd_failures_created
                ON obd_failure_reports(created_at);
            CREATE INDEX IF NOT EXISTS idx_obd_failures_kind
                ON obd_failure_reports(error_kind, transport);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_obd_failures_kind;
            DROP INDEX IF EXISTS idx_obd_failures_created;
            DROP TABLE IF EXISTS obd_failure_reports;
        """,
    ),
    # Migration 049 — Phase 206: bring known_issues under migration
    # control and index the sort its own query path uses.
    Migration(
        version=49,
        name="known_issues_sort_index",
        description=(
            "Phase 206: `known_issues` is the only large table in the "
            "product and was the only one NOT under "
            "migration control — it is created by SCHEMA_SQL with a "
            "single (make, model) index that its primary query path "
            "cannot use, because that path filters `make LIKE '%x%'` "
            "(leading wildcard, unusable by any B-tree) and then sorts "
            "`ORDER BY severity DESC, title` on unindexed columns. "
            "EXPLAIN QUERY PLAN showed `SCAN` + `USE TEMP B-TREE FOR "
            "ORDER BY`: every listing sorted the whole table to return "
            "50. With this index the plan becomes an ordered walk that "
            "stops at the LIMIT. Additive only — the table and its rows "
            "already exist from SCHEMA_SQL, so this adds indexes and "
            "touches no data."
        ),
        upgrade_sql="""
            CREATE INDEX IF NOT EXISTS idx_known_issues_sort
                ON known_issues(severity DESC, title);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_known_issues_sort;
        """,
    ),
    # Migration 050 — Phase 207: give `customers` a real tenancy column.
    Migration(
        version=50,
        name="customers_shop_scope",
        description=(
            "Phase 207 security audit: the customers table carried an "
            "`owner_user_id` column whose docstring claimed it "
            "'prevents customer data leakage in multi-tenant "
            "deployments' — but nothing in the codebase ever set it, "
            "so every row held the DEFAULT 1 (the system user) and the "
            "column was inert. Meanwhile GET /v1/shop/{shop_id}/"
            "customers listed the table unfiltered, so any shop-tier "
            "member of any one shop received every customer row in the "
            "database: name, email, phone, address and shop-private "
            "notes. `owner_user_id` is the wrong key regardless — a "
            "shop has many members, and customers belong to the shop, "
            "not to whichever mechanic typed them in. This adds the "
            "`shop_id` column the rest of the schema already uses "
            "(work_orders.shop_id, intake_visits.shop_id) so the API "
            "can scope by shop the way every other shop route does. "
            "Additive and nullable: pre-existing rows are backfilled "
            "to the only shop when a deployment has exactly one "
            "(the single-shop case, which is every install today), "
            "and otherwise left NULL rather than guessed at. NULL "
            "means unclaimed — the API never serves such a row to a "
            "shop, so the failure mode is an invisible customer, not "
            "a leaked one. Customer id=1 is the seeded 'unassigned' "
            "placeholder that owns pre-retrofit vehicles; it is global "
            "and deliberately stays NULL."
        ),
        upgrade_sql="""
            ALTER TABLE customers ADD COLUMN shop_id INTEGER
                REFERENCES shops(id) ON DELETE SET NULL;

            CREATE INDEX IF NOT EXISTS idx_customers_shop
                ON customers(shop_id);

            UPDATE customers
               SET shop_id = (SELECT id FROM shops LIMIT 1)
             WHERE shop_id IS NULL
               AND id != 1
               AND (SELECT COUNT(*) FROM shops) = 1;
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_customers_shop;
            ALTER TABLE customers DROP COLUMN shop_id;
        """,
    ),
    # Migration 051 — Phase 211: record where each known issue came from.
    Migration(
        version=51,
        name="known_issues_source",
        description=(
            "Phase 211 (Track K opener): `known_issues` carried 660 rows of "
            "specific repair claims — test voltages, torque figures, fix "
            "procedures — with no record of where any of them came from. "
            "A mechanic could not tell a service-manual figure from a "
            "model-generated one. Track K adds thirty phases of content "
            "authored from training data rather than a manual on the "
            "bench, so before any of it is written the table gains a "
            "`source` column, CHECK-constrained to a fixed vocabulary that "
            "mirrors `parts.verified_by` and adds `unverified` (origin "
            "never recorded — the honest value for every existing row) "
            "and `model-generated` (what Track K writes). NOT NULL with a "
            "constant default, which is the only form SQLite allows on an "
            "added column and also what makes the backfill implicit."
        ),
        upgrade_sql="""
            ALTER TABLE known_issues ADD COLUMN source TEXT NOT NULL
                DEFAULT 'unverified'
                CHECK (source IN (
                    'unverified', 'model-generated', 'forum',
                    'service-manual', 'mechanic-verified'
                ));
        """,
        rollback_sql="""
            ALTER TABLE known_issues DROP COLUMN source;
        """,
    ),
    # Migration 052 — Phase 235B: a provenance value for primary legal text.
    Migration(
        version=52,
        name="known_issues_source_regulation",
        description=(
            "Phase 235 shipped knowledge entries quoted verbatim from "
            "Commission Delegated Regulation (EU) No 44/2014 as amended "
            "by (EU) 2018/295, and migration 051's five-value vocabulary "
            "had no slot for a primary legal document. They were filed "
            "as `service-manual`, meaning 'primary official document', "
            "because the honest-looking alternative `unverified` sits in "
            "Gate 2's forum-derived allowlist and would have held a "
            "regulation to the forum-tip rule. This is a recurring "
            "content class rather than a one-off: Track K has leaned on "
            "regulator and legal sources at 228 (a national index "
            "defect), 231 (a recall misfiled under a misspelled make), "
            "233 (a do-not-ride campaign) and 235 (EU type approval). "
            "SQLite cannot alter a CHECK constraint in place, so the "
            "table is rebuilt — the CREATE-COPY-DROP-RENAME shape used "
            "by the rollbacks of migrations 003 and 004. The foreign "
            "key pragma is genuinely required and not defensive: "
            "`repair_plan_items.source_issue_id` REFERENCES "
            "known_issues(id), `get_connection` sets foreign_keys=ON, "
            "and DROP TABLE is refused outright while any child row "
            "points at the table."
        ),
        upgrade_sql="""
            PRAGMA foreign_keys=OFF;

            CREATE TABLE known_issues_rebuild (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                severity TEXT NOT NULL DEFAULT 'medium',
                symptoms TEXT,
                dtc_codes TEXT,
                causes TEXT,
                fix_procedure TEXT,
                parts_needed TEXT,
                estimated_hours REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_user_id INTEGER DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'unverified'
                    CHECK (source IN (
                        'unverified', 'model-generated', 'forum',
                        'service-manual', 'mechanic-verified', 'regulation'
                    ))
            );

            INSERT INTO known_issues_rebuild (id, title, description, make, model, year_start, year_end,
                 severity, symptoms, dtc_codes, causes, fix_procedure,
                 parts_needed, estimated_hours, created_at,
                 created_by_user_id, source)
            SELECT id, title, description, make, model, year_start, year_end,
                   severity, symptoms, dtc_codes, causes, fix_procedure,
                   parts_needed, estimated_hours, created_at,
                   created_by_user_id, source
            FROM known_issues;

            DROP TABLE known_issues;
            ALTER TABLE known_issues_rebuild RENAME TO known_issues;

            CREATE INDEX idx_known_issues_make_model
                ON known_issues(make, model);
            CREATE INDEX idx_known_issues_sort
                ON known_issues((CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END) DESC, title);

            PRAGMA foreign_keys=ON;
        """,
        # Maps `regulation` back to `service-manual` — which is exactly
        # what Phase 235 used as the stand-in, so this restores the
        # pre-052 state rather than inventing one. Without the mapping
        # the five-value CHECK would reject those rows and the rollback
        # would fail on real data.
        rollback_sql="""
            PRAGMA foreign_keys=OFF;

            CREATE TABLE known_issues_rollback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                severity TEXT NOT NULL DEFAULT 'medium',
                symptoms TEXT,
                dtc_codes TEXT,
                causes TEXT,
                fix_procedure TEXT,
                parts_needed TEXT,
                estimated_hours REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_user_id INTEGER DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'unverified'
                    CHECK (source IN (
                        'unverified', 'model-generated', 'forum',
                        'service-manual', 'mechanic-verified'
                    ))
            );

            INSERT INTO known_issues_rollback (id, title, description, make, model, year_start, year_end,
                 severity, symptoms, dtc_codes, causes, fix_procedure,
                 parts_needed, estimated_hours, created_at,
                 created_by_user_id, source)
            SELECT id, title, description, make, model, year_start, year_end,
                   severity, symptoms, dtc_codes, causes, fix_procedure,
                   parts_needed, estimated_hours, created_at,
                   created_by_user_id, CASE WHEN source = 'regulation' THEN 'service-manual' ELSE source END
            FROM known_issues;

            DROP TABLE known_issues;
            ALTER TABLE known_issues_rollback RENAME TO known_issues;

            CREATE INDEX idx_known_issues_make_model
                ON known_issues(make, model);
            CREATE INDEX idx_known_issues_sort
                ON known_issues((CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END) DESC, title);

            PRAGMA foreign_keys=ON;
        """,
    ),
    Migration(
        version=53,
        name="known_issues_severity_rank_index",
        description=(
            "Phase 240C. Six query paths ordered by `severity DESC` on a "
            "TEXT column, which SQLite sorts lexicographically: the four "
            "values alphabetise to `medium, low, high, critical`, so "
            "`critical` came back LAST everywhere. The queries now order by "
            "a CASE rank instead. "
            "That fix alone would have undone migration 206. Its index "
            "`idx_known_issues_sort` exists because EXPLAIN QUERY PLAN "
            "showed `SCAN` + `USE TEMP B-TREE FOR ORDER BY` -- every "
            "listing sorted the whole table to return 50. A CASE expression "
            "cannot use that index, so this migration replaces it with an "
            "index on the SAME expression the queries now use; the plan "
            "returns to `SCAN known_issues USING INDEX "
            "idx_known_issues_sort`. "
            "The expression comes from `motodiag.core.severity."
            "SEVERITY_RANK_SQL`, shared with the queries deliberately -- "
            "SQLite only uses an expression index when the ORDER BY "
            "expression matches the indexed one, so writing it twice would "
            "silently cost the optimisation. Index-only; touches no data."
        ),
        upgrade_sql="""
            DROP INDEX IF EXISTS idx_known_issues_sort;
            CREATE INDEX idx_known_issues_sort
                ON known_issues((CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END) DESC, title);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_known_issues_sort;
            CREATE INDEX idx_known_issues_sort
                ON known_issues(severity DESC, title);
        """,
    ),
    Migration(
        version=54,
        name="known_issues_dedup_and_unique_identity",
        description=(
            "Phase 244D. `known_issues` held 6,600 rows for 660 distinct "
            "issues -- every entry exactly ten times. The table had no "
            "uniqueness constraint and `add_known_issue` was a plain INSERT, "
            "so every run of the seed loop duplicated the whole corpus. Not "
            "cosmetic: a request for 20 corpus rows returned two distinct "
            "facts repeated ten times, and a live guidance run reported the "
            "corpus covered only those two topics. "
            "The constraint is a UNIQUE **expression** index over "
            "(COALESCE(make,''), COALESCE(model,''), title), not a plain "
            "column constraint. 43 seeded entries carry a NULL model, and "
            "SQLite treats NULLs as DISTINCT in a UNIQUE constraint -- a "
            "plain UNIQUE(make, model, title) would have left those 43 free "
            "to keep multiplying behind something that looked like a fix. "
            "Dedup keeps MIN(id) per key so the earliest load survives and "
            "ids stay stable for anything referencing them. "
            "The rebuild re-declares `idx_known_issues_sort` in its Phase "
            "240C EXPRESSION form; recreating the older `severity DESC` form "
            "would silently undo migration 053, because SQLite only uses an "
            "expression index when the ORDER BY expression matches it. "
            "IRREVERSIBLE: rollback restores the table and drops the unique "
            "index, but the deleted duplicate rows are NOT recoverable. They "
            "are exact duplicates by the key, so nothing distinct is lost -- "
            "but a rollback does not return the row count to 6,600."
        ),
        upgrade_sql="""
            PRAGMA foreign_keys=OFF;

            CREATE TABLE known_issues_dedup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                severity TEXT NOT NULL DEFAULT 'medium',
                symptoms TEXT,
                dtc_codes TEXT,
                causes TEXT,
                fix_procedure TEXT,
                parts_needed TEXT,
                estimated_hours REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_user_id INTEGER DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'unverified'
                    CHECK (source IN (
                        'unverified', 'model-generated', 'forum',
                        'service-manual', 'mechanic-verified', 'regulation'
                    ))
            );

            INSERT INTO known_issues_dedup (id, title, description, make, model,
                 year_start, year_end, severity, symptoms, dtc_codes, causes,
                 fix_procedure, parts_needed, estimated_hours, created_at,
                 created_by_user_id, source)
            SELECT id, title, description, make, model,
                   year_start, year_end, severity, symptoms, dtc_codes, causes,
                   fix_procedure, parts_needed, estimated_hours, created_at,
                   created_by_user_id, source
            FROM known_issues
            WHERE id IN (
                SELECT MIN(id) FROM known_issues
                GROUP BY COALESCE(make, ''), COALESCE(model, ''), title
            );

            DROP TABLE known_issues;
            ALTER TABLE known_issues_dedup RENAME TO known_issues;

            CREATE INDEX idx_known_issues_make_model
                ON known_issues(make, model);
            CREATE INDEX idx_known_issues_sort
                ON known_issues((CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END) DESC, title);
            CREATE UNIQUE INDEX idx_known_issues_identity
                ON known_issues(COALESCE(make, ''), COALESCE(model, ''), title);

            PRAGMA foreign_keys=ON;
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_known_issues_identity;
        """,
    ),
    Migration(
        version=55,
        name="known_issue_makes_junction",
        description=(
            "Phase 244F. `known_issues.make` is one free-text column doing four "
            "jobs -- a marque, a list of marques, a scope phrase, and in one row "
            "a whole sentence of findings ('BMW and Ducati have listed "
            "adjustments; KTM, Triumph, Aprilia, Moto Guzzi have none'). The cost "
            "was concrete: LiveWire and Damon were not queryable makes AT ALL, "
            "because every one of their entries lives inside a multi-marque "
            "string. All 24 LiveWire rows are tagged 'Harley-Davidson, LiveWire', "
            "so Phase 243's entire output was unreachable by make. "
            "This adds a junction table holding one row per (issue, marque) pair, "
            "derived from the make string by "
            "`motodiag.knowledge.marques.extract_marques`. "
            "The `make` column is NOT modified: it stays exactly what the author "
            "wrote and remains the single source, with the junction derived from "
            "it. Rewriting 970 entries by script is a larger risk than the defect. "
            "The backfill runs as a post_apply hook inside this migration's own "
            "transaction, because an index that exists but is empty is "
            "indistinguishable from a corpus that says nothing -- the exact "
            "confusion Phase 244C was written to end. "
            "Reversible: the junction is derived, so dropping it loses nothing "
            "that cannot be rebuilt from the column."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS known_issue_makes (
                issue_id INTEGER NOT NULL,
                make TEXT NOT NULL,
                UNIQUE (issue_id, make),
                FOREIGN KEY (issue_id) REFERENCES known_issues(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_known_issue_makes_make
                ON known_issue_makes(make);
        """,
        post_apply="motodiag.knowledge.marques:rebuild_make_index",
        rollback_sql="""
            DROP INDEX IF EXISTS idx_known_issue_makes_make;
            DROP TABLE IF EXISTS known_issue_makes;
        """,
    ),
    Migration(
        version=56,
        name="known_issue_models_junction",
        description=(
            "Phase 244I. The sibling of migration 055, for the `model` column: "
            "221 of 363 distinct values carry list or prose structure, so an "
            "equality filter reaches almost none of them. "
            "The hazard `make` did not have is that entries name models in "
            "order to EXCLUDE them -- '390 Adventure, 790 Adventure, 890 "
            "Adventure -- as distinct from 1290 Super Adventure', 'Hypermotard "
            "1100 (not EVO)', '1190/1290 fitment unknown, not excluded'. "
            "Attaching an entry to a machine its author ruled out is worse than "
            "the gap it closes: a wrong marque is obvious to a technician, a "
            "wrong MODEL of the right marque reads as a machine-specific match "
            "and gets acted on. Extraction therefore truncates at the first "
            "contrast marker and reads only what precedes it. "
            "Phase 244E already makes these rows reachable as `make_other_model`, "
            "so this buys precision rather than reachability -- a bad extraction "
            "has no upside to trade against. "
            "As with 055 the `model` column is NOT modified; the junction is "
            "derived beside it and can be rebuilt at any time."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS known_issue_models (
                issue_id INTEGER NOT NULL,
                model TEXT NOT NULL,
                UNIQUE (issue_id, model),
                FOREIGN KEY (issue_id) REFERENCES known_issues(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_known_issue_models_model
                ON known_issue_models(model);
        """,
        post_apply="motodiag.knowledge.models:rebuild_model_index",
        rollback_sql="""
            DROP INDEX IF EXISTS idx_known_issue_models_model;
            DROP TABLE IF EXISTS known_issue_models;
        """,
    ),
    Migration(
        version=57,
        name="cost_events_vision_kinds",
        description=(
            "Phase 244L. `cost_events.kind` carried "
            "CHECK (kind IN ('whisper', 'claude_extraction')) -- an accurate "
            "description of the product at Phase 195B, and untrue from Phase "
            "191B when vision analysis landed. A vision cost could not be "
            "recorded even by a caller who tried: the database would reject "
            "the row. Meanwhile Phase 244J's guidance endpoint discarded its "
            "usage entirely (`_usage`), so a request that spends a vision call "
            "recorded nothing, and `cost_events` sat at zero rows. "
            "Widens the CHECK to add `vision_sweep` and `vision_guidance`, and "
            "adds a nullable video_id FK (ON DELETE SET NULL, matching "
            "transcript_id) so a ledger row survives its video being deleted. "
            "TWO kinds rather than one generic `vision` because the question "
            "this exists to answer is what the QUESTIONS cost, and averaging "
            "guidance into sweeps loses exactly that number -- a kind cannot "
            "be split retroactively, since rows already written would be "
            "unattributable. "
            "No backfill: the sweep costs sitting in `analysis_findings` JSON "
            "stay there. Inventing ledger rows with fabricated timestamps "
            "would put numbers in a financial report that never came from a "
            "recorded event. "
            "ROLLBACK REBUILDS the pre-057 table rather than dropping it. "
            "The first draft copied migration 043's rollback verbatim, "
            "which drops `cost_events` outright -- correct for 043, which "
            "CREATED the table, and destructive here, where this migration "
            "only widened a CHECK. It necessarily DISCARDS vision rows, "
            "because the narrowed CHECK cannot hold them: that loss is "
            "stated here rather than left to be discovered."
        ),
        upgrade_sql="""
            PRAGMA foreign_keys=OFF;

            CREATE TABLE cost_events_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL
                    CHECK (kind IN ('whisper', 'claude_extraction',
                                    'vision_sweep', 'vision_guidance')),
                model TEXT NOT NULL,
                transcript_id INTEGER,
                video_id INTEGER,
                shop_id INTEGER,
                units_label TEXT,
                units_value INTEGER,
                cost_usd_cents INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (transcript_id)
                    REFERENCES voice_transcripts(id) ON DELETE SET NULL,
                FOREIGN KEY (video_id)
                    REFERENCES videos(id) ON DELETE SET NULL
            );

            INSERT INTO cost_events_new
                (id, kind, model, transcript_id, shop_id,
                 units_label, units_value, cost_usd_cents, created_at)
            SELECT id, kind, model, transcript_id, shop_id,
                   units_label, units_value, cost_usd_cents, created_at
            FROM cost_events;

            DROP TABLE cost_events;
            ALTER TABLE cost_events_new RENAME TO cost_events;

            CREATE INDEX idx_cost_events_created ON cost_events(created_at);
            CREATE INDEX idx_cost_events_shop ON cost_events(shop_id);
            CREATE INDEX idx_cost_events_kind ON cost_events(kind);

            PRAGMA foreign_keys=ON;
        """,
        rollback_sql="""
            PRAGMA foreign_keys=OFF;

            CREATE TABLE cost_events_old (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL
                    CHECK (kind IN ('whisper', 'claude_extraction')),
                model TEXT NOT NULL,
                transcript_id INTEGER,
                shop_id INTEGER,
                units_label TEXT,
                units_value INTEGER,
                cost_usd_cents INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (transcript_id)
                    REFERENCES voice_transcripts(id) ON DELETE SET NULL
            );

            INSERT INTO cost_events_old
                (id, kind, model, transcript_id, shop_id,
                 units_label, units_value, cost_usd_cents, created_at)
            SELECT id, kind, model, transcript_id, shop_id,
                   units_label, units_value, cost_usd_cents, created_at
            FROM cost_events
            WHERE kind IN ('whisper', 'claude_extraction');

            DROP TABLE cost_events;
            ALTER TABLE cost_events_old RENAME TO cost_events;

            CREATE INDEX idx_cost_events_created ON cost_events(created_at);
            CREATE INDEX idx_cost_events_shop ON cost_events(shop_id);
            CREATE INDEX idx_cost_events_kind ON cost_events(kind);

            PRAGMA foreign_keys=ON;
        """,
    ),
    # Migration 058 — Phase 244M: per-vehicle compiled memory
    Migration(
        version=58,
        name="memory_facts",
        description=(
            "Phase 244M. A compiled long-term memory so the shop can answer "
            "questions about a machine without spending an API call. "
            "THE SUBJECT IS THE VEHICLE, NOT THE CUSTOMER, and that is the "
            "load-bearing decision. `customers` row 1 is named `Unassigned` "
            "and all ten vehicle rows carry `customer_id = 1` -- the column "
            "DEFAULT, never overwritten -- while `customer_bikes`, the "
            "junction intended for this, is empty. Compiling per customer "
            "against that key produces ONE memory belonging to `Unassigned` "
            "holding every bike in the shop, which is the exact "
            "cross-contamination the feature exists to prevent. Keying on the "
            "vehicle is also right independently: machines outlive ownership, "
            "and a diagnostic history is continuous across a sale. Customer "
            "is recovered by joining, which is all an erasure request needs. "
            "`fact_key` is UNIQUE and COALESCEs its nullable parts, because "
            "SQLite treats NULLs as DISTINCT in a UNIQUE constraint and a "
            "naive key would let every re-compile insert duplicates "
            "(Phase 244D). "
            "`source` reuses the corpus provenance vocabulary rather than "
            "inventing one: Phase 244M's research found that field already "
            "maps onto shareability, and it is the control point a later "
            "cross-shop phase gates on. "
            "ON DELETE CASCADE from vehicles: the memory of a deleted machine "
            "goes with it. Deliberate, and the erase path's backstop rather "
            "than an accident of FK defaults."
        ),
        upgrade_sql="""
            CREATE TABLE memory_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                fact_kind TEXT NOT NULL
                    CHECK (fact_kind IN ('complaint', 'observation', 'repair',
                                         'part-replaced', 'measurement',
                                         'correction')),
                subject TEXT NOT NULL,
                value TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL
                    CHECK (source IN ('mechanic-verified', 'model-generated',
                                      'customer-reported', 'service-record')),
                origin_table TEXT NOT NULL,
                origin_id INTEGER,
                at_miles INTEGER,
                established_at TEXT NOT NULL,
                superseded_at TEXT,
                fact_key TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX idx_memory_facts_vehicle
                ON memory_facts(vehicle_id);
            CREATE INDEX idx_memory_facts_kind
                ON memory_facts(vehicle_id, fact_kind);
            CREATE INDEX idx_memory_facts_established
                ON memory_facts(vehicle_id, established_at DESC);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_memory_facts_established;
            DROP INDEX IF EXISTS idx_memory_facts_kind;
            DROP INDEX IF EXISTS idx_memory_facts_vehicle;
            DROP TABLE IF EXISTS memory_facts;
        """,
    ),
    # Migration 059 — Phase 244N: passive capture of what already happens
    Migration(
        version=59,
        name="passive_capture",
        description=(
            "Phase 244N. Two append-only logs for streams the product already "
            "produces and then discards. "
            "`guidance_interactions`: /ask returns a full GuidanceResponse -- "
            "restated question, ranked candidates each with a discriminating "
            "check and a Grounding label, what would narrow it, what could not "
            "be established -- and persists NONE of it. Since Phase 244L the "
            "product records what a question COST and not what it WAS. The "
            "whole response is kept as JSON and the fields worth querying are "
            "promoted to columns: `answers_the_question` is the single most "
            "interesting bit in the product (how often can it not answer?) and "
            "must not require a JSON scan to count. "
            "`video_analyses`: `set_analysis_findings` ran "
            "UPDATE videos SET analysis_findings = ?, one blob per video with "
            "no history, so every re-analysis destroyed the prior sweep. That "
            "already cost real data -- commit d2c23f8 exists because session "
            "6's sweep had to be rescued into git by hand before a re-run. "
            "The `videos.analysis_findings` column is NOT changed and keeps "
            "working exactly as it does today; it becomes a pointer to the "
            "current sweep rather than the only copy, so 244M's compile, the "
            "API and the reports all keep reading it unchanged. "
            "THERE IS NO OUTCOME COLUMN, and that is deliberate, not an "
            "omission. A finding nobody acted on is unresolved, not wrong -- it "
            "may have been right and deprioritised, or right and fixed without "
            "paperwork. A nullable outcome column invites a default, and a "
            "default here fabricates negatives that nothing downstream could "
            "later detect. Interpretation belongs to a phase that can be "
            "judged on it, against data this migration keeps honest. "
            "Backfills the existing sweeps into `video_analyses`: adding a "
            "table whose purpose is to stop dropping sweeps, while dropping "
            "the sweeps already recorded, would be its own joke."
        ),
        upgrade_sql="""
            CREATE TABLE guidance_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER,
                vehicle_id INTEGER,
                session_id INTEGER,
                question TEXT NOT NULL,
                question_understood_as TEXT NOT NULL DEFAULT '',
                answers_the_question INTEGER,
                candidate_count INTEGER NOT NULL DEFAULT 0,
                response_json TEXT NOT NULL,
                model_used TEXT,
                cost_event_id INTEGER,
                asked_by_user_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (video_id) REFERENCES videos(id)
                    ON DELETE SET NULL,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
                    ON DELETE SET NULL,
                FOREIGN KEY (cost_event_id) REFERENCES cost_events(id)
                    ON DELETE SET NULL
            );

            CREATE INDEX idx_guidance_interactions_vehicle
                ON guidance_interactions(vehicle_id);
            CREATE INDEX idx_guidance_interactions_video
                ON guidance_interactions(video_id);
            CREATE INDEX idx_guidance_interactions_created
                ON guidance_interactions(created_at DESC);
            CREATE INDEX idx_guidance_interactions_answered
                ON guidance_interactions(answers_the_question);

            CREATE TABLE video_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER NOT NULL,
                findings_json TEXT NOT NULL,
                model_used TEXT,
                cost_usd_cents INTEGER,
                frames_analyzed INTEGER,
                analyzed_at TEXT,
                superseded_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (video_id) REFERENCES videos(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX idx_video_analyses_video
                ON video_analyses(video_id, created_at DESC);
            CREATE INDEX idx_video_analyses_current
                ON video_analyses(video_id, superseded_at);

            INSERT INTO video_analyses
                (video_id, findings_json, analyzed_at)
            SELECT id, analysis_findings, analyzed_at
            FROM videos
            WHERE analysis_findings IS NOT NULL;
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_video_analyses_current;
            DROP INDEX IF EXISTS idx_video_analyses_video;
            DROP TABLE IF EXISTS video_analyses;

            DROP INDEX IF EXISTS idx_guidance_interactions_answered;
            DROP INDEX IF EXISTS idx_guidance_interactions_created;
            DROP INDEX IF EXISTS idx_guidance_interactions_video;
            DROP INDEX IF EXISTS idx_guidance_interactions_vehicle;
            DROP TABLE IF EXISTS guidance_interactions;
        """,
    ),
    # Migration 060 — Phase 244Q: the text diagnosis reaches the cost ledger
    Migration(
        version=60,
        name="cost_events_text_diagnosis",
        description=(
            "Phase 244Q. `cost_events.kind` accepted whisper, "
            "claude_extraction, vision_sweep and vision_guidance -- Phase 244L "
            "widened it for vision, and the TEXT diagnosis path was never in "
            "it. So `motodiag diagnose` has always spent money that the ledger "
            "could not hold, and this phase spent its first half tuning "
            "max_tokens and the fallback against spend that cannot be "
            "measured. The only trace of a real call was an "
            "`ai_response_cache` row, which is a cache artifact rather than a "
            "ledger entry, and this phase's cache-format bump orphaned it. "
            "Adds `text_diagnosis` and NOTHING else. No session_id column: "
            "`cost_events` already carries transcript_id, video_id and "
            "shop_id, and per-session attribution would be a second table "
            "rebuild for something nobody has needed yet -- cost by kind, by "
            "model and by day is what `what does a day cost` actually "
            "requires. "
            "Callers record `units_label='tokens'` with the real output token "
            "count, using the pair that is already kind-polymorphic "
            "(duration_ms for Whisper, tokens for Claude). That accumulates "
            "the COMPLETION-LENGTH DISTRIBUTION as a side effect, which is "
            "what should set max_tokens later -- from a p95 rather than from "
            "doubling 2048 on a single observation, which is what this phase "
            "did and said so. "
            "ROLLBACK REBUILDS rather than drops, per the defect Phase 244L "
            "shipped and Phase 235B caught: 043 created this table and may "
            "drop it; a migration that merely widens a CHECK may not. Rolling "
            "back necessarily DISCARDS text_diagnosis rows, because the "
            "narrowed CHECK cannot hold them -- stated here rather than "
            "discovered."
        ),
        upgrade_sql="""
            PRAGMA foreign_keys=OFF;

            CREATE TABLE cost_events_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL
                    CHECK (kind IN ('whisper', 'claude_extraction',
                                    'vision_sweep', 'vision_guidance',
                                    'text_diagnosis')),
                model TEXT NOT NULL,
                transcript_id INTEGER,
                video_id INTEGER,
                shop_id INTEGER,
                units_label TEXT,
                units_value INTEGER,
                cost_usd_cents INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (transcript_id)
                    REFERENCES voice_transcripts(id) ON DELETE SET NULL,
                FOREIGN KEY (video_id)
                    REFERENCES videos(id) ON DELETE SET NULL
            );

            INSERT INTO cost_events_new
                (id, kind, model, transcript_id, video_id, shop_id,
                 units_label, units_value, cost_usd_cents, created_at)
            SELECT id, kind, model, transcript_id, video_id, shop_id,
                   units_label, units_value, cost_usd_cents, created_at
            FROM cost_events;

            DROP TABLE cost_events;
            ALTER TABLE cost_events_new RENAME TO cost_events;

            CREATE INDEX idx_cost_events_created ON cost_events(created_at);
            CREATE INDEX idx_cost_events_shop ON cost_events(shop_id);
            CREATE INDEX idx_cost_events_kind ON cost_events(kind);

            PRAGMA foreign_keys=ON;
        """,
        rollback_sql="""
            PRAGMA foreign_keys=OFF;

            CREATE TABLE cost_events_old (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL
                    CHECK (kind IN ('whisper', 'claude_extraction',
                                    'vision_sweep', 'vision_guidance')),
                model TEXT NOT NULL,
                transcript_id INTEGER,
                video_id INTEGER,
                shop_id INTEGER,
                units_label TEXT,
                units_value INTEGER,
                cost_usd_cents INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (transcript_id)
                    REFERENCES voice_transcripts(id) ON DELETE SET NULL,
                FOREIGN KEY (video_id)
                    REFERENCES videos(id) ON DELETE SET NULL
            );

            INSERT INTO cost_events_old
                (id, kind, model, transcript_id, video_id, shop_id,
                 units_label, units_value, cost_usd_cents, created_at)
            SELECT id, kind, model, transcript_id, video_id, shop_id,
                   units_label, units_value, cost_usd_cents, created_at
            FROM cost_events
            WHERE kind IN ('whisper', 'claude_extraction',
                           'vision_sweep', 'vision_guidance');

            DROP TABLE cost_events;
            ALTER TABLE cost_events_old RENAME TO cost_events;

            CREATE INDEX idx_cost_events_created ON cost_events(created_at);
            CREATE INDEX idx_cost_events_shop ON cost_events(shop_id);
            CREATE INDEX idx_cost_events_kind ON cost_events(kind);

            PRAGMA foreign_keys=ON;
        """,
    ),
    # Migration 061 — Phase 209D: a session belongs to a shop
    Migration(
        version=61,
        name="session_shop_id",
        description=(
            "Phase 209D (F78). Adds nullable `diagnostic_sessions.shop_id`. "
            "Every `cost_events` row written before this had `shop_id = "
            "NULL`: voice attributed (its route is shop-scoped), vision and "
            "text did not, because a session carried `user_id` and "
            "`customer_id` and nothing that resolves a shop. A monthly cap "
            "enforced through `shop_cost_this_month` would therefore have "
            "read $0 for every shop and never fired -- a safeguard that "
            "looks like it works, which is the failure this phase exists to "
            "prevent. Sessions are stamped at creation from an explicit, "
            "membership-checked shop or from the owner's single active "
            "membership; vision and text spend then carry it. "
            "NOT BACKFILLED on purpose: attributing finished work from "
            "today's memberships would be a guess, and it would change no "
            "ledger row, since those are NULL whatever this column says. "
            "Nullable is a legitimate state -- a walk-in diagnosis, a CLI "
            "session on a machine with no shop -- exactly as migration 046 "
            "left `customer_id`. Rollback drops the index and the column, "
            "the same shape 046 uses; no table rebuild is needed because "
            "this migration created neither the table nor a CHECK."
        ),
        upgrade_sql="""
            ALTER TABLE diagnostic_sessions
                ADD COLUMN shop_id INTEGER
                REFERENCES shops(id) ON DELETE SET NULL;

            CREATE INDEX IF NOT EXISTS idx_sessions_shop
                ON diagnostic_sessions(shop_id);
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_sessions_shop;
            ALTER TABLE diagnostic_sessions DROP COLUMN shop_id;
        """,
    ),
    # Migration 062 — Phase 244R: classify the DTC codes already seeded
    Migration(
        version=62,
        name="dtc_category_backfill",
        description=(
            "Phase 244R. `knowledge/loader.py` built every DTCCode without "
            "`dtc_category`, so the field took its default and all 99 seeded "
            "codes were written as 'unknown' -- `motodiag code --category "
            "engine` answered 'No DTCs found' over 29 engine codes, and 19 of "
            "the 20 categories behaved the same way (the twentieth, "
            "'unknown', returned the whole table). The loader is fixed to "
            "read the key, but a fix in the loader only reaches a database "
            "someone re-seeds; this migration classifies the rows already "
            "there. "
            "The `post_apply` hook reads the same seed files and issues one "
            "UPDATE per code, matched on (code, make) -- the pair the loader "
            "dedupes on -- so `dtc_codes.id` never changes. A re-seed would "
            "have worked too, but `add_dtc` is INSERT OR REPLACE without an "
            "id and would have churned them. Rows the seed files do not "
            "mention are left alone. "
            "ALSO rewrites two `dtc_category_meta` descriptions. The shipped "
            "text made `emissions` ('O2, EVAP, PAIR, cat') and `exhaust` "
            "('O2, catalyst, SAI') claim the same faults, so the table could "
            "not settle where P0420 or P0131 belongs -- an authority that "
            "contradicts itself is not an authority. Emissions now names the "
            "emission-CONTROL systems and their monitors; exhaust names "
            "exhaust-PATH hardware that is not one. "
            "Rollback returns every row this touched to 'unknown' and "
            "restores both descriptions, which is exactly the pre-migration "
            "state."
        ),
        upgrade_sql="""
            UPDATE dtc_category_meta
               SET description = 'Emission-control systems and their monitors (EVAP, catalyst efficiency, O2/lambda, PAIR/SAI, EGR)'
             WHERE category = 'emissions';

            UPDATE dtc_category_meta
               SET description = 'Exhaust-path hardware that is not an emission-control device (exhaust valve/servo, flap, backpressure)'
             WHERE category = 'exhaust';
        """,
        post_apply="motodiag.knowledge.loader:backfill_dtc_categories",
        rollback_sql="""
            UPDATE dtc_codes SET dtc_category = 'unknown';

            UPDATE dtc_category_meta
               SET description = 'Emissions system faults (O2, EVAP, PAIR, cat)'
             WHERE category = 'emissions';

            UPDATE dtc_category_meta
               SET description = 'Exhaust system faults (O2, catalyst, SAI)'
             WHERE category = 'exhaust';
        """,
    ),
    # Migration 063 — Phase 255: the transmission axis.
    Migration(
        version=63,
        name="transmission_axis",
        description=(
            "Phase 255. Phase 254 shipped twelve rows about scooter CVTs "
            "whose `make` column names seven marques, and two of those "
            "marques also build motorcycles. Measured on the live "
            "database: a Honda GL1800 Gold Wing retrieved 7 of them, a "
            "CBR1000RR 7, a Grom 7, a Yamaha YZF-R1 8 and an XS650 8, "
            "while a Kawasaki Ninja 400 retrieved 0 -- Kawasaki simply is "
            "not in that make list, which isolates the make column as the "
            "cause. Nothing in the schema could have caught it, because "
            "there was no way to say what a row is ABOUT and no way to say "
            "what a machine HAS. "
            "This adds both. `vehicles.transmission` is a per-axis typed "
            "column with a CHECK constraint, exactly as `powertrain` is, "
            "and it is NULLABLE with no default: unlike powertrain, which "
            "defaults to 'ice', a machine whose transmission nobody "
            "recorded has an unknown transmission, and writing 'manual' "
            "would be a fabrication that retrieval would then act on. "
            "`known_issues.applicability` is a JSON object keyed by axis, "
            "so the next axis is a new key rather than a new migration. "
            "An absent key means unscoped on that axis, which is what "
            "every row written before this phase is. "
            "The `post_apply` hook backfills the twelve Phase 254 rows "
            "from the seed file, because a loader fix only reaches a "
            "database someone re-seeds and these rows are already live. "
            "Matched on (title, make) and applied with an UPDATE, so "
            "`known_issues.id` never changes. "
            "NOTE a deliberate limit, recorded rather than discovered "
            "later: a JSON column carries no CHECK constraint, so the "
            "Phase 195C schema lint does not cover `applicability` the way "
            "it covers `source`. The pydantic model in "
            "`knowledge/applicability.py` is the only guard, which makes "
            "it load-bearing and is why it rejects an unknown axis key and "
            "an unknown axis value loudly rather than dropping either."
        ),
        upgrade_sql="""
            ALTER TABLE vehicles ADD COLUMN transmission TEXT
                CHECK (transmission IS NULL OR transmission IN (
                    'manual', 'cvt', 'dct', 'semi_auto_centrifugal',
                    'semi_auto_actuated', 'direct_drive'
                ));

            ALTER TABLE known_issues ADD COLUMN applicability TEXT;
        """,
        post_apply="motodiag.knowledge.loader:backfill_row_applicability",
        rollback_sql="""
            ALTER TABLE known_issues DROP COLUMN applicability;
            ALTER TABLE vehicles DROP COLUMN transmission;
        """,
    ),
    # Migration 064 — Phase 256: the retrieval chokepoint.
    Migration(
        version=64,
        name="retrieval_chokepoint",
        description=(
            "Phase 256. Two changes, both in service of one function "
            "deciding whether a corpus row may reach a machine. "
            "(1) `retrieval_withheld` records every distinct make/model "
            "pair whose transmission resolves to `unknown` or `ambiguous`, "
            "with the provenance, the purpose it was retrieved for, how "
            "many retrievals it cost and how many rows were withheld. "
            "Phase 255 counted this in process memory, which meant the "
            "number was unreadable by anyone: every CLI command is a fresh "
            "process, so a stats command would have printed zeros forever "
            "(209B recorded the two accessors as orphans for exactly that "
            "reason). Persisted, the table IS the lookup's to-do list -- "
            "the machines that lost rows, ranked by how often. "
            "(2) `known_issues` is rebuilt to add "
            "CHECK (applicability IS NULL OR json_valid(applicability)). "
            "Migration 063 added the column without one because a JSON "
            "column carries no constraint by default, and the pydantic "
            "model was left as the only guard. This narrows the failure "
            "surface so the column cannot hold unparseable text at all. "
            "It does NOT validate the JSON *schema* -- an unknown axis key "
            "or an unknown value is still the pydantic model's job. "
            "A rebuild rather than ALTER TABLE ADD CONSTRAINT: the latter "
            "was verified to parse AND enforce on SQLite 3.53.2 (checked "
            "with a positive control, because an ALTER returning without "
            "raising is not evidence that it did anything), but the "
            "shipped product does not control the user's SQLite version, "
            "and the rebuild works everywhere. Migrations 051 and 052 "
            "established the pattern for this table. Verified before "
            "writing: zero of 1,045 rows fail json_valid today. "
            "PRAGMA foreign_keys=OFF is genuinely required, not "
            "defensive: repair_plan_items, known_issue_makes and "
            "known_issue_models all reference known_issues(id), "
            "get_connection sets foreign_keys=ON, and DROP TABLE is "
            "refused outright while any child row points at it."
        ),
        upgrade_sql="""
            CREATE TABLE IF NOT EXISTS retrieval_withheld (
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                provenance TEXT NOT NULL CHECK (provenance IN (
                    'explicit', 'model-sourced', 'powertrain-default',
                    'ambiguous', 'unknown'
                )),
                purpose TEXT NOT NULL CHECK (purpose IN (
                    'prompt', 'prediction', 'search'
                )),
                rows_withheld INTEGER NOT NULL DEFAULT 0,
                retrievals INTEGER NOT NULL DEFAULT 0,
                corrupt_rows INTEGER NOT NULL DEFAULT 0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                PRIMARY KEY (make, model, provenance, purpose)
            );

            CREATE INDEX IF NOT EXISTS idx_retrieval_withheld_cost
                ON retrieval_withheld(rows_withheld DESC, retrievals DESC);

            PRAGMA foreign_keys=OFF;

            CREATE TABLE known_issues_rebuild_064 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                severity TEXT NOT NULL DEFAULT 'medium',
                symptoms TEXT,
                dtc_codes TEXT,
                causes TEXT,
                fix_procedure TEXT,
                parts_needed TEXT,
                estimated_hours REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_user_id INTEGER DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'unverified'
                    CHECK (source IN (
                        'unverified', 'model-generated', 'forum',
                        'service-manual', 'mechanic-verified', 'regulation'
                    )),
                applicability TEXT
                    CHECK (applicability IS NULL OR json_valid(applicability))
            );

            INSERT INTO known_issues_rebuild_064 (id, title, description, make, model,
                 year_start, year_end, severity, symptoms, dtc_codes, causes,
                 fix_procedure, parts_needed, estimated_hours, created_at,
                 created_by_user_id, source, applicability)
            SELECT id, title, description, make, model, year_start, year_end,
                   severity, symptoms, dtc_codes, causes, fix_procedure,
                   parts_needed, estimated_hours, created_at,
                   created_by_user_id, source, applicability
            FROM known_issues;

            DROP TABLE known_issues;
            ALTER TABLE known_issues_rebuild_064 RENAME TO known_issues;

            CREATE INDEX idx_known_issues_make_model
                ON known_issues(make, model);
            CREATE INDEX idx_known_issues_sort
                ON known_issues((CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END) DESC, title);
            CREATE UNIQUE INDEX idx_known_issues_identity
                ON known_issues(COALESCE(make, ''), COALESCE(model, ''), title);

            PRAGMA foreign_keys=ON;
        """,
        rollback_sql="""
            DROP INDEX IF EXISTS idx_retrieval_withheld_cost;
            DROP TABLE IF EXISTS retrieval_withheld;

            PRAGMA foreign_keys=OFF;

            CREATE TABLE known_issues_rollback_064 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                severity TEXT NOT NULL DEFAULT 'medium',
                symptoms TEXT,
                dtc_codes TEXT,
                causes TEXT,
                fix_procedure TEXT,
                parts_needed TEXT,
                estimated_hours REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_user_id INTEGER DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'unverified'
                    CHECK (source IN (
                        'unverified', 'model-generated', 'forum',
                        'service-manual', 'mechanic-verified', 'regulation'
                    )),
                applicability TEXT
            );

            INSERT INTO known_issues_rollback_064 (id, title, description, make, model,
                 year_start, year_end, severity, symptoms, dtc_codes, causes,
                 fix_procedure, parts_needed, estimated_hours, created_at,
                 created_by_user_id, source, applicability)
            SELECT id, title, description, make, model, year_start, year_end,
                   severity, symptoms, dtc_codes, causes, fix_procedure,
                   parts_needed, estimated_hours, created_at,
                   created_by_user_id, source, applicability
            FROM known_issues;

            DROP TABLE known_issues;
            ALTER TABLE known_issues_rollback_064 RENAME TO known_issues;

            CREATE INDEX idx_known_issues_make_model
                ON known_issues(make, model);
            CREATE INDEX idx_known_issues_sort
                ON known_issues((CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END) DESC, title);
            CREATE UNIQUE INDEX idx_known_issues_identity
                ON known_issues(COALESCE(make, ''), COALESCE(model, ''), title);

            PRAGMA foreign_keys=ON;
        """,
    ),
    # Migration 065 — Phase 255B: the row edits Phase 256 deferred.
    Migration(
        version=65,
        name="twist_and_go_row_edits",
        description=(
            "Phase 255B. Three debts Phase 256 recorded and deferred, plus "
            "F115. All four are edits to rows that are already live, and "
            "all four touch a column in the identity index -- which is why "
            "they are applied here and not by re-seeding. "
            "`known_issues` has a UNIQUE index on (make, model, title) and "
            "`add_known_issue` upserts ON CONFLICT DO NOTHING, so a seed "
            "edit to any of those three columns does not update the row: "
            "the conflict never fires and a second row is inserted. "
            "Measured while planning this phase -- re-seeding after "
            "dropping `Filly LX 50` from 4609's model column took a "
            "12-row corpus to 13, with the over-claiming row still there. "
            "Filed as F129 and NOT fixed here. "
            "Row 4609 drops `Filly LX 50`. The row named it because the "
            "Kymco Agility service manual prints FILLY LX 50 in the "
            "recycled header of 21 of its 183 pages -- evidence Phase 254 "
            "examined and the transmission lookup rejected. Withdrawing "
            "the claim does NOT give the Filly the row: the Filly is "
            "absent from the lookup, resolves `unknown`, and the "
            "fail-closed filter withholds a {cvt} row from it before and "
            "after this migration. What changes is that the row stops "
            "asserting a machine its document does not establish. "
            "No lookup entry is added and no override is written. "
            "Row 4615 splits. It declared {cvt} over two claims: one about "
            "scooter CVT campaigns, and one about how the regulator's "
            "record behaves for ANY machine -- two contradictory index "
            "endpoints, and a per-vehicle lookup whose empty answer is "
            "identical for a wrong model name and a clean record. The "
            "second was withheld from every non-CVT machine in the corpus "
            "and named the SYM Symba, which the lookup classifies "
            "`semi_auto_centrifugal`. The general half becomes its own "
            "UNSCOPED row and carries the Symba; the CVT half keeps its "
            "id, its title and {cvt}, and drops the Symba. "
            "`Vespa 946` deliberately stays on the CVT half: it is a live "
            "KNOWN_SELF_EXCLUDING entry the operator ruled stays as-is "
            "under F119, and moving it would have resolved a pin this "
            "phase was not asked to touch. "
            "Row 4611 splits on the same principle, without a column "
            "edit. It declared {cvt} over a kickstart-availability survey "
            "-- which machines in this class have one, carburetted versus "
            "injected, and the Buddy Kick that is named for a kickstart it "
            "does not have -- and over a diagnostic that is not about "
            "transmissions at all: a brake-lever switch failure kills "
            "electric start and leaves the kickstart working, so an engine "
            "that kick-starts but will not start electrically is pointing "
            "at the switch or the starter circuit rather than at itself. "
            "The interlock is a lever and a switch. Unscoping that half "
            "reaches the Honda Super Cub C125 and the CT125 Hunter Cub, "
            "both `semi_auto_centrifugal` and both kickstart-equipped, "
            "which a {cvt} declaration had been withholding it from. "
            "Measured while writing this, and NOT fixed here: the CT125 "
            "reaches it as `CT125`, `Trail 125` or `Hunter Cub` but not "
            "as `CT125 Hunter Cub`, because that entry's canonical label "
            "is missing from its own alias tuple. Six of the 50 lookup "
            "entries have that shape; five are compound display labels "
            "nobody types. Filed as F131. "
            "F115: row 4605's make column gains Harley-Davidson, BMW and "
            "LiveWire. It is a vocabulary row -- three mechanically "
            "unrelated components are all called a drive belt -- and its "
            "make column reached the scooter marques but not the marques "
            "whose owners produce the collision, so the owners it exists "
            "to inform could not receive it. The list is measured: "
            "`drive belt` over title/description/symptoms across all "
            "1,045 rows returns 13, of which five carry a non-CVT meaning "
            "(188 and 1312 Harley-Davidson/LiveWire final drive, 715 and "
            "870 BMW alternator, 579 Yamaha final drive). Yamaha was "
            "already there, so three marques are added. Makes only, not "
            "models. "
            "4605 stays UNSCOPED and a test pins it there: a Road King, "
            "an R1200GS and a LiveWire ONE all resolve `unknown`, so any "
            "transmission set on this row would withhold it from exactly "
            "the three marques this fix adds -- F115 re-created by "
            "another route, in the migration claiming to close it. "
            "F132: the unevidenced year windows go, and so do the repair "
            "estimates on rows that describe no repair. The Phase 254 CVT "
            "rows carried year_start/year_end of 2002-2026 cited to nothing "
            "at either end, and `cli/diagnose.py::_covers_year` applies that "
            "window BEFORE retrieval, so it silently added and removed rows. "
            "Two rows whose own prose names a model-year range keep theirs. "
            "`estimated_hours` was set on every row in the file and none of "
            "them describes a repair. "
            "Nulling a bound removes a gate, so this can only widen. "
            "Measured over 11 machines and 8 model years: 143 row-slots "
            "gained, 0 lost, and for every row declaring {cvt} the widening "
            "reaches only machines the filter already admits. The two "
            "exceptions are the rows that are unscoped by design -- 4605, "
            "the drive-belt vocabulary row, and 4615's general half about "
            "the regulator record -- which now reach a 2001 Gold Wing. That "
            "is those rows doing their job. Operator's decision, "
            "2026-09-22, on the table in the phase's v1.1 Results."
            "4611 has no KNOWN_SELF_EXCLUDING entry before or after: its "
            "junction names no machine it excludes. Two of this phase's "
            "three splits touch that pin, not three. "
            "The hook rebuilds both junctions because both are derived "
            "from the columns this migration edits."
        ),
        upgrade_sql="",
        post_apply="motodiag.knowledge.loader:reconcile_255B_rows",
        rollback_sql="""
            UPDATE known_issues
               SET model = 'Agility 50, Agility 125, People S 250, People 250, Filly LX 50'
             WHERE title LIKE 'A Kymco service manual gives four CVT figures twice%'
               AND make IS 'Kymco'
               AND model IS 'Agility 50, Agility 125, People S 250, People 250';

            DELETE FROM known_issues
             WHERE title = 'The regulator''s two indexes contradict each other, and an empty recall answer is not a clean record';

            UPDATE known_issues
               SET model = 'XC155, Vespa GTS, Vespa Primavera, Vespa 946, Piaggio MP3, Honda Metropolitan, Kymco Agility, Kymco Like 150i, SYM Symba, Genuine Buddy, Genuine Buddy Kick'
             WHERE title LIKE 'What the regulator record shows for scooter CVTs%';

            DELETE FROM known_issues
             WHERE title = 'A kickstart that works when the starter button does not is a brake-lever switch test';

            -- known_issue_models is DERIVED from the model column, and the
            -- rollback path has no post_apply hook to rebuild it with. The
            -- two UPDATEs above restore the columns; these restore the two
            -- junction rows those columns lost. Without them a rollback
            -- lands at 2,422 junction rows where it started at 2,424 --
            -- measured, not assumed, on a copy of the live database.
            --
            -- These literals are junction values, so they are written in
            -- whatever form the extractor currently produces -- NOT in the
            -- form the model column spells. Phase 255C canonicalised the
            -- junction: the model never carries its marque, so the column's
            -- `SYM Symba` indexes as `Symba`. Restoring the pre-255C literal
            -- here put a string in the junction that no rebuild would ever
            -- produce, and the round trip landed one row short (2,385 ->
            -- 2,384) with `(164, 'Symba')` lost and `SYM Symba` left behind.
            -- `Filly LX 50` needs no change: its marque is Kymco, which the
            -- column does not prefix, so canonicalisation leaves it alone.
            INSERT OR IGNORE INTO known_issue_models (issue_id, model)
            SELECT id, 'Filly LX 50' FROM known_issues
             WHERE title LIKE 'A Kymco service manual gives four CVT figures twice%';

            INSERT OR IGNORE INTO known_issue_models (issue_id, model)
            SELECT id, 'Symba' FROM known_issues
             WHERE title LIKE 'What the regulator record shows for scooter CVTs%';

            -- F132, reversed: the unevidenced year windows and the repair
            -- estimates on rows that describe no repair.
            UPDATE known_issues SET year_start = 2002, year_end = 2026, estimated_hours = 0.5
             WHERE title = 'What a scooter CVT is, in the makers'' own words — and why searching for the word ''variator'' finds nothing';

            UPDATE known_issues SET year_start = 2002, year_end = 2026, estimated_hours = 0.5
             WHERE title = 'Three unrelated components are all called a drive belt, and a search for one returns the other two';

            UPDATE known_issues SET year_start = 2002, year_end = 2026, estimated_hours = 0.5
             WHERE title = 'Every maker publishes a roller wear limit — in a service manual, and two of them publish it twice with different numbers';

            UPDATE known_issues SET year_start = 2002, year_end = 2026, estimated_hours = 0.5
             WHERE title = 'The clutch side: one maker publishes an engagement speed, one publishes a 1 mm lining limit where everyone else says 2 mm';

            UPDATE known_issues SET year_start = 2002, year_end = 2026, estimated_hours = 0.5
             WHERE title = 'No scooter owner''s manual publishes a belt width or wear limit — one even prints the measuring figure with the number left off';

            UPDATE known_issues SET year_start = 2004, year_end = 2012, estimated_hours = 0.5
             WHERE title = 'A Kymco service manual gives four CVT figures twice with different numbers, and carries three different model names in its own page headers';

            UPDATE known_issues SET year_start = 2002, year_end = 2026, estimated_hours = 0.5
             WHERE title = 'What the makers themselves say a CVT symptom means — quoted rather than inferred';

            UPDATE known_issues SET year_start = 2002, year_end = 2026, estimated_hours = 0.5
             WHERE title = 'Kickstart backup, and the scooter named Kick that has none';

            UPDATE known_issues SET year_start = 2002, year_end = 2026, estimated_hours = 0.5
             WHERE title = 'No maker publishes a fault code for a CVT — the transmission is diagnosed by symptom, not by the lamp';

            UPDATE known_issues SET year_start = 2004, year_end = 2020, estimated_hours = 1.0
             WHERE title = 'Piaggio''s belt limit is three different numbers, and one manual prints two of them on the same page';

            UPDATE known_issues SET estimated_hours = 1.0
             WHERE title = 'A CVT recall exists that no belt, pulley or variator search would find — it is filed under the word sheave';

            UPDATE known_issues SET estimated_hours = 0.5
             WHERE title = 'What the regulator record shows for scooter CVTs — one campaign, and two indexes that disagree with each other and with the data';

            UPDATE known_issues SET year_start = 2003, year_end = 2026, estimated_hours = 1.0
             WHERE title = 'The regulator''s two indexes contradict each other, and an empty recall answer is not a clean record';

            -- F115, reversed. The make column and, because it is derived
            -- the same way and has no rebuild on this path, the three
            -- marque junction rows it produced.
            UPDATE known_issues
               SET make = 'Piaggio, Vespa, Honda, Yamaha, Kymco, SYM, Genuine'
             WHERE title LIKE 'Three unrelated components are all called a drive belt%';

            DELETE FROM known_issue_makes
             WHERE make IN ('Harley-Davidson', 'BMW', 'LiveWire')
               AND issue_id IN (
                   SELECT id FROM known_issues
                    WHERE title LIKE 'Three unrelated components are all called a drive belt%');
        """,
    ),
    # Migration 066 — Phase 255C: the junction carries the marque.
    Migration(
        version=66,
        name="model_junction_carries_marque",
        description=(
            "Phase 255C. A row that NAMES a machine could not reach tier 0 "
            "for it, because the tier query compares the resolved model "
            "against `known_issue_models.model` by equality and the resolver "
            "returned TWO canonical forms for one machine -- 'PCX 150' when "
            "the caller typed the model alone, 'Honda PCX150' when they "
            "typed the marque, both `exact`, both confidence 1.0. The "
            "junction held seven strings for the PCX family. One machine, "
            "two disjoint tier-0 sets, chosen by how somebody typed. "
            "Measured: 50 of 706 distinct junction strings were one machine "
            "under several spellings, and 48 of those 50 resolved to more "
            "than one canonical. "
            "The resolver has no rule about marques -- `known_models` returns "
            "244I's vocabulary, derived from what row authors typed -- so "
            "there was no design to preserve, only an inconsistency. "
            "Identity is now a (make, model) PAIR. The junction gains the "
            "make, populated from Phase 250C's attribution ladder, which "
            "already resolves which marque owns a token and already handles "
            "a marque that is also a model line. 250C computed it and the "
            "junction write discarded it; this carries it through. "
            "A table rebuild rather than ALTER, because the UNIQUE "
            "constraint moves from (issue_id, model) to "
            "(issue_id, make, model) and SQLite cannot alter a constraint. "
            "The `model` COLUMN on known_issues is untouched -- 244I pins "
            "that it is never rewritten, and the junction is derived beside "
            "it as it always was."
        ),
        upgrade_sql="""
            PRAGMA foreign_keys=OFF;

            CREATE TABLE known_issue_models_rebuild_066 (
                issue_id INTEGER NOT NULL,
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                UNIQUE (issue_id, make, model),
                FOREIGN KEY (issue_id) REFERENCES known_issues(id) ON DELETE CASCADE
            );

            DROP INDEX IF EXISTS idx_known_issue_models_model;
            DROP TABLE known_issue_models;
            ALTER TABLE known_issue_models_rebuild_066 RENAME TO known_issue_models;

            CREATE INDEX idx_known_issue_models_model
                ON known_issue_models(model);
            CREATE INDEX idx_known_issue_models_pair
                ON known_issue_models(make, model);

            PRAGMA foreign_keys=ON;
        """,
        post_apply="motodiag.knowledge.models:rebuild_model_index",
        rollback_sql="""
            PRAGMA foreign_keys=OFF;

            CREATE TABLE known_issue_models_rollback_066 (
                issue_id INTEGER NOT NULL,
                model TEXT NOT NULL,
                UNIQUE (issue_id, model),
                FOREIGN KEY (issue_id) REFERENCES known_issues(id) ON DELETE CASCADE
            );

            INSERT OR IGNORE INTO known_issue_models_rollback_066 (issue_id, model)
            SELECT issue_id, model FROM known_issue_models;

            DROP INDEX IF EXISTS idx_known_issue_models_model;
            DROP INDEX IF EXISTS idx_known_issue_models_pair;
            DROP TABLE known_issue_models;
            ALTER TABLE known_issue_models_rollback_066 RENAME TO known_issue_models;

            CREATE INDEX idx_known_issue_models_model
                ON known_issue_models(model);

            PRAGMA foreign_keys=ON;
        """,
    ),
    # Migration 067 — Phase 259: the engine-side pre-purchase inspection
    Migration(
        version=67,
        name="ppi_engine_workflow",
        description=(
            "Phase 259 (Track N opener): seed the engine-side "
            "pre-purchase inspection template on the Phase 114 substrate. "
            "One template (ppi_engine_v1, category 'ppi', powertrains "
            "ice+hybrid — the six subjects are ICE subjects, so the "
            "substrate's all-powertrains default is deliberately not used) "
            "and seven checklist items covering the row's subjects: "
            "static visual inspection, battery/charging health, "
            "starter/cold start/running check, compression test, leak-down "
            "test, oil level/condition/sample, fuel quality. Every figure "
            "in the item text cites the document it comes from (Honda "
            "CHF50 service manual; Honda Metropolitan 2025 owner's "
            "manual, with PDF pages); where no document sets a figure — "
            "leak-down, per Phase 259's census of 260 library PDFs — the "
            "item defers to the machine's own manual and invents nothing. "
            "Also re-points generic_ppi_v1's stale forward pointer "
            "('Track N phase 259 expands with engine-specific content') "
            "at the new template: this phase ships a new template "
            "alongside the generic quick check rather than editing it. "
            "Seeded inside the one-shot migration journal like 007: "
            "checklist_items has no unique constraint, so an item insert "
            "re-run outside the journal would duplicate rows."
        ),
        upgrade_sql="""
            INSERT OR IGNORE INTO workflow_templates
                (slug, name, description, category, applicable_powertrains,
                 estimated_duration_minutes, required_tier, created_by_user_id)
            VALUES
                ('ppi_engine_v1', 'Pre-purchase inspection — engine',
                 'Engine-side protocol for buying a used ICE motorcycle: compression, leak-down, oil, fuel, starter/charging health and the visual checks. Companion to generic_ppi_v1 (the quick check); the chassis protocol is Phase 260. Figures in the item text cite the document they come from; where no document sets a figure the item says where the figure belongs — nothing here is invented.',
                 'ppi', '["ice","hybrid"]', 70, 'individual', 1);

            -- generic_ppi_v1's description promised this phase's expansion
            -- inside the generic template; this phase ships it as a separate
            -- protocol, so re-point the pointer at what shipped.
            UPDATE workflow_templates
               SET description = 'Quick pre-purchase inspection covering engine, chassis, fluids, electrical. For the full engine-side protocol see ppi_engine_v1.',
                   updated_at = CURRENT_TIMESTAMP
             WHERE slug = 'generic_ppi_v1';

            INSERT OR IGNORE INTO checklist_items
                (template_id, sequence_number, title, description, instruction_text,
                 expected_pass, expected_fail, diagnosis_if_fail, required,
                 tools_needed, estimated_minutes)
            VALUES
            ((SELECT id FROM workflow_templates WHERE slug='ppi_engine_v1'), 1,
             'Static visual inspection — engine cold, off',
             'The walk-around before any key is turned. Cited: the Honda CHF50 service manual''s troubleshooting table (PDF p. 79, printed 4-3) lists an external oil leak as the first cause of oil consumption.',
             'With the engine cold and untouched, look over the whole engine for oil weeping at gaskets and case seams, coolant residue on liquid-cooled engines, and fresh oil on the frame, swingarm or tyre walls traced to its highest point. Check hoses and wiring for hardening, chafing, and improvised repairs (tape, zip ties). Look under the machine where it has been parked — a stain on the floor is a leak you will inherit. An external oil leak is the first cause of oil consumption in the Honda CHF50 service manual''s troubleshooting table (PDF p. 79).',
             'Engine and cases dry or lightly dusty; no fresh residue; no improvised repairs.',
             'Fresh oil at a gasket or seal, coolant residue, chafed wiring, taped hoses.',
             'An external leak means at minimum a gasket or seal job; weeping at a cylinder-head joint or behind a cover points deeper than a gasket.',
             1, '["flashlight","inspection mirror"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='ppi_engine_v1'), 2,
             'Battery condition and charging output',
             'Worked example figures: Honda CHF50 service manual, BATTERY/CHARGING SYSTEM SPECIFICATIONS (PDF p. 13): battery 12V-6Ah; current leakage 0.1 mA max; voltage 13.0-13.2 V fully charged at 20 °C/68 °F; below 12.3 V needs charging; alternator capacity 190 W at 5,000 rpm; charging coil resistance 0.05-0.5 Ω at 20 °C/68 °F.',
             'Measure the battery''s open-circuit voltage before starting (ignition off, ideally after the machine has stood). Read the machine''s own manual for its numbers: the CHF50 service manual (PDF p. 13) gives 13.0-13.2 V fully charged at 20 °C/68 °F and below 12.3 V needs charging for its 12V-6Ah battery, with 0.1 mA maximum current leakage. Then start the engine and measure the voltage at the battery terminals with the engine running — the CHF50''s alternator is rated 190 W at 5,000 rpm. Compare against the machine''s own manual: a voltage that does not rise with RPM points at the charging system, not the battery.',
             'Rest voltage within the manual''s fully-charged window; voltage at the battery rises when the engine runs.',
             'Rest voltage below the manual''s needs-charging line (12.3 V on the CHF50 example); no rise with RPM.',
             'A flat battery is cheap to re-test on a known-good unit; no rise with RPM points at the stator, regulator/rectifier or their connectors (the CHF50 manual''s charging chapter tests the coil at 0.05-0.5 Ω and ends its tree at the ECM).',
             1, '["multimeter"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='ppi_engine_v1'), 3,
             'Starter, cold start and running check',
             'How it cranks, catches and settles. No document sets a universal figure for this — the item observes behaviour, not numbers.',
             'From cold, watch and listen: crank speed (sluggish cranking separates a weak battery or starter from everything else), whether it catches within a normal few seconds, and how it settles to idle. Let it warm up, blip the throttle, and watch the exhaust: smoke that persists after warm-up, or a haze that grows with RPM, means the engine is burning oil — the CHF50 service manual''s oil-consumption table (PDF p. 79) attributes that to a worn or mis-installed piston ring, worn cylinder, or worn valve guide or seal. Listen for top-end tick, bottom-end knock, and smoke from the crankcase breather.',
             'Crisp crank, starts without tricks, settles to a steady idle, no persistent smoke, no mechanical noise.',
             'Slow crank, hard catch, stalls at idle, persistent blue-grey smoke, audible knock.',
             'A knock or a deep tick under load prices an engine rebuild into the deal. Persistent oil smoke matches the manual''s worn-ring / worn-cylinder / worn-valve-guide causes — confirm with the compression and leak-down items before negotiating.',
             1, '[]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='ppi_engine_v1'), 4,
             'Compression test',
             'The single most telling engine measurement on a used machine. Worked example figure: Honda CHF50 service manual, CYLINDER HEAD/VALVES SPECIFICATIONS (PDF p. 11): cylinder compression 1,393 kPa (14.2 kgf/cm2, 202 psi) at 1,500 rpm.',
             'Warm the engine, then kill the ignition and fuel delivery per the machine''s manual (pull the fuel-pump fuse or disconnect the injectors or coils so the engine is not firing during the test). Remove the spark plug, screw the gauge into the plug hole, hold the throttle wide open, and crank until the gauge stops rising. Compare the peak against the machine''s own service-manual spec — the CHF50 service manual gives 1,393 kPa (202 psi) at 1,500 rpm (PDF p. 11). On a multi-cylinder engine test every cylinder and compare them: one cylinder well below its siblings points at that cylinder, not at the engine''s age.',
             'Peak reading at or near the machine''s manual spec; cylinders in a close spread.',
             'Peak well below the manual spec, one cylinder far below its siblings, or the needle fluttering.',
             'Low on all cylinders: worn rings or cylinder (the CHF50 manual''s oil-consumption causes, PDF p. 79). Low on one: valve seal or gasket on that cylinder — follow with the leak-down item to localise.',
             1, '["compression gauge","spark plug socket"]', 15),

            ((SELECT id FROM workflow_templates WHERE slug='ppi_engine_v1'), 5,
             'Leak-down test (when compression is low or marginal)',
             'No document in the research library (260 PDFs searched; the control term "compression" finds 178) describes a leak-down test or sets a leak-down percentage, so this item carries no figure. Where a figure would appear, it defers to the machine''s own manual or the gauge''s own scale.',
             'Bring the cylinder to top dead centre on the compression stroke (both valves closed), lock the engine against rotation, connect a leak-down gauge to the plug hole at the gauge''s specified input pressure, and read the loss on the gauge''s own scale — interpret it against the machine''s service manual, which is where a threshold belongs. Then listen for where the air escapes: hissing at the intake or air box is the intake valve; at the exhaust pipe, the exhaust valve; bubbling in a liquid-cooled engine''s radiator or reservoir, the head gasket; breath from the crankcase breather or oil filler, the rings and cylinder. This test tells you WHERE compression went; the compression item tells you WHETHER it went.',
             'Low loss on the gauge''s scale, and no strong flow at any of the four escape routes.',
             'High loss, or a strong hiss or bubbles at one route.',
             'The escape route names the seal: intake valve, exhaust valve, head gasket (coolant path), or rings and cylinder wall. A head-gasket route on a liquid-cooled machine also means the coolant system has been pressurised — check the oil item for coolant contamination.',
             0, '["leak-down gauge","compressed air source","spark plug socket"]', 15),

            ((SELECT id FROM workflow_templates WHERE slug='ppi_engine_v1'), 6,
             'Oil level, condition and sample',
             'The oil tells you how the machine was kept. Guidance cited: Honda Metropolitan 2025 owner''s manual (PDF p. 62): "Check the engine oil level regularly, and add the recommended engine oil if necessary. Dirty oil or old oil should be changed as soon as possible."',
             'Check the oil level the way the machine''s manual says (usually upright and level, engine off, after a minute). Read the dipstick or sight glass: level between the marks, and the oil''s colour and clarity — the Metropolitan owner''s manual (PDF p. 62) says oil quality deteriorates with use and time, and that dirty or old oil should be changed as soon as possible. Pull the dipstick and smell: a strong fuel smell is fuel dilution (short trips or leaking injectors); a milky, chocolate-milk colour is water or coolant — stop and walk, or price a rebuild. On a purchase that matters, take a sample for laboratory oil analysis: fuel, coolant and wear metals name the engine''s health with figures no visual check can.',
             'Level between the marks; amber-to-dark oil, no milkiness, no fuel smell.',
             'Level below the lower mark, milky oil, or a strong fuel smell.',
             'Milky oil on a liquid-cooled machine matches the leak-down item''s head-gasket route — price it as such. Fuel dilution means tune, trim or injector trouble; a low level means the seller has not been checking (the manual says to check regularly).',
             1, '["clean rag","sample bottle"]', 5),

            ((SELECT id FROM workflow_templates WHERE slug='ppi_engine_v1'), 7,
             'Fuel quality',
             'Guidance cited: Honda Metropolitan 2025 owner''s manual (PDF p. 17): "Do not use stale or contaminated gasoline or an oil/gasoline mixture. Avoid getting dirt or water in the fuel tank."',
             'Ask how long the machine has stood and when the tank was last filled. Open the filler: smell for varnish (old fuel) and look for cloudiness, stratification or debris. If the machine stood with a low or empty tank, suspect rust or condensation inside — the Metropolitan owner''s manual''s fuel guidelines (PDF p. 17) warn against stale or contaminated gasoline, an oil/gasoline mixture, and dirt or water in the fuel tank. On a carburetted machine, pull the float-bowl drain into a clear jar: water or sediment settles out in seconds. Budget a tank drain, line flush and carb or injector service when the fuel is doubtful — it is never just the fuel.',
             'Fresh, clear fuel; dry bowl; no water line in the jar.',
             'Varnish smell, cloudy fuel, visible water or sediment, or rust inside the filler neck.',
             'Bad fuel means the whole path is suspect — tank, tap or pump, lines, carburettor or injectors. Water plus long storage means rust in a steel tank; price the tank, not just a flush.',
             1, '["clear jar","funnel"]', 5);
        """,
        rollback_sql="""
            DELETE FROM checklist_items
             WHERE template_id = (SELECT id FROM workflow_templates
                                   WHERE slug = 'ppi_engine_v1');

            DELETE FROM workflow_templates WHERE slug = 'ppi_engine_v1';

            UPDATE workflow_templates
               SET description = 'Quick pre-purchase inspection covering engine, chassis, fluids, electrical. Track N phase 259 expands with engine-specific content.',
                   updated_at = CURRENT_TIMESTAMP
             WHERE slug = 'generic_ppi_v1';
        """,
    ),
    # Migration 068 — Phase 260: the chassis-side pre-purchase inspection
    # template on the Phase 114 substrate, plus the one-row F158 re-point:
    # ppi_engine_v1's seeded description ends with a build reference
    # ("the chassis protocol is Phase 260") that no user-visible text may
    # carry. The chassis protocol this phase seeds is what it now points
    # at, by name. Rollback restores the seeded text verbatim.
    Migration(
        version=68,
        name="ppi_chassis_workflow",
        description=(
            "Phase 260: seed the chassis-side pre-purchase inspection "
            "template on the Phase 114 substrate. One template "
            "(ppi_chassis_v1, category 'ppi', powertrains ice+electric"
            "+hybrid — chassis subjects are powertrain-agnostic, unlike "
            "259's engine subjects) and seven checklist items covering "
            "the row's subjects: frame straightness and crash evidence, "
            "steering head bearings, front fork, swingarm, wheel "
            "bearings, brakes, tires. Every figure in the item text "
            "cites the document it comes from (KTM 250/300 EXC TPI "
            "owner's manual; Yamaha Zuma 125 2009 service manual; Honda "
            "CHF50 service manual; Honda Metropolitan 2025 owner's "
            "manual; BMW F800R rider's manual; Vespa GTS Super 300 ie "
            "(2008) service station manual, with PDF pages); where no "
            "document sets a figure — frame alignment, wheel-bearing "
            "play, per whitespace-proof library censuses with positive "
            "controls — the item says where the "
            "figure belongs and invents nothing. Also re-points "
            "ppi_engine_v1's description at the new template by name, "
            "removing the 'the chassis protocol is Phase 260' build "
            "reference (the F158 review miss recorded 2026-09-25). "
            "Seeded inside the one-shot migration journal like 007 and "
            "067: checklist_items has no unique constraint, so an item "
            "insert re-run outside the journal would duplicate rows."
        ),
        upgrade_sql="""
            INSERT OR IGNORE INTO workflow_templates
                (slug, name, description, category, applicable_powertrains,
                 estimated_duration_minutes, required_tier, created_by_user_id)
            VALUES
                ('ppi_chassis_v1', 'Pre-purchase inspection — chassis',
                 'Chassis-side protocol for buying a used motorcycle: frame and crash evidence, steering head bearings, front fork, swingarm, wheel bearings, brakes and tires. Companion to generic_ppi_v1 (the quick check) and ppi_engine_v1 (the engine-side protocol). Figures in the item text cite the document they come from; where no document sets a figure the item says where the figure belongs — nothing here is invented.',
                 'ppi', '["ice","electric","hybrid"]', 80, 'individual', 1);

            -- The F158 re-point: the engine template's seeded description
            -- promised the chassis protocol by phase number; name it instead.
            UPDATE workflow_templates
               SET description = 'Engine-side protocol for buying a used ICE motorcycle: compression, leak-down, oil, fuel, starter/charging health and the visual checks. Companion to generic_ppi_v1 (the quick check); for the full chassis-side protocol see ppi_chassis_v1. Figures in the item text cite the document they come from; where no document sets a figure the item says where the figure belongs — nothing here is invented.',
                   updated_at = CURRENT_TIMESTAMP
             WHERE slug = 'ppi_engine_v1';

            INSERT OR IGNORE INTO checklist_items
                (template_id, sequence_number, title, description, instruction_text,
                 expected_pass, expected_fail, diagnosis_if_fail, required,
                 tools_needed, estimated_minutes)
            VALUES
            ((SELECT id FROM workflow_templates WHERE slug='ppi_chassis_v1'), 1,
             'Frame, straightness and crash evidence',
             'The one component whose damage ends the deal rather than pricing it. Cited: the KTM 250/300 EXC owner''s manual directs "Check the frame for damage, cracks, and deformation" and adds the guideline "Repairs on the frame are not permitted" (PDF p. 94); the Honda CHF50 service manual lists a bent frame as a cause of steering pull and wheel wobble (PDF pp. 217, 318).',
             'Walk the whole frame front to back: every weld seam (fresh or amateur welds, grind marks, repaint that does not match the factory finish), the steering-head area for hairline cracks, the peg and lever mounts for bent brackets, and the bar-ends, engine covers and exhaust for slide evidence. Sight down the steering head to the rear axle: the CHF50 service manual names a bent frame behind a machine that steers to one side or will not track straight (PDF p. 217). Ask for the service records, any crash story and the title status, and read the machine against them — new OEM plastics on a "never dropped" seller story is a question, not an answer. No document in the research library sets a frame-alignment measurement or a straightening tolerance, so none is invented here: a frame suspected of bending goes to the machine''s own service manual or a specialist jig, and the KTM manual''s position on repairs to its own frames is that they are not permitted — a damaged frame is a replaced frame (PDF p. 94).',
             'Seams and paint consistent throughout, no welded repair outside factory joints, no bent mounts, history and title clean.',
             'Cracks, non-factory welds, repainted sections hiding damage, bent peg or lever mounts, a crash story that does not match the machine.',
             'A repaired frame is a salvage decision, not a price adjustment: the KTM owner''s manual''s rule for its own machines is that a damaged frame is changed, not repaired (PDF p. 94). Cosmetic scuffs price themselves; cracks at the steering head or the rear-arm pivot area end the inspection.',
             1, '["flashlight","inspection mirror"]', 15),

            ((SELECT id FROM workflow_templates WHERE slug='ppi_chassis_v1'), 2,
             'Steering head bearings',
             'Feel, not figures — the cited manuals give the procedure and the adjustment torques, not a play tolerance. Cited: the Yamaha Zuma 125 2009 service manual (PDF p. 93): "Grasp the bottom of the front fork legs and gently rock the front fork"; the KTM 250/300 EXC owner''s manual (PDF p. 76): "Play should not be detectable on the steering head bearing."',
             'Raise the front wheel clear of the ground. Grasp the bottom of the fork legs and rock them to and fro in the direction of travel: the KTM manual''s standard is that play should not be detectable (PDF p. 76); the Zuma 125 service manual calls the same movement binding or looseness (PDF p. 93). Then turn the bars slowly lock to lock — they must move easily over the entire range with no detent position. A notch at the straight-ahead position is dented bearing races. The Zuma manual''s adjustment is made on the lower ring nut, 38 N·m initial tightening torque and 14 N·m final (PDF p. 94) — freshly adjusted but unchanged bearings only hide the notch until the grease settles.',
             'No detectable play rocked; bars swing freely lock to lock, no notch at straight-ahead.',
             'A knock when rocked; a notch or heavy spot through the range; bars that feel heavy or notch anywhere through the range.',
             'Rocking play is loose adjustment or worn bearings; a notch at straight-ahead is brinelled races from an impact or years of load in one position — and the KTM manual warns that running with play damages the bearing seats in the frame as well (PDF p. 76). Adjustment is cheap; dented races mean a steering-stem strip, and seats damaged at the frame belong to the frame item''s walk-away.',
             1, '[]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='ppi_chassis_v1'), 3,
             'Front fork — seals, stanchions and action',
             'Cited: the Yamaha Zuma 125 2009 service manual''s front-fork check (PDF p. 95): inner tube "Damage/scratches → Replace", oil seal "Oil leakage → Replace", and "Push down hard on the handlebar several times and check if the front fork rebounds smoothly. Rough movement → Repair." Its chassis specifications (PDF p. 34) give that machine''s fork spring a 252.1 mm standard free length with a 247 mm limit, and the inner tube a 0.2 mm bending limit.',
             'Hold the machine upright, pull the front brake, and push down hard on the bars several times: the fork must rebound smoothly — the Zuma 125 service manual''s check is exactly this, and rough movement is a repair (PDF p. 95). Then look at each leg: run a gloved finger or a thin plastic card over the chrome above the seal line for nicks and pitting, and inspect the seal lips and the back of the dust wipers for an oil ring — oil on the stanchion or a film on the slider is a seal already weeping, and the manual''s rule for a weeping oil seal is replace, and for a damaged or scratched inner tube, replace (PDF p. 95). A leg that has been weeping a while feels dry and sticky on the first compression. Sight along both legs from the side for a bend: a twisted or bent fork is crash evidence, and the frame item gets the story.',
             'Smooth rebound, dry stanchions and wipers, no nicks in the travel zone, straight legs.',
             'An oil ring or wet film on the stanchion, pitting or scratches where the seal runs, notched or uneven damping, a visible bend.',
             'Weeping seals mean a seal and oil service at minimum; a nick in the chrome tears new seals, so a nicked stanchion prices a tube. For spring and straightness figures, the machine''s own manual owns the numbers: the Zuma 125''s fork spring measures 252.1 mm free against a 247 mm limit and its inner tube''s bending limit is 0.2 mm (PDF p. 34); the CHF50''s fork spring is 128.5 mm against a 125.9 mm service limit (PDF p. 12).',
             1, '[]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='ppi_chassis_v1'), 4,
             'Swingarm, linkage and rear suspension',
             'Cited: the KTM 250/300 EXC owner''s manual checks its "link fork" — the rear arm — "for damage, cracks, and deformation", with the guideline "Repairs on the link fork are not permitted" (PDF p. 94); the Honda CHF50 service manual names "worn or damaged engine mounting bushings" as a cause of steering pull and wheel wobble on its unit-mounted engine (PDF pp. 217, 318) and "oil leakage from damper unit" as a cause of soft suspension (PDF p. 241); the Vespa GTS Super 300 ie (2008) service station manual sets the axial clearance between its two swinging arms, and of the frame-side arm, at 0.40–0.60 mm standard with a 1.5 mm allowable limit after use, measured with a feeler gauge (PDF p. 227).',
             'Grab the rear wheel firmly at the sides and push it left and right while watching and feeling the pivot: anything beyond tyre flex is play at the rear-arm bearings or the engine hanger — the CHF50 manual names those mounting bushings as a cause of pull and of wobble (PDF pp. 217, 318). On a linkage machine, check every linkage bearing and heim joint for play and dryness; on a unit-construction scooter, feel at the engine mounts. Inspect the rear arm, the linkage and the shock absorbers for cracks, dents and an oil film at the damper shaft — the CHF50 manual lists oil leakage from the damper unit as a cause of soft suspension (PDF p. 241). A play figure is a workshop measurement on the removed arm, not a roadside check, and it is the machine''s own: the Vespa GTS Super 300 ie (2008) service station manual takes the swinging arm off and sets the axial clearance between its two arms at 0.40–0.60 mm standard, 1.5 mm allowable limit after use, by feeler gauge (PDF pp. 226–227). Where a figure would decide a borderline case, the machine''s own service manual owns it — and any detectable knock at a pivot on a used machine is a service item now, not a negotiating point later.',
             'No side-to-side movement beyond tyre flex at the pivot; linkage joints tight and lubricated; dry damper shafts; no cracks.',
             'A clunk or visible movement at the pivot, dry or rusted linkage bearings, oil mist or weeping at a damper, cracks or dents.',
             'Pivot or linkage play means the machine has been ridden loose: bearing replacement at the arm, or engine-mount bushings on a unit scooter. A weeping damper is a shock service or replacement. The KTM manual''s rule for its own rear arm is the frame''s rule — damaged means changed, not repaired (PDF p. 94).',
             1, '[]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='ppi_chassis_v1'), 5,
             'Wheel bearings and rims',
             'Cited: the Yamaha Zuma 125 2009 service manual''s maintenance table (PDF p. 55): wheels — check runout and for damage; wheel bearings — "Check bearings for smooth operation. Replace if necessary." The Honda CHF50 service manual gives axle runout a 0.20 mm service limit (PDF p. 218) and wheel rim runout 2.0 mm radial and 2.0 mm axial service limits (PDF pp. 12, 242), and names faulty wheel bearings and a bent front axle as causes of a front wheel that turns hard (PDF p. 217), and worn or damaged wheel bearings and a bent axle behind a wheel that will not spin freely by hand (PDF p. 314).',
             'Raise each wheel in turn and spin it: it must turn freely and quietly — the CHF50 manual''s drag causes are brake dragging, worn or damaged wheel bearings, and a bent axle (PDF p. 314). Grasp the wheel at opposite sides and rock it hard: any movement you can feel is bearing play (a drum-brake machine drags lightly through its shoes — feel past it); the Zuma 125 manual''s table check is bearings for smooth operation, replace if necessary (PDF p. 55). Watch the rim at the valve while it spins for hop and wobble, and check the rim for dents, flat spots and cracked or missing spokes on a laced wheel. No document in the research library sets a wheel-bearing play figure, so none is invented here: the hand test is the standard — smooth and silent passes, any grinding, rumble or knock fails — and a borderline case belongs to the machine''s own manual, whose runout limits for its own parts are figures like the CHF50''s 0.20 mm axle and 2.0 mm rim limits (PDF pp. 12, 218, 242).',
             'Wheels spin freely and quietly, no rock at the bearings, rims run true, spokes intact where fitted.',
             'Grinding or rumbling while spinning, a knock when rocked, visible hop or wobble, a dented or flat-spotted rim, missing or loose spokes.',
             'Bearing noise or play means bearings now, and how long it has been ridden that way measures what else has been skipped. A wheel that still will not run true after new bearings follows the CHF50 manual''s diagnosis path — axle runout against its 0.20 mm service limit, rim runout against its 2.0 mm limits (PDF pp. 218, 242) — and an impact hard enough to dent a rim belongs in the frame item''s crash story.',
             1, '[]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='ppi_chassis_v1'), 6,
             'Brakes — pads or shoes, drums, discs and levers',
             'Figures are the cited machine''s own. Cited: Honda CHF50 service manual — front and rear brake drum I.D. 95.0 mm standard, 95.5 mm service limit; lining thickness 3.5 mm standard, 1.0 mm service limit; lever free play 10-20 mm; "Always replace the brake shoes as a set" (PDF pp. 12, 241, 243). BMW F800R rider''s manual — brake pad wear limit 1.0 mm front and rear; the front''s reads "min 1.0 mm (Friction pad only, without backing plate. The wear indicators (grooves) must be clearly visible.)" (PDF pp. 94-95). KTM 250/300 EXC owner''s manual — brake disc wear limits for the standard models, front 2.5 mm, rear 3.5 mm (PDF p. 164); hand brake lever free travel at least 3 mm (PDF p. 99).',
             'Drum machines: pull the inspection covers where the machine has them and read the shoe linings, then measure what the covers will let you reach against the machine''s own manual — the CHF50''s drum measures 95.0 mm standard with a 95.5 mm service limit and its linings 3.5 mm against a 1.0 mm limit (PDF pp. 12, 243), and a drum at its limit cannot be machined back. Disc machines: read the friction material on both pads through the caliper — the F800R manual''s pad limit is a minimum 1.0 mm of friction pad only, without backing plate, and the wear grooves must still be clearly visible (PDF p. 94) — then measure the disc thickness against the machine''s own manual (a standard KTM EXC''s discs wear to 2.5 mm front, 3.5 mm rear, PDF p. 164), sighting for scoring, a wear lip and blue heat spots. Pull each lever and press the pedal: free play should be small and definite (the CHF50''s levers specify 10-20 mm, PDF p. 12; the KTM''s hand lever at least 3 mm free travel, PDF p. 99) and the pressure point must be firm and hold under a hard steady pull. On hydraulic machines, read the fluid level and its colour: the KTM manual''s reading of a level below the marking is that the system is leaking or the linings are worn down, and old brake fluid reduces the braking effect (PDF p. 101).',
             'Pads or shoes above their limits with indicators or grooves visible, discs and drums within thickness, firm holding pressure point, clean fluid at its level.',
             'Pads at or past their grooves, a drum past its limit, scored or blued discs, a lever that pumps up or sinks, black fluid.',
             'Worn pads are cheap; a disc or drum at its limit prices the friction surface and sometimes the caliper or the whole drum, and shoes always go as a set (CHF50 manual, PDF p. 243). A lever that needs pumping on a used machine means air, a leak or a failing master cylinder — the KTM manual''s leak-or-worn-linings reading of a falling fluid level (PDF p. 101). Grabbing, dragging or pulsing brakes tell of a bent disc or an out-of-round drum; take the machine''s own figures from its manual before pricing any of it.',
             1, '["flashlight"]', 15),

            ((SELECT id FROM workflow_templates WHERE slug='ppi_chassis_v1'), 7,
             'Tires — tread, pressure, damage and age',
             'Cited: Honda CHF50 service manual — minimum tire tread depth 0.8 mm service limit, cold pressures 125 kPa (18 psi) front, 200 kPa (28 psi) rear (PDF p. 12). Honda Metropolitan 2025 owner''s manual — the same pressures, front 18 psi (125 kPa), rear 29 psi (200 kPa) (PDF p. 121); tread wear indicators: "If they become visible, replace the tires immediately" (PDF p. 65); and the damage list — cuts, slits, cracks that expose fabric or cords, embedded objects, sidewall bumps and bulges (PDF p. 64). KTM 250/300 EXC owner''s manual — minimum tread depth at least 2 mm (PDF p. 115); tire age: the last four digits of the DOT number are week and year of manufacture, and "KTM recommends that the tires be changed after 5 years at the latest, regardless of the actual state of wear" (PDF p. 116).',
             'Check the pressures cold against the machine''s own manual — the Metropolitan 2025 owner''s manual specifies 18 psi (125 kPa) front and 29 psi (200 kPa) rear (PDF p. 121), and the CHF50 service manual the same shape (PDF p. 12). Measure tread depth at the centre and both shoulders and find the wear indicators in the grooves: if they are visible the tire is finished — the Metropolitan manual''s word is replace immediately (PDF p. 65). Minimum tread depth is each manual''s own figure: the CHF50''s service limit is 0.8 mm, the KTM''s minimum is 2 mm (PDF pp. 12, 115). Inspect the whole carcass of both tires for the Metropolitan manual''s damage list — cuts, slits and cracks that expose fabric or cords, nails and other embedded objects, and any bump or bulge in the sidewall (PDF p. 64) — and for dry-checking in the grooves and sidewall. Read the date: the DOT moulding''s last four digits are week then year of manufacture (PDF p. 116), and the KTM manual draws the age line itself — changed after 5 years at the latest, regardless of wear. Run a finger round each bead and match the pair: different tread patterns front and rear is the KTM manual''s handling warning (PDF p. 39).',
             'Tread above the machine''s minimum with indicators not visible, correct cold pressures, no cuts or bulges, date codes within 5 years, a matched pair.',
             'Indicators showing, tread at the limit, exposed cords, a sidewall bump, date codes older than 5 years, mismatched patterns.',
             'A sidewall bump is a carcass failure — replace before riding the machine home (the Metropolitan manual''s damage list, PDF p. 64). Tread older than the 5-year line is a negotiating point the KTM manual sets itself (PDF p. 116). Uneven wear — cupping, flat-centre, one-sided — points past the tire at the pressure history, the wheel item''s bearings or the frame item''s alignment story.',
             1, '["tread depth gauge","tire pressure gauge"]', 10);
        """,
        rollback_sql="""
            DELETE FROM checklist_items
             WHERE template_id = (SELECT id FROM workflow_templates
                                   WHERE slug = 'ppi_chassis_v1');

            DELETE FROM workflow_templates WHERE slug = 'ppi_chassis_v1';

            UPDATE workflow_templates
               SET description = 'Engine-side protocol for buying a used ICE motorcycle: compression, leak-down, oil, fuel, starter/charging health and the visual checks. Companion to generic_ppi_v1 (the quick check); the chassis protocol is Phase 260. Figures in the item text cite the document they come from; where no document sets a figure the item says where the figure belongs — nothing here is invented.',
                   updated_at = CURRENT_TIMESTAMP
             WHERE slug = 'ppi_engine_v1';
        """,
    ),
    # Migration 069 — Phase 261 (Track N batch 1): four service protocols
    # on the Phase 114 substrate, one per ROADMAP row — tire (261), brake
    # (269), suspension (270), chain/belt/shaft (271). Inserts only: no
    # existing row is altered or deleted. Rollback removes the four
    # templates and their items.
    Migration(
        version=69,
        name="chassis_drivetrain_service_workflows",
        description=(
            "Phase 261, Track N batch 1: seed four service protocols on the "
            "Phase 114 substrate — tire_service_v1, brake_service_v1, "
            "suspension_service_v1 and drivetrain_service_v1, all three "
            "powertrains. Every figure in the item text names its machine "
            "and cites the maker's document with its PDF page (claims "
            "T1-T29, B1-B38, S1-S29, D1-D34 in 261_implementation.md); "
            "where no document sets a figure (tire wear-pattern names, "
            "universal-joint inspection, belt alignment — negatives N1-N3 "
            "with positive controls) the item says so and invents none. "
            "Seeded inside the one-shot migration journal like 007, 067 "
            "and 068: checklist_items has no unique constraint. Inserts "
            "only; the rollback deletes the four templates and their items."
        ),
        upgrade_sql="""
            INSERT OR IGNORE INTO workflow_templates
                (slug, name, description, category, applicable_powertrains,
                 estimated_duration_minutes, required_tier, created_by_user_id)
            VALUES
                ('tire_service_v1', 'Tire service',
                 'Service protocol for inspecting and changing a motorcycle tire: reading the old tire, damage and age cracking, the date code, pressure sensors, fitting, balance, pressure and run-in. Figures in the item text are the named machine''s own and cite the document and PDF page they come from; where no document sets a figure the item says so and invents none.',
                 'tire_service', '["ice","electric","hybrid"]', 60, 'individual', 1),
                ('brake_service_v1', 'Brake service',
                 'Service protocol for hydraulic disc brakes: pads, discs, caliper and master-cylinder overhaul, the fluid, bleeding, reassembly and bedding-in. Figures in the item text are the named machine''s own and cite the document and PDF page they come from; take the machine in hand''s figures from its own service manual.',
                 'brake_service', '["ice","electric","hybrid"]', 90, 'individual', 1),
                ('suspension_service_v1', 'Suspension service',
                 'Service protocol for the fork and rear shock: sag, spring rate for the rider, fork oil, fork seals, fork air, the rear shock, and the damping and preload settings. Figures in the item text are the named machine''s own and cite the document and PDF page they come from; where the makers disagree the item says so.',
                 'suspension_service', '["ice","electric","hybrid"]', 180, 'individual', 1),
                ('drivetrain_service_v1', 'Chain, belt and shaft drive service',
                 'Service protocol for the final drive. A machine has one drive type, so every item is optional: do the chain items on a chain drive, the belt item on a belt drive, the shaft items on a shaft drive. The machine''s own specifications name its type (for example "Shaft drive with bevel gears", BMW R 1200 GS rider''s manual, PDF p. 156). Figures in the item text are the named machine''s own and cite the document and PDF page they come from; where no document sets a figure the item says so and invents none.',
                 'drivetrain_service', '["ice","electric","hybrid"]', 60, 'individual', 1);

            INSERT OR IGNORE INTO checklist_items
                (template_id, sequence_number, title, description, instruction_text,
                 expected_pass, expected_fail, diagnosis_if_fail, required,
                 tools_needed, estimated_minutes)
            VALUES
            -- ---------------------------------------------------- tire_service_v1
            ((SELECT id FROM workflow_templates WHERE slug='tire_service_v1'), 1,
             'Read the old tire before it comes off',
             'The worn tire is evidence about the machine, so read it before it is gone. Cited: the KTM 2022 250/300 EXC TPI owner''s manual — "Low tire pressure leads to abnormal wear and overheating of the tire" (PDF p. 116); the Honda CB500F owner''s manual — "Inspect the tires for signs of abnormal wear on the contact surface" (PDF p. 60); the Kymco People S 50/125/200 owner''s manual — significant flat spots on the tread are damage: "Replace the tire immediately" (PDF p. 27). No maker''s document in the research library names cupping, feathering or squaring, so none is named here: the makers describe abnormal or uneven wear and name its causes, and the one tread shape a maker names is the flat spot.',
             'Measure the tread depth and look for the tread wear indicators: the BMW F800R rider''s manual reads a tyre as worn out when the tread reaches the marks, located by the letters TI or TWI or by an arrow on the tyre edge (PDF p. 100). The minimum depth is the machine''s own figure: the Honda CB500F owner''s manual sets 1.5 mm front and 2.0 mm rear (PDF p. 134), the Honda PCX150 (2013–2017) service manual the same, measured at the centre of the tread (PDF p. 97), and the KTM EXC TPI manual at least 2 mm (PDF p. 115). Then run a hand and an eye around the whole contact surface and across its profile, and note wear that is not even — across the tread, around the circumference, or different from one side to the other — and where on the tire it sits; a significant flat spot is a replacement finding in the Kymco People S 50/125/200 owner''s manual (PDF p. 27). Record the pressure the tire came in at before letting it down.',
             'Even wear across the profile and around the tire, tread above the machine''s minimum, indicators not reached, no flat spots, pressure at the machine''s figure.',
             'Tread at or below the machine''s minimum or at the indicators, wear that is uneven across or around the tire, a significant flat spot, a tire that came in under pressure.',
             'A new tire does not cure what wore the old one. Start with pressure: the KTM EXC TPI manual ties abnormal wear and overheating to low pressure (PDF p. 116), so the pressure the tire came in at is the first question. Then the wheel: the Kymco Like 150i/50i owner''s manual says proper wheel balance is important to avoid uneven tire wear (PDF p. 53), and the KTM manual warns that spokes with too little tension form lateral and radial run-out in the wheel (PDF p. 116); the balance and fitting items check both while the wheel is off. What the wear says about suspension or alignment is the machine''s service manual''s to answer, not a named pattern''s.',
             1, '["tread depth gauge","tire pressure gauge"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='tire_service_v1'), 2,
             'Damage and age cracking',
             'Cited: the Honda CB500F owner''s manual — inspect "for cuts, slits, or cracks that exposes fabric or cords, or nails or other foreign objects embedded in the side of the tire or the tread" (PDF p. 60); the Yamaha SR400 owner''s manual — "Tires age, even if they have not been used or have only been used occasionally. Cracking of the tread and sidewall rubber, sometimes accompanied by carcass deformation, is an evidence of ageing" (PDF p. 56).',
             'On a tire that stays in service, and on the pair when one is being replaced, work round the whole carcass in good light: tread, shoulders, both sidewalls and the bead area. Look for the CB500F manual''s damage list — cuts, slits and cracks that expose fabric or cords, and nails or other objects embedded in the tread or the side (PDF p. 60). Open the tread grooves and flex the sidewall by hand to see fine cracking in the rubber: the Yamaha SR400 manual makes cracking of the tread and sidewall rubber, sometimes with carcass deformation, the evidence of ageing, and says tires age even when they have hardly been used (PDF p. 56). A low-mileage tire is not a young tire.',
             'No cuts, slits or cracks reaching fabric or cords, nothing embedded, no cracking in the grooves or sidewall, no carcass deformation.',
             'Exposed fabric or cords, an embedded object, cracking in the tread or sidewall rubber, a bulge or deformation of the carcass.',
             'A cracked sidewall is a replacement finding: the Yamaha SR400 manual has the dealer replace the tire immediately (PDF p. 55), and the KTM EXC TPI manual changes tires with cuts, run-in objects or other damage (PDF p. 115). A tire with ageing cracks in the tread goes to a tire specialist to judge whether it can stay in service — the SR400 manual''s words are "Old and aged tires shall be checked by tire specialists to ascertain their suitability for further use" (PDF p. 56). Read its date code (the next item).',
             1, '["flashlight"]', 5),

            ((SELECT id FROM workflow_templates WHERE slug='tire_service_v1'), 3,
             'Date code and age',
             'Cited: the KTM 2022 250/300 EXC TPI owner''s manual — the date of manufacture is "indicated by the last four digits of the DOT number. The first two digits indicate the week of manufacture and the last two digits the year of manufacture", and "KTM recommends that the tires be changed after 5 years at the latest, regardless of the actual state of wear" (PDF p. 116); the Honda CB500F owner''s manual — its example "22 09" is week 22 of 2009 (PDF p. 63), with annual inspections once the tires reach 5 years old and removal from service 10 years after manufacture, regardless of condition or wear (PDF p. 62).',
             'Find the DOT or tire identification number on the sidewall and read its last four digits: the first two are the week and the last two the year of manufacture — the Honda CB500F manual''s example "22 09" is week 22 of 2009 (PDF p. 63; the KTM EXC TPI manual says the same, PDF p. 116). Work out the age of both tires. Then apply the maker''s own line for the machine in hand, because the makers differ: KTM recommends changing its tires after 5 years at the latest, regardless of wear (PDF p. 116); the Honda CB500F manual recommends annual inspection from 5 years and removal from service after 10 years from manufacture, regardless of condition (PDF p. 62). On a new tire, read the code before fitting it.',
             'Both date codes read, both tires inside the age line the machine''s maker sets.',
             'A date code past the maker''s line, an unreadable or missing code, a new tire that has already aged on the shelf.',
             'An old tire with good tread still ages: the makers'' lines apply regardless of wear (KTM EXC TPI manual, PDF p. 116; Honda CB500F manual, PDF p. 62). Record the codes on the job so the next service starts from them.',
             1, '[]', 3),

            ((SELECT id FROM workflow_templates WHERE slug='tire_service_v1'), 4,
             'Tire pressure sensors (TPMS / BMW RDC)',
             'Only for machines with a pressure sensor in the wheel. Cited: the BMW F800R rider''s manual — "each wheel rim bears an adhesive label indicating the position of the RDC sensor", and the fitter must be told the wheel has one (PDF p. 103); readings are temperature-compensated to 20 °C (PDF p. 76); a battery-capacity warning means the sensor''s integral battery has lost much of its capacity (PDF p. 39). The BMW R 1200 GS rider''s manual — sensors do not transmit until the machine has first passed approximately 30 km/h (PDF p. 100).',
             'Before breaking the bead, find the adhesive label on the rim that marks the sensor''s position, and tell whoever mounts the tire that the wheel carries one: the F800R manual warns that incorrect tyre-removal procedures can damage the sensors (PDF p. 103). Break the bead away from the sensor and keep the mounting tools clear of it. After fitting, the display shows "--" for each tyre until the machine has first been ridden above approximately 30 km/h and the first pressure signal arrives (R 1200 GS manual, PDF p. 100). The displayed pressure is corrected to a 20 °C tyre temperature (F800R manual, PDF p. 76), so a warm tire reads differently on a gauge: the R 1200 GS manual has you compare the reading with the table value and correct the difference with the air line (PDF p. 101).',
             'Sensor position marked and respected, sensor undamaged, readings appear after the first ride above about 30 km/h and match the machine''s table.',
             'No reading after a ride, a sensor-failure or battery warning, a reading that does not match the gauge once temperature is accounted for.',
             '"--" straight after a tire change is first the 30 km/h threshold not yet passed (F800R manual, PDF p. 37); then radio interference nearby, a wheel without sensors, a failed sensor (the tire change can damage one, PDF p. 103) or a system error (PDF p. 38). A battery warning means the sensor''s integral battery has lost much of its capacity: not a tire fault, and the manual refers it to a specialist workshop (PDF p. 39).',
             0, '["tire pressure gauge"]', 5),

            ((SELECT id FROM workflow_templates WHERE slug='tire_service_v1'), 5,
             'Fitting the replacement tire',
             'Cited: the KTM 2022 250/300 EXC TPI owner''s manual — "Only mount tires approved and/or recommended by KTM" (PDF p. 115); the Honda CB500F owner''s manual — the recommended tires or equivalents "of the same size, construction, speed rating, and load range" (PDF p. 61), and never a tube inside a tubeless tire (PDF p. 62); the BMW F 800 GS rider''s manual — "Front wheel installed wrong way round" is an accident risk; "Note direction-of-rotation arrows on tyre or rim" (PDF p. 178); the Honda PCX150 (2013–2017) service manual — rim runout service limits 2.0 mm axial and 2.0 mm radial (PDF p. 326).',
             'Check the new tire against the machine''s own manual: the KTM EXC TPI manual allows only tires KTM approves or recommends (PDF p. 115), and the Honda CB500F manual the recommended tires or equivalents of the same size, construction, speed rating and load range (PDF p. 61). Never fit a tube inside a tubeless tire on a tubeless rim — the CB500F manual warns the tube can burst from heat build-up (PDF p. 62). Mount the tire with its direction-of-rotation arrow running the way the wheel turns, and refit the wheel the right way round: the BMW F 800 GS manual names a front wheel installed the wrong way round as an accident risk (PDF p. 178). While the wheel is off, spin the rim on a stand against a dial indicator: actual runout is half the total indicator reading, and the Honda PCX150 service manual''s limits are 2.0 mm axial and 2.0 mm radial (PDF p. 326), as are the Kymco People / People S 250''s (service manual PDF p. 188) — for other machines, their own manual''s figure.',
             'The tire the maker approves or an equivalent of the same size, construction, speed rating and load range; tubeless on tubeless; arrow with the direction of rotation; rim runout within the machine''s limit.',
             'A different size, speed rating or load range; a tube in a tubeless tire; the arrow backwards; rim runout over the limit.',
             'A rim over its runout limit is a wheel problem a new tire will not hide: on a laced wheel, true it or check the spokes (the KTM EXC TPI manual''s run-out warning, PDF p. 116); on a cast wheel, the machine''s manual decides repair or replacement.',
             1, '["tire irons or changer","rim protectors","dial indicator","wheel stand"]', 20),

            ((SELECT id FROM workflow_templates WHERE slug='tire_service_v1'), 6,
             'Balance',
             'Cited: the Honda CB500F owner''s manual — "Have the wheel balanced with Honda Genuine balance weights or equivalent after the tire is installed" (PDF p. 62); the Yamaha XC50J owner''s manual — "The wheel should be balanced whenever either the tire or wheel has been changed or replaced" (PDF p. 51); the BMW S 1000 XR rider''s manual — permissible imbalance front max 5 g (PDF p. 205), rear max 45 g (PDF p. 206), balance weight max 80 g, one half on the left and one half on the right of the rim (PDF pp. 205–206).',
             'Balance every wheel that has had its tire or the wheel itself changed — the Honda and Yamaha manuals both call for it (CB500F PDF p. 62; XC50J PDF p. 51), and the Kymco Like 150i/50i manual gives the reason: proper wheel balance avoids uneven tire wear (PDF p. 53). Use the maker''s balance weights or equivalent. Where the machine''s manual sets limits, balance to them: the BMW S 1000 XR''s are a permissible imbalance of 5 g at the front and 45 g at the rear, with no more than 80 g of weight, split half on each side of the rim (PDF pp. 205–206). Clean the rim where adhesive weights go, and fit them where they cannot touch the brake disc or caliper.',
             'Balanced to the machine''s limit, weights secure and clear of the brake.',
             'A wheel that will not come into balance, weight needed beyond the machine''s maximum, weights touching the brake.',
             'A wheel that needs more than the maker''s maximum weight to balance, or will not balance at all, is telling you about the rim or the tire''s seating: re-seat the bead and re-check rim runout before adding weight.',
             1, '["wheel balancer","balance weights"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='tire_service_v1'), 7,
             'Pressure, bead check and run-in',
             'Cited: the BMW F800R rider''s manual — "New tyres have a smooth surface. This must be roughened by riding in a restrained manner at various heel angles until the tyres are run in" (PDF p. 67); the BMW R 1200 GS rider''s manual — "New tyres do not provide full grip straight away" (PDF p. 85).',
             'Set the cold pressure to the machine''s own figure — its manual or the label on the machine, for example 2.5 bar front and 2.9 bar rear, tyre cold, on the BMW F800R (rider''s manual PDF p. 134) — and check the bead line sits evenly round both sides of the rim. Tell the rider how to run the new tires in: the F800R manual has the smooth new surface roughened by riding in a restrained manner at various lean angles (PDF p. 67), and the R 1200 GS manual warns that new tyres do not give full grip straight away, and that "Wet roads and extremely sharp inclines pose a risk of accident" (PDF p. 85).',
             'Cold pressures at the machine''s figures, even bead line both sides, the rider told about run-in.',
             'Pressure off the machine''s figure, an uneven bead line, a machine handed back without the run-in warning.',
             'An uneven bead line means the tire is not seated: let it down, lubricate the bead and re-seat it before the machine leaves.',
             1, '["tire pressure gauge"]', 5),

            -- --------------------------------------------------- brake_service_v1
            ((SELECT id FROM workflow_templates WHERE slug='brake_service_v1'), 1,
             'Pads — measure, and replace in pairs',
             'Figures are the named machine''s own. Cited: KTM 2022 250/300 EXC TPI owner''s manual — lining minimum thickness at least 1 mm (PDF p. 102), linings always changed in pairs, and while pushing the pistons back "Ensure that brake fluid does not flow out of the brake fluid reservoir" (PDF p. 104); BMW F800R rider''s manual — pad wear limit min 1.0 mm, "Friction pad only, without backing plate. The wear indicators (grooves) must be clearly visible" (PDF p. 94); Yamaha YW125Y 2009 service manual — pad wear limit 0.8 mm (PDF p. 134); Piaggio Beverly 125 service manual — pad minimum 1.5 mm (PDF p. 196); Honda CB500F owner''s manual — "Always replace both left and right brake pads at the same time" (PDF p. 77).',
             'Measure every pad the way the machine''s manual defines its limit: the BMW F800R''s 1.0 mm is friction material only, without the backing plate, with the grooves still clearly visible (PDF p. 94); the KTM EXC TPI''s at least 1 mm (PDF p. 102), the Yamaha YW125Y''s 0.8 mm (PDF p. 134) and the Piaggio Beverly 125''s 1.5 mm (PDF p. 196) are measured as each manual''s own figure shows. Replace pads as a set — the KTM manual changes linings in pairs (PDF p. 104) and the Honda CB500F owner''s manual replaces left and right pads at the same time (PDF p. 77). Before pressing the pistons back to make room, open or watch the reservoir: the KTM manual has you extract fluid if necessary so it cannot overflow (PDF p. 104). Check that the pads slide freely on their pins and that the pins and springs are sound.',
             'Every pad above the machine''s limit as its manual measures it, or new pads fitted as a set; pistons pushed back without overflowing the reservoir.',
             'Any pad at or under its limit, grooves worn away, pads contaminated with fluid or oil, uneven wear between the pads of one caliper.',
             'Pads contaminated with brake fluid are not cleaned: the Piaggio Beverly manual has them replaced and the disc cleaned with a high-quality solvent (PDF p. 190), and the leak found. Uneven wear between the two pads of one caliper points at a sticking piston or slide: go to the caliper item.',
             1, '["vernier caliper","flashlight"]', 15),

            ((SELECT id FROM workflow_templates WHERE slug='brake_service_v1'), 2,
             'Discs — thickness and runout',
             'Figures are the named machine''s own. Cited: KTM 2022 250/300 EXC TPI owner''s manual — disc wear limits for the standard models front 2.5 mm, rear 3.5 mm (PDF p. 100); Honda PCX150 (2013–2017) service manual — disc thickness service limit 3.0 mm, warpage service limit 0.30 mm, and over the warpage limit "check the wheel bearings for excessive play" (PDF p. 371); Yamaha YW125Y 2009 service manual — thickness minimum 3.5 mm, deflection maximum 0.15 mm (PDF p. 119); Kymco People / People S 250 service manual — thickness 4.0 mm standard, 3.0 mm limit, runout 0.30 mm (PDF p. 184); Piaggio Beverly 125 service manual — the axial run-out checked with the wheel removed, and "THOROUGHLY CLEAN THE DISC AND ITS SEAT ON THE HUB" (PDF p. 196).',
             'Measure the disc thickness with a micrometer at several points round the swept area, and check the runout with a dial indicator set up as the machine''s manual describes (the Piaggio Beverly 125 removes the wheel, PDF p. 196). Compare with the machine''s own limits: the KTM EXC TPI standard models'' discs wear to 2.5 mm front and 3.5 mm rear (PDF p. 100); the Honda PCX150 disc to 3.0 mm, with 0.30 mm warpage (PDF p. 371); the Yamaha YW125Y disc to 3.5 mm, with 0.15 mm deflection (PDF p. 119); the Kymco People / People S 250 disc from 4.0 mm new to 3.0 mm, with 0.30 mm runout (PDF p. 184). Inspect the friction surface for deep scoring, cracks and heat discolouration.',
             'Thickness above the machine''s limit at every point, runout inside its limit, no cracks or deep scoring.',
             'Thickness under the machine''s limit anywhere, runout over the limit, cracks, deep scoring.',
             'A disc under its thickness limit is replaced. With warpage over the limit, the Honda PCX150 manual has the wheel bearings checked for excessive play (PDF p. 371); the Piaggio Beverly replaces a disc over its run-out limit and repeats the test, and when installing a disc cleans it and its seat on the hub thoroughly (PDF p. 196).',
             1, '["micrometer","dial indicator"]', 15),

            ((SELECT id FROM workflow_templates WHERE slug='brake_service_v1'), 3,
             'Caliper overhaul — pistons and seals',
             'When a caliper leaks, a piston sticks or the seals are due. Cited: Yamaha YW125Y 2009 service manual — "Whenever a brake caliper is disassembled, replace the piston seal and dust seal" (PDF p. 146), its component schedule: piston seal every two years, brake hose every four (PDF p. 146), "Never use solvents on internal brake components", and piston seals lubricated with brake fluid, dust seals with silicone grease (PDF p. 147); Honda PCX150 (2013–2017) service manual — caliper cylinder I.D. service limits 25.460 mm upper and 22.710 mm centre/lower, piston O.D. 25.31 mm upper and 22.56 mm centre/lower (PDF p. 384); Kymco People / People S 250 service manual — piston O.D. limit 25.30 mm, silicone grease on the piston and oil seal (PDF p. 194); Piaggio Beverly 125 service manual — reused parts cleaned with denatured alcohol (PDF p. 190), every seal replaced when the caliper is serviced (PDF p. 193), a scratched cylinder means the entire caliper (PDF p. 192).',
             'Drain the system and remove the pistons (the Yamaha YW125Y service manual drains the whole system first and blows the pistons out with compressed air at the hose joint, PDF p. 145), then the piston seals and dust seals. Clean the bores and grooves with what the machine''s manual specifies: the YW125Y uses clean brake fluid and forbids solvents on internal brake components because they make the piston seal swell and distort (PDF p. 147); the Piaggio Beverly 125 cleans reused parts with denatured alcohol, rubber parts no longer than 20 seconds (PDF p. 190). Inspect the pistons and bores for scoring and corrosion, and measure them against the machine''s own limits: the Honda PCX150''s three-piston caliper has cylinder I.D. limits of 25.460 mm (upper) and 22.710 mm (centre/lower) and piston O.D. limits of 25.31 mm (upper) and 22.56 mm (centre/lower) (PDF p. 384); the Kymco People / People S 250''s piston O.D. limit is 25.30 mm (service manual PDF p. 194). Fit new piston seals and dust seals every time — the YW125Y manual''s rule (PDF p. 146) and the Piaggio Beverly''s, which replaces all seals every time the caliper is serviced (PDF p. 193) — and lubricate them as the machine''s manual says: the YW125Y puts brake fluid on the piston seals and silicone grease on the dust seals (PDF p. 147), while the Kymco puts silicone grease on the piston and oil seal (PDF p. 194).',
             'Bores and pistons clean, unscored and inside the machine''s limits; new piston and dust seals fitted and lubricated as the manual specifies.',
             'Scored or corroded pistons or bores, a dimension past its limit, old seals refitted, a cleaning agent the manual does not allow.',
             'A piston past its limit is replaced; a cylinder past its limit or scratched means a new caliper assembly (Yamaha YW125Y, PDF p. 146; Piaggio Beverly, PDF p. 192). The YW125Y manual''s schedule is its maker''s answer to "when": piston seals every two years, the hose every four, the fluid every two years and whenever the brake is disassembled (PDF p. 146).',
             0, '["brake fluid","silicone grease","micrometer","bore gauge"]', 40),

            ((SELECT id FROM workflow_templates WHERE slug='brake_service_v1'), 4,
             'Master cylinder',
             'When the lever sinks, the master cylinder leaks, or the seals are due. Cited: Honda PCX150 (2013–2017) service manual — front brake master cylinder I.D. service limit 12.755 mm, master piston O.D. 12.645 mm (PDF p. 373); its CBS master cylinder I.D. 11.055 mm and piston O.D. 10.945 mm (PDF p. 363); "Keep the piston, cups, spring, snap ring and boot as a set; do not substitute individual parts" (PDF p. 374); Kymco People / People S 250 service manual — cylinder I.D. limit 12.75 mm, the main piston and spring installed as a unit (PDF p. 191); Piaggio Beverly 125 service manual — all seals and gaskets replaced every time the pump is serviced (PDF p. 201).',
             'Drain the system, remove the master cylinder, and take out the boot, snap ring, piston, cups and spring. Clean as the machine''s manual specifies, inspect the bore for scratches and corrosion, and measure against the machine''s own limits — the Honda PCX150''s front brake master cylinder I.D. 12.755 mm and piston O.D. 12.645 mm (PDF p. 373), while its CBS master cylinder has its own, 11.055 mm and 10.945 mm (PDF p. 363); the Kymco People / People S 250''s cylinder I.D. 12.75 mm (service manual PDF p. 191). Keep the piston, cups, spring, snap ring and boot as a set, never mixed with other parts (PCX150, PDF p. 374; the Kymco installs the main piston and spring as a unit, PDF p. 191), and fit every seal new (Beverly, PDF p. 201).',
             'Bore clean and inside its limit; the piston parts fitted as a set, never mixed; every seal new.',
             'A scratched or corroded bore, a dimension past its limit, individual parts mixed into an old set.',
             'A master cylinder past its bore limit is replaced. After any master-cylinder work the whole circuit is bled (the bleeding item).',
             0, '["brake fluid","bore gauge","micrometer"]', 30),

            ((SELECT id FROM workflow_templates WHERE slug='brake_service_v1'), 5,
             'Brake fluid — type, age and change',
             'Cited: KTM 2022 250/300 EXC TPI owner''s manual — "Never use DOT 5 brake fluid. It is silicone-based", "Brake fluid attacks paint", and spills cleaned up immediately with water (PDF p. 102); DOT 4 / DOT 5.1 specified (PDF p. 170); Honda CB500F owner''s manual — brake fluid every 2 years (PDF p. 49), Honda DOT 4 or equivalent, and it can damage plastic and painted surfaces (PDF p. 57); Honda PCX150 (2013–2017) service manual — fresh DOT 3 or DOT 4 from a sealed container, and do not mix types (PDF p. 363); Piaggio Beverly 125 service manual — the fluid is hygroscopic (PDF p. 48), changed every 20,000 km or every two years under normal climatic conditions (PDF p. 49) and more often under intense or harsh use (PDF p. 190); Yamaha YW125Y 2009 service manual — water "will significantly lower the boiling point of the brake fluid and could cause vapor lock", and other brake fluids may make the rubber seals deteriorate (PDF p. 89).',
             'Read the fluid type off the reservoir cap or the machine''s manual and use only that — the KTM EXC TPI specifies DOT 4 / DOT 5.1 and forbids silicone DOT 5 (PDF pp. 102, 170); the Honda CB500F Honda DOT 4 or equivalent (PDF p. 57). Use fresh fluid from a sealed container and never mix types (Honda PCX150, PDF p. 363). Change it on the maker''s interval whatever it looks like: the fluid absorbs moisture from the air (Piaggio Beverly, PDF p. 48), and water lowers its boiling point and can cause vapor lock (Yamaha YW125Y, PDF p. 89) — every 2 years on the Honda CB500F (PDF p. 49); on the Beverly every 20,000 km or two years under normal conditions, and more often under intense or harsh use (PDF pp. 49, 190). Keep fluid off painted and plastic parts, and wipe up any spill at once and wash it off with water (CB500F, PDF p. 57; KTM, PDF p. 102).',
             'The specified fluid, fresh from a sealed container, changed inside the maker''s interval, no spill on paint or plastic.',
             'The wrong fluid type, mixed fluids, fluid past the maker''s interval, fluid on paint.',
             'Fluid past its interval is changed and the system bled. A wrong or silicone fluid is flushed out and the rubber parts inspected and renewed — this remedy is the template''s own; the makers'' reasons are that the KTM''s oil seals and brake lines are not designed for DOT 5 (PDF p. 102) and that other fluids may make the Yamaha YW125Y''s rubber seals deteriorate (PDF p. 89).',
             1, '["brake fluid","clear hose","catch bottle"]', 20),

            ((SELECT id FROM workflow_templates WHERE slug='brake_service_v1'), 6,
             'Bleeding',
             'Cited: Honda PCX150 (2013–2017) service manual — "Once the hydraulic system has been opened, or if the brake feels spongy, the system must be bled" (PDF p. 363); the sequence: squeeze the lever all the way, open the bleed valve 1/2 of a turn, close it, release the lever slowly, repeat until there are no air bubbles in the bleed hose, checking the fluid level often; bleed valve 5.4 N·m (PDF p. 367); Yamaha YW125Y 2009 service manual — "If bleeding is difficult, it may be necessary to let the brake fluid settle for a few hours" (PDF p. 91); bleed screw 6 Nm (PDF p. 92); Piaggio Beverly 125 service manual — if air keeps coming out, examine all the fittings, then the seals of the pump and caliper pistons (PDF p. 199).',
             'Bleed whenever the circuit has been opened or the lever feels spongy (Honda PCX150, PDF p. 363). Check the fluid level often while bleeding so no air is pumped into the system (PCX150, PDF p. 367). With a clear hose from the bleed valve into a catch bottle: squeeze the lever all the way, loosen the bleed valve half a turn, wait, close it, release the lever slowly, and repeat until there are no air bubbles in the bleed hose (PCX150, PDF p. 367). Tighten the bleed valve to the machine''s own torque — 5.4 N·m on the Honda PCX150 (PDF p. 367), 6 Nm on the Yamaha YW125Y (PDF p. 92). If the bubbles will not stop, let the fluid settle for a few hours and bleed again (YW125Y, PDF p. 91). Top up to the level mark and refit the cap.',
             'No air bubbles in the bleed hose; bleed valves at their torque; reservoir at the level mark; a firm lever.',
             'Bubbles that will not clear, a lever that stays spongy, a weeping bleed valve.',
             'If air keeps coming out, examine every fitting, then the seals of the master cylinder and caliper pistons for where it is getting in (Piaggio Beverly, PDF p. 199). A lever that stays soft after a careful bleed may have air trapped high in the system: let the fluid settle and bleed again (YW125Y, PDF p. 91), then go to the master-cylinder item.',
             1, '["clear hose","catch bottle","ring spanner","torque wrench"]', 20),

            ((SELECT id FROM workflow_templates WHERE slug='brake_service_v1'), 7,
             'Reassembly torques, pressure point and bedding-in',
             'Figures are the named machine''s own. Cited: KTM 2022 250/300 EXC TPI owner''s manual — front caliper screw M8 25 Nm with Loctite 243 (PDF p. 69); operate the hand brake lever (PDF p. 104) and the foot brake lever (PDF p. 109) "repeatedly until the brake linings are in contact with the brake disc and there is a pressure point"; BMW F800R rider''s manual — brake caliper on fork leg 30 Nm (PDF p. 106), and "New brake pads have to bed down before they can achieve their optimum friction levels" (PDF p. 67); Honda PCX150 (2013–2017) service manual — caliper mounting bolt 30 N·m, ALOC bolts replaced with new ones (PDF p. 21); Kymco People / People S 250 service manual — caliper bolts 29–35 N·m (PDF p. 195).',
             'Torque every caliper and mounting bolt to the machine''s own figure and thread-locker: the KTM EXC TPI''s front caliper screw is 25 Nm with Loctite 243 (PDF p. 69); the BMW F800R''s caliper on the fork leg 30 Nm (PDF p. 106); the Honda PCX150''s caliper mounting bolts 30 N·m, and its ALOC bolts are replaced with new ones (PDF p. 21); the Kymco People / People S 250''s 29–35 N·m (service manual PDF p. 195). Before the machine moves, pump the lever and pedal until the pads meet the disc and there is a firm pressure point (KTM, PDF pp. 104, 109). Spin each wheel to check the brake releases. Tell the rider that new pads must bed in and will stop longer until they do (F800R, PDF p. 67).',
             'All fasteners at their torque with the specified thread-locker, a firm pressure point before moving, wheels free, rider told about bedding-in.',
             'A fastener untorqued or reused where the maker says new, no pressure point, a dragging brake.',
             'A brake that drags after reassembly has a piston or slide that has not returned, or pads fitted without freeing the pins; go back to the caliper item before the machine leaves.',
             1, '["torque wrench","thread-locker"]', 15),

            -- ---------------------------------------------- suspension_service_v1
            ((SELECT id FROM workflow_templates WHERE slug='suspension_service_v1'), 1,
             'Record the settings and measure sag',
             'Figures are the named machine''s own. Cited: KTM 2022 250/300 EXC TPI owner''s manual — "first adjust the shock absorber and then the fork" (PDF p. 55); the sag gauge at the rear axle to the SAG marking (PDF p. 57); static sag 37 mm and riding sag 110 mm, the rider in full protective clothing bouncing a few times, feet on the footrests, and static sag corrected by the shock''s spring preload (PDF p. 58); riding sag corrected by choosing a suitable spring, and "no exact riding sag can be determined for the fork" (PDF p. 60); 2010 KTM 690 Enduro owner''s manual — static sag 25 mm (PDF p. 73), riding sag 70–80 mm (PDF p. 74).',
             'Before touching anything, write down every clicker, preload and ride-height setting as found, counted from the maker''s reference position. Then measure the rear sag the maker''s way: the KTM EXC TPI manual takes a reading at the rear axle unloaded, one with the machine on its own weight (static sag), and one with the rider in full protective clothing aboard, feet on the footrests, after bouncing a few times (riding sag), each the difference from the unloaded reading (PDF pp. 57–58). Compare with the machine''s own figures — the KTM EXC TPI''s static sag 37 mm and riding sag 110 mm (PDF p. 58); the 2010 KTM 690 Enduro''s 25 mm and 70–80 mm (PDF pp. 73–74). Set the shock before the fork, the KTM manual''s order (PDF p. 55); the fork has no exact riding-sag figure (PDF p. 60).',
             'Settings recorded as found; static and riding sag measured and compared with the machine''s figures.',
             'Settings changed before they were recorded; sag outside the machine''s figures.',
             'The KTM EXC TPI manual corrects static sag with the shock''s spring preload (PDF p. 58) and riding sag by choosing a suitable spring (PDF p. 60): riding sag that stays wrong once static sag is right means the wrong spring for the rider (the next item).',
             1, '["sag gauge or tape measure","helper"]', 20),

            ((SELECT id FROM workflow_templates WHERE slug='suspension_service_v1'), 2,
             'Spring rate for the rider',
             'Figures are the named machine''s own. Cited: KTM 2022 250/300 EXC TPI owner''s manual — the standard rider weight is 75–85 kg, and "Small weight differences can be compensated by adjusting the spring preload, but in the case of large weight differences, the springs must be replaced" (PDF p. 55); its spring tables by rider weight for 65–75 / 75–85 / 85–95 kg: fork 4.2 / 4.4 / 4.6 N/mm (PDF p. 166), shock 57–63 / 60–66 / 63–69 N/mm (PDF pp. 60, 166); a fork that frequently bottoms out needs harder springs (PDF p. 60); 2010 KTM 690 Enduro owner''s manual — fork 5.2 / 5.4 / 5.6 N/mm for the same weights on the 690 Enduro (PDF p. 183), one 5.2 N/mm spring on the 690 Enduro R (PDF p. 184).',
             'Weigh the rider in full riding gear. Look up the machine''s own spring table where its maker publishes one — for riders of 65–75, 75–85 and 85–95 kg the KTM EXC TPI''s fork springs are 4.2, 4.4 and 4.6 N/mm (PDF p. 166) and its shock springs 57–63, 60–66 and 63–69 N/mm (PDF pp. 60, 166); the 2010 KTM 690 Enduro''s (not the Enduro R''s) fork springs 5.2, 5.4 and 5.6 N/mm (PDF p. 183). Read the rate on the spring fitted — the KTM manual notes that the shock spring''s rate is shown on its outside (PDF p. 60). Inside the standard band (75–85 kg on the KTM EXC TPI) the stock springs are right; a small difference outside it is taken up by preload, a large one by changing the springs (PDF p. 55). A fork that frequently bottoms out needs harder springs (PDF p. 60). Where the maker publishes no table, its own spring specification is the reference, and it may offer no alternative: the Yamaha YW125Y service manual gives its fork spring as two rates, 7.1 N/mm (K1) and 15.4 N/mm (K2), with no optional spring available (PDF p. 34).',
             'The fitted springs match the rider''s weight in the machine''s table, or the difference is small enough for preload.',
             'Springs far from the rider''s band, a fork that bottoms, preload wound to its end to hold the sag.',
             'Preload does not change the spring''s rate. The KTM manual''s rule is that small weight differences are taken up by preload and large ones by changing the springs (PDF p. 55), so a spring that needs its preload at the end of the adjuster to make sag belongs to a different rider.',
             1, '["scale for the rider"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='suspension_service_v1'), 3,
             'Fork oil — drain, quantity and level',
             'For oil-damped forks: some scooter forks, such as the Honda CHF50''s, are lubricated with grease, and its service manual gives no fork-oil figure (PDF pp. 226–227). Figures are the named machine''s own. Cited: KTM 2022 250/300 EXC TPI owner''s manual — fork oil per leg 636 ± 10 ml, SAE 4 (PDF p. 166); 2010 KTM 690 Enduro owner''s manual — 620 ml per leg, SAE 5, on the 690 Enduro (PDF p. 183), 635 ml on the Enduro R (PDF p. 184); Honda PCX150 (2013–2017) service manual — Pro Honda Suspension Fluid SS-8 or equivalent, capacity 122.0 ± 2.5 cm³, level 75 mm measured from the top of the fork pipe with the leg fully compressed, pump the fork pipe to remove trapped air, and the same level in both forks (PDF p. 335); Yamaha YW125Y 2009 service manual — 0.104 L per leg of 10W fork oil (PDF p. 160), levels in both legs equal, because uneven levels mean poor handling and a loss of stability (PDF p. 158), stroke the outer tube while draining (PDF p. 155).',
             'Drain each leg completely, stroking the tube several times while it drains (Yamaha YW125Y, PDF p. 155). Refill with the machine''s own oil grade and quantity — 636 ± 10 ml of SAE 4 per leg on the KTM EXC TPI (PDF p. 166); 620 ml of SAE 5 on the 2010 KTM 690 Enduro (PDF p. 183; 635 ml on the Enduro R, PDF p. 184); 122.0 ± 2.5 cm³ of Pro Honda Suspension Fluid SS-8 or equivalent on the Honda PCX150 (PDF p. 335); 0.104 L of 10W on the Yamaha YW125Y (PDF p. 160). Pump the leg slowly to purge the air, then set the level where the manual gives one, under its own measuring condition — the Honda PCX150''s is 75 mm from the top of the fork pipe with the leg fully compressed (PDF p. 335) — and make both legs equal (YW125Y, PDF p. 158; PCX150, PDF p. 335).',
             'Both legs drained, refilled with the specified grade and quantity, air purged, levels equal and at the machine''s figure.',
             'A grade or quantity other than the machine''s, unequal legs, trapped air.',
             'Uneven oil levels mean poor handling and a loss of stability (Yamaha YW125Y, PDF p. 158): set them equal. Oil that came out dark, milky or full of metal points at the seal item and at wear inside the leg — this reading is the template''s own, not a maker''s.',
             0, '["fork oil","measuring cylinder","fork oil level tool"]', 45),

            ((SELECT id FROM workflow_templates WHERE slug='suspension_service_v1'), 4,
             'Fork seals, dust wipers and springs',
             'Figures are the named machine''s own. Cited: Yamaha YW125Y 2009 service manual — "Never reuse the oil seal" (PDF p. 156); lubricate the new seal lips, and fit it numbered side up (PDF p. 159); spring free length 252.1 mm, limit 247 mm, and an inner tube with bends, damage or scratches replaced (PDF p. 157); Honda PCX150 (2013–2017) service manual — fork fluid on the new oil-seal and dust-seal lips, and the stopper ring in its groove (PDF p. 334); KTM 2022 250/300 EXC TPI owner''s manual — dirt behind the dust boots, if not removed, makes the oil seals leak (PDF p. 67); Honda CHF50 service manual — fork spring free length service limit 125.9 mm (PDF p. 227).',
             'On a fork with oil seals, fit new ones whenever they come out — the Yamaha YW125Y manual never reuses them (PDF p. 156) — with new dust seals. Lubricate the new lips as the manual says (lithium soap base grease on the YW125Y, PDF p. 159; fork fluid on the Honda PCX150, PDF p. 334), drive the seal in square with the numbered side up (YW125Y, PDF p. 159), and seat the stopper ring in its groove (PCX150, PDF p. 334). While the leg is apart, inspect the inner and outer tubes for bends, damage and scratches — the YW125Y manual replaces either and warns never to straighten a bent inner tube (PDF p. 157) — and measure the spring free length against the machine''s limit — the YW125Y''s 252.1 mm standard and 247 mm limit (PDF p. 157); the Honda CHF50''s 125.9 mm limit (PDF p. 227). On every service, clean behind the dust boots: the KTM EXC TPI manual says dirt left there makes the seals leak (PDF p. 67).',
             'New seals and wipers fitted square with the right side up, stopper rings seated, tubes smooth, springs above their limit, dust boots clean.',
             'A reused seal, a bent, damaged or scratched tube, a spring under its free-length limit.',
             'A new seal on a scratched tube leaks again: the YW125Y manual replaces an inner tube with bends, damage or scratches (PDF p. 157). A spring under its free-length limit is replaced.',
             1, '["seal driver","lithium soap base grease or fork oil"]', 60),

            ((SELECT id FROM workflow_templates WHERE slug='suspension_service_v1'), 5,
             'Fork air bleed',
             'Only for forks with bleeder screws. Cited: KTM 2022 250/300 EXC TPI owner''s manual — "If the fork feels unusually hard after extended periods of operation, the fork legs need to be bled" (PDF p. 60); the bleeding procedure on a lift stand with neither wheel on the ground: release the bleeder screws, "Any excess pressure escapes from the interior of the fork", tighten them (PDF p. 66); 2010 KTM 690 Enduro owner''s manual — bleeding the fork legs with the machine leaning on its side stand (PDF p. 75), the excess pressure escaping (PDF p. 76).',
             'Set the machine as its maker says: the KTM EXC TPI on a lift stand with neither wheel touching the ground (PDF p. 66); the 2010 KTM 690 Enduro leaning on its side stand (PDF p. 75). Release each fork leg''s bleeder screw briefly so the excess pressure escapes from inside the fork, then tighten it (KTM EXC TPI, PDF p. 66; 690 Enduro, PDF p. 76). Do both legs.',
             'Both legs bled, the fork''s action as soft at the end of a ride as at the start.',
             'A fork that stiffens over a ride and softens after bleeding.',
             'KTM lists bleeding the fork legs among its checks before every trip (PDF p. 46), and calls for it when the fork feels unusually hard after extended periods of operation (PDF p. 60). A fork that stays hard after bleeding goes to the fork-oil and seal items.',
             0, '[]', 5),

            ((SELECT id FROM workflow_templates WHERE slug='suspension_service_v1'), 6,
             'Rear shock — service or replace',
             'Service policy differs by shock, and the machine''s own maker decides. Cited: KTM 2022 250/300 EXC TPI owner''s manual — "Perform the shock absorber service" in its service schedule (PDF p. 53); "The shock absorber is filled with highly compressed nitrogen", and "Your authorized KTM workshop will be glad to help" (PDF p. 55); gas pressure 10 bar and shock fluid SAE 2.5 (PDF p. 167); Honda XR650L owner''s manual — to the owner: the damper unit "contains high pressure nitrogen gas. Do not attempt to disassemble, service, or improperly dispose of the damper. See your dealer." (PDF p. 85); Yamaha YW125Y 2009 service manual — rear shock oil leaks: "Replace the rear shock absorber assembly" (PDF p. 175); Honda PCX150 (2013–2017) service manual — compress the shock several times and check the whole assembly for leaks, damage and loose fasteners (PDF p. 95).',
             'Compress the shock several times and check the whole assembly for oil on the shaft or body, damage and loose fasteners (Honda PCX150, PDF p. 95). Then follow the machine''s own maker: KTM schedules a shock absorber service (PDF p. 53) on a nitrogen-charged unit at 10 bar with SAE 2.5 fluid (PDF pp. 55, 167), and points the owner to its authorised workshop (PDF p. 55); Honda''s XR650L owner''s manual tells the owner not to disassemble, service or improperly dispose of the damper, which holds high-pressure nitrogen, and to see the dealer (PDF p. 85) — Honda''s workshop procedure is in its service manual, which is not in the research library; Yamaha''s YW125Y service manual replaces a leaking rear shock as an assembly (PDF p. 175). Never open a gas-charged shock without the maker''s procedure and the equipment to depressurise and recharge it.',
             'A dry, undamaged shock with a smooth action; or a serviceable shock serviced to its maker''s figures; or a sealed one replaced.',
             'Oil on the shaft or body, a knock or dead spot in the stroke, a damper opened against its maker''s instruction.',
             'Where the maker''s manual replaces a leaking shock as an assembly, it is replaced, not rebuilt (Yamaha YW125Y, PDF p. 175); an XR650L owner is sent to the dealer (PDF p. 85). A shock its maker services goes to a workshop that can charge nitrogen, filled to the maker''s gas pressure and fluid (KTM EXC TPI, PDF pp. 53, 167).',
             1, '[]', 30),

            ((SELECT id FROM workflow_templates WHERE slug='suspension_service_v1'), 7,
             'Damping and preload back to base',
             'Figures are the named machine''s own. Cited: KTM 2022 250/300 EXC TPI owner''s manual — clickers counted out from fully clockwise, "as far as the last perceptible click" (PDF p. 56); shock standard low-speed compression 15 clicks, high-speed compression 2 turns (PDF p. 56), rebound 15 clicks (PDF p. 57), spring preload 9 mm (PDF p. 59); 2010 KTM 690 Enduro owner''s manual — its guideline settings are in a table under the seat, and "Do not change the adjustments at random or by more than ± 40%" (PDF p. 64); Honda CB500F owner''s manual — rear preload adjuster 9 positions, standard 4 with the index mark aligned with the left end of the lower mounting bolt, and "Attempting to adjust directly from 1 to 9 or 9 to 1 may damage the shock absorber" (PDF p. 92).',
             'Return every adjuster to the machine''s standard, counted the maker''s way, before any rider-specific change — the KTM EXC TPI counts its clickers out from fully clockwise (PDF p. 56), and its shock''s standard is 15 clicks low-speed compression, 2 turns high-speed compression (PDF p. 56), 15 clicks rebound (PDF p. 57) and 9 mm spring preload (PDF p. 59); the Honda CB500F''s rear preload standard is position 4 of 9, with the index mark at the left end of the lower mounting bolt, and its manual warns that adjusting directly from 1 to 9 or 9 to 1 may damage the shock absorber (PDF p. 92). On the 2010 KTM 690 Enduro, do not change the adjustments at random or by more than ± 40 % from the guideline settings in the table under its seat (PDF p. 64). Record the final settings on the job.',
             'Every adjuster at the machine''s standard or a recorded change from it; nothing forced past its stop.',
             'Settings unknown, an adjuster forced past its limit, the CB500F''s preload jumped from 1 to 9 or back.',
             'If the machine only feels right far from its standard settings, go back to the spring-rate and shock items rather than winding the adjusters further — this advice is the template''s own.',
             1, '["screwdriver","pin spanner"]', 10),

            -- ---------------------------------------------- drivetrain_service_v1
            ((SELECT id FROM workflow_templates WHERE slug='drivetrain_service_v1'), 1,
             'Chain drive — slack',
             'Chain-drive machines. Figures are the named machine''s own, and each belongs to its own way of measuring. Cited: KTM 2022 250/300 EXC TPI owner''s manual — chain tension 55–58 mm, measured with the motorcycle raised on a lift stand (PDF p. 89) by pulling the chain upward at the end of the chain sliding piece with the lower run taut, repeated at different chain positions because wear is not even (PDF p. 90); too tight wears the chain, sprockets, transmission and rear wheel bearings faster, too loose and "the chain may fall off" (PDF p. 89); Honda CB500F owner''s manual — on the side stand in neutral, slack of the lower run midway between the sprockets 35–45 mm, never ridden over 60 mm, checked at several points: "If the slack is not constant at all points, some links may be kinked and binding" (PDF p. 80); BMW F800R rider''s manual — chain deflection 30–40 mm, the chain pushed up and down at the position with the least sag, the machine on its side stand with no weight applied (PDF p. 101).',
             'Measure the machine''s maker''s way, because the three figures below measure different things and cannot be compared across machines. On the KTM EXC TPI, raised on a lift stand (PDF p. 89), pull the chain upward at the end of the chain sliding piece with the lower run taut, at several chain positions: 55–58 mm (PDF p. 90). On the Honda CB500F, in neutral on its side stand, measure the slack of the lower run midway between the sprockets at several points: 35–45 mm, and never ridden over 60 mm (PDF p. 80). On the BMW F800R, on its side stand with no weight applied, turn the wheel to the position with the least sag and push the chain up and down: 30–40 mm deflection (PDF p. 101).',
             'Tension, slack or deflection inside the machine''s range, measured its maker''s way, and constant where the maker checks several points.',
             'Out of the machine''s range, or not constant from point to point round the chain.',
             'Slack that is not constant means some links may be kinked and binding (Honda CB500F, PDF p. 80) or uneven wear: go to the wear item. Too tight is as harmful as too loose — the KTM manual lists faster wear of the chain, sprockets, transmission and rear wheel bearings (PDF p. 89).',
             0, '["ruler"]', 5),

            ((SELECT id FROM workflow_templates WHERE slug='drivetrain_service_v1'), 2,
             'Chain drive — wear, sprockets and guides',
             'Chain-drive machines. Cited: KTM 2022 250/300 EXC TPI owner''s manual — pull the upper run with 10–15 kg and measure 18 chain rollers of the lower run: maximum 272 mm, beyond it "Change the drivetrain kit" (PDF p. 92); chain sliding guard and sliding piece changed when the lower edge of the chain pins is in line with or below them (PDF pp. 92–93); chain guide changed when its light part is worn (PDF p. 93); Honda CB500F owner''s manual — the chain wear label''s red zone after adjustment means the chain must be replaced (PDF p. 83); "Use of a new chain with worn sprockets will cause rapid chain wear" (PDF p. 58); BMW F800R rider''s manual — pull the chain back at the rearmost point of the rear sprocket (PDF p. 102).',
             'Measure the wear the maker''s way: the KTM EXC TPI manual loads the upper run with 10–15 kg and measures across 18 rollers of the lower run, 272 mm at most (PDF p. 92); the Honda CB500F reads its chain wear label, where the index mark on the washer in the red zone after the slack is correctly adjusted means replace (PDF p. 83); the BMW F800R pulls the chain back at the rearmost point of the rear sprocket — the tips of the teeth still between the links pass, a chain that lifts clear over the teeth needs a specialist (PDF p. 102). Inspect both sprockets for worn or damaged teeth (Honda CB500F, PDF p. 58). Check the chain sliding guard, sliding piece and chain guide against the KTM manual''s criteria: the chain pins'' lower edge in line with or below the slider, or the guide''s light part worn, means change it (PDF pp. 92–93).',
             'Chain inside its wear limit, sprocket teeth not worn or damaged, sliders and guide inside their wear criteria.',
             'Chain past its limit, worn or damaged sprocket teeth, sliders or guide past their wear criteria.',
             'A worn chain, a worn sprocket or both means the set: the KTM manual replaces the engine sprocket, rear sprocket and chain together (PDF p. 91), and the Honda CB500F manual warns that a new chain on worn sprockets wears rapidly (PDF p. 58).',
             0, '["ruler or vernier","spring balance"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='drivetrain_service_v1'), 3,
             'Chain drive — clean and lubricate',
             'Chain-drive machines. Cited: KTM 2022 250/300 EXC TPI owner''s manual — rinse off loose dirt with a soft jet of water, remove old grease with chain cleaner, and after drying apply chain spray (PDF p. 89); Honda CB500F owner''s manual — for O-ring chains, "Do not use a steam cleaner, a high pressure cleaner, a wire brush, volatile solvent such as gasoline", nor cleaner or lubricant not designed for O-ring chains, and keep lubricant off the brakes and tires (PDF p. 59); BMW F800R rider''s manual — "Lubricate the drive chain every 1000 km at the latest", more often in wet, dusty or dirty conditions, and wipe off the excess (PDF p. 100).',
             'Clean the chain gently: the KTM EXC TPI manual rinses loose dirt off with a soft jet of water and removes old grease with chain cleaner (PDF p. 89). On an O-ring chain, use only cleaners and lubricants made for O-ring chains — the Honda CB500F manual forbids steam cleaners, high-pressure washers, wire brushes and volatile solvents such as gasoline, which can damage the rubber seals (PDF p. 59). Dry it, lubricate it, and wipe off the excess (BMW F800R, PDF p. 100), keeping lubricant off the tire and the brake (CB500F, PDF p. 59). Lubricate on the maker''s interval — every 1000 km at the latest on the BMW F800R, more often in wet, dusty or dirty conditions (PDF p. 100).',
             'A clean chain with lubricant on the rollers and the excess wiped off; the brake and tire clean.',
             'Grit packed in the rollers, rust, dry or kinked links, lubricant on the tire or brake.',
             'Rust and stiff links that do not free up after cleaning and lubrication are wear: go to the wear item.',
             0, '["chain cleaner","chain lubricant","soft brush","rag"]', 15),

            ((SELECT id FROM workflow_templates WHERE slug='drivetrain_service_v1'), 4,
             'Chain drive — adjust, align and replace',
             'Chain-drive machines. Figures are the named machine''s own. Cited: KTM 2022 250/300 EXC TPI owner''s manual — adjuster markings level on both sides against the reference marks, "The rear wheel is then correctly aligned"; rear axle nut 80 Nm (PDF p. 91); rear sprocket nut 35 Nm and engine sprocket screw 60 Nm, both with Loctite 2701 (PDF pp. 168, 163); Honda CB500F owner''s manual — rear axle nut 88 N·m, adjusting lock nuts 21 N·m (PDF p. 82); chain DID520V0, 112 links, 15T/41T sprockets (PDF p. 134); BMW F800R rider''s manual — scale readings equal on left and right (PDF p. 101); chain tensioning-screw locknut 19 Nm, rear axle 100 Nm (PDF p. 102).',
             'Loosen the axle and turn both adjusters by an equal number of turns until the slack is right (Honda CB500F, PDF p. 82), then check the alignment: the adjuster marks must read the same on both sides (KTM EXC TPI, PDF p. 91; BMW F800R, PDF p. 101). Tighten to the machine''s own torques — the KTM EXC TPI''s rear axle nut 80 Nm (PDF p. 91); the Honda CB500F''s axle nut 88 N·m and adjuster lock nuts 21 N·m (PDF p. 82); the BMW F800R''s tensioner locknut 19 Nm and rear axle 100 Nm (PDF p. 102) — and re-check the slack after tightening. When replacing, fit the chain and sprockets as a set to the machine''s own specification (for example the Honda CB500F''s DID520V0, 112 links, 15T/41T, PDF p. 134), torque the sprocket fasteners with the specified thread-locker (the KTM EXC TPI''s rear sprocket nuts 35 Nm and engine sprocket screw 60 Nm, Loctite 2701, PDF pp. 168, 163), and on a chain with a joint link fit it the way the chain maker specifies.',
             'Slack right after tightening, adjuster marks equal on both sides, every fastener at its torque, a replacement set to the machine''s specification.',
             'Unequal adjuster marks, slack that changed when the axle was tightened, fasteners untorqued, a chain or sprocket that is not the machine''s specification.',
             'Equal adjuster marks are the makers'' alignment check. If the chain still runs to one side of the sprockets with the marks equal, check the adjusters and the swingarm against the machine''s service manual.',
             0, '["torque wrench","thread-locker"]', 20),

            ((SELECT id FROM workflow_templates WHERE slug='drivetrain_service_v1'), 5,
             'Belt drive — slack and condition',
             'Belt-drive machines. Figures are the named machine''s own. Cited: Yamaha XVS95CL/XVS95CLC owner''s manual — note the belt''s position against the marks at the check hole, then again with 45 N (4.5 kgf, 10 lbf) applied with a belt tension gauge (PDF p. 65); the difference is the slack, 6.0–8.0 mm, and a Yamaha dealer adjusts it if it is out (PDF p. 66); check the belt''s condition and tension every 2500 mi (4000 km), and replace it if damaged (PDF p. 48); Yamaha XVS13AF/XVS13AFC owner''s manual — slack 5.0–7.0 mm, the check-hole marks 5.0 mm apart (PDF p. 64), a Yamaha dealer adjusts it (PDF p. 65); "Never apply oil or wax to the drive belt" (PDF p. 82). No document in the research library sets a belt alignment figure, so none is given here.',
             'On the machine as the manual sets it (the XVS13AF on its sidestand, PDF p. 64), note where the belt sits against the marks at the check hole, then press it with the specified force on a belt tension gauge and note it again: the difference is the slack. Compare with the machine''s own figure — 6.0–8.0 mm under 45 N on the Yamaha XVS95CL (PDF pp. 65–66), 5.0–7.0 mm on the XVS13AF, whose marks are 5.0 mm apart (PDF p. 64). Check the belt''s condition and replace it if damaged, on the maker''s interval — every 2500 mi (4000 km) on the XVS95CL (PDF p. 48); looking along its whole length for cracks, damaged teeth and debris in the pulleys is the template''s own way of doing that check. Never put oil or wax on the belt (XVS13AF, PDF p. 82). No document in the research library sets a belt alignment figure: alignment and adjustment follow the machine''s own service manual, and both Yamaha owner''s manuals send adjustment to the dealer (XVS95CL, PDF p. 66; XVS13AF, PDF p. 65).',
             'Slack inside the machine''s figure, belt undamaged, pulleys clean, nothing applied to the belt.',
             'Slack out of range, a damaged belt, stones or debris in the pulley, oil or wax on the belt.',
             'A damaged belt is replaced (XVS95CL, PDF p. 48). Slack out of range is adjusted to the machine''s service procedure, which also sets the alignment — no figure for it is given here because no document in the library sets one.',
             0, '["belt tension gauge","flashlight"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='drivetrain_service_v1'), 6,
             'Shaft drive — final drive oil',
             'Shaft-drive machines. Figures are the named machine''s own. Cited: BMW R 1100 S Service and Technical Booklet — "Change the oil in the rear wheel drive while at regular operating temperature" (PDF p. 6), every 40,000 km (24,000 miles) or at the latest every 2 years (PDF p. 8); brand-name hypoid gear oil, API class GL 5, final drive approx. 0.25 l to the bottom edge of the filler screw, SAE 90 above 5 °C and SAE 80 below, alternatively SAE 80 W 90 (PDF p. 87); BMW R 850 R / R 1150 R Maintenance Instructions — final drive approx. 0.25 l to the bottom edge of the filler opening, EPX 90 alternatively SAE 90 (PDF p. 67); BMW K 1200 RS Maintenance Instructions — final drive 0.25 l, Castrol EPX 90 or SAE 90 (PDF p. 70).',
             'Ride the machine to operating temperature first — the R 1100 S booklet changes the rear-wheel drive oil warm (PDF p. 6). Drain it and refill with the machine''s own oil and quantity: on the BMW R 1100 S, brand-name hypoid gear oil to API class GL 5, approximately 0.25 l to the bottom edge of the filler screw, SAE 90 above 5 °C and SAE 80 below, alternatively SAE 80 W 90 (PDF p. 87); on the R 850 R / R 1150 R, hypoid GL 5, approximately 0.25 l to the bottom edge of the filler opening, EPX 90 or SAE 90 (PDF p. 67); on the K 1200 RS, 0.25 l of Castrol EPX 90 or SAE 90 (PDF p. 70). Change it on the maker''s interval — every 40,000 km or at the latest every 2 years on the R 1100 S (PDF p. 8). Two steps here are the template''s own, not from the cited booklets: look at the drain plug and the old oil for metal particles, and fit a new sealing washer. Check the final-drive housing and its seals for leaks.',
             'Oil changed warm to the machine''s grade and level, housing and seals dry.',
             'Oil past the interval, a leaking seal or housing, metal particles in the old oil.',
             'Oil at a seal, or metal in the old oil, is a matter for the machine''s service manual; the reading of metal as wear inside the housing is the template''s own, not a maker''s.',
             0, '["hypoid gear oil","drain pan","new sealing washer","torque wrench"]', 20),

            ((SELECT id FROM workflow_templates WHERE slug='drivetrain_service_v1'), 7,
             'Shaft drive — universal joints and swinging arm bearings',
             'Shaft-drive machines. Cited: the BMW R 1100 S Service and Technical Booklet describes the secondary drive as a shaft inside the hollow Paralever swinging arm, "with integral torsional vibration damper and two universal joints" (PDF p. 81), and its schedule checks the swinging arm bearings for freedom from play (PDF p. 7). No document in the research library gives a universal-joint inspection procedure or a play figure, so none is given here.',
             'A check the template adds, which no document sets: with the rear wheel raised and the transmission in neutral, turn the wheel slowly back and forth and feel for a clunk or free rotation before the drive takes up — lash in the drive line. Grip the wheel and the swinging arm and feel for play at the swinging-arm pivots: the R 1100 S schedule checks the swinging arm bearings for freedom from play (PDF p. 7). Look along the swinging arm and the final-drive housing for leaks. No document in the research library gives a universal-joint inspection procedure or a play figure, so none is invented here: a joint suspected of wear is inspected and measured to the machine''s own service manual.',
             'No clunk or free play in the drive line, swinging-arm bearings free of play, no leaks.',
             'A clunk as the drive takes up, play at the swinging-arm pivots, oil at the swinging arm or the housing.',
             'Drive-line lash or pivot play on a shaft machine is dismantled and measured to its service manual; the universal joints sit inside the hollow swinging arm (R 1100 S, PDF p. 81), which makes them service-manual work.',
             0, '["paddock stand or lift"]', 15);
        """,
        rollback_sql="""
            DELETE FROM checklist_items
             WHERE template_id IN (SELECT id FROM workflow_templates
                                    WHERE slug IN ('tire_service_v1',
                                                   'brake_service_v1',
                                                   'suspension_service_v1',
                                                   'drivetrain_service_v1'));

            DELETE FROM workflow_templates
             WHERE slug IN ('tire_service_v1', 'brake_service_v1',
                            'suspension_service_v1', 'drivetrain_service_v1');
        """,
    ),
    # Migration 070 — Phase 264 (Track N batch 2): four protocols on the
    # Phase 114 substrate, one per ROADMAP row — winterization (264),
    # de-winterization (265), engine break-in (266), valve adjustment
    # (268) — plus two re-points of live rows the operator scoped in:
    # generic_winterization_v1's description loses its build reference
    # (F158) and names winterization_v1, and ppi_chassis_v1's items name
    # the Yamaha service manual by its title page's model code, YW125Y,
    # not "Zuma" (F160). The rollback restores both verbatim.
    Migration(
        version=70,
        name="seasonal_breakin_valve_workflows",
        description=(
            "Phase 264, Track N batch 2: seed four protocols on the Phase "
            "114 substrate — winterization_v1 and de_winterization_v1 (all "
            "three powertrains), engine_break_in_v1 and valve_adjustment_v1 "
            "(ICE and hybrid). Every figure in the item text names its "
            "machine and cites the maker's document with its PDF page "
            "(the claims table in 264_implementation.md); where no "
            "document sets a figure (heat cycles, a rebuild break-in in a "
            "service manual, inline-four, boxer and desmodromic valve "
            "clearances — negatives with positive controls in "
            "264_step0.md) the item says so and invents none. Also "
            "re-points two live rows: generic_winterization_v1's "
            "description names winterization_v1 instead of a build "
            "reference, and ppi_chassis_v1's items name the Yamaha "
            "service manual YW125Y, as its title page does. Seeded inside "
            "the one-shot journal like 007 and 067-069."
        ),
        upgrade_sql="""
            INSERT OR IGNORE INTO workflow_templates
                (slug, name, description, category, applicable_powertrains,
                 estimated_duration_minutes, required_tier, created_by_user_id)
            VALUES
                ('winterization_v1', 'Winterization — seasonal storage',
                 'Seasonal storage protocol: service and clean before storage, fuel, carburetor float chambers, engine oil and cylinders, the 12-V battery, an electric machine''s traction battery, and the stand, tires, cover and place. The makers disagree on fuel, cylinder oil and battery intervals: each item gives each named machine''s own figure with the document and PDF page it comes from, and invents none. Its companion for the spring is de_winterization_v1.',
                 'winterization', '["ice","electric","hybrid"]', 90, 'individual', 1),
                ('de_winterization_v1', 'De-winterization — return to service',
                 'Return-to-service protocol after storage: uncover and clean, the 12-V battery, an electric machine''s traction battery, fuel and engine oil, the maker''s before-use checks, brakes and tire pressures, and a test ride. Its companion for the autumn is winterization_v1. Figures in the item text are the named machine''s own and cite the document and PDF page they come from.',
                 'de_winterization', '["ice","electric","hybrid"]', 75, 'individual', 1),
                ('engine_break_in_v1', 'Engine break-in',
                 'Protocol for running in a new engine or new engine parts: which break-in applies, the limits by distance, how to ride it, cool-down, the first oil change and first service, and trouble during break-in. Each maker limits its break-in its own way — by engine speed, by throttle opening or by engine performance — so every figure names its machine and cites its document and PDF page, and none is turned into a universal.',
                 'break_in', '["ice","hybrid"]', 30, 'individual', 1),
                ('valve_adjustment_v1', 'Valve clearance check and adjustment',
                 'Protocol for checking and adjusting valve clearance: the engine cold by its maker''s definition, the piston at TDC on the compression stroke, measuring with a feeler gauge, adjusting by screw and lock nut or by shims, rechecking and closing up, and the per-engine-type items — V-twin; inline-four, boxer and desmodromic engines, for which the research library holds no clearance figure. Figures are the named machine''s own and cite the document and PDF page they come from.',
                 'valve_service', '["ice","hybrid"]', 120, 'individual', 1);

            -- The F158 re-point: the generic template's description promised
            -- this phase by number; name the protocol instead.
            UPDATE workflow_templates
               SET description = 'Seasonal storage: fuel stabilization, battery tender, oil change, storage position. For the full protocol, with each maker''s own figures cited, see winterization_v1.',
                   updated_at = CURRENT_TIMESTAMP
             WHERE slug = 'generic_winterization_v1'
               AND description = 'Seasonal storage: fuel stabilization, battery tender, oil change, storage position. Track N phase 264 expands.';

            -- The F160 re-point: the Yamaha service manual's title page
            -- reads "Model : YW125Y"; "Zuma" is on none of its pages. The
            -- one bare "Zuma" first, then "Zuma 125", in every text field.
            UPDATE checklist_items
               SET title = replace(replace(title, 'The Zuma manual''s', 'The YW125Y manual''s'), 'Zuma 125', 'YW125Y'),
                   description = replace(replace(description, 'The Zuma manual''s', 'The YW125Y manual''s'), 'Zuma 125', 'YW125Y'),
                   instruction_text = replace(replace(instruction_text, 'The Zuma manual''s', 'The YW125Y manual''s'), 'Zuma 125', 'YW125Y'),
                   expected_pass = replace(replace(expected_pass, 'The Zuma manual''s', 'The YW125Y manual''s'), 'Zuma 125', 'YW125Y'),
                   expected_fail = replace(replace(expected_fail, 'The Zuma manual''s', 'The YW125Y manual''s'), 'Zuma 125', 'YW125Y'),
                   diagnosis_if_fail = replace(replace(diagnosis_if_fail, 'The Zuma manual''s', 'The YW125Y manual''s'), 'Zuma 125', 'YW125Y')
             WHERE template_id = (SELECT id FROM workflow_templates WHERE slug = 'ppi_chassis_v1')
               AND (title || description || instruction_text || expected_pass
                    || expected_fail || diagnosis_if_fail) LIKE '%Zuma%';

            INSERT OR IGNORE INTO checklist_items
                (template_id, sequence_number, title, description, instruction_text,
                 expected_pass, expected_fail, diagnosis_if_fail, required,
                 tools_needed, estimated_minutes)
            VALUES
            -- ---------------------------------------------------- winterization_v1
            ((SELECT id FROM workflow_templates WHERE slug='winterization_v1'), 1,
             'Before storage: service, clean and protect',
             'Cited: the KTM 690 Enduro 2010 owner''s manual checks all parts for function and wear before storage and does any service, repairs or replacements during the storage period (PDF p. 172). The Honda CB500F owner''s manual washes the machine, waxes painted surfaces except matte ones, coats chrome with rust-inhibiting oil and lubricates the drive chain (PDF p. 117). The BMW F800R rider''s manual sprays the brake and clutch lever pivots and the stand pivots with a suitable lubricant and coats bright metal and chrome with an acid-free grease such as Vaseline (PDF p. 124).',
             'Check every part for function and wear now and book the work into the storage period: the KTM 690 Enduro manual''s reason is avoiding long workshop waits when the season starts (PDF p. 172), and the Yamaha XVS95CL owner''s manual makes repairs step 1 of long-term storage, 60 days or more (PDF pp. 80–81). Wash the machine and let it dry completely before it is covered: the XVS95CL manual warns that a tarp over a wet machine lets water and humidity cause rust (PDF p. 80). Wax painted surfaces except matte ones and coat chrome with rust-inhibiting oil (Honda CB500F, PDF p. 117) or an acid-free grease (BMW F800R, PDF p. 124). Lubricate the control cables, the lever and pedal pivots and the side and centre stands (Yamaha XVS95CL, PDF p. 81) and, on a chain drive, the chain (Honda CB500F, PDF p. 117).',
             'Faults listed or repaired, machine clean and dry, paint waxed, bright metal protected, pivots and cables lubricated, no wax or lubricant on the brakes or tires.',
             'Machine stored dirty or wet, repairs left for the spring, wax or lubricant on a brake disc or tire.',
             'Wax or lubricant on the brakes or tires costs control. The Yamaha XVS95CL manual washes the tires with warm water and a mild detergent, cleans the brake discs and pads with brake cleaner or acetone, and tests braking and cornering before riding at higher speeds (PDF p. 80).',
             1, '["wash kit","wax","lubricant"]', 30),

            ((SELECT id FROM workflow_templates WHERE slug='winterization_v1'), 2,
             'Fuel — full and stabilized, or empty: the machine''s own way',
             'The makers disagree, and the item keeps them apart. The Yamaha XVS95CL owner''s manual fills the tank, adds fuel stabilizer to the product''s instructions and runs the engine for 5 minutes to carry treated fuel through the fuel system (PDF p. 81). The KTM 1290 Super Duke R / RR 2023 owner''s manual adds fuel additive at the last refuel and fills the tank completely with the lowest-ethanol fuel available (PDF p. 157). The KTM 690 Enduro 2010 owner''s manual leaves the tank as empty as possible, so it can be filled with fresh fuel after storage (PDF p. 172). The Kymco People S 50/125/200 owner''s manual empties the tank into an approved container and sprays its inside with aerosol rust-inhibiting oil (PDF p. 60).',
             'Follow the machine''s own manual: the four positions cannot be averaged. Where it says full and stabilized, add the stabilizer at the last fill-up, fill the tank, and run the engine long enough to carry the treated fuel through: 5 minutes is the Yamaha XVS95CL''s figure (PDF p. 81). The two-stroke KTM 2022 250/300 EXC TPI adds its fuel additive at the last refuel and 2-stroke oil after it (PDF p. 154). That run is before storage, not during it: the KTM EXC TPI manual warns against running the engine for a short time only, because it cannot warm up and the water vapour from combustion condenses and rusts engine parts and the exhaust (PDF p. 155). Where the manual says empty, drain into an approved container outdoors with heat, sparks and flame kept away, and treat the tank as that manual says (Kymco People S, PDF p. 60).',
             'Fuel left in the state the machine''s own manual asks for, with the maker''s additive where the manual names one.',
             'A part-filled tank of untreated fuel; the engine started and run briefly during storage.',
             'The Yamaha XV250T1 owner''s manual gives the reason for stabilizer: it keeps the fuel tank from rusting and the fuel from deteriorating (PDF p. 81). Short engine runs during storage are the KTM manuals'' named cause of rusted valves and exhaust (KTM 1290 Super Duke R, PDF p. 157).',
             0, '["fuel stabilizer","approved fuel container"]', 15),

            ((SELECT id FROM workflow_templates WHERE slug='winterization_v1'), 3,
             'Carburetor float chambers (carbureted machines)',
             'For carbureted machines. Cited: the Yamaha XV250T1 owner''s manual drains the carburetor float chambers by loosening the drain bolts, which keeps fuel deposits from building up, and pours the drained fuel into the tank (PDF p. 81). The Yamaha XVS95CL owner''s manual gives the same step for vehicles with a carburetor, into a clean container, and turns a fuel cock off where one is fitted (PDF p. 81). The Kymco People S 50/125/200 owner''s manual drains the carburetor, if equipped, before emptying the tank (PDF p. 60).',
             'Turn the fuel cock off where the machine has one (Yamaha XVS95CL, PDF p. 81). Put a clean container under each float chamber, loosen its drain bolt, let the chamber empty and retighten the bolt. The Yamaha XV250T1 pours that fuel back into the tank (PDF p. 81); the Kymco People S empties the tank as well (PDF p. 60).',
             'Every float chamber empty, drain bolts tight and dry, fuel cock off where fitted.',
             'Fuel left standing in a float chamber; a drain bolt weeping.',
             'Fuel left in the float chambers is what the Yamaha XV250T1 manual drains to stop fuel deposits building up (PDF p. 81).',
             0, '["drain pan","screwdriver"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='winterization_v1'), 4,
             'Engine oil and cylinder protection',
             'Cited: the KTM 690 Enduro 2010 owner''s manual changes the engine oil and filter and cleans the oil screens before storage (PDF p. 172); the BMW F800R rider''s manual has the oil and filter changed before laying up (PDF p. 124); the Kymco People S 50/125/200 owner''s manual makes the oil and filter change step 1 (PDF p. 60). No storage procedure in the research library names an oil grade for storage: the oil is the one the machine''s own manual specifies. For the cylinders, the Yamaha XVS95CL owner''s manual uses engine fogging oil or, without it, a teaspoonful of engine oil in each spark plug bore (PDF p. 81); the Kymco People S pours a tablespoon (15 - 20 cc) into the cylinder (PDF p. 60).',
             'Change the engine oil and filter now, not in the spring, with the oil the machine''s own manual specifies (KTM 690 Enduro, PDF p. 172; Kymco People S, PDF p. 60). The KTM 2022 250/300 EXC TPI is a two-stroke, and its storage list changes the gear oil instead (PDF p. 154). Then protect the cylinders the maker''s way: fogging oil to its product instructions, or the plug out and the maker''s measure in — a teaspoonful per cylinder on the Yamaha XVS95CL (PDF p. 81), a tablespoon (15 - 20 cc) on the Kymco People S (PDF p. 60) — and the engine turned over several times. The Yamaha XVS95CL grounds the plug electrodes on the cylinder head while it turns the engine (PDF p. 81); the Kymco People S keeps the plug cap secured away from the plug and covers the plug hole with a cloth (PDF p. 60). Refit the plugs, and cover the muffler outlet with a plastic bag against moisture (Yamaha XVS95CL, PDF p. 81).',
             'Fresh oil and filter in, cylinders oiled by the maker''s measure, plugs refitted, exhaust outlet covered.',
             'Used oil left in over the winter; cylinders left dry; a plug left ungrounded while the engine was turned over.',
             'The two cylinder measures differ (a teaspoonful on the Yamaha XVS95CL, PDF p. 81; 15 - 20 cc on the Kymco People S, PDF p. 60): take the machine''s own. The Yamaha XVS95CL grounds the electrodes to prevent damage or injury from sparking (PDF p. 81).',
             0, '["drain pan","oil filter wrench","spark plug socket"]', 30),

            ((SELECT id FROM workflow_templates WHERE slug='winterization_v1'), 5,
             '12-V battery — charge it, and keep it charged',
             'The makers agree on a full charge and disagree on how often. Cited: the Honda CB500F owner''s manual removes the battery, charges it fully and keeps it shaded and ventilated, or disconnects the negative terminal if it stays in (PDF p. 117). Recharge intervals: every two weeks in the Honda PCX150 (2013–2017) service manual (PDF p. 390); once a month in the Yamaha XVS95CL owner''s manual (PDF p. 81); about every 4 months in store, and every 2 months at the latest if left connected, in the BMW R 850 R / R 1150 R Maintenance Instructions (PDF p. 49); every six months for a sealed battery stored in open circuit in the Piaggio Beverly 125 service station manual (PDF p. 78).',
             'Charge the battery fully, then do what the machine''s own manual says: remove it; or leave it in with the earth lead off — the BMW R 850 R / R 1150 R instructions say the on-board electronics (the clock) otherwise run it flat, and then warranty claims are not accepted (PDF p. 49); or keep it on a maintenance charger (Yamaha XVS95CL, PDF p. 81), which on the BMW F800R is BMW''s own float charger (PDF p. 117). Charge with the charger its manual names: the BMW gel battery only with an electronically controlled charger limited to 14.4 V (R 850 R / R 1150 R, PDF p. 48); the Yamaha never charges a VRLA battery with a conventional charger (XVS95CL, PDF p. 81). Store it where its manual says: 0–30 °C for the Yamaha XVS95CL (PDF p. 81), 0–35 °C out of direct sunshine for the KTM 690 Enduro (PDF p. 172), 10–20 °C for the lithium-ion battery of the KTM 2022 250/300 EXC TPI (PDF p. 154). Then recharge on the machine''s own interval from the description.',
             'Battery fully charged, stored or connected as its manual says, the next recharge dated to its interval.',
             'Battery left connected with no charger all winter; charged with the wrong charger; stored frozen or in the sun.',
             'A battery run flat in storage is the case the BMW instructions exclude from warranty (R 850 R / R 1150 R, PDF p. 49). The Piaggio Beverly 125 manual says a battery not used for a month or more needs periodic recharging and runs down completely in three months (PDF p. 78).',
             1, '["battery charger","voltmeter"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='winterization_v1'), 6,
             'Electric machine — the traction battery',
             'For electric machines. Cited: the Vespa Elettrica service station manual, for prolonged periods with the vehicle not in use, charges the traction battery completely at least once every three months (PDF p. 9). A sealed 12-V battery is checked and recharged every six months while the vehicle is stored in open circuit (PDF p. 163).',
             'Charge the traction battery completely before storage and at least once every three months while it stands, from a public charging station or a household socket with an earth connection and a differential circuit breaker (Vespa Elettrica, PDF p. 9). Store it where it can charge: at 0 °C to -10 °C the Elettrica''s electronics allow only a slow, partial charge of about 6 hours to a 60 % state of charge (PDF p. 9). For any other electric machine, its own manual owns the figure.',
             'Traction battery fully charged, a three-monthly recharge dated, stored above 0 °C.',
             'Stored discharged, or left more than three months without a charge.',
             'A partial charge in the cold is the Elettrica protecting its battery, not a fault: it charges slowly to about 60 % at 0 °C to -10 °C (PDF p. 9).',
             0, '["charging cable"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='winterization_v1'), 7,
             'Stand, tires, cover and place',
             'Cited: the Honda CB500F owner''s manual puts the machine on a maintenance stand with a block so both tires are off the ground (PDF p. 117); the BMW F800R rider''s manual stands it in a dry room with no load on either wheel (PDF p. 124); the Yamaha XVS95CL owner''s manual corrects the tire pressure first and, without a stand, turns the wheels a little once a month so the tires do not degrade in one spot (PDF p. 81). The cover lets humidity out: the KTM 2022 250/300 EXC TPI owner''s manual uses an air-permeable tarp, because non-porous materials trap humidity and cause corrosion (PDF pp. 154–155).',
             'Set the tires to the machine''s own pressure, then take the weight off both wheels on a stand, a lift stand or blocks (Honda CB500F, PDF p. 117; KTM EXC TPI, PDF p. 154). If it must stand on its tires, turn the wheels a little once a month (Yamaha XVS95CL, PDF p. 81). Choose the place: cool and dry, not a damp cellar, a stable (ammonia) or where strong chemicals are kept (XVS95CL, PDF p. 80), and not subject to large swings in temperature (KTM EXC TPI, PDF p. 154). Let the engine and exhaust cool before covering (XVS95CL, PDF p. 80). Stored outdoors under a full-body cover, the Honda takes the cover off after rain and lets the machine dry (CB500F, PDF p. 117).',
             'Tires at pressure and off the ground, or a monthly turn dated; a cool, dry place; a breathable cover over a cool machine.',
             'On its tires on the side stand all winter, a plastic tarp, a damp or chemical-laden place.',
             'Corrosion found in the spring points back at the cover or the place: the Yamaha XVS95CL names damp rooms and a tarp over a wet machine (PDF p. 80), the KTM EXC TPI non-porous covers (PDF p. 155). A tire flattened on one spot goes to tire_service_v1.',
             1, '["paddock stand","breathable cover","tire pressure gauge"]', 15),

            -- ------------------------------------------------- de_winterization_v1
            ((SELECT id FROM workflow_templates WHERE slug='de_winterization_v1'), 1,
             'Uncover, clean and take it off the stand',
             'Cited: the BMW F800R rider''s manual restores a machine to use by removing the protective wax coating, cleaning it and installing a charged battery, then working through its checklist before starting (PDF p. 124); the Kymco People S 50/125/200 owner''s manual starts by uncovering and cleaning the scooter (PDF p. 61); the KTM 2022 250/300 EXC TPI owner''s manual by taking the motorcycle off the lift stand (PDF p. 155).',
             'Take the cover off, take the machine off its stand or blocks, and clean it; remove the protective wax coating where it was applied (BMW R 850 R / R 1150 R Maintenance Instructions, PDF p. 59). Take the bag off the muffler outlet if one was fitted for storage, as the Yamaha XVS95CL owner''s manual does (PDF p. 81). Then look for what the winter did — rust on bright metal, debris in the intake or the exhaust, a tire flattened on one spot; that list is the template''s own, not a cited document''s.',
             'Cover, bag and wax off; machine clean; nothing blocked or corroded.',
             'Exhaust outlet still bagged; wax left on; corrosion or debris found.',
             'Corrosion under the cover points back at the storage place or the cover (winterization_v1, item 7). A muffler bag left on blocks the exhaust — the template''s own warning.',
             1, '["wash kit"]', 20),

            ((SELECT id FROM workflow_templates WHERE slug='de_winterization_v1'), 2,
             '12-V battery — check the voltage, charge, install',
             'Cited: the Piaggio Beverly 125 service station manual checks the open-circuit voltage before a stored battery goes in: above 12.60 V it is installed without a recharge; below 12.60 V it gets a renewal recharge at a constant 14.40 ÷ 14.70 V, 10 to 12 hours recommended (PDF p. 78). The BMW R 1100 S Service and Technical Booklet installs a charged battery and greases its terminals (PDF p. 79).',
             'Measure the open-circuit voltage with a tester before the battery goes in. On the Piaggio Beverly 125, above 12.60 V it is installed as it is; below 12.60 V it is charged first at a constant 14.40 ÷ 14.70 V, 10 to 12 hours recommended, 6 minimum and 24 maximum (PDF p. 78). Other machines charge by their own manual: the BMW R 850 R / R 1150 R instructions always fully recharge before restoring to use (PDF p. 49). Connect it the right way round, grease the terminals (BMW R 1100 S, PDF p. 79; the Beverly coats them with Vaseline, PDF p. 78), and reset what lost power: the KTM 1190 Adventure 2016 owner''s manual sets the time and date if the battery was removed (PDF p. 206).',
             'Battery at or above its manual''s voltage, charged, fitted the right way round, terminals greased, clock set.',
             'Battery fitted flat; fitted reversed; a flat battery jump-started.',
             'Do not jump-start around a flat battery: the BMW R 850 R / R 1150 R instructions recharge it instead, because jump-starting risks the control units (PDF p. 48). A battery that will not hold a charge after the refresh may be worn out: the Honda PCX150 (2013–2017) service manual says a maintenance-free battery''s performance deteriorates after 2-3 years even in normal use (PDF p. 390).',
             1, '["voltmeter","battery charger"]', 15),

            ((SELECT id FROM workflow_templates WHERE slug='de_winterization_v1'), 3,
             'Electric machine — the traction battery',
             'For electric machines. Cited: the Vespa Elettrica service station manual charges the traction battery to 100 % state of charge, and runs the normal charge to 100 % only at battery temperatures above 0 °C; below 0 °C it runs a slow, partial charge (PDF p. 9).',
             'Charge the traction battery to 100 % before the first ride (Vespa Elettrica, PDF p. 9). If it charges only part of the way, look at the battery''s temperature first: the Elettrica runs the normal charge only above 0 °C (PDF p. 9). With the traction battery full, the Elettrica''s ancillary battery may still not be fully charged; it is charged while the vehicle is running (PDF p. 9).',
             'Traction battery at 100 %, charged above 0 °C.',
             'A charge that stops short in the cold taken for a battery fault.',
             'A short charge in the cold is the Elettrica protecting its battery (PDF p. 9). Below a 10 % state of charge the Elettrica limits its speed and the battery icon flashes (PDF p. 90).',
             0, '["charging cable"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='de_winterization_v1'), 4,
             'Fuel and engine oil',
             'Cited: the Kymco People S 50/125/200 owner''s manual changes the engine oil if more than 1 month has passed since the start of storage, drains any excess aerosol rust-inhibiting oil from the fuel tank and fills it with fresh gasoline (PDF p. 61); the KTM 690 Enduro 2010 owner''s manual refuels as it puts the machine back into operation (PDF p. 173).',
             'If the tank was emptied for storage, drain what is left of the rust-inhibiting oil and fill it with fresh fuel (Kymco People S, PDF p. 61; KTM 690 Enduro, PDF p. 173). Oil: the Kymco People S changes it if more than 1 month has passed since storage began (PDF p. 61); other machines follow their own manual. Check the oil level and look for leaks, as the Kymco People S pre-ride inspection does (PDF p. 25).',
             'Fresh fuel, no rust-inhibiting oil left in the tank, engine oil changed or checked by the manual''s rule, no leaks.',
             'Stale fuel; the tank still holding rust-inhibiting oil; oil not changed after more than a month on a machine whose manual asks for it.',
             'An oil level below its mark or a leak is a repair before the ride: the Kymco People S pre-ride inspection adds oil if required and checks for leaks (PDF p. 25).',
             0, '["approved fuel container","drain pan"]', 20),

            ((SELECT id FROM workflow_templates WHERE slug='de_winterization_v1'), 5,
             'The maker''s before-use checks',
             'Cited: the KTM 2022 250/300 EXC TPI owner''s manual prepares a stored machine for use with its checks and maintenance measures (PDF p. 155), which list brake fluid levels, brake linings, brake function, coolant level, the chain, tire condition and pressure, spoke tension, the controls, and the screws, nuts and hose clamps (PDF p. 46). The Honda CB500F owner''s manual inspects every item on its Maintenance Schedule after storage (PDF p. 117).',
             'Work through the machine''s own before-use list, not a generic one. The KTM EXC TPI''s is: brake fluid level front and rear, the brake linings, that the brake system works, coolant level, the chain for dirt, wear and tension, tire condition and pressure, spoke tension, every control for smooth operation, and screws, nuts and hose clamps for tightness (PDF p. 46). The Kymco People S 50/125/200''s is engine oil, tires, fuel, front and rear brakes, steering, instruments, lights and horn, and the chassis (PDF p. 25). The Honda CB500F''s is every item on its Maintenance Schedule (PDF p. 117). The BMW R 850 R / R 1150 R instructions perform the rider''s manual''s safety checks (PDF p. 59).',
             'Every item on the machine''s own list checked and passed.',
             'A fluid below its mark, a loose fastener, a control that binds.',
             'A brake fluid level below its marking is a leak or worn linings in the KTM EXC TPI manual''s reading, and the machine is not ridden until it is found (PDF p. 101).',
             1, '["flashlight","tire pressure gauge"]', 25),

            ((SELECT id FROM workflow_templates WHERE slug='de_winterization_v1'), 6,
             'Brakes and tire pressures',
             'Cited: the BMW R 850 R / R 1150 R Maintenance Instructions restore a machine to use with "Check the brakes" and "Check/correct tyre pressures" (PDF p. 59), and the BMW R 1100 S Service and Technical Booklet the same (PDF p. 79). No maker''s document in the research library asks for the brakes to be exercised after storage; what they ask is a check. The Yamaha XVS95CL owner''s manual sets tire pressure on cold tires, at ambient temperature (PDF p. 58).',
             'Brakes: fluid levels and linings from item 5, then check that the brake system works (KTM 2022 250/300 EXC TPI, PDF p. 46). If wax or lubricant reached the discs or pads during storage, clean them with brake cleaner or acetone (Yamaha XVS95CL, PDF p. 80). Tires: check and correct the pressure cold, with the tires at ambient temperature (XVS95CL, PDF p. 58), to the machine''s own figure.',
             'Brakes working with fluid and linings in order; tires at the machine''s own cold pressure.',
             'A lever that sinks or feels spongy; contamination on a disc or pad; a tire below its pressure.',
             'A spongy lever after storage goes to brake_service_v1, and a tire that lost pressure or flattened on one spot to tire_service_v1, before the machine is ridden (the template''s own routing).',
             1, '["tire pressure gauge","brake cleaner"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='de_winterization_v1'), 7,
             'Test ride',
             'Cited: the Kymco People S 50/125/200 owner''s manual test-rides the scooter at low speeds in a safe riding area, away from traffic (PDF p. 61); the KTM 2022 250/300 EXC TPI owner''s manual ends its return to use with a test ride (PDF p. 155), as the KTM 690 Enduro 2010 owner''s manual does (PDF p. 173).',
             'Ride first at low speed, away from traffic (Kymco People S, PDF p. 61). Test braking and cornering before higher speeds, as the Yamaha XVS95CL owner''s manual does after cleaning (PDF p. 80). Listen and feel for what the stationary checks could not show — a dragging brake, a pull, a misfire, a warning light; that list is the template''s own.',
             'Brakes, steering and engine behave normally at low speed and then at road speed.',
             'A dragging or weak brake, a pull, a misfire or a warning light.',
             'Anything the test ride finds routes to its own protocol — brake_service_v1, tire_service_v1, suspension_service_v1 or drivetrain_service_v1 (the template''s own routing).',
             1, '[]', 15),

            -- -------------------------------------------------- engine_break_in_v1
            ((SELECT id FROM workflow_templates WHERE slug='engine_break_in_v1'), 1,
             'Which break-in applies — new engine or new parts',
             'Cited: the Genuine Buddy 125 owner''s manual applies its run-in "When your engine is new or when you have installed new engine components" (PDF p. 25). The Yamaha SR400 owner''s manual gives the reason for a new engine: over the first 1600 km (1000 mi) its parts wear and polish themselves to the correct operating clearances (PDF p. 39). No service manual in the research library gives a separate break-in after an engine or top-end rebuild.',
             'Find the break-in in the machine''s own owner''s manual and use it for a new engine. After a rebuild or new top-end parts, the only maker in the research library that speaks to it is Genuine, whose run-in covers newly installed engine components (Buddy 125, PDF p. 25). For any other machine its own service manual owns the post-rebuild procedure; where that says nothing, following the owner''s-manual break-in is the template''s own recommendation, not a cited document''s. Record the odometer reading at the start: every limit below is counted from it.',
             'The machine''s own break-in found and the start odometer reading recorded.',
             'A generic break-in used in place of the maker''s; no start reading.',
             'One manual can carry two schedules: the Genuine Buddy 125''s gives 0 - 100 miles on PDF p. 25 and 0~95 miles on PDF p. 27. Where they differ, follow the stricter (the template''s own rule).',
             1, '[]', 5),

            ((SELECT id FROM workflow_templates WHERE slug='engine_break_in_v1'), 2,
             'The limits, by distance — each maker''s own measure',
             'Each maker''s limit, with its measure. Engine speed: the KTM 690 Enduro 2010 owner''s manual, 6,000 rpm for the first 1,000 km and 7,800 rpm after (PDF p. 46); the KTM 1190 Adventure 2016 owner''s manual, 6,500 rpm and then 10,250 rpm (PDF p. 86); the Yamaha SR400 owner''s manual, no prolonged operation above 3500 r/min from 0 to 1000 km and above 4200 r/min from 1000 to 1600 km (PDF p. 39); the BMW R 1200 GS rider''s manual, running-in speeds below 5000 rpm until the running-in check (PDF p. 85). Throttle: the Yamaha XVS95CL owner''s manual, no prolonged operation above 1/3 throttle from 0 to 1000 km and above 1/2 throttle from 1000 to 1600 km (PDF p. 41); the Kymco People S 50/125/200 owner''s manual, less than 1/2 throttle for the initial 300 miles (600 km) and less than 3/4 up to 600 miles (1,000 km), in its own printed conversions (PDF p. 23). Engine performance: the two-stroke KTM 2022 250/300 EXC TPI owner''s manual, under 70 % for the first 3 operating hours (PDF p. 40).',
             'Take the machine''s own limits in their own measure, and do not convert one into another: a throttle fraction is not an engine speed, and operating hours are not kilometres. The Honda CB500F owner''s manual sets no engine speed: for the first 300 miles (500 km) it avoids full-throttle starts and rapid acceleration, hard braking and rapid down-shifts (PDF p. 14). The Kymco People S also keeps the road speed below 25 MPH (40 KPH) for its first 600 miles (1,000 km) (PDF p. 40). Keep the engine speed out of the red zone throughout (Yamaha SR400, PDF p. 39).',
             'Every limit the machine''s manual sets kept, in its own measure, to its own distance or time.',
             'Full throttle or high engine speed inside the break-in distance; one maker''s figure used on another machine.',
             'Exceeding the running-in engine speeds leads to increased engine wear, in the BMW F800R rider''s manual''s words (PDF p. 66).',
             1, '[]', 5),

            ((SELECT id FROM workflow_templates WHERE slug='engine_break_in_v1'), 3,
             'How to ride it — vary the load',
             'Cited: the BMW R 1200 GS rider''s manual varies the throttle opening and engine-speed range frequently, avoids constant engine rpm for prolonged periods, and does most of its riding on twisting, fairly hilly roads (PDF p. 85). The BMW F800R rider''s manual avoids low engine speeds at full load (PDF p. 67). The Kymco People S 50/125/200 owner''s manual varies the engine speed so the parts are loaded, then unloaded and allowed to cool (PDF p. 23).',
             'Ride it with a changing load: vary throttle and engine speed and avoid long stretches at one engine speed (BMW R 1200 GS, PDF p. 85); the BMW F800R avoids high-speed main roads and highways where possible and makes no full-load acceleration (PDF p. 66), and does not labour the engine at low speed under full load (PDF p. 67). The Yamaha SR400 avoids prolonged full-throttle operation and any condition that might overheat the engine (PDF p. 39). Some stress is part of it: the Kymco People S says some stress must be placed on the components, but not excessive load on the drive line (PDF p. 23).',
             'Riding with varied throttle and engine speed, no full-load acceleration, no labouring, no long constant-speed runs.',
             'Long constant-speed or highway runs, full-throttle acceleration, labouring the engine at low speed.',
             'Constant low speed is not the gentle choice: the Kymco People S warns that constant low speed (light load) can glaze parts (PDF p. 23).',
             1, '[]', 5),

            ((SELECT id FROM workflow_templates WHERE slug='engine_break_in_v1'), 4,
             'Cool-down between runs (where the maker asks for it)',
             'Only one maker in the research library prescribes a cool-down, and no document names heat cycles. The Genuine Buddy 125 owner''s manual prints two schedules: cool the engine for 10 minutes after every 30 minutes of operation for the first 100 miles (PDF p. 25), and 5-10 minutes per hour for the first 95 miles (PDF p. 27).',
             'On a machine whose manual prescribes a cool-down, stop and let the engine cool on its schedule; on the Genuine Buddy 125, where its two pages differ, 10 minutes after every 30 (PDF p. 25) is the stricter. No other maker''s document in the research library asks for cool-downs, so none is invented for other machines.',
             'Cool-downs kept on the manual''s schedule, where the manual has one.',
             'Long first rides with no stop on a machine whose manual asks for cool-downs.',
             'High engine temperature is what the Genuine Buddy 125''s run-in avoids through its first 500 miles (PDF p. 25).',
             0, '[]', 5),

            ((SELECT id FROM workflow_templates WHERE slug='engine_break_in_v1'), 5,
             'First oil change and first service',
             'Cited: the Yamaha XVS95CL owner''s manual changes the engine oil and replaces the oil filter after 1000 km (600 mi) (PDF p. 41). The Honda PCX150 (2013–2017) service manual changes the engine oil first at 600 mi (1,000 km) or 1 month (PDF p. 77), and says the first scheduled maintenance compensates for the initial wear of the break-in period (PDF p. 3). The Kymco People S 50/125/200 owner''s manual has the initial service done after one month or 200 miles (300 km), whichever comes first (PDF p. 25). The BMW F800R rider''s manual has its running-in check done between 500 km and 1200 km (PDF p. 141).',
             'Book the first oil change and the first service at the machine''s own distance, counted from the start reading: 1000 km on the Yamaha XVS95CL, oil and filter (PDF p. 41); 600 mi (1,000 km) or 1 month on the Honda PCX150 (PDF p. 77); one month or 200 miles (300 km) on the Kymco People S (PDF p. 25), where all fasteners are tightened and the contaminated engine oil is replaced (PDF p. 23); between 500 km and 1200 km for the BMW F800R''s running-in check (PDF p. 141). The Genuine Buddy 125 changes its gear oil after 200 miles (PDF p. 27). Do not skip it: the F800R manual says not to omit the first inspection (PDF p. 67).',
             'First oil change and first service done at the machine''s own distance, and recorded.',
             'The first service skipped or pushed past its distance.',
             'The first oil carries the break-in''s wear: the Kymco People S calls it contaminated and replaces it at the initial service (PDF p. 23).',
             1, '["drain pan","oil filter wrench"]', 30),

            ((SELECT id FROM workflow_templates WHERE slug='engine_break_in_v1'), 6,
             'Trouble during break-in',
             'Cited: the Yamaha XVS95CL owner''s manual has a Yamaha dealer check the vehicle immediately if any engine trouble occurs during the break-in period (PDF p. 42); the Genuine Buddy 125 owner''s manual refers any problem during the initial run-in to the dealer (PDF p. 27).',
             'At the first sign of trouble stop riding and have the machine checked — the makers'' word is immediately (Yamaha XVS95CL, PDF p. 42). What counts as trouble here is the template''s own list: an unfamiliar noise, smoke, overheating, a warning light, oil where it should not be. Check the idle speed as well: on the KTM 2022 250/300 EXC TPI it may change during the run-in time, its guideline is 1,400 … 1,500 rpm, and it is adjusted if it changes (PDF p. 40).',
             'No trouble during break-in, or trouble stopped and checked at once.',
             'Riding on through a noise, overheating or a warning light during break-in.',
             'The makers send trouble during break-in to the dealer rather than riding on (Yamaha XVS95CL, PDF p. 42; Genuine Buddy 125, PDF p. 27).',
             1, '[]', 5),

            -- ------------------------------------------------- valve_adjustment_v1
            ((SELECT id FROM workflow_templates WHERE slug='valve_adjustment_v1'), 1,
             'Engine cold — by the maker''s definition',
             '"Cold" is three definitions in the makers'' own documents: below 35 °C (95 °F) in the Honda PCX150 (2013–2017) service manual (PDF p. 82), the Honda CHF50 service manual (PDF p. 64) and the Kymco People / People S 250 service manual (PDF p. 59); "a cold engine, at room temperature" in the Yamaha YW125Y 2009 service manual (PDF p. 62); and figures given at 20 °C (68 °F) in the KTM 1190 Adventure 2016 owner''s manual (PDF p. 209).',
             'Let the engine cool to its own manual''s definition before measuring: a clearance read warm is not the clearance in the book. Where the manual says only that the service must be performed when the engine is cold — the Yamaha XVS95CL owner''s manual''s wording (PDF p. 58) — reading that as room temperature after the engine has stood is the template''s own.',
             'Engine at or below its manual''s temperature.',
             'Measured on a warm engine.',
             'A clearance read warm cannot be compared with the cold figures in item 3: let the engine cool and measure again (the template''s own rule).',
             1, '[]', 5),

            ((SELECT id FROM workflow_templates WHERE slug='valve_adjustment_v1'), 2,
             'Piston at TDC on the compression stroke',
             'Cited: the Yamaha YW125Y 2009 service manual measures with the piston at top dead center on the compression stroke: the punch mark on the camshaft sprocket on the stationary mark on the cylinder head, and the TDC mark on the AC magneto rotor on the pointer on the crankcase, turning the crankshaft counterclockwise (PDF pp. 62–63). The Honda PCX150 (2013–2017) service manual confirms the compression stroke by slack in the rocker arm (PDF p. 82).',
             'Remove what the machine''s manual lists to reach the valves, then turn the crankshaft in its own direction (counterclockwise on the Yamaha YW125Y, PDF p. 62) until the flywheel TDC mark and the camshaft marks line up. They line up on the exhaust stroke too: on the Honda PCX150, slack in the rocker arm confirms the compression stroke, and no slack means one more full turn (PDF p. 82); on the Honda CHF50 the camshaft lobe faces the cylinder side at compression TDC, and if it does not, the crankshaft turns one more revolution (PDF p. 64).',
             'Flywheel and camshaft marks aligned on the compression stroke, the rocker arms slack.',
             'Marks aligned on the exhaust stroke, rocker arms tight.',
             'No slack in the rocker arm means the piston is on the exhaust stroke, in the Honda PCX150 manual''s reading: turn one full turn and align again (PDF p. 82).',
             1, '["socket set"]', 10),

            ((SELECT id FROM workflow_templates WHERE slug='valve_adjustment_v1'), 3,
             'Measure with a feeler gauge',
             'Clearances, cold, each the named machine''s own: the Yamaha YW125Y 2009 service manual, intake 0.10 ~ 0.14 mm and exhaust 0.16 ~ 0.20 mm (PDF p. 62); the Honda PCX150 (2013–2017) service manual, intake 0.10 ± 0.02 mm and exhaust 0.24 ± 0.02 mm (PDF p. 82); the Honda CHF50 service manual, intake 0.10 ± 0.03 mm and exhaust 0.19 ± 0.03 mm (PDF p. 64); the Kymco People / People S 250 service manual, intake 0.1 mm and exhaust 0.1 mm (PDF p. 59); the KTM 690 Enduro 2010 owner''s manual, valve play cold 0.07… 0.13 mm (PDF p. 174); the Vespa GTS Super 300 ie (2008) service station manual, intake 0.10 mm and exhaust 0.15 mm (PDF p. 9).',
             'On a screw-adjusted rocker the gauge goes between the adjusting screw and the valve stem (Honda PCX150, PDF p. 82); on a shim engine, between the valve lifter and the shim (Honda CHF50, PDF p. 64). The right clearance gives a slight drag on the feeler gauge (PCX150, PDF p. 83). Measure every valve and write each reading down, intake and exhaust apart: their figures differ, and a shim engine needs the reading to calculate the new shim.',
             'Every valve within its own machine''s figure for its side.',
             'Any valve outside its figure, or a reading that could not be taken.',
             'Too small a clearance is a cause of low compression in the Kymco People / People S 250 service manual (PDF p. 60). Unadjusted valves lead to an improper air-fuel mixture, engine noise and eventually engine damage in the Yamaha XVS95CL owner''s manual (PDF p. 58).',
             1, '["feeler gauge"]', 15),

            ((SELECT id FROM workflow_templates WHERE slug='valve_adjustment_v1'), 4,
             'Adjust — adjusting screw and lock nut',
             'For rocker arms with an adjusting screw. Cited: the Yamaha YW125Y 2009 service manual loosens the locknut, sets the gauge between the adjusting screw and the valve tip, turns the screw to the clearance, holds it and tightens the locknut to 7 Nm (PDF p. 63), then measures again and repeats until the clearance is in specification (PDF p. 64). The Honda PCX150 (2013–2017) service manual oils the lock nut threads and seat and tightens it to 10 N·m (PDF p. 83). The Kymco People / People S 250 service manual tightens the adjusting nut to 8.8 N-m with engine oil on the threads (PDF p. 81) and checks the clearance again after the lock nut is tightened (PDF p. 59).',
             'Loosen the lock nut, turn the screw until the gauge slides with a slight drag (Honda PCX150, PDF p. 83), hold the screw still and tighten the lock nut to the machine''s own torque: 7 Nm on the Yamaha YW125Y (PDF p. 63), 10 N·m on the Honda PCX150 (PDF p. 83), 6 ÷ 8 Nm for the tappet set screw lock nut on the Vespa GTS Super 300 ie (PDF p. 16). Measure again after tightening, as the Kymco People S 250 does (PDF p. 59); the YW125Y repeats every step until the clearance is in specification (PDF p. 64). Use the maker''s tool where it names one: the YW125Y''s valve adjusting tool 90890-01311 (PDF p. 63).',
             'Every adjusted valve within its figure after the lock nut is at torque.',
             'A clearance that moved when the lock nut was tightened; a lock nut left below its torque.',
             'A reading that changes after tightening is why the makers measure again: repeat until it holds (Yamaha YW125Y, PDF p. 64).',
             0, '["feeler gauge","valve adjusting tool","torque wrench"]', 20),

            ((SELECT id FROM workflow_templates WHERE slug='valve_adjustment_v1'), 5,
             'Adjust — shims',
             'For engines with shims. Cited: the Honda CHF50 service manual removes the shim, measures it and calculates the new one as A = (B - C) + D, where A is the new shim thickness, B the recorded valve clearance, C the specified valve clearance and D the old shim thickness; sixty-nine thicknesses are available from 1.200 mm to 2.900 mm in 0.025 mm increments (PDF p. 65).',
             'Mark every shim to its valve so each goes back in its original place, and do not let one fall into the crankcase; tweezers or a magnet lift them out (Honda CHF50, PDF p. 65). Measure the old shim, calculate A = (B - C) + D, and check the new shim with a micrometer before it goes in. Turn the crankshaft several times and check the clearance again (PDF p. 65).',
             'Every valve within its figure with the new shims, rechecked after the crankshaft has turned.',
             'A shim dropped into the crankcase; a shim fitted to the wrong valve; a calculated shim outside the range.',
             'A calculated shim over 2.900 mm means carbon deposits: the Honda CHF50 manual refaces the valve seat (PDF p. 65).',
             0, '["feeler gauge","micrometer","magnet"]', 40),

            ((SELECT id FROM workflow_templates WHERE slug='valve_adjustment_v1'), 6,
             'Recheck, close up and set the next interval',
             'Cited: the Yamaha YW125Y 2009 service manual refits the breather and valve covers at 7 Nm and the spark plug at 13 Nm (PDF p. 64); the Honda PCX150 (2013–2017) service manual replaces the crankcase cover duct''s rubber seal if it is not in good condition (PDF p. 83). The interval is each machine''s own schedule: every 16000 mi (25000 km) on the Yamaha XVS95CL, checked when the engine is cold (PDF p. 45).',
             'Check the clearance once more with everything tight, then refit the covers with their seals in good condition (Honda PCX150, PDF p. 83) and the spark plug to the manual''s torque (Yamaha YW125Y: covers 7 Nm, plug 13 Nm, PDF p. 64). Record every reading with the date and odometer, and set the next check from the machine''s own schedule.',
             'Readings recorded, covers and plug at torque, no leak at the cover seal, next check scheduled.',
             'A cover seal reused when damaged; no record of the readings.',
             'Oil at the valve cover after the job is the cover or its seal: the Honda PCX150 manual checks the seal and replaces it if it is not in good condition (PDF p. 83).',
             1, '["torque wrench"]', 15),

            ((SELECT id FROM workflow_templates WHERE slug='valve_adjustment_v1'), 7,
             'V-twin — both cylinders, each at its own figure',
             'Cited: the KTM 1190 Adventure 2016 owner''s manual — a 2-cylinder engine in a 75° V arrangement, DOHC with 4 valves per cylinder — gives valve clearance at 20 °C (68 °F): intake 0.10… 0.15 mm, exhaust 0.25… 0.30 mm (PDF p. 209); the KTM 1290 Super Duke R / RR 2023 owner''s manual gives the same figures at 20 °C (PDF p. 161). The Yamaha XVS95CL owner''s manual, for its V-type 2-cylinder (PDF p. 82), gives the owner no figure: the clearance is checked and adjusted when the engine is cold every 16000 mi (25000 km), by a Yamaha dealer (PDF p. 45).',
             'Treat each cylinder as its own job: bring each to TDC on its own compression stroke and measure its valves against the figure for that side — that method is the template''s own; the KTM manuals give one figure set for all valves (KTM 1190 Adventure, PDF p. 209). The KTM 1190 Adventure''s service schedule checks the clearance with the air filter and spark plugs removed (PDF p. 103). On the Yamaha XVS95CL, the owner''s manual sends the job to a Yamaha dealer (PDF p. 58).',
             'Both cylinders'' valves within the machine''s own figures.',
             'One cylinder measured and the other assumed; a figure from another V-twin used.',
             'The two KTM V-twins share one figure set (KTM 1190 Adventure, PDF p. 209; KTM 1290 Super Duke R, PDF p. 161); other V-twins take theirs from their own manual.',
             0, '["feeler gauge","socket set"]', 60),

            ((SELECT id FROM workflow_templates WHERE slug='valve_adjustment_v1'), 8,
             'Inline-four, boxer twin and desmodromic engines — no figure in the library',
             'No document in the research library gives a valve clearance figure for an inline-four or a boxer twin, and none covers a desmodromic valve train. What the documents do give: the Yamaha YZFR6L owner''s manual checks and adjusts the clearance when the engine is cold every 26600 mi (42000 km), by a Yamaha dealer (PDF p. 60); the BMW K 1200 RS Maintenance Instructions describe bucket-type tappets under two chain-driven overhead camshafts (PDF p. 63); the BMW R 1100 S Service and Technical Booklet describes tappets and short pushrods (PDF p. 80) and schedules "Check/adjust valve clearances" (PDF p. 7).',
             'Items 1 to 6 are the shape of the job on any engine, but the figures, the timing marks and the adjustment method are the machine''s own, and for these engine types they are not in the research library: take them from the machine''s own service manual. Do not use a single-cylinder or V-twin figure from this template on these engines.',
             'The machine''s own service manual in hand before the valve cover comes off.',
             'A clearance figure borrowed from another machine.',
             'Without the maker''s figure there is no pass or fail reading: the job waits for the manual (the template''s own rule).',
             0, '[]', 5);
        """,
        rollback_sql="""
            DELETE FROM checklist_items
             WHERE template_id IN (SELECT id FROM workflow_templates
                                    WHERE slug IN ('winterization_v1', 'de_winterization_v1',
                                                   'engine_break_in_v1', 'valve_adjustment_v1'));

            DELETE FROM workflow_templates
             WHERE slug IN ('winterization_v1', 'de_winterization_v1',
                            'engine_break_in_v1', 'valve_adjustment_v1');

            UPDATE workflow_templates
               SET description = 'Seasonal storage: fuel stabilization, battery tender, oil change, storage position. Track N phase 264 expands.',
                   updated_at = CURRENT_TIMESTAMP
             WHERE slug = 'generic_winterization_v1';

            -- The F160 text back: the specific phrase first, then the rest.
            UPDATE checklist_items
               SET title = replace(replace(title, 'The YW125Y manual''s', 'The Zuma manual''s'), 'YW125Y', 'Zuma 125'),
                   description = replace(replace(description, 'The YW125Y manual''s', 'The Zuma manual''s'), 'YW125Y', 'Zuma 125'),
                   instruction_text = replace(replace(instruction_text, 'The YW125Y manual''s', 'The Zuma manual''s'), 'YW125Y', 'Zuma 125'),
                   expected_pass = replace(replace(expected_pass, 'The YW125Y manual''s', 'The Zuma manual''s'), 'YW125Y', 'Zuma 125'),
                   expected_fail = replace(replace(expected_fail, 'The YW125Y manual''s', 'The Zuma manual''s'), 'YW125Y', 'Zuma 125'),
                   diagnosis_if_fail = replace(replace(diagnosis_if_fail, 'The YW125Y manual''s', 'The Zuma manual''s'), 'YW125Y', 'Zuma 125')
             WHERE template_id = (SELECT id FROM workflow_templates WHERE slug = 'ppi_chassis_v1');
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

        # Phase 244F: a migration whose backfill needs parsing runs it here,
        # inside the same transaction as its DDL. Running it afterwards would
        # leave a window in which the table exists and is empty, and an empty
        # index is indistinguishable from a corpus that says nothing.
        if migration.post_apply:
            module_name, _, func_name = migration.post_apply.partition(":")
            import importlib

            func = getattr(importlib.import_module(module_name), func_name)
            func(conn)

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
