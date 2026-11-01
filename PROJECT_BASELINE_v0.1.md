# Agent State Contract

**Document:** Project Baseline and Task Lifecycle Contract  
**Version:** 0.1  
**Milestone:** M0 closed; M1 contract baseline  
**Status:** Design specification — no implementation  
**Date:** 2026-11-01

## 1. Product definition (M0)

### Problem
Coding agents working in an existing software system may encounter multiple apparent state owners and mutation pathways. This makes it harder to determine which actions are valid, what state changes they produce, and how to verify those changes.

### Objective
Specify and test a small, provider-independent contract in which agents can inspect authoritative state through a defined query and request changes only through explicit commands with deterministic, verifiable outcomes.

### Hypothesis, not an established result
A constrained command/state contract can reduce invalid state mutations and architecture rediscovery by coding agents. Any effect on token consumption, completion quality, or task duration must be measured in a separate agent evaluation; it is not assumed.

### Target users
Engineers designing agent-accessible workflows and builders of coding-agent integrations. M0–M2 target a synthetic test client rather than an actual model or agent provider.

### In scope
- Exactly one domain: Task Lifecycle.
- Four commands: `task.create`, `task.claim`, `task.release`, `task.complete`.
- One query: `task.get`.
- A single authoritative, in-memory sequence of accepted events per task.
- State derived deterministically from the event sequence.
- Task-version preconditions, command idempotency, ownership invariants, error results, and automated test cases.

### Explicit non-goals
- Redux or other frontend state management integrations.
- A general-purpose state machine, workflow, or event-sourcing framework.
- LLM calls, agent orchestration, MCP, inboxes, shared memory, Kanban UI, or task scheduling.
- Database persistence, distributed transactions, locks across processes, message brokers, retries across restarts, or production authentication.
- Role-based authorization, task deletion, reassignment, timeout, cancellation, reopening, priorities, dependencies, or multi-owner tasks.
- Unverified token-saving or reliability claims.

### Scope rule
A feature is not added because it might be useful later. It must be required to demonstrate or falsify the product hypothesis in the initial Task Lifecycle scenario.

## 2. Contract (M1)

### 2.1 Authority model
Accepted events are the **only authoritative record** for the prototype. Task state is computed by folding that ordered event stream. A temporary computed snapshot or index is never a separate write authority. All accepted commands append exactly one event; rejected commands append none.

This deliberately uses only a small in-memory event history and pure transitions. It does not introduce an event-sourcing infrastructure.

### 2.2 Task state

```typescript
// Illustrative shape only; this does not select TypeScript for implementation.
type Task = {
  task_id: string;
  title: string;
  status: 'todo' | 'in_progress' | 'done';
  owner_agent_id: string | null;
  version: number; // positive integer, starts at 1
};
```

**State invariants**
1. `todo` implies `owner_agent_id === null`.
2. `in_progress` implies `owner_agent_id` is a non-empty agent identifier.
3. `done` implies `owner_agent_id === null` and is terminal in v0.1.
4. A task is created at version `1`. Every accepted subsequent command increments that task's version by exactly one.
5. A command has no direct write access to task fields.
6. Exactly one owner can exist at any task version.
7. Events for an individual task have contiguous ascending versions, starting at `1`.

### 2.3 Command envelope

```json
{
  "command_id": "cmd-002",
  "actor_id": "agent-a",
  "type": "task.claim",
  "task_id": "task-001",
  "expected_version": 1,
  "payload": {}
}
```

- `command_id`: unique, opaque, non-empty identifier within the prototype's event history.
- `actor_id`: non-empty logical actor identifier. In tests, the simulator supplies it. In a real integration it must come from a trusted caller adapter, not an untrusted agent-generated claim. Authentication is outside v0.1.
- `type`: one of the four command names.
- `task_id`: non-empty opaque identifier supplied by the caller.
- `expected_version`: required positive integer for `claim`, `release`, and `complete`; absent for `create`.
- `payload`: `{"title":"..."}` for `create`; exactly `{}` for all other commands. A title must be a non-empty string after trimming for validation; the original input text is preserved.
- Unknown envelope/payload fields are rejected. No `null` substitute for absent `expected_version` on creation.

### 2.4 Allowed transitions

