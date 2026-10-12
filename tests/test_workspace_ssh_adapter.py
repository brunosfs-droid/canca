"""R02 fenced real SSH family adapter: deterministic blocked I/O, no network."""
import sys
import threading
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
import P01_Workspace_Service as service
import P01_Workspace_SSH_Adapter as adapter
import test_workspace_coordinator as fixtures

pg = service.pg


class SSHCoordinatorTests(unittest.TestCase):
    setUp = fixtures.CoordinatorTests.setUp
    cleanup = fixtures.CoordinatorTests.cleanup
    opened = fixtures.CoordinatorTests.opened

    def test_fenced_private_ssh_evidence_export_and_cleanup(self):
        token = self.opened()
        with tempfile.TemporaryDirectory() as directory:
            with self.c.borrow("writer", token, "workspace:write") as op:
                receipt = adapter.export_verified_ssh_evidence(
                    op, directory, "lab-ssh", {"collection_status": "collected"})
                path = Path(directory) / receipt["filename"]
                self.assertTrue(path.is_file())
                self.assertFalse(receipt["bundle_created"])
                self.assertEqual(receipt["workspace_id"], "A")
                self.assertEqual(list(Path(directory).glob("*.tmp")), [])
            self.c.close("writer", "A", token.generation, timeout=0)
            self.opened("B")
            with self.assertRaisesRegex(pg.PersistenceError, "workspace_generation_stale"):
                with self.c.borrow("writer", token, "workspace:write") as op:
                    adapter.export_verified_ssh_evidence(op, directory, "old", {})

    def test_cancel_between_export_write_and_publish_removes_artifact(self):
        token = self.opened()
        with tempfile.TemporaryDirectory() as directory:
            with self.c.borrow("writer", token, "workspace:write") as op:
                before = op.check
                count = [0]
                def cancelled_after_write():
                    count[0] += 1
                    if count[0] >= 3:
                        raise pg.PersistenceError("workspace_generation_stale")
                    return before()
                with patch.object(op, "check", side_effect=cancelled_after_write):
                    with self.assertRaisesRegex(pg.PersistenceError, "workspace_generation_stale"):
                        adapter.export_verified_ssh_evidence(op, directory, "lab", {"a": 1})
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_live_ssh_families_are_bound_to_workspace(self):
        token = self.opened()
        obj = service.WorkspaceService(self.c, service.SourceRoots({}))
        with patch.object(adapter.ssh, "run_first_success",
                          return_value={"success": True, "selected_command": "hostname"}):
            result = obj.ssh_read_only("reader", token, object())
        self.assertEqual(result["workspace_id"], "A")
        self.assertEqual(result["generation"], token.generation)
        self.assertFalse(result["raw_output_persisted"])
        self.assertFalse(self.c._jobs)

    def test_revoked_actor_never_invokes_collector(self):
        token = self.opened()
        obj = service.WorkspaceService(self.c, service.SourceRoots({}))
        self.grants["reader"].clear()
        with patch.object(adapter.ssh, "run_first_success") as run:
            with self.assertRaisesRegex(pg.PersistenceError, "workspace_access_denied"):
                obj.ssh_read_only("reader", token, object())
            run.assert_not_called()

    def test_cancellation_closes_blocked_ssh_transport(self):
        token = self.opened()
        obj = service.WorkspaceService(self.c, service.SourceRoots({}))
        entered, released = threading.Event(), threading.Event()
        result, errors = [], []
        class Transport:
            def close(self):
                released.set()
        transport = Transport()
        def blocked_run(*args):
            entered.set()
            if not released.wait(3):
                raise RuntimeError("transport was not closed on cancellation")
            return {"success": False, "selected_command": None}
        def work():
            try:
                result.append(obj.ssh_read_only("writer", token, transport))
            except pg.PersistenceError as exc:
                errors.append(str(exc))
        with patch.object(adapter.ssh, "run_first_success", side_effect=blocked_run):
            worker = threading.Thread(target=work)
            worker.start()
            self.assertTrue(entered.wait(3))
            with self.assertRaisesRegex(pg.PersistenceError, "workspace_close_pending"):
                self.c.close("writer", "A", token.generation, timeout=0)
            worker.join(3)
        self.assertTrue(released.is_set())
        self.assertFalse(worker.is_alive())
        self.assertFalse(result)
        self.assertEqual(errors, ["workspace_generation_stale"])
        self.assertFalse(self.c._jobs)

    def test_auth_denied_before_credentials_or_connect(self):
        token = self.opened()
        obj = service.WorkspaceService(self.c, service.SourceRoots({}))
        self.grants["reader"].clear()
        with patch.object(adapter.ssh, "connect_with_profile") as connect:
            with self.assertRaisesRegex(pg.PersistenceError, "workspace_access_denied"):
                obj.ssh_authenticated("reader", token, "192.168.100.10", 22,
                                      object(), Path("known_hosts"))
            connect.assert_not_called()

    def test_cancellation_during_authentication_discards_result(self):
        token = self.opened()
        obj = service.WorkspaceService(self.c, service.SourceRoots({}))
        entered, release = threading.Event(), threading.Event()
        results, errors = [], []
        def blocked_connect(*args, **kwargs):
            entered.set()
            if not release.wait(3):
                raise RuntimeError("synthetic timeout")
            return ({"success": True, "result": "authenticated"}, {"private": "not-published"})
        def worker():
            try:
                results.append(obj.ssh_authenticated(
                    "writer", token, "192.168.100.10", 22,
                    object(), Path("known_hosts")))
            except pg.PersistenceError as exc:
                errors.append(str(exc))
        with patch.object(adapter.ssh, "connect_with_profile", side_effect=blocked_connect):
            thread = threading.Thread(target=worker)
            thread.start()
            self.assertTrue(entered.wait(3))
            with self.assertRaisesRegex(pg.PersistenceError, "workspace_close_pending"):
                self.c.close("writer", "A", token.generation, timeout=0)
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results, [])
        self.assertEqual(errors, ["workspace_generation_stale"])
        self.assertFalse(self.c._jobs)

    def test_close_during_ssh_io_drops_result_before_publication(self):
        token = self.opened()
        obj = service.WorkspaceService(self.c, service.SourceRoots({}))
        entered, release = threading.Event(), threading.Event()
        result, errors = [], []
        def slow_run(*args):
            entered.set()
            if not release.wait(3):
                raise RuntimeError("synthetic I/O timeout")
            return {"success": True, "selected_command": "hostname"}
        def work():
            try: result.append(obj.ssh_read_only("writer", token, object()))
            except pg.PersistenceError as exc: errors.append(str(exc))
        with patch.object(adapter.ssh, "run_first_success", side_effect=slow_run):
            worker = threading.Thread(target=work)
            worker.start()
            self.assertTrue(entered.wait(3))
            try:
                with self.assertRaisesRegex(pg.PersistenceError, "workspace_close_pending"):
                    self.c.close("writer", "A", token.generation, timeout=0)
            finally:
                release.set()
                worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(result, [])
        self.assertEqual(errors, ["workspace_generation_stale"])
        self.assertFalse(self.c._jobs)
        self.c.close("writer", "A", self.c.generation, timeout=0)
        self.opened("B")
        with self.assertRaisesRegex(pg.PersistenceError, "workspace_generation_stale"):
            obj.ssh_read_only("writer", token, object())


if __name__ == "__main__":
    unittest.main()
