"""Lightweight offline publication-boundary checks (not a legal/security clearance)."""
import ast
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from demo.mock_sink import MockSink

ROOT = Path(__file__).resolve().parents[1]


class BoundaryTests(unittest.TestCase):
    def test_no_live_network_imports_in_application(self):
        banned = {'socket', 'urllib', 'requests', 'httpx', 'aiohttp', 'websockets'}
        for path in (ROOT / 'demo').glob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(alias.name.split('.')[0], banned)
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split('.')[0], banned)

    def test_fixture_data_uses_only_invented_task_fields(self):
        allowed = {'event_id', 'task_id', 'kind', 'title'}
        for path in (ROOT / 'examples').glob('*.json'):
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertIsInstance(data, list)
            for record in data:
                self.assertTrue(set(record).issubset(allowed))

    def test_local_mock_never_requires_credentials(self):
        sink = MockSink()
        sink.deliver('fictional-task', 'queued')
        self.assertEqual(sink.deliveries, [{'task_id': 'fictional-task', 'state': 'queued'}])

    def test_no_nested_git_metadata_in_project_materials(self):
        for section in ('demo', 'docs', 'examples', 'tests'):
            for path in (ROOT / section).rglob('.git'):
                self.fail(f'Unexpected nested Git metadata: {path.relative_to(ROOT)}')


if __name__ == '__main__':
    unittest.main()
