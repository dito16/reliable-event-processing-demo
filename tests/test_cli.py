"""CLI integration tests; all data and database files are disposable and local."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENV = dict(os.environ)
ENV['PYTHONDONTWRITEBYTECODE'] = '1'
ENV['PYTHONNOUSERSITE'] = '1'


class CLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='portfolio_cli_')
        self.directory = Path(self.tmp.name)
        self.db = self.directory / 'database.sqlite'
        self.happy = ROOT / 'examples' / 'events_happy.json'
        self.duplicate = ROOT / 'examples' / 'events_duplicates.json'

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, source, *options, db=None, rc=0):
        cmd = [sys.executable, '-m', 'demo', 'run', '--input', str(source),
               '--db', str(db or self.db), *options]
        result = subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True,
                                timeout=15, check=False)
        self.assertEqual(result.returncode, rc, result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return json.loads(result.stdout) if rc == 0 else result.stderr

    def fixture(self, data):
        path = self.directory / 'input.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def counts(self):
        with sqlite3.connect(self.db) as conn:
            return [conn.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]
                    for name in ('tasks', 'processed_events', 'outbox')]

    def test_happy_fixture_reaches_completed(self):
        result = self.cli(self.happy)
        self.assertEqual(result['states'], {'task-101': 'completed'})
        self.assertEqual(result['processed'], 3)
        self.assertEqual(result['deliveries'], 3)
        self.assertEqual(self.counts(), [1, 3, 3])

    def test_repeat_same_database_is_idempotent(self):
        self.cli(self.happy)
        again = self.cli(self.happy)
        self.assertEqual(again['processed'], 0)
        self.assertEqual(again['ignored'], 3)
        self.assertEqual(again['deliveries'], 0)
        self.assertEqual(self.counts(), [1, 3, 3])

    def test_duplicate_fixture_counts_one_ignored(self):
        result = self.cli(self.duplicate)
        self.assertEqual(result['processed'], 3)
        self.assertEqual(result['ignored'], 1)
        self.assertEqual(result['states'], {'task-202': 'failed'})

    def test_sink_failure_and_recovery(self):
        failure = self.cli(self.happy, '--simulate-sink-failure')
        self.assertEqual(failure['pending'], 3)
        self.assertEqual(failure['delivery_failures'], 1)
        self.assertEqual(failure['deliveries'], 0)
        again = self.cli(self.happy)
        self.assertEqual(again['processed'], 0)
        self.assertEqual(again['ignored'], 3)
        self.assertEqual(again['deliveries'], 3)
        self.assertEqual(again['pending'], 0)
        self.assertEqual(self.counts(), [1, 3, 3])

    def test_out_of_order_event_rejected_without_partial_record(self):
        source = self.fixture([
            {'event_id': 'a', 'task_id': 'x', 'kind': 'task_started'},
            {'event_id': 'b', 'task_id': 'x', 'kind': 'task_created', 'title': 'Invented task'},
        ])
        result = self.cli(source)
        self.assertEqual(result['rejected'], 1)
        self.assertEqual(result['processed'], 1)
        self.assertEqual(result['states'], {'x': 'queued'})
        self.assertEqual(self.counts(), [1, 1, 1])

    def test_conflicting_event_id_rejected(self):
        source = self.fixture([
            {'event_id': 'same', 'task_id': 'x', 'kind': 'task_created', 'title': 'A'},
            {'event_id': 'same', 'task_id': 'x', 'kind': 'task_created', 'title': 'B'},
        ])
        result = self.cli(source)
        self.assertEqual(result['processed'], 1)
        self.assertEqual(result['rejected'], 1)
        self.assertEqual(self.counts(), [1, 1, 1])

    def test_malformed_json_does_not_create_db(self):
        source = self.directory / 'broken.json'
        source.write_text('{invalid', encoding='utf-8')
        self.assertIn('INPUT_ERROR', self.cli(source, rc=2))
        self.assertFalse(self.db.exists())

    def test_non_array_json_does_not_create_db(self):
        self.assertIn('INPUT_ERROR', self.cli(self.fixture({'kind': 'task_created'}), rc=2))
        self.assertFalse(self.db.exists())

    def test_missing_input_does_not_create_db(self):
        self.assertIn('INPUT_ERROR', self.cli(self.directory / 'not-found.json', rc=2))
        self.assertFalse(self.db.exists())

    def test_db_path_outside_allowed_roots_rejected(self):
        outside = Path.home() / 'not-approved-event-demo.sqlite'
        self.assertIn('DB_PATH_ERROR', self.cli(self.happy, db=outside, rc=2))
        self.assertFalse(outside.exists())

    def test_db_symlink_rejected(self):
        target = self.directory / 'real.sqlite'
        target.touch()
        alias = self.directory / 'alias.sqlite'
        alias.symlink_to(target)
        self.assertIn('DB_PATH_ERROR', self.cli(self.happy, db=alias, rc=2))

    def test_mixed_events_return_complete_summary(self):
        source = self.fixture([
            {'event_id': 'e1', 'task_id': 'z', 'kind': 'task_created', 'title': 'Demo'},
            {'event_id': 'e1', 'task_id': 'z', 'kind': 'task_created', 'title': 'Demo'},
            {'event_id': 'e2', 'task_id': 'z', 'kind': 'task_completed'},
            {'event_id': 'e3', 'task_id': 'z', 'kind': 'task_started'},
        ])
        result = self.cli(source)
        self.assertEqual(result, {
            'processed': 2, 'ignored': 1, 'rejected': 1, 'deliveries': 2,
            'delivery_failures': 0, 'pending': 0, 'states': {'z': 'running'},
        })


if __name__ == '__main__':
    unittest.main()
