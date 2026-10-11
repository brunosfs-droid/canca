import importlib.util
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "credentialed_enrichment" / "P01_SSH_Enricher.py"
spec = importlib.util.spec_from_file_location("p01_ssh_enricher", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CommandPolicyTests(unittest.TestCase):
    def test_catalog_is_read_only(self):
        mod.validate_command_catalog()

    def test_mutating_command_is_rejected(self):
        self.assertFalse(mod.command_is_read_only("rm -rf /tmp/foo"))
        self.assertFalse(mod.command_is_read_only("systemctl restart sshd"))
        self.assertTrue(mod.command_is_read_only("ip -j address"))
        self.assertTrue(mod.command_is_read_only(mod.EXEC_PROBE_COMMAND))


class ExecCapabilityTests(unittest.TestCase):
    def test_probe_requires_expected_output(self):
        self.assertTrue(mod.exec_probe_has_output({
            "success": True,
            "stdout": "P01_EXEC_PROBE"
        }))
        self.assertFalse(mod.exec_probe_has_output({
            "success": True,
            "stdout": ""
        }))
        self.assertFalse(mod.exec_probe_has_output({
            "success": False,
            "stdout": "P01_EXEC_PROBE"
        }))


class InterfaceParserTests(unittest.TestCase):
    def test_ip_json_and_candidates(self):
        text = """[
          {"ifname":"lo","addr_info":[{"family":"inet","local":"127.0.0.1","prefixlen":8,"scope":"host"}]},
          {"ifname":"br-lan","address":"00:11:22:33:44:55",
           "addr_info":[{"family":"inet","local":"192.168.15.1","prefixlen":24,"scope":"global"}]},
          {"ifname":"guest","address":"00:11:22:33:44:66",
           "addr_info":[{"family":"inet","local":"192.168.50.1","prefixlen":24,"scope":"global"}]}
        ]"""
        interfaces = mod.parse_ip_json_interfaces(text)
        candidates = mod.build_candidate_networks(interfaces, [])
        nets = [x["network"] for x in candidates]
        self.assertEqual(nets, ["192.168.15.0/24", "192.168.50.0/24"])
        self.assertTrue(all(x["auto_scan"] is False for x in candidates))

    def test_ifconfig_busybox(self):
        text = """br0      Link encap:Ethernet  HWaddr 00:11:22:33:44:55
          inet addr:192.168.15.1  Bcast:192.168.15.255  Mask:255.255.255.0
eth1      Link encap:Ethernet  HWaddr 00:11:22:33:44:66
          inet addr:10.20.30.1  Bcast:10.20.30.255  Mask:255.255.255.0
"""
        interfaces = mod.parse_ifconfig_interfaces(text)
        candidates = mod.build_candidate_networks(interfaces, [])
        self.assertEqual([x["network"] for x in candidates], ["10.20.30.0/24", "192.168.15.0/24"])


class RouteParserTests(unittest.TestCase):
    def test_ip_route_text(self):
        rows = mod.parse_ip_route_text(
            "default via 192.168.15.1 dev eth0\n"
            "10.20.30.0/24 dev eth1 proto kernel src 10.20.30.1\n"
        )
        self.assertEqual(rows[0]["destination"], "default")
        self.assertEqual(rows[1]["destination"], "10.20.30.0/24")
        candidates = mod.build_candidate_networks([], rows)
        self.assertEqual([x["network"] for x in candidates], ["10.20.30.0/24"])


class SafetyTests(unittest.TestCase):
    def test_exception_redaction(self):
        value = mod._safe_exception_message(Exception("password=secret123 failed"))
        self.assertNotIn("secret123", value)
        self.assertIn("<redacted>", value)

    def test_secret_resolution_error_never_echoes_provider_exception(self):
        match = SimpleNamespace(
            profile={"id": "synthetic", "username": "tester", "auth_type": "password",
                     "secret_refs": {"password": "env://SYNTHETIC"}},
            matched_scope="192.0.2.0/24", prefix_length=24)
        provider = SimpleNamespace(resolve_secret=lambda *args, **kwargs:
                                   (_ for _ in ()).throw(RuntimeError("token=SECRET-MUST-NOT-LEAK")))
        with patch.object(mod, "paramiko", object()), patch.object(mod, "_credential_api", return_value=provider):
            attempt, result = mod.connect_with_profile(
                "192.0.2.1", 22, match, pathlib.Path("unused_known_hosts"),
                "strict", 1.0, 1.0, False)
        self.assertIsNone(result)
        self.assertEqual(attempt["result"], "secret_resolution_failed")
        self.assertEqual(attempt["error"], "credential_provider_unavailable")
        self.assertNotIn("SECRET-MUST-NOT-LEAK", str(attempt))

    def test_tofu_requires_explicit_operator_acknowledgement(self):
        arguments = ["--profiles", "synthetic.json", "--target", "192.0.2.10",
                     "--ack-authorized-access", "--host-key-policy", "tofu"]
        with self.assertRaises(SystemExit) as denied:
            mod.main(arguments)
        self.assertEqual(denied.exception.code, 2)
        # With explicit acknowledgement, argument validation allows provider setup.
        with patch.object(mod, "_credential_api", side_effect=RuntimeError("synthetic provider unavailable")) as provider:
            self.assertEqual(mod.main(arguments + ["--ack-tofu-host-key"]), 2)
            provider.assert_called_once()

    def test_command_exception_message_is_not_persisted(self):
        class BrokenSSH:
            def exec_command(self, *args, **kwargs):
                raise RuntimeError("SECRET-DO-NOT-LOG")
        result = mod._run_command(BrokenSSH(), "hostname", 1.0)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "ssh_operation_failed")
        self.assertNotIn("SECRET-DO-NOT-LOG", str(result))

    def test_stderr_is_not_persisted_in_command_evidence(self):
        def fake_run(client, family, timeout):
            return {"success": False, "result": {
                "command": mod.SAFE_COMMAND_FAMILIES[family][0],
                "success": False, "exit_status": 1, "stdout": "",
                "stderr": "SECRET-STDERR-DO-NOT-STORE",
                "stderr_truncated": False}}
        with patch.object(mod, "run_first_success", side_effect=fake_run):
            evidence = mod.collect_read_only(object(), 1.0)
        self.assertTrue(evidence["command_evidence"])
        self.assertNotIn("SECRET-STDERR-DO-NOT-STORE", str(evidence))
        self.assertTrue(all(row["stderr"] is None and row["stderr_present"]
                            for row in evidence["command_evidence"]))

    def test_public_network_never_auto_scans(self):
        interfaces = [{"ifname": "wan", "ipv4": [{"address": "203.0.113.10", "prefix_length": 24}]}]
        candidates = mod.build_candidate_networks(interfaces, [])
        self.assertEqual(len(candidates), 1)
        self.assertFalse(candidates[0]["auto_scan"])
        self.assertEqual(candidates[0]["authorization_status"], "unassessed")


if __name__ == "__main__":
    unittest.main()
