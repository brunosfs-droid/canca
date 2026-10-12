"""Network membership candidates from observed addresses, never topology edges."""
from ipaddress import IPv4Address, IPv4Network

def subnet_candidates(observations, *, prefix_length):
    """Group observed IPv4 addresses by a caller-supplied explicit prefix.

    IP-only discovery does not prove VLAN assignment, interfaces, site placement
    or device ownership. No graph edge may be created from this projection.
    """
    if type(prefix_length) is not int or not 0 <= prefix_length <= 32:
        raise ValueError("network_prefix_invalid")
    if type(observations) is not list or len(observations) > 1000:
        raise ValueError("network_observations_invalid")
    result=[]
    for item in observations:
        if type(item) is not dict or item.get("kind")!="ip" or item.get("origin")!="observed":
            raise ValueError("network_observations_invalid")
        if type(item.get("source_asset_id")) is not str or not item["source_asset_id"]:
            raise ValueError("network_observations_invalid")
        if type(item.get("source_paths")) is not list or not item["source_paths"] or any(type(p) is not str or not p for p in item["source_paths"]):
            raise ValueError("network_observations_invalid")
        try:
            address=IPv4Address(item["value"])
        except (ValueError,TypeError):
            raise ValueError("network_observations_invalid") from None
        network=IPv4Network((address,prefix_length),strict=False)
        result.append(dict(source_asset_id=item["source_asset_id"],
                           observed_ip=str(address),candidate_subnet=str(network),
                           prefix_source="operator_supplied",source_paths=sorted(set(item["source_paths"])),
                           status="candidate",vlan_id=None,ownership_confirmed=False,
                           graph_edges=[]))
    return result
