# Reliable Event Processing - Scope and Security

## Status
Independent Python reference demo for portfolio evaluation.
Synthetic workflow data only.
Not a commercial product or production integration.

## Purpose
Demonstrate reliable backend event processing with:
- JSON input and strict validation
- SQLite persistence
- Idempotent event handling
- Explicit workflow state transitions
- Recovery across application restarts
- Mock delivery and failure handling
- Reproducible CLI output and automated tests

## Synthetic domain
Fictional task-management workflow.

Supported event types:
- task_created
- task_started
- task_completed
- task_failed

No external business systems are connected.

## Functional acceptance criteria

F01: Read two local JSON fixture sets.
F02: Reject invalid types, missing fields and malformed input.
F03: Ignore duplicate event IDs without repeating side effects.
F04: Persist local state in SQLite.
F05: Enforce explicit valid workflow transitions.
F06: Recover confirmed state after restarting.
F07: Reject invalid events without partial state changes.
F08: Use a local mock for all external actions.
F09: Report processed, ignored, rejected and current states.
F10: Pass automated unit and integration tests.

## Security and intellectual-property boundaries
All implementation code must be written independently.

Never import or copy:
- Third-party or client-owned application source code
- Proprietary architectural documents or specifications
- Internal tests, reports, logs or project archives
- Actual customer, employee or account data
- Credentials, tokens, private endpoints or configurations
- Commercial algorithms or confidential business rules
- Private repository history or Git metadata

Only invented task events and synthetic identifiers are allowed.

## Technical constraints
- Python 3.11+
- Standard library wherever practical
- Local JSON fixtures
- Local SQLite database
- Deterministic CLI examples
- No external network connections
- No real external integrations
- No production deployment
- No performance or reliability claims without evidence

## Portfolio disclosure
Independent reference implementation built for portfolio
demonstration. Synthetic data only.

## Required evidence before release
- Reproducible local execution
- Complete automated tests
- Accurate README and architecture of this demo only
- Security and intellectual-property review
- File-by-file review of the publication candidate
- Explicit approval before any Git or GitHub changes

## Verification

Local implementation completed.
43 automated tests passed.
No production deployment or external integration.
