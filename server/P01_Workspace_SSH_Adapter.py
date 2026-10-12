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
