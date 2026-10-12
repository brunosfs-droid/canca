"""Bounded, evidence-only network candidates; no topology inference or SQL writes."""
import ipaddress
import re

_MAC = re.compile(r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")


def project_network_assets(network_document):
    """Extract per-asset observed addresses from a previously verified source document.

    Caller must validate bundle integrity, trust and workspace partition before use.
    These are observations, never asserted device ownership or inferred graph edges.
    """
    if type(network_document) is not dict or type(network_document.get("assets")) is not list:
        raise ValueError("network_document_invalid")
    assets = network_document["assets"]
    if len(assets) > 1000:
        raise ValueError("network_document_invalid")
    result = []
    for ordinal, asset in enumerate(assets):
        if type(asset) is not dict:
            raise ValueError("network_asset_invalid")
        address = asset.get("ip")
        if type(address) is not str:
            raise ValueError("network_asset_invalid")
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            raise ValueError("network_asset_invalid") from None
        if parsed.version != 4:
            raise ValueError("network_asset_invalid")
        mac = asset.get("mac")
        if mac is not None and (type(mac) is not str or not _MAC.fullmatch(mac)):
            raise ValueError("network_asset_invalid")
        result.append({
            "source_asset_ordinal": ordinal,
            "address_family": "ipv4",
            "observed_ip": str(parsed),
            "observed_mac": mac.lower() if mac is not None else None,
            "origin": "observed",
            "ownership_confirmed": False,
            "graph_edges": [],
        })
    return result


def project_verified_network_observations(projection):
    """Use registry-verified source references, never raw unauthenticated asset input.

    The caller still owns workspace authorization and matching the imported store.
    IP and MAC evidence do not prove topology, port ownership or asset identity.
    """
    import P01_Asset_Registry as registry
    registry.validate_projection(projection)
    result = []
    for observation in projection["observations"]:
        refs = {ref["path"] for ref in observation["source_refs"]
                if ref["role"] == "network_discovery"}
        for signal in observation["signals"]:
            if signal["kind"] not in ("ip", "mac") or signal["qualified"]:
                continue
            origin_paths = sorted(refs.intersection(signal["sources"]))
            if not origin_paths:
                continue
            result.append({
                "source_asset_id": observation["source_asset_id"],
                "kind": signal["kind"],
                "value": signal["value"],
                "source_paths": origin_paths,
                "origin": "observed",
                "ownership_confirmed": False,
                "graph_edges": [],
            })
    return result
