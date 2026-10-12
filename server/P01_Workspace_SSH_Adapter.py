"""Trusted R02 adapter for a pre-authenticated read-only SSH transport.

Internal-only: no public HTTP route or automatic credential resolution.
Transport ownership belongs to the trusted caller. Cancellation is checked at
I/O boundaries, and no result escapes after a stale lease. A blocking SSH
socket may still require its configured timeout; this is not an async kill.
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "credentialed_enrichment"))
import P01_Workspace_Coordinator as coordinator
import P01_SSH_Enricher as ssh

pg = coordinator.pg


def collect(operation, client, *, timeout=5.0):
    """Execute the real SSH read-only catalog under one live workspace operation."""
    pg.require(type(operation) is coordinator.Operation, "workspace_input_invalid")
    pg.require(type(timeout) in (float, int) and 0.5 <= timeout <= 30,
               "workspace_input_invalid")
    operation.check()
    original = ssh.run_first_success
    def fenced_first_success(transport, family, command_timeout):
        operation.check()
        stopped = threading.Event()
        def abort_on_cancel():
            # An active SSH channel may be blocked in network I/O. Closing the
            # transport wakes Paramiko; the caller still retains bounded timeouts.
            while not stopped.is_set():
                if operation.cancel.wait(0.02):
                    close = getattr(transport, "close", None)
                    if callable(close):
                        try:
                            close()
                        except Exception:
                            operation.coordinator.fail_closed()
                    return
        watcher = threading.Thread(target=abort_on_cancel, name="canca-r02-ssh-cancel", daemon=True)
        watcher.start()
        try:
            result = original(transport, family, command_timeout)
            operation.check()
            return result
        finally:
            stopped.set()
            watcher.join(timeout=1)
            if watcher.is_alive():
                operation.coordinator.fail_closed()
    # Do not monkeypatch shared SSH globals: call a scoped collector loop with
    # the same existing family parser and per-command contract.
    families = {}
    for family in ssh.SAFE_COMMAND_FAMILIES:
        operation.check()
        families[family] = fenced_first_success(client, family, timeout)
        operation.check()
    # Reuse the canonical parser with precomputed results, avoiding extra I/O.
    # The existing collector does not accept precomputed families yet.
    # Return only family status for this first bounded adapter slice.
    operation.check()
    return {
        "workspace_id": operation.token.workspace_id,
        "generation": operation.token.generation,
        "families": {name: {"success": bool(item.get("success")),
                             "selected_command": item.get("selected_command")}
                     for name, item in families.items()},
        "raw_output_persisted": False,
    }


def authenticate(operation, target, port, profile_match, known_hosts, *,
                 connect_timeout=5.0, command_timeout=5.0, collect_commands=False):
    """Internal, caller-authorized credentialed SSH; no HTTP/SQL publication."""
    import ipaddress
    pg.require(type(operation) is coordinator.Operation, "workspace_input_invalid")
    try:
        address = ipaddress.ip_address(target)
    except ValueError:
        raise pg.PersistenceError("workspace_input_invalid") from None
    pg.require(address.version == 4 and address.is_private and
               type(port) is int and 1 <= port <= 65535,
               "workspace_input_invalid")
    operation.check()
    attempt, evidence = ssh.connect_with_profile(
        target, port, profile_match, Path(known_hosts), "strict",
        connect_timeout, command_timeout, collect_commands,
        operation=operation)
    operation.check()
    # No raw SSH output or identity is published without an explicit
    # workspace-bound persistence schema and transactional generation fence.
    return {
        "workspace_id": operation.token.workspace_id,
        "generation": operation.token.generation,
        "success": bool(attempt.get("success")),
        "result": attempt.get("result"),
        "raw_output_persisted": False,
        "evidence_persisted": False,
    }


def export_verified_ssh_evidence(operation, output_dir, run_label, payload):
    """Internal staging export, not a workspace import bundle.

    Publish only after generation checks. The output is still sensitive private
    evidence and must be handled by the existing verified-bundle pipeline.
    """
    import os
    import json
    import tempfile
    import hashlib
    pg.require(type(operation) is coordinator.Operation, "workspace_input_invalid")
    pg.require(type(payload) is dict and type(run_label) is str, "workspace_input_invalid")
    output_dir = Path(output_dir)
    pg.require(output_dir.is_dir() and not output_dir.is_symlink(), "workspace_input_invalid")
    operation.check()
    label = ssh.safe_label(run_label)
    raw = (json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    pg.require(len(raw) <= 4 * 1024 * 1024, "workspace_input_invalid")
    name = "P01-SSH-Enrichment_" + label + "_" + hashlib.sha256(raw).hexdigest()[:16] + ".json"
    destination = output_dir / name
    pg.require(not destination.exists() and not destination.is_symlink(), "workspace_input_invalid")
    staging = None
    claimed = False
    try:
        with tempfile.NamedTemporaryFile(dir=output_dir, prefix=".canca-ssh-", suffix=".tmp",
                                         delete=False) as temp:
            staging = Path(temp.name)
            if os.name != "nt":
                os.chmod(staging, 0o600)
            temp.write(raw)
            temp.flush()
            os.fsync(temp.fileno())
        operation.check()
        # Exclusive creation prevents replacing an existing evidence artifact.
        with destination.open("xb") as final:
            claimed = True
            if os.name != "nt":
                os.chmod(destination, 0o600)
            final.write(staging.read_bytes())
            final.flush()
            os.fsync(final.fileno())
        operation.check()
        return {"workspace_id": operation.token.workspace_id,
                "generation": operation.token.generation,
                "filename": name, "sha256": hashlib.sha256(raw).hexdigest(),
                "bundle_created": False}
    except BaseException:
        if claimed:
            destination.unlink(missing_ok=True)
        raise
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)


def package_verified_ssh_bundle(operation, output, assessment_id, run_id, node_id,
                                network_path, credentialed_paths, manifest_path=None):
    """Build the official portable bundle from already verified private evidence.

    Internal operator-controlled paths only; no scanner, import, or HTTP route.
    Staging and exclusive publication prevent replacing unrelated outputs.
    """
    import os
    import tempfile
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evidence_bundle"))
    import P01_Evidence_Bundle as bundles

    pg.require(type(operation) is coordinator.Operation, "workspace_input_invalid")
    destination = Path(output)
    pg.require(destination.suffix == ".p01bundle" and destination.parent.is_dir()
               and not destination.parent.is_symlink()
               and not destination.exists(), "workspace_input_invalid")
    pg.require(type(credentialed_paths) in (list, tuple) and
               len(credentialed_paths) == 1, "workspace_input_invalid")
    operation.check()
    with tempfile.TemporaryDirectory(prefix=".canca-r02-bundle-", dir=destination.parent) as temp:
        staged = Path(temp) / destination.name
        result = bundles.create_bundle(
            staged, assessment_id, run_id, node_id, Path(network_path),
            [Path(p) for p in credentialed_paths],
            Path(manifest_path) if manifest_path is not None else None,
            require_evidence_sidecars=True)
        operation.check()
        verified = bundles.validate_bundle(staged)
        pg.require(verified.get("bundle_id") == result["bundle_id"],
                   "workspace_input_invalid")
        operation.check()
        sidecar = destination.with_suffix(destination.suffix + ".sha256")
        pg.require(not sidecar.exists(), "workspace_input_invalid")
        owned = []
        try:
            # Both hard links use exclusive create semantics. Remove any owned
            # partial pair when a cancellation or write failure occurs.
            os.link(staged, destination)
            owned.append(destination)
            operation.check()
            os.link(staged.with_suffix(staged.suffix + ".sha256"), sidecar)
            owned.append(sidecar)
            operation.check()
            return {"workspace_id": operation.token.workspace_id,
                    "generation": operation.token.generation,
                    "bundle_id": result["bundle_id"],
                    "bundle_sha256": result["bundle_sha256"],
                    "artifact_count": result["artifact_count"]}
        except BaseException:
            for item in reversed(owned):
                item.unlink(missing_ok=True)
            raise
