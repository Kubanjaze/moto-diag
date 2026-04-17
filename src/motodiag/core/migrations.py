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
