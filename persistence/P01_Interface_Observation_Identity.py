"""Stable evidence-scoped identity for verified interface observations.

The identity denotes an observation within one collection, not physical-device
identity or proof of topology membership.
"""
import hashlib
import json

def observation_keys(workspace_id, collection_id, source_sha256, interfaces):
    for value in (workspace_id,collection_id):
        if type(value) is not str or not value or len(value)>256:
            raise ValueError("interface_identity_invalid")
    if type(source_sha256) is not str or len(source_sha256)!=64 or any(c not in "0123456789abcdef" for c in source_sha256):
        raise ValueError("interface_identity_invalid")
    if type(interfaces) is not list or len(interfaces)>6400:
        raise ValueError("interface_identity_invalid")
    rows=[]
    for item in interfaces:
        if type(item) is not dict or type(item.get("interface_ordinal")) is not int or item["interface_ordinal"]<0 or item.get("source_sha256")!=source_sha256:
            raise ValueError("interface_identity_invalid")
        if type(item.get("address")) is not str or type(item.get("prefix_length")) is not int or not 0<=item["prefix_length"]<=32:
            raise ValueError("interface_identity_invalid")
        import ipaddress
        try:
            address=str(ipaddress.IPv4Address(item["address"]))
        except ipaddress.AddressValueError:
            raise ValueError("interface_identity_invalid") from None
        key=[workspace_id,collection_id,source_sha256,item["interface_ordinal"],address,item["prefix_length"]]
        digest=hashlib.sha256(json.dumps(key,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        rows.append(dict(item,observation_id="ifobs-"+digest[:32],workspace_id=workspace_id,
                         collection_id=collection_id,identity_scope="observation_only"))
    return rows
