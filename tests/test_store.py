"""SQLite transaction, state-transition and outbox tests with synthetic IDs."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from demo.mock_sink import MockSink
from demo.processor import run_batch
from demo.store import SQLiteStore
from demo.validator import InvalidEvent


def evt(event_id, task_id='t1', kind='task_created', title=None):
    result = {'event_id': event_id, 'task_id': task_id, 'kind': kind}
    if kind == 'task_created':
        result['title'] = title or 'Write sample note'
    return result


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='portfolio_unit_')
        self.path = Path(self.tmp.name) / 'state.sqlite'
        self.store = SQLiteStore(self.path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def counts(self):
        return [self.store.connection.execute(
            f'SELECT COUNT(*) FROM {table}'
        ).fetchone()[0] for table in ('tasks', 'processed_events', 'outbox')]

    def test_create_persists_queued_state(self):
        self.assertEqual(self.store.record(evt('e1')), 'processed')
        self.assertEqual(self.store.states(), {'t1': 'queued'})
        self.assertEqual(self.counts(), [1, 1, 1])

    def test_valid_happy_transition_sequence(self):
        for e in (evt('e1'), evt('e2', kind='task_started'), evt('e3', kind='task_completed')):
            self.assertEqual(self.store.record(e), 'processed')
        self.assertEqual(self.store.states(), {'t1': 'completed'})

    def test_valid_failed_transition(self):
        for e in (evt('e1'), evt('e2', kind='task_started'), evt('e3', kind='task_failed')):
            self.assertEqual(self.store.record(e), 'processed')
        self.assertEqual(self.store.states(), {'t1': 'failed'})

    def test_start_before_create_is_rejected_atomically(self):
        with self.assertRaises(InvalidEvent):
            self.store.record(evt('bad', kind='task_started'))
        self.assertEqual(self.counts(), [0, 0, 0])
        self.assertEqual(self.store.states(), {})

    def test_early_completion_does_not_partially_write(self):
        self.store.record(evt('e1'))
        with self.assertRaises(InvalidEvent):
            self.store.record(evt('early', kind='task_completed'))
        self.assertEqual(self.counts(), [1, 1, 1])
        self.assertEqual(self.store.states(), {'t1': 'queued'})

    def test_repeat_same_id_and_payload_is_ignored(self):
        event = evt('e1')
        self.assertEqual(self.store.record(event), 'processed')
        self.assertEqual(self.store.record(dict(event)), 'ignored')
        self.assertEqual(self.counts(), [1, 1, 1])

    def test_duplicate_id_with_conflicting_payload_rejected(self):
        self.store.record(evt('e1', title='First'))
        with self.assertRaises(InvalidEvent):
            self.store.record(evt('e1', title='Different'))
        self.assertEqual(self.store.states(), {'t1': 'queued'})
        self.assertEqual(self.counts(), [1, 1, 1])

    def test_second_task_independent(self):
        self.store.record(evt('e1', task_id='t1'))
        self.store.record(evt('e2', task_id='t2'))
        self.store.record(evt('e3', task_id='t2', kind='task_started'))
        self.assertEqual(self.store.states(), {'t1': 'queued', 't2': 'running'})
        self.assertEqual(self.counts(), [2, 3, 3])

    def test_one_outbox_message_per_event(self):
        self.store.record(evt('e1'))
        self.store.record(evt('e1'))
        self.assertEqual(self.store.pending_count(), 1)
        self.assertEqual(len(self.store.pending()), 1)

    def test_acknowledge_only_pending_delivery(self):
        self.store.record(evt('e1'))
        rowid = self.store.pending()[0][0]
        self.store.acknowledge(rowid)
        self.store.acknowledge(rowid)
        self.assertEqual(self.store.pending_count(), 0)
        self.assertEqual(self.counts(), [1, 1, 1])

    def test_receiver_failure_leaves_outbox_pending(self):
        sink = MockSink(fail=True)
        report = run_batch([evt('e1')], sink, self.store)
        self.assertEqual(report['processed'], 1)
        self.assertEqual(report['delivery_failures'], 1)
        self.assertEqual(report['pending'], 1)
        self.assertEqual(sink.deliveries, [])

    def test_retry_drains_outbox_with_no_new_state_change(self):
        run_batch([evt('e1')], MockSink(fail=True), self.store)
        sink = MockSink()
        report = run_batch([evt('e1')], sink, self.store)
        self.assertEqual(report['processed'], 0)
        self.assertEqual(report['ignored'], 1)
        self.assertEqual(report['deliveries'], 1)
        self.assertEqual(report['pending'], 0)

    def test_restart_reads_durable_state_and_deduplicates(self):
        self.store.record(evt('e1'))
        self.store.close()
        self.store = SQLiteStore(self.path)
        self.assertEqual(self.store.states(), {'t1': 'queued'})
        self.assertEqual(self.store.record(evt('e1')), 'ignored')
        self.assertEqual(self.counts(), [1, 1, 1])

    def test_closed_state_cannot_be_restarted(self):
        for e in (evt('e1'), evt('e2', kind='task_started'), evt('e3', kind='task_completed')):
            self.store.record(e)
        with self.assertRaises(InvalidEvent):
            self.store.record(evt('e4', kind='task_started'))
        self.assertEqual(self.counts(), [1, 3, 3])

    def test_database_integrity(self):
        self.store.record(evt('e1'))
        self.assertEqual(self.store.connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok')


if __name__ == '__main__':
    unittest.main()
