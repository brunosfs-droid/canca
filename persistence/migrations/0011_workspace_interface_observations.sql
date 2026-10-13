-- Opt-in R03 workspace-scoped historical interface observations.
DO $$ BEGIN
 IF NOT pg_try_advisory_xact_lock(-2660897858987708572::bigint) THEN
  RAISE EXCEPTION 'workspace coordinator is active' USING ERRCODE='55006';
 END IF;
END $$;
CREATE TABLE canca.workspace_interface_observations (
 workspace_id text NOT NULL REFERENCES canca.workspaces,
 collection_id text NOT NULL,
 observation_id text NOT NULL CHECK (observation_id ~ '^ifobs-[0-9a-f]{32}$'),
 source_asset_id text NOT NULL,
 source_path text NOT NULL,
 source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
 interface_ordinal integer NOT NULL CHECK (interface_ordinal BETWEEN 0 AND 255),
 interface_alias text NOT NULL CHECK (length(interface_alias) BETWEEN 1 AND 256),
 ipv4_address inet NOT NULL CHECK (family(ipv4_address)=4),
 prefix_length smallint NOT NULL CHECK (prefix_length BETWEEN 0 AND 32),
 observed_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
 PRIMARY KEY (workspace_id,collection_id,observation_id)
);
CREATE INDEX workspace_interface_obs_asset_idx
 ON canca.workspace_interface_observations(workspace_id,source_asset_id,collection_id);
ALTER TABLE canca.workspace_interface_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE canca.workspace_interface_observations FORCE ROW LEVEL SECURITY;
CREATE POLICY interface_observation_read ON canca.workspace_interface_observations
 FOR SELECT USING (workspace_id=current_setting('canca.workspace_id',true)
                   AND canca.workspace_model_allowed(false));
CREATE POLICY interface_observation_write ON canca.workspace_interface_observations
 FOR INSERT WITH CHECK (workspace_id=current_setting('canca.workspace_id',true)
                        AND canca.workspace_model_allowed(true));
-- No UPDATE/DELETE policies; observations are append-only.
-- No broad grants: DB role grants must be separately audited before rollout.
