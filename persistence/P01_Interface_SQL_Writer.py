"""Verified, append-only interface observation SQL writer (opt-in migration v11).

Requires a live workspace-scoped write lease and caller-provided trusted root.
No physical interface identity or topology links are inferred.
"""
from pathlib import Path
import P01_PostgreSQL as pg
import P01_Workspace_Model as model
import P01_Verified_Interface_Inventory as inventory
import P01_Interface_Observation_Identity as identity

def persist_verified_interfaces(conn, workspace_id, token, store, import_dir, collection_id, *, limit=100):
    model.token_args(workspace_id,token)
    model.require(type(collection_id) is str and 1<=len(collection_id)<=256)
    model.require(type(limit) is int and 1<=limit<=100)
    data=inventory.inventory(store,import_dir,limit=limit)
    grouped={}
    for item in data["interfaces"]:
        grouped.setdefault(item["source_sha256"],[]).append(item)
    rows=[]
    for sha,items in sorted(grouped.items()):
        rows.extend(identity.observation_keys(workspace_id,collection_id,sha,items))
    # All evidence bytes and identity checks precede the first SQL write.
    with model.scope(conn,workspace_id,token,writing=True):
        pg.schema_check(conn,minimum=11,interfaces=True)
        for item in rows:
            source_refs=inventory.registry.prepare_assets(store,import_dir)["observations"]
            owning={obs["source_asset_id"] for obs in source_refs
                    if any(ref["role"]=="credentialed_evidence"
                           and ref["path"]==item["source_path"]
                           and ref["sha256"]==item["source_sha256"]
                           for ref in obs["source_refs"])}
            pg.require(len(owning)==1,"model_import_conflict")
            source_asset_id=owning.pop()
            conn.execute(
                "INSERT INTO canca.workspace_interface_observations "
                "(workspace_id,collection_id,observation_id,source_asset_id,"
                "source_path,source_sha256,interface_ordinal,interface_alias,"
                "ipv4_address,prefix_length) VALUES "
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (workspace_id,collection_id,item["observation_id"],source_asset_id,
                 item["source_path"],item["source_sha256"],item["interface_ordinal"],
                 item["interface_alias"],item["address"],item["prefix_length"]))
    return dict(status="persisted",workspace_id=workspace_id,
                collection_id=collection_id,observation_count=len(rows))
