"""Offline CLI for invented task events and an explicitly local SQLite DB."""

import argparse
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from .mock_sink import MockSink
from .processor import run_batch
from .store import SQLiteStore


def safe_db_path(raw_path):
    """Keep SQLite files within the workspace tree or the OS temporary folder."""
    path = Path(raw_path).expanduser()
    if not path.is_absolute() or path.is_symlink():
        raise ValueError('database path must be absolute and not a symlink')
    if not path.parent.is_dir():
        raise ValueError('database parent directory must already exist')
    parent = path.parent.resolve()
    home_workspace = (Path.home() / 'portfolio_workspace').resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    allowed = any(parent == root or root in parent.parents for root in (home_workspace, temp_root))
    if not allowed:
        raise ValueError('database must be within workspace or system temporary directory')
    if path.exists() and not path.is_file():
        raise ValueError('database destination must be a regular file')
    return path


def main():
    parser = argparse.ArgumentParser(description='Offline synthetic event-processing demo')
    parser.add_argument('command', choices=['run'])
    parser.add_argument('--input', required=True, help='Local JSON array of fictional task events')
    parser.add_argument('--db', required=True, help='Absolute path to a local SQLite state file')
    parser.add_argument('--simulate-sink-failure', action='store_true', help='Test failure of local mock')
    args = parser.parse_args()

    try:
        db_path = safe_db_path(args.db)
    except ValueError:
        parser.exit(2, 'DB_PATH_ERROR: use a regular file in a local workspace/temp directory\n')

    try:
        events = json.loads(Path(args.input).read_text(encoding='utf-8'))
        if not isinstance(events, list):
            raise ValueError('expected a JSON array')
    except (OSError, UnicodeError, ValueError):
        parser.exit(2, 'INPUT_ERROR: expected a readable JSON array\n')

    old_umask = os.umask(0o077)
    try:
        store = SQLiteStore(db_path)
        try:
            result = run_batch(events, MockSink(fail=args.simulate_sink_failure), store)
        finally:
            store.close()
    except (sqlite3.Error, OSError):
        parser.exit(3, 'DATABASE_ERROR: local SQLite operation failed\n')
    finally:
        os.umask(old_umask)
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))


if __name__ == '__main__':
    main()
