-- R03 interface observations: proposed additive SQL schema (NOT registered as migration).
-- These are collection-scoped historical observations, never physical identity.
-- Activate only after RLS policy integration and migration validation.
CREATE TABLE IF NOT EXISTS canca.workspace_interface_observations (
  workspace_id text NOT NULL,
  collection_id text NOT NULL,
  observation_id text NOT NULL,
  source_asset_id text NOT NULL,
  source_path text NOT NULL,
  source_sha256 char(64) NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
  interface_ordinal integer NOT NULL CHECK (interface_ordinal >= 0),
  interface_alias text NOT NULL,
  ipv4_address inet NOT NULL CHECK (family(ipv4_address) = 4),
  prefix_length smallint NOT NULL CHECK (prefix_length BETWEEN 0 AND 32),
  observed_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
  PRIMARY KEY (workspace_id, collection_id, observation_id),
  FOREIGN KEY (workspace_id, collection_id)
    REFERENCES canca.workspace_collections(workspace_id, collection_id)
    ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS workspace_interface_observations_asset_idx
  ON canca.workspace_interface_observations(workspace_id, source_asset_id, collection_id);
ALTER TABLE canca.workspace_interface_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE canca.workspace_interface_observations FORCE ROW LEVEL SECURITY;
-- No policies/grants here deliberately: fail closed until approved migration.
