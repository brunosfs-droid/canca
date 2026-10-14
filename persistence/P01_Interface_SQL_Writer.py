"""Verified, append-only interface observation SQL writer (opt-in migration v11).

Requires a live workspace-scoped write lease and caller-provided trusted root.
No physical interface identity or topology links are inferred.
"""
import P01_PostgreSQL as pg
import P01_Workspace_Model as model
import P01_Verified_Interface_Inventory as inventory
import P01_Interface_Observation_Identity as identity

def persist_verified_interfaces(conn, workspace_id, token, store, import_dir, collection_id, *, limit=100, before_commit=None):
    model.token_args(workspace_id,token)
    model.require(type(collection_id) is str and 1<=len(collection_id)<=256)
    model.require(type(limit) is int and 1<=limit<=100)
    pg.require(before_commit is None or callable(before_commit),'model_input_invalid')
    data=inventory.inventory(store,import_dir,limit=limit)
    grouped={}
    for item in data["interfaces"]:
        grouped.setdefault(item["source_sha256"],[]).append(item)
    rows=[]
    for sha,items in sorted(grouped.items()):
        rows.extend(identity.observation_keys(workspace_id,collection_id,sha,items))
    projection=inventory.registry.prepare_assets(store,import_dir)
    owners={}
    for obs in projection["observations"]:
        for ref in obs["source_refs"]:
            if ref["role"]=="credentialed_evidence":
                owners.setdefault((ref["path"],ref["sha256"]),set()).add(obs["source_asset_id"])
    pending=[]
    seen_ids=set()
    for item in rows:
        # Duplicate IDs inside one verified batch are ambiguous, even when
        # ON CONFLICT would otherwise silently turn them into a replay.
        pg.require(item['observation_id'] not in seen_ids,'model_import_conflict')
        seen_ids.add(item['observation_id'])
        matching=owners.get((item["source_path"],item["source_sha256"]),set())
        pg.require(len(matching)==1,"model_import_conflict")
        pending.append((item,next(iter(matching))))
    # All verified evidence is validated before the first database write.
    # The transaction rolls back the entire collection on any failure.
    inserted=0
    with model.scope(conn,workspace_id,token,writing=True):
        pg.schema_check(conn,minimum=11,interfaces=True)
        for item,source_asset_id in pending:
            values=(workspace_id,collection_id,item["observation_id"],source_asset_id,
                    item["source_path"],item["source_sha256"],item["interface_ordinal"],
                    item["interface_alias"],item["address"],item["prefix_length"])
            result=conn.execute(
                "INSERT INTO canca.workspace_interface_observations "
                "(workspace_id,collection_id,observation_id,source_asset_id,"
                "source_path,source_sha256,interface_ordinal,interface_alias,"
                "ipv4_address,prefix_length) VALUES "
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (workspace_id,collection_id,observation_id) DO NOTHING "
                "RETURNING observation_id",values).fetchone()
            if result is not None:
                inserted+=1
            else:
                prior=conn.execute(
                    "SELECT source_asset_id,source_path,source_sha256,"
                    "interface_ordinal,interface_alias,host(ipv4_address),prefix_length "
                    "FROM canca.workspace_interface_observations "
                    "WHERE workspace_id=%s AND collection_id=%s AND observation_id=%s",
                    (workspace_id,collection_id,item["observation_id"])).fetchone()
                pg.require(prior==values[3:],"model_import_conflict")
        if before_commit is not None:
            before_commit()
    return dict(status="persisted",workspace_id=workspace_id,
                collection_id=collection_id,observation_count=len(rows),inserted_count=inserted)
