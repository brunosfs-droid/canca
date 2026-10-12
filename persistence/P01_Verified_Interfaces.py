"""Verified interface evidence reader: never trust caller-supplied enrichment."""
import hashlib
import json
import zipfile
from pathlib import Path
import P01_PostgreSQL as pg
import P01_Asset_Registry as registry
import P01_Observed_Interfaces as interfaces


def read_verified_interfaces(store, import_dir, source_path, source_sha256):
    """Return interface observations only from a verified imported bundle.

    The registry independently replays and validates the original receipt and
    bundle. This reader checks the requested entry's declared hash and content.
    """
    projection=registry.prepare_assets(store,import_dir)
    artifacts=projection["import"]["artifacts"]
    matches=[a for a in artifacts if a["role"]=="credentialed_evidence"
             and a["path"]==source_path and a["sha256"]==source_sha256]
    pg.require(len(matches)==1,"asset_input_invalid")
    receipt_path=pg.owned(Path(import_dir).resolve(),"receipt/import-receipt.json")
    receipt=pg.read_json(receipt_path.read_bytes())
    raw_path=pg.owned(Path(import_dir).resolve(),receipt["raw_bundle"])
    with zipfile.ZipFile(raw_path) as archive:
        entry=matches[0]
        pg.require(entry["size_bytes"]<=16*1024**2,"asset_input_invalid")
        with archive.open(entry["path"]) as source:
            raw=source.read(entry["size_bytes"]+1)
    pg.require(len(raw)==entry["size_bytes"] and hashlib.sha256(raw).hexdigest()==source_sha256,
               "bundle_integrity_failed")
    doc=pg.read_json(raw)
    import P01_Asset_Resolver as resolver
    _,enrichment,authentication,_=resolver._unwrap_credentialed(doc)
    pg.require(authentication.get("success") is True,"asset_input_invalid")
    rows=interfaces.project_interfaces(enrichment,source_path,source_sha256)
    return rows
