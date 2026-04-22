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
