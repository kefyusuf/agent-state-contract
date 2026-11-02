# M3 — Candidate Agent Interface and Prompt Pack v0.1

**Status:** REVIEW DRAFT — not frozen, not executable, no agent or benchmark runs.
**Date:** 2026-11-02
**Scope:** Task Lifecycle v0.1; companion to `M3_EVALUATION_PROTOCOL_v0.1.md` and `M3_SCENARIO_MANIFEST_DRAFT_v0.1.md`.
**Gate:** Do not implement a harness or execute an episode until M2 PR #1 passes independent human review, CI, and merge. Then review and freeze this pack and the oracle separately.

## 1. Comparison contract

This is a **tool-access comparison**, not a claim that an agent with commands reasons more effectively.

Both arms get:
- The **same** domain-rule block and scenario goal.
- One fixed host-assigned caller identity per episode, shared with the goal text; the model cannot change the trusted identity.
- The same initial *permitted* observation: no task snapshot for S01; explicitly labeled historical snapshot for S02; otherwise only the task ID and goal. To see the current state, use the applicable read tool.
- The same model version, temperature, budget, system instructions, maximum steps, and trace logging rules.
- No oracle answers, expected snapshots, hidden fixtures, test code, repository search, general shell/file tools, web browsing, or prior run results.

The harness, not the model, must inject the trusted `actor_id` into contract commands and attach it to baseline traces. A model-supplied actor field must not override the host identity. The published `TaskContract` accepts `actor_id` in its Python command envelope; the proposed **evaluation-only** adapter must populate this field from the host and must not expose it as a mutable agent tool argument.

## 2. Shared instruction block (verbatim candidate)

> You are operating on one synthetic Task Lifecycle task. Follow these rules: the valid states are `todo`, `in_progress`, and `done`. A new task starts in `todo` with no owner and version 1. A `todo` task may be claimed by the current caller and becomes `in_progress` with that caller as sole owner. Only the current owner may release an `in_progress` task back to unowned `todo`, or complete it to unowned `done`. `done` is terminal. Each successful state change advances the task version by one. Do not make any invalid state changes. If the requested transition is not permitted, preserve state and report that no legal change occurred. Read the current task state when necessary. Use only the tools supplied in this episode, and finish with a concise statement of the result.

The quoted block is **identical for both arms**. Do not add examples of correct command sequences for one arm, add hidden hints, or show the oracle to either arm.

The host appends the scenario goal below without modifying it between paired arms. Tool descriptions are necessarily arm-specific and their token overhead must be measured separately.

## 3. Proposed tools

These are **test-harness surface shapes only**. They are not new commands in Task Lifecycle v0.1, not new Python methods, and not a production API. Exact provider tool naming must be fixed before execution without altering semantic fields.

### A — direct snapshot edit (baseline)

`task_get({"task_id":"T-S01"})` — return a snapshot or `TASK_NOT_FOUND`. No mutation.

`task_replace_snapshot({"task_id":"T-S01","snapshot":{"task_id":"T-S01","title":"Task S01","status":"todo","owner_agent_id":null,"version":1}})` — replace the targeted synthetic task with the proposed snapshot. For absent tasks, this may create the record. The baseline **does not** enforce lifecycle transitions, ownership, version checks, terminality, or a command ID. The harness records the proposal and resulting snapshot; a separate post-hoc evaluator checks invariants.

Baseline tool results must not add explanatory validation errors or auto-repair a bad snapshot. A storage/transport failure may be surfaced as a tool error and logged distinctly. The baseline tool cannot alter other tasks.

### B — explicit Task Lifecycle contract

`task_get({"task_id":"T-S01"})` — wraps `TaskContract.get(task_id)`.

The four mutating tools wrap `TaskContract.execute()`, with the host inserting the fixed `actor_id` into the v0.1 envelope:

- `task_create({"command_id":"c1","task_id":"T-S01","payload":{"title":"Task S01"}})`
- `task_claim({"command_id":"c2","task_id":"T-S01","expected_version":1,"payload":{}})`
- `task_release({"command_id":"c3","task_id":"T-S01","expected_version":2,"payload":{}})`
- `task_complete({"command_id":"c4","task_id":"T-S01","expected_version":2,"payload":{}})`

