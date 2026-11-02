import importlib.util
import pathlib
import unittest
from unittest.mock import patch

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / 'network_discovery' / 'P01_Network_Discovery_Scanner.py'
spec = importlib.util.spec_from_file_location('p01_network_discovery', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ScopeTests(unittest.TestCase):
    def test_cidr_and_exclusion(self):
        scope, excluded = mod.resolve_scope(['192.168.10.0/30'], ['192.168.10.2'])
        self.assertEqual(scope, ['192.168.10.1'])
        self.assertEqual(excluded, ['192.168.10.2'])

    def test_shorthand_range(self):
        values = [str(x) for x in mod.expand_ipv4_expression('192.168.1.10-12')]
        self.assertEqual(values, ['192.168.1.10', '192.168.1.11', '192.168.1.12'])

    def test_port_profile(self):
        safe = mod.parse_ports(None, 'safe')
        standard = mod.parse_ports(None, 'standard')
        self.assertIn(445, safe)
        self.assertIn(8291, standard)
        self.assertGreater(len(standard), len(safe))


class ClassificationTests(unittest.TestCase):
    def test_windows_classification(self):
        device, os_guess, confidence, evidence = mod.classify_asset(
            '192.168.1.10', 'pc01', {135, 445, 3389}, [], [], {'default_gateways': []}
        )
        self.assertEqual(device, 'Windows Host')
        self.assertEqual(os_guess, 'Windows')
        self.assertEqual(confidence, 'High')
        self.assertTrue(evidence)

    def test_printer_classification(self):
        device, _, confidence, _ = mod.classify_asset(
            '192.168.1.50', None, {9100}, [], [], {'default_gateways': []}
        )
        self.assertEqual(device, 'Printer')
        self.assertEqual(confidence, 'High')

    def test_gateway_classification(self):
        device, _, confidence, _ = mod.classify_asset(
            '192.168.1.1', None, {80, 443}, [], [], {'default_gateways': ['192.168.1.1']}
        )
        self.assertEqual(device, 'Router/Gateway')
        self.assertEqual(confidence, 'High')


    def test_mac_address_type(self):
        self.assertEqual(mod.mac_address_type("92:9A:4A:05:80:77"), "Locally Administered")
        self.assertEqual(mod.mac_address_type("00:D7:6D:74:79:17"), "Universally Administered")

    def test_same_mac_multiple_ips_correlation(self):
        assets = [
            {"ip": "192.168.15.7", "mac": "92:9A:4A:05:80:77"},
            {"ip": "192.168.15.102", "mac": "92:9A:4A:05:80:77"},
            {"ip": "192.168.15.9", "mac": "34:C6:DD:93:7B:12"},
        ]
        correlations = mod.build_mac_correlations(assets)
        self.assertEqual(len(correlations), 1)
        self.assertEqual(correlations[0]["ips"], ["192.168.15.7", "192.168.15.102"])
        self.assertFalse(correlations[0]["automatic_deduplication"])



class HTTPSProbeSecurityTests(unittest.TestCase):
    def test_https_probe_uses_verified_default_context(self):
        class FakeResponse:
            status = 200
            reason = "OK"
            def getheader(self, key): return None
        class FakeConnection:
            sock = None
            def __init__(self, *args, **kwargs):
                self.context = kwargs.get("context")
            def request(self, *args, **kwargs): pass
            def getresponse(self): return FakeResponse()
            def close(self): pass
        with patch.object(mod.ssl, "create_default_context", return_value="VERIFIED") as factory, \
             patch.object(mod.http.client, "HTTPSConnection", FakeConnection):
            result = mod.http_probe("192.0.2.10", 443, tls=True, timeout=1)
        factory.assert_called_once_with()
        self.assertEqual(result["tls_certificate_validation"], "required")
        self.assertEqual(result["http_status"], 200)

    def test_https_certificate_error_is_observed_without_unsafe_retry(self):
        class RejectConnection:
            def __init__(self, *args, **kwargs): pass
            def request(self, *args, **kwargs):
                raise mod.ssl.SSLCertVerificationError("certificate verification failed")
            def close(self): pass
        with patch.object(mod.http.client, "HTTPSConnection", RejectConnection), \
             patch.object(mod.ssl, "_create_unverified_context", side_effect=AssertionError("unsafe fallback")):
            result = mod.http_probe("192.0.2.10", 443, tls=True, timeout=1)
        self.assertEqual(result["tls_certificate_validation"], "required")
        self.assertIn("probe_error", result)
        self.assertNotIn("http_status", result)


if __name__ == '__main__':
    unittest.main()
