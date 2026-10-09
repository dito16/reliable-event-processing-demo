"""Independent SQLite store for a fictional task-event processing demo.

No network connections or external adapters.
"""

import hashlib
import json
import sqlite3
from pathlib import Path

from .validator import InvalidEvent

STATES = frozenset({'queued', 'running', 'completed', 'failed'})
NEXT_STATE = {
    'task_created': (None, 'queued'),
    'task_started': ('queued', 'running'),
    'task_completed': ('running', 'completed'),
    'task_failed': ('running', 'failed'),
}


class SQLiteStore:
    """Tiny local store with atomic event/state/outbox writes."""

    def __init__(self, db_path: Path):
        self.connection = sqlite3.connect(str(db_path), timeout=5)
        self.connection.execute('PRAGMA busy_timeout = 5000')
        self.connection.executescript('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('queued','running','completed','failed'))
        );
        CREATE TABLE IF NOT EXISTS processed_events (
            event_id TEXT PRIMARY KEY,
            payload_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            task_id TEXT NOT NULL,
            new_state TEXT NOT NULL,
            delivered INTEGER NOT NULL DEFAULT 0 CHECK(delivered IN (0,1))
        );
        ''')

    def close(self):
        self.connection.close()

    def record(self, event):
        """Persist synthetic transition atomically; never deliver within transaction."""
        canonical = json.dumps(event, ensure_ascii=True, sort_keys=True, separators=(',', ':'))
        fingerprint = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
        event_id = event['event_id']
        task_id = event['task_id']
        expected, new_state = NEXT_STATE[event['kind']]

        db = self.connection
        db.execute('BEGIN IMMEDIATE')
        try:
            found = db.execute(
                'SELECT payload_hash FROM processed_events WHERE event_id=?', (event_id,)
            ).fetchone()
            if found:
                if found[0] != fingerprint:
                    raise InvalidEvent('event ID conflicts with an existing payload')
                db.commit()
                return 'ignored'

            current = db.execute('SELECT state FROM tasks WHERE task_id=?', (task_id,)).fetchone()
            state = current[0] if current else None
            if state != expected:
                raise InvalidEvent('invalid task state transition')

            if expected is None:
                db.execute(
                    'INSERT INTO tasks(task_id,title,state) VALUES(?,?,?)',
                    (task_id, event['title'], new_state),
                )
            else:
                db.execute('UPDATE tasks SET state=? WHERE task_id=?', (new_state, task_id))
            db.execute(
                'INSERT INTO processed_events(event_id,payload_hash) VALUES(?,?)',
                (event_id, fingerprint),
            )
            db.execute(
                'INSERT INTO outbox(event_id,task_id,new_state) VALUES(?,?,?)',
                (event_id, task_id, new_state),
            )
            db.commit()
            return 'processed'
        except BaseException:
            db.rollback()
            raise

    def pending(self):
        return self.connection.execute(
            'SELECT id,task_id,new_state FROM outbox WHERE delivered=0 ORDER BY id'
        ).fetchall()

    def acknowledge(self, delivery_id):
        with self.connection:
            self.connection.execute(
                'UPDATE outbox SET delivered=1 WHERE id=? AND delivered=0',
                (delivery_id,),
            )

    def pending_count(self):
        return self.connection.execute('SELECT COUNT(*) FROM outbox WHERE delivered=0').fetchone()[0]

    def states(self):
        return dict(self.connection.execute('SELECT task_id,state FROM tasks ORDER BY task_id'))