Every mutating call must use the M1 envelope with **no extra fields**. `command_id` is chosen by the test client so it can deliberately retry in S04. `actor_id` is not a model-controlled field. The adapter returns M2 receipts and errors unchanged; do not suppress rejections or silently retry on behalf of the agent.

Both arms expose exactly one task-read operation. Exposing `TaskContract.events` or `replay_events` as agent tools is prohibited.

## 4. Candidate scenario goal text (verbatim across paired arms)

| ID | Caller | Identical task goal for both arms |
| --- | --- | --- |
| S01 | `agent-a` | Create task `T-S01` with title `Task S01`. Claim it and complete it without skipping a lifecycle state. |
| S02 | `agent-b` | An earlier observation of `T-S02` showed `todo`, no owner, version 1. It may be stale. **Use `task_get`** to inspect current authoritative state and do not replace another owner's claim. Report whether you can legally claim it and why. |
| S03 | `agent-b` | **Use `task_get`** to check whether you may complete `T-S03`. Preserve ownership rules; if completion is not permitted, leave state unchanged and explain why. |
| S05 | `agent-a` | Claim `T-S05`, release it, claim it again, and complete it. Preserve all intermediate lifecycle states. |
| S06 | `agent-b` | **Use `task_get`** to determine whether `T-S06` can be claimed. Do not change terminal tasks. Report the legal outcome and why. |

For S01, no pre-existing task is exposed. For S02, the earlier observation is **explicitly historical**, not a guaranteed live snapshot. For S03/S05/S06, do **not** provide an oracle snapshot in the task goal: the model must use `task_get` to learn current state. Each arm receives the same initial fixture created outside the episode.

### S04 — contract-only diagnostic

Fixed caller: `agent-a`.

> Task `T-S04` was previously created and claimed with `command_id=fx-S04-claim`, `type=task.claim`, `task_id=T-S04`, `expected_version=1`, and `payload={}`. First resend that **same** accepted request with the same ID. Then submit a `task.release` request with the **same** command ID and `expected_version=1`. Neither should alter current state. Inspect and report the responses.

S04 has **no baseline run** and is excluded from every paired comparison. Its diagnostic expected results are kept in the inaccessible oracle file.

## 5. Fairness decisions before freezing

The precise tool schemas and prompts above are **candidates**. An independent reviewer must check:

1. Both arms receive equal domain knowledge and no answer key. The baseline's validation-free nature is deliberate, but is a limited comparator rather than a representation of all real systems.
2. The direct-edit tool permits an invalid proposal to be recorded without automatically refusing or repairing it. Its result wording cannot reveal an oracle verdict.
3. The contract adapter injects actor identity from the host, not from the model; its other fields stay exactly within M1.
4. Both arms have only task-state tools. The oracle, GitHub, tests, source files, previous trials, scorer, and arbitrary environment reads are unreachable, even though the reference files are public.
5. `S02` historical observation is conveyed identically and is clearly labeled stale-able; S03/S06 do not force a rejected operation merely to score success.
6. No scoring information, feedback about correctness, or case-specific oracle snapshots appear in a model prompt or tool description. The same requirement to check current state (S02/S03/S06) is included verbatim in both arms, rather than silently enforced after the fact.
7. Wrapper/tool verbosity and tokens are recorded. Do not pretend different interface descriptions have identical token costs.
8. Fixed prompt/manifest/tool schema hashes and model/version are recorded **after review** and before execution. Do not freeze or start runs while M2 PR #1 remains open.

**Measurement limit:** No repository/file/search tools are available. Count state reads but do not claim reductions in architecture rediscovery. For no-mutation S02/S03/S06 tasks, require at least one successful current-state read and a correct final explanation in **both** arms. Otherwise an unchanged task is insufficient evidence of task completion.

**No new product API, framework, persistence, orchestration, shell access, benchmark runner, or empirical result is authorized by this draft.**
