# Reliable Event Processing Demo

**Standalone Python reference demo for reliable processing of synthetic workflow events.**

An offline, small backend example that takes fictional task events, validates their shape and ordering, stores state in SQLite, and delivers state changes to a local mock receiver. It focuses on **persistence, idempotent ingestion, transaction boundaries, recovery, and testability**.

> **Scope:** Standalone Python backend demo using synthetic task events. Runs locally without external services.

## At a glance

| Area | Demonstrated here |
| --- | --- |
| Runtime | Python 3.11+, standard library only |
| Input | Local JSON arrays of fictional task events |
| State | SQLite with atomic event/state/outbox writes |
| Duplicate handling | Same event ID + identical validated payload is ignored; conflicting reuse is rejected |
| Delivery | Local in-memory mock only; pending outbox rows can be retried |
| Verification | 43 automated unit and CLI/integration tests |
| External services | **None:** offline execution with a local mock receiver |

## Quick start (2 minutes)

From the repository root, with Python 3.11+ installed:

```bash
DEMO_DIR="$(mktemp -d)"
python3 -m demo run --input examples/events_happy.json --db "$DEMO_DIR/demo.sqlite3"
python3 -m demo run --input examples/events_happy.json --db "$DEMO_DIR/demo.sqlite3"
python3 -m unittest discover -s tests -v
```

The **first** CLI invocation processes three synthetic events and ends with `task-101=completed`. The **second**, against the same database, ignores those three already-processed events. `DEMO_DIR` is a temporary local directory; no application network access is needed. Use a new temporary directory for a fresh first run.

Example first-run output (one compact JSON line):

```json
{"deliveries":3,"delivery_failures":0,"ignored":0,"pending":0,"processed":3,"rejected":0,"states":{"task-101":"completed"}}
```

See [`examples/expected_output.txt`](examples/expected_output.txt) for the duplicate-event and mock-failure examples as well.

## What the demo does

1. Reads a local JSON list (`--input`) of invented `task_created`, `task_started`, `task_completed`, `task_failed` events.
2. Checks required fields, allowed keys, types, and event kinds.
3. Applies the task state machine: **new -> queued -> running -> completed / failed**.
4. Atomically persists each accepted event, task state and pending delivery in a local SQLite database.
5. Ignores repeats of the same event ID and same payload, and rejects invalid transitions and conflicting IDs without committing partial state.
6. Flushes pending deliveries to a **local-only mock receiver**; retains them for a later retry if that mock fails.

Architecture and the exact state/transaction semantics: [`docs/architecture.md`](docs/architecture.md).

## Try duplicate input

```bash
OTHER_DIR="$(mktemp -d)"
python3 -m demo run --input examples/events_duplicates.json --db "$OTHER_DIR/demo.sqlite3"
```

This processes 3 distinct synthetic events, ignores 1 repeat, and finishes at `task-202=failed`.

## Try a local mock failure and retry

```bash
FAIL_DIR="$(mktemp -d)"
python3 -m demo run --input examples/events_happy.json --db "$FAIL_DIR/demo.sqlite3" --simulate-sink-failure
python3 -m demo run --input examples/events_happy.json --db "$FAIL_DIR/demo.sqlite3"
```

The first run persists the state and **three pending mock deliveries**. The second reuses the database, ignores the 3 already-processed inputs, and clears pending deliveries after the mock succeeds. No message is sent to the internet.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The 43 automated tests cover event validation, state transitions, SQLite integrity, rollback on rejected transitions, duplicate IDs, recovery after reopening the database, pending-outbox retries, CLI input errors and isolation from live integrations. CI is **not configured** and there are **no performance guarantees**.

## Engineering choices and trade-offs

- **SQLite transactions:** task update, event receipt, and outbox record are committed together. This prevents partial state changes for rejected input.
- **Persistent event receipts:** event-ID + canonical-payload digest enables deterministic duplicate treatment across process restarts.
- **Local outbox:** separates durable state from mock delivery and permits retry. It does **not** claim exactly-once external delivery; an interrupted delivery before its acknowledgement could be attempted again.

## Safety and scope

Only synthetic task events are used. No personal data, credentials or external integrations are required. The application makes no network connections. Review [`docs/security-and-scope.md`](docs/security-and-scope.md) before sharing files.

**Scope:** an offline reference implementation, not a production service. No open-source license is granted or implied by this README.

## Known limitations

- Single-process example; no multi-writer or distributed coordination claims.
- Small local fixtures; no streaming ingestion, HTTP server, UI, or scheduler.
- Mock delivery only. Not a production message broker or exactly-once transport.
- The SQLite path must be absolute and remain inside the demo workspace or system temporary directory.
- No deployment automation or CI workflow is provided yet.

## Deliberately omitted / possible future improvements

- Real APIs, external services, credentials, production configuration and deployment automation are intentionally absent.
- Possible improvements: abstract storage interface, richer observability, property-based tests and an isolated CI job.
