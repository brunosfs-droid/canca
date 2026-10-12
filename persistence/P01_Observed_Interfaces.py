"""Bounded read-only projection of credentialed interface evidence."""
from ipaddress import IPv4Address

def project_interfaces(enrichment, source_path, source_sha256):
    if not isinstance(enrichment,dict) or enrichment.get("collection_status")!="collected":
        raise ValueError("interface_evidence_invalid")
    network=enrichment.get("network")
    interfaces=network.get("interfaces") if isinstance(network,dict) else None
    if not isinstance(interfaces,list) or len(interfaces)>256 or not isinstance(source_path,str) or not source_path or not isinstance(source_sha256,str) or len(source_sha256)!=64 or any(ch not in "0123456789abcdef" for ch in source_sha256):
        raise ValueError("interface_evidence_invalid")
    out=[]
    for ordinal,interface in enumerate(interfaces):
        if not isinstance(interface,dict):
            raise ValueError("interface_evidence_invalid")
        alias=interface.get("interface_alias")
        ipv4=interface.get("ipv4",[])
        if not isinstance(alias,str) or not 1<=len(alias)<=256 or any(ord(c)<32 for c in alias) or not isinstance(ipv4,list) or len(ipv4)>64:
            raise ValueError("interface_evidence_invalid")
        for item in ipv4:
            if not isinstance(item,dict) or type(item.get("address")) is not str or type(item.get("prefix_length")) is not int or not 0<=item["prefix_length"]<=32:
                raise ValueError("interface_evidence_invalid")
            try:
                ip=str(IPv4Address(item["address"]))
            except ValueError:
                raise ValueError("interface_evidence_invalid") from None
            out.append(dict(interface_ordinal=ordinal,interface_alias=alias,address=ip,
                            prefix_length=item["prefix_length"],source_path=source_path,
                            source_sha256=source_sha256,origin="observed",
                            ownership_confirmed=False,graph_edges=[]))
    return out
