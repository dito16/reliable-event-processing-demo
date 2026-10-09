# Architecture of this independent demo

This document describes **only the new, fictional task-event application in this repository**. It is not a drawing of any client system or private integration.

## Components

```text
Local JSON fixtures
        |
        v
CLI: python3 -m demo run
        |
        v
Validator (required keys, types, allowed event kinds)
        |
        v
Processor: sequential event loop
        |
        v
SQLiteStore (local SQLite file)
   | tasks: current task state
   | processed_events: event ID + canonical payload digest
   | outbox: pending synthetic state notifications
        |
        v
Local MockSink (in-memory only)
        |
        v
Acknowledged outbox rows; compact CLI summary
```

## State machine

```text
absent --task_created--> queued --task_started--> running
                                                    |       |
                                         task_completed  task_failed
                                                    |       |
                                                completed  failed
```

`completed` and `failed` are terminal in this demo. Other transitions are rejected. All IDs and task descriptions in fixtures are invented.

## Persistence and idempotency

For each valid incoming event, `SQLiteStore.record` opens an SQLite `BEGIN IMMEDIATE` transaction, checks whether `event_id` has already been processed, validates the transition, and commits task state + processed-event digest + outbox record atomically. Conflicting reuse of an event ID is rejected. Identical events are ignored without another state change or new outbox message.

The SQLite connection is reopened for each new CLI invocation. Persisted state and event receipts remain after the process exits. `run_batch` sends queued outbox items **after** event transactions to an in-memory `MockSink`. Delivery failure leaves pending rows unacknowledged, so a subsequent CLI run can retry them.

**Delivery semantics:** at-least-once *attempt* is possible across a crash between delivery and outbox acknowledgement. This toy demo does not offer exactly-once effects to external systems and makes no operational reliability guarantees.

## Error boundaries

- Unsupported event shape/kind, missing fields and invalid state transitions -> counted as rejected; no partial transition.
- Duplicate event ID + identical canonical payload -> ignored.
- Reused event ID with different payload -> rejected.
- Missing/malformed JSON input -> CLI error before SQLite initialization.
- Unsafe SQLite file location or symlink -> CLI error.
- Mock receiver failure -> pending outbox retained, counted; no real external action.

## Tests and local reproduction

Run `python3 -m unittest discover -s tests -v` from the repository root. For example commands and precise output, see the root README and `examples/expected_output.txt`.

## Architectural boundaries

One process, sequential batch processing, SQLite file state, mock output, zero network adapters, no original client data/code, no application deployment. These constraints are intentional for a small demonstrable backend slice.