| Command | Preconditions | Accepted transition | Event |
| --- | --- | --- | --- |
| `task.create` | Task ID does not exist; valid title | absent → `todo`, owner `null`, version `1` | `TaskCreated` |
| `task.claim` | `todo`; expected version matches | `todo` → `in_progress`, owner = actor | `TaskClaimed` |
| `task.release` | `in_progress`; actor is owner; version matches | `in_progress` → `todo`, owner `null` | `TaskReleased` |
| `task.complete` | `in_progress`; actor is owner; version matches | `in_progress` → `done`, owner `null` | `TaskCompleted` |

Every transition other than those above is invalid. Repeating a previously accepted command with the **same** `command_id` and identical content is handled by idempotency rather than running another transition.

### 2.5 Validation order

1. Parse and validate the command's shape and required fields.
2. Search accepted history for `command_id`:
   - Same command content → return an already-applied acknowledgement, without writing an event and without checking the task's *current* version.
   - Different content → `COMMAND_ID_REUSED`.
3. For `create`, check task ID uniqueness. For other commands, check task existence.
4. For non-create commands, compare `expected_version` to current task version.
5. Check state transition validity and, where relevant, ownership.
6. Append exactly one accepted event; the next state is derived by applying that event.

Only **accepted** commands participate in deduplication. Rejected commands have no event and do not reserve an ID. Command identity comparison includes `actor_id`, `type`, `task_id`, presence/value of `expected_version`, and payload; it excludes `command_id` itself. Comparison is semantic over validated fields, not dependent on JSON property order.

**Concurrency limit:** v0.1 serializes command evaluation within a single process. `expected_version` detects stale requests in that model; it does not claim distributed or multiprocess atomicity.

### 2.6 Read and response contract

The only read operation is `task.get(task_id)`, which returns the current derived task snapshot or `TASK_NOT_FOUND`. Reading does not append events.

An accepted command returns:

```json
{
  "ok": true,
  "applied": true,
  "command_id": "cmd-002",
  "task_id": "task-001",
  "version": 2,
  "event_type": "TaskClaimed"
}
```

A duplicate accepted command returns the same original `version` and `event_type`, but `"applied": false`; this is an acknowledgement of the original operation, **not** a claim that the task is still at that version. Clients use `task.get` to read current state.

A rejected command returns `{"ok": false, "code": "..."}` and may include `current_version` for a version conflict. It never changes state or event history.

**Defined errors**

| Code | Meaning |
| --- | --- |
| `INVALID_COMMAND` | Malformed schema, missing fields, unsupported type, or invalid title |
| `COMMAND_ID_REUSED` | A previously accepted command ID appears with different content |
| `TASK_ALREADY_EXISTS` | A different create command uses an existing task ID |
| `TASK_NOT_FOUND` | Target task is absent |
| `VERSION_CONFLICT` | Supplied task version is stale or otherwise different |
| `INVALID_TRANSITION` | State does not permit the requested command |
| `NOT_OWNER` | Release/complete attempted by a non-owner while task is in progress |

Error evaluation follows section 2.5, so a stale non-owner request reports `VERSION_CONFLICT` first. For `release` or `complete` on a current `in_progress` task, a non-owner receives `NOT_OWNER`.

### 2.7 Event representation and replay

Each accepted event contains `command_id`, `actor_id`, `task_id`, `version`, `event_type`, and necessary event `data` (the title on creation; empty object on other events). A command ID occurs at most once in all accepted event history.

Event types: `TaskCreated`, `TaskClaimed`, `TaskReleased`, `TaskCompleted`.

`replay(task_id)` starts with no task and folds that task's events in order. It must reconstruct the same task state as `task.get`. Replay rejects invalid streams (missing creation, version gaps, duplicate versions, incompatible transition or ownership facts). There is no persisted event storage or cross-process recovery guarantee in this milestone.

## 3. Required test vectors

The following sequence starts with an empty event history.

