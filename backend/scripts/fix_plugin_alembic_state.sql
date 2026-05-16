
*-- One-time recovery for the plugin-migration refactor.
--
-- The old installer mixed plugin branch heads into the main `alembic_version`
-- table and then tried to "restore" the main head with a destructive UPDATE.
-- After the refactor each plugin owns its own `alembic_version_<name>` table,
-- so we need to:
--
--   1. Confirm the main `alembic_version` row contains exactly the main head.
--   2. Drop any orphaned plugin tables from a half-finished install, OR
--      adopt them by inserting the head revision into the new per-plugin
--      version table (only if the plugin is already installed and its tables
--      are intact).
--
-- Run this BEFORE re-installing any plugin after deploying the refactor.

BEGIN;

-- ──────────────────────────────────────────────────────────────────────────
-- A) Diagnose current state. Inspect manually before continuing.
-- ──────────────────────────────────────────────────────────────────────────
-- SELECT * FROM alembic_version;
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public'
--   AND (tablename LIKE 'srp_%'
--     OR tablename LIKE 'fleet_action_%'
--     OR tablename LIKE 'helm_mcp_%'
--     OR tablename LIKE 'alembic_version_%');


-- ──────────────────────────────────────────────────────────────────────────
-- B) Reset main alembic_version to exactly one row (the main head).
--    Replace <MAIN_HEAD> with `alembic heads` output from `backend/`.
-- ──────────────────────────────────────────────────────────────────────────
-- DELETE FROM alembic_version;
-- INSERT INTO alembic_version (version_num) VALUES ('<MAIN_HEAD>');


-- ──────────────────────────────────────────────────────────────────────────
-- C) For each plugin: choose ONE of the following branches.
-- ──────────────────────────────────────────────────────────────────────────

-- C-1) Plugin tables exist & are healthy → adopt them into a new version table.
--      This avoids re-running the initial migration on top of existing tables.
--
--      SRP example (head revision = '0001srp'):
-- CREATE TABLE IF NOT EXISTS alembic_version_srp (
--     version_num VARCHAR(32) NOT NULL,
--     CONSTRAINT alembic_version_srp_pkc PRIMARY KEY (version_num)
-- );
-- INSERT INTO alembic_version_srp (version_num) VALUES ('0001srp')
--   ON CONFLICT DO NOTHING;
--
--      fleet-action (current head = '0002fleet_action'):
-- CREATE TABLE IF NOT EXISTS alembic_version_fleet_action (
--     version_num VARCHAR(32) NOT NULL,
--     CONSTRAINT alembic_version_fleet_action_pkc PRIMARY KEY (version_num)
-- );
-- INSERT INTO alembic_version_fleet_action (version_num)
--   VALUES ('0002fleet_action')
--   ON CONFLICT DO NOTHING;
--
--      helm-mcp (head = '0001helm_mcp'):
-- CREATE TABLE IF NOT EXISTS alembic_version_helm_mcp (
--     version_num VARCHAR(32) NOT NULL,
--     CONSTRAINT alembic_version_helm_mcp_pkc PRIMARY KEY (version_num)
-- );
-- INSERT INTO alembic_version_helm_mcp (version_num) VALUES ('0001helm_mcp')
--   ON CONFLICT DO NOTHING;


-- C-2) Plugin install was half-finished / never recovered → wipe its tables
--      and let the new installer recreate them cleanly.
--
--      SRP example:
-- DROP TABLE IF EXISTS srp_requests CASCADE;
-- DROP TABLE IF EXISTS srp_configs CASCADE;
-- DROP TYPE  IF EXISTS srp_status;
-- DROP TABLE IF EXISTS alembic_version_srp;
--
--      fleet-action:
-- DROP TABLE IF EXISTS fleet_action_pap_records CASCADE;
-- DROP TABLE IF EXISTS fleet_action_actions      CASCADE;
-- DROP TYPE  IF EXISTS fleet_action_status;
-- DROP TABLE IF EXISTS alembic_version_fleet_action;
--
--      helm-mcp:
-- DROP TABLE IF EXISTS helm_mcp_call_logs CASCADE;
-- DROP TABLE IF EXISTS alembic_version_helm_mcp;


COMMIT;
