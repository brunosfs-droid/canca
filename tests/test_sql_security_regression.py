"""Regression tests for Bandit B608 dynamic SQL review (no live database)."""
import importlib.util
from contextlib import nullcontext
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "persistence" / "P01_Workspace.py"
spec = importlib.util.spec_from_file_location("canca_workspace_sql_security", MODULE)
workspace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workspace)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
    def fetchall(self):
        return self.rows


class RecordingConnection:
    def __init__(self):
        self.calls = []
    def execute(self, query, params=None):
        self.calls.append((query, params))
        return FakeCursor([])


class WorkspaceSQLSecurityTests(unittest.TestCase):
    def test_category_cannot_inject_sql_identifiers(self):
        conn = RecordingConnection()
        for category in ("sites;DROP TABLE canca.workspace_sites", "sites --", "missing"):
            with self.subTest(category=category):
                with self.assertRaises(Exception):
                    workspace.list_items(conn, "workspace-1", category)
        self.assertEqual(conn.calls, [])

    def test_pagination_input_cannot_inject_sql(self):
        conn = RecordingConnection()
        with self.assertRaises(Exception):
            workspace.list_items(conn, "workspace-1", "sites", after="x' OR 1=1 --")
        self.assertEqual(conn.calls, [])

    def test_allowed_categories_use_fixed_table_names_and_bound_values(self):
        with patch.object(workspace, "scope", side_effect=lambda conn, workspace_id: nullcontext()):
            for category, table in (("sites", "workspace_sites"),
                                    ("environments", "workspace_environments"),
                                    ("assessments", "workspace_assessments")):
                with self.subTest(category=category):
                    conn = RecordingConnection()
                    result = workspace.list_items(conn, "workspace-1", category, after="page-1", limit=10)
                    self.assertEqual(result["items"], [])
                    self.assertEqual(len(conn.calls), 1)
                    sql, params = conn.calls[0]
                    self.assertIn("FROM canca." + table + " ", sql)
                    self.assertIn("workspace_id=%s", sql)
                    self.assertEqual(params, ("workspace-1", "page-1", 11))
                    self.assertNotIn("workspace-1", sql)
                    self.assertNotIn("page-1", sql)


if __name__ == "__main__":
    unittest.main()