| Step | Operation | Expected result | Task state / version |
| --- | --- | --- | --- |
| 1 | `cmd-1`: A creates T | Applied, `TaskCreated` | `todo`, owner null, v1 |
| 2 | `cmd-2`: A claims T, expected v1 | Applied, `TaskClaimed` | `in_progress`, owner A, v2 |
| 3 | `cmd-3`: B claims T, expected v1 | `VERSION_CONFLICT` | unchanged, v2 |
| 4 | `cmd-4`: B releases T, expected v2 | `NOT_OWNER` | unchanged, v2 |
| 5 | Repeat identical `cmd-2` | Already applied, original v2 receipt | unchanged, v2 |
| 6 | `cmd-5`: A releases T, expected v2 | Applied, `TaskReleased` | `todo`, owner null, v3 |
| 7 | `cmd-6`: B claims T, expected v3 | Applied, `TaskClaimed` | `in_progress`, owner B, v4 |
| 8 | `cmd-7`: B completes T, expected v4 | Applied, `TaskCompleted` | `done`, owner null, v5 |
| 9 | `cmd-8`: B completes T, expected v5 | `INVALID_TRANSITION` | unchanged, v5 |
| 10 | Repeat identical `cmd-7` | Already applied, original v5 receipt | unchanged, v5 |
| 11 | Reuse `cmd-7` with changed body | `COMMAND_ID_REUSED` | unchanged, v5 |
| 12 | `cmd-9`: create T with a new ID | `TASK_ALREADY_EXISTS` | unchanged, v5 |
| 13 | Malformed/unknown command | `INVALID_COMMAND` | unchanged, v5 |
| 14 | Replay T's event history | Exact match with `task.get(T)` | `done`, owner null, v5 |

After step 14, T has exactly five accepted events. Add isolated tests for missing task, invalid task title, claim on already-in-progress task with a fresh command ID, release on `todo`, complete on `todo`, and malformed event replay.

## 4. Evaluation and success criteria

**Contract correctness** (M2 automated tests):
- All specified accepted and rejected cases behave as stated.
- Zero invariant violations in the test corpus.
- Rejected/duplicate commands never append new events.
- Concurrent-looking claims evaluated serially produce at most one owner.
- Replay equals the computed current state for all valid event sequences under test.

**Hypothesis evaluation** (later, only if M2 passes): Compare agent behavior under a documented contract versus an unconstrained baseline using matched tasks, controlled context, the same model and tool budget, and auditable measures: invalid mutations, successful completion, architecture rediscovery actions, token usage, and time. These are planned measures, not promised improvements. M3 must avoid changing the product's scope to chase favorable results.

## 5. Risks and exclusions

- The contract might simply relocate complexity into adapters rather than reduce it.
- An authoritative event stream must not be mistaken for production-ready durable event sourcing.
- A simulated actor ID proves ownership logic, not authentication or authorization.
- A single-process version check does not guarantee distributed concurrency safety.
- A single simple domain cannot establish general benefits for arbitrary software systems.

## 6. Decisions and release gates

| ID | Decision | Rationale |
| --- | --- | --- |
| ADR-001 | Task Lifecycle only | Keeps domain and state transitions enumerable |
| ADR-002 | Accepted in-memory events are authoritative | Makes replay and state provenance inspectable without extra storage technology |
| ADR-003 | Explicit commands only | Prevents arbitrary agent-initiated state writes |
| ADR-004 | Per-task integer versions | Simple stale-write protection in serial execution |
| ADR-005 | Idempotency by accepted command ID | Prevents duplicate effects from resubmitted accepted commands |
| ADR-006 | Trusted actor injection deferred to adapter | Keeps ownership logic separate from production identity and security |
| ADR-007 | Technology selection deferred to M2 | Contract must not depend on a framework or language |

**M0:** Closed at design level.  
**M1:** Contract baseline complete at v0.1; implementation and test verification pending.  
**M2 entry gate:** Review this specification for internal consistency, select one minimal implementation language, and create a repository only when writing the first RED tests.  
**M2 workflow:** RED tests → minimal GREEN implementation → refactor → verify. Scope changes must be recorded explicitly, not added silently.

### Internal consistency review (design level)
- Exactly four mutating commands and one query are specified.
- Every accepted command emits exactly one event; the five successful operations in the primary vector yield five events.
- Terminal `done` state cannot be reopened.
- Idempotent replay is evaluated before stale-version validation.
- Event history, not an independently mutable snapshot, is authoritative.
- No distributed concurrency, persistence, authentication, real agent integration, or token-efficiency result is claimed.

**Next action:** M2 planning (technology selection, RED test cases, minimal project layout). A GitHub repository is first needed when implementation begins, not for the current contract phase.