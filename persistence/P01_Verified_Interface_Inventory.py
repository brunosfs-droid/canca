"""Batch interface projection from an independently verified import."""
import P01_Asset_Registry as registry
import P01_Verified_Interfaces as reader
import P01_PostgreSQL as pg

def inventory(store, import_dir, *, limit=100):
    pg.require(type(limit) is int and 1 <= limit <= 100, "asset_input_invalid")
    projection=registry.prepare_assets(store,import_dir)
    refs=sorted({(ref["path"],ref["sha256"])
                 for obs in projection["observations"]
                 for ref in obs["source_refs"]
                 if ref["role"]=="credentialed_evidence"})
    pg.require(len(refs)<=limit,"asset_input_invalid")
    rows=[]
    for path,sha in refs:
        rows.extend(reader.read_verified_interfaces(store,import_dir,path,sha))
        pg.require(len(rows)<=6400,"asset_input_invalid")
    return {"sources":len(refs),"interfaces":rows,"persistence_state":"not_persisted",
            "topology_edges_created":0}
