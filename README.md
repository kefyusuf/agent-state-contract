# Agent State Contract

A small, provider-independent reference implementation of a **Task Lifecycle state contract** for coding-agent-accessible systems.

**Status:** M2 local reference implementation; not a production service.  
**Canonical design contract:** [`PROJECT_BASELINE_v0.1.md`](PROJECT_BASELINE_v0.1.md).

## Problem and hypothesis

Coding agents may face multiple plausible pathways for updating an application's state. This project demonstrates one narrow alternative: a defined set of commands, explicit preconditions, a single authoritative in-memory event history, and deterministic state reconstruction.

**Hypothesis (not yet empirically validated):** Explicit command/state contracts can reduce incorrect state mutations and architectural rediscovery by agents. This implementation **does not demonstrate token savings, increased completion success, or production suitability**.

## What this prototype implements

- One domain: Task Lifecycle (`todo` → `in_progress` → `done`; release returns to `todo`).
- Exactly four mutating commands: `task.create`, `task.claim`, `task.release`, `task.complete`.
- One agent-facing read: `task.get` (Python method `get`).
- Single-process serialization, expected-version validation, command-ID idempotency, and owner checks.
- One event per newly accepted command, no event for duplicates or rejections.
- Read-only diagnostic event snapshots and pure replay with invalid-history rejection.

No database, framework, network server, authentication, LLM, MCP, Redux, workflow engine, broker, or distributed coordination.

## Requirements and tests

Python 3.10+; standard library only. Verified locally using Python 3.13.5.

```bash
python -m unittest discover -s tests -v
```

The regression and acceptance tests include the 14-step canonical scenario, malformed envelopes/events, ownership, stale commands, duplicate IDs, replay consistency, independent per-task versioning, a controlled two-thread claim collision, and 300 deterministic mixed command attempts.

## Example

```python
from agent_state_contract import TaskContract

store = TaskContract()

created = store.execute({
    "command_id": "c1",
    "actor_id": "agent-a",
    "type": "task.create",
    "task_id": "task-1",
    "payload": {"title": "Write documentation"},
})

claimed = store.execute({
    "command_id": "c2",
    "actor_id": "agent-a",
    "type": "task.claim",
    "task_id": "task-1",
    "expected_version": 1,
    "payload": {},
})

assert created["version"] == 1
assert claimed["version"] == 2
assert store.get("task-1")["task"]["status"] == "in_progress"
assert len(store.events) == 2  # Diagnostic snapshot, not an agent-facing query
```

The `actor_id` field is supplied by test clients. **This project does not authenticate actors** and must not be directly exposed to untrusted agents as a production endpoint.

## Repository layout

```text
agent-state-contract/
├── PROJECT_BASELINE_v0.1.md    # M0 and M1 decisions and contract
├── README.md
├── agent_state_contract.py     # M2 implementation, standard library
├── tests/
│   └── test_contract.py        # Acceptance, invariant, regression tests
└── docs/
    └── M2_VERIFICATION.md      # Local M2 test record
```

## Scope and milestone control

- **M0:** Closed — product problem and exclusions defined.
- **M1:** Frozen v0.1 contract — no language or framework requirements.
- **M2:** Local RED → GREEN → regression verification finished. A dedicated Git branch and CI workflow are prepared; PR review and CI must pass before merge.
- **M3:** Optional evidence-backed comparison of bounded versus unconstrained agent behavior. No agent integration or token-use claim in M2.

Do not add infrastructure or generic extensibility in response to speculative future needs. Any contract change requires an explicit revision to the baseline and corresponding tests.