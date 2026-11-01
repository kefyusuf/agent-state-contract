# M3 — Candidate Scenario Manifest and Independent Oracles v0.1

**Status:** DRAFT ONLY — not frozen, not executable authorization, no benchmark observations.
**Date:** 2026-11-02
**Dependency:** M2 PR #1 must pass independent review, the current CI gate, and merge before running M3.
**Companion:** `M3_EVALUATION_PROTOCOL_v0.1.md`.
**Domain:** Task Lifecycle Contract v0.1; no additional operations.

## 1. Why this draft exists

This document proposes concrete fixtures, matched task requests, and expected traces *before* model outcomes are available. It is not a benchmark implementation and makes no claim of agent improvement.

The contract implementation is **not** the scoring oracle. Fixed expectations below come from the M1 state machine, version, actor, and idempotency rules. A reviewer must check the fixture and oracle reasoning independently before the manifest is frozen.

### Actor and interface restrictions

- `agent-a` and `agent-b` are **synthetic actor labels**, not authenticated accounts or independently running AI agents.
- Each episode contains **one** model interaction. For multi-actor scenarios the benchmark harness would need two predefined caller contexts. That implementation is **not yet approved**; it must never trust the model's arbitrary self-asserted identity. Until the adapter semantics are resolved, those scenarios are blocked from execution.
- Both arms receive the **same domain rules, user goal, and visible state fields**: `task_id`, `title`, `status`, `owner_agent_id`, `version`.
- Arm A proposes entire replacement snapshots without enforcing transitions; each proposal and actor context is logged. Arm B calls only the four M1 commands and `task.get`. Neither arm gets extra help from the evaluator.
- The baseline must not silently validate or reject malformed state changes; it must expose them to an independent *post-hoc* trajectory oracle. Do not mistake oracle failure for a tool rejection.
- Each scenario is reset for each episode; fixture setup is **not** counted as agent activity, tool calls, or agent tokens.
- A fixed `expected_version` on an arm-B command is verified as in M1; arm-A proposed snapshots are scored for version continuity *without* installing an enforcing version check.

### Fixed output vocabulary

- `todo`: owner `null`.
- `in_progress`: exactly one owner, a non-empty actor label.
- `done`: owner `null`, terminal.
- Each **accepted** transition increases version by exactly one; rejected or duplicate requests do not change the authoritative state.
- Successful episode means the target objective **and all intermediate invariants** hold.
- Any incorrectly accepted mutation disqualifies an episode even if a later step repairs the final snapshot.
- Arm-specific command error codes, idempotent receipts, and event counts are reported as diagnostic evidence, not assumed to exist on arm A.

## 2. Candidate fixtures and user-task intents

The following IDs and titles are proposed but **not frozen**. In every scenario, use a fresh task identifier and command IDs, never reuse state between episodes.

### S01 — Complete the normal lifecycle (paired)

**Initial state:** task `T-S01` absent; zero seeded events.
**Task instruction (same objective in both arms):** "Create 'Task S01' as `T-S01`; move it through a claim by `agent-a` to successful completion by `agent-a`. Do not skip a lifecycle state."
**Caller context:** `agent-a`.
**Oracle states, in order:**

| Step | Task state | Owner | Version |
| --- | --- | --- | --- |
| Creation | `todo` | `null` | 1 |
| Claim | `in_progress` | `agent-a` | 2 |
| Completion | `done` | `null` | 3 |

**Independent check:** Three legal state changes, no skipped state, no invalid intermediate snapshot; final title preserved. Contract arm additionally expects `TaskCreated`, `TaskClaimed`, `TaskCompleted` and exactly three accepted events.

### S02 — Stale view and competing claim (paired)

**True initial state:** `T-S02`, title `Task S02`, `in_progress`, owned by `agent-a`, version 2.
**Fixture provenance:** `TaskCreated` v1 by A; `TaskClaimed` v2 by A. No other events.
**Available earlier observation:** `T-S02` at version 1, `todo`, unowned. Clearly label this observation as *earlier*; do not lie about the authoritative state.
**Task instruction:** "You are operating as `agent-b`. Attempt to claim `T-S02` based on your earlier observation only if ownership rules allow it. Do not replace an existing owner; check and report the current authoritative state."
**Caller context:** `agent-b`.
**Oracle:** No accepted mutation; `in_progress`, owner A, version 2 throughout. The agent may inspect and abstain. If it submits a stale v1 claim in arm B, `VERSION_CONFLICT` is the required response, not an accepted mutation.
**Interpretation:** A model may succeed without attempting a mutation. Record reads, attempts, and abstention rather than manufacturing a rejection.

### S03 — Non-owner attempt followed by owner's completion (paired; actor-switch design gate)

**True initial state:** `T-S03`, title `Task S03`, `in_progress`, owner `agent-a`, version 2.
**Fixture provenance:** create v1 and claim v2 by A.
**Task instruction:** "First test an attempted completion from `agent-b`; that attempt must not alter the task. Then, from `agent-a`'s caller context, complete the task."
**Predefined caller contexts:** attempt 1 = B; attempt 2 = A. A model must not directly declare a trusted identity.
**Independent oracle:** B attempt changes nothing and does not advance version. A completion changes task to `done`, owner `null`, version 3. Any temporary success for B fails the full-trajectory oracle.
**Contract-specific diagnostics:** B's complete at expected v2 -> `NOT_OWNER`; A's complete at v2 -> accepted `TaskCompleted` v3. Rejected attempts do not append events.
**Gate:** Adapter must support a controlled caller-context change with identical rules across arms; otherwise this scenario must be revised before freezing.

### S04 — Idempotent retry and reused identifier (diagnostic, **not paired-primary**)

**True initial state:** `T-S04`, title `Task S04`, `in_progress`, owner A, version 2.
**Fixture provenance:** command `fx-s04-create` accepted as `TaskCreated` v1, then `fx-s04-claim` accepted as `TaskClaimed` v2 by A (expected v1).
**Task instruction:** "Re-submit the previously accepted `fx-s04-claim` request unchanged. Then submit a different operation using the **same** command ID. Verify that neither request changes the current state."
**Caller context:** `agent-a`.
**Common oracle:** No new legal state transition; task remains `in_progress`, owner A, version 2; do not accept any invalid intermediate state.
**Arm-B diagnostic:** Exact duplicate `task.claim` returns original v2 receipt with `applied: false`; changing operation to `task.release` under the same `command_id` returns `COMMAND_ID_REUSED`. Neither adds events.
**Arm-A caveat:** A direct replacement snapshot has **no command-ID/receipt semantics**. Arm-A attempts and state effects may be logged for illustration but cannot be scored as an equivalent idempotency test. **Exclude S04 from aggregate paired primary outcome, token, and time comparisons.**
**Gate:** Do not assert S04 establishes a comparative advantage in model reasoning.

### S05 — Release and handoff (paired; actor-switch design gate)

**True initial state:** `T-S05`, title `Task S05`, `todo`, owner `null`, version 1.
**Fixture provenance:** `TaskCreated` v1 by A.
**Task instruction:** "From A's caller context, claim and release `T-S05`. Then from B's caller context, claim and complete it. Do not skip intermediate transitions."
**Predefined caller contexts:** first two successful steps A, next two B.
**Oracle states, in order:**

| Step | Task state | Owner | Version |
| --- | --- | --- | --- |
| Initial | `todo` | `null` | 1 |
| A claim | `in_progress` | `agent-a` | 2 |
| A release | `todo` | `null` | 3 |
| B claim | `in_progress` | `agent-b` | 4 |
| B complete | `done` | `null` | 5 |

**Independent check:** Each transition occurs once in order, no overlapping ownership, no skipped state, and final state matches. Contract arm expects exactly four *new* events beyond the fixture.
**Gate:** Same controlled actor-context requirement as S03.

### S06 — Terminal state remains terminal (paired)

**True initial state:** `T-S06`, title `Task S06`, `done`, owner `null`, version 3.
**Fixture provenance:** created v1, claimed by A v2, completed by A v3.
**Task instruction:** "Try to claim `T-S06` as `agent-b`, but preserve the rule that done is terminal. Report whether a legal state change occurred."
**Caller context:** `agent-b`.
**Oracle:** No successful transition or change to the terminal task. Status remains `done`, owner `null`, version 3. Arm-B claim at expected v3 must return `INVALID_TRANSITION` if attempted; the agent may instead detect the illegal transition and abstain.
**Interpretation:** A correctly abstaining agent may complete the task with zero mutation calls.

## 3. Comparability and denominators

The candidate study contains **60 planned episodes**: six scenarios, five repeats, two arms. This preserves a balanced data collection layout, but **does not** make all scenarios equivalent.

- **Primary paired population:** S01, S02, S03, S05, S06 = 5 scenarios × 5 repeats × 2 arms = **50 episodes**. Denominator is **all 50 attempted episodes**, including errors/timeouts as failures under the predeclared rubric.
- **Diagnostic subset:** S04 = 5 repeats × 2 arms = **10 episodes**, reported separately and never included in the primary paired success aggregate, relative token/time summary, or "win" claims.
- **Per-scenario results:** Report all six scenarios, but label S04 `non-comparable diagnostic`.
- **Missing usage:** Missing token telemetry is `null`, not zero; separately report count of episodes with missing telemetry.
- **Failed attempts:** A mutation proposal that violates the post-hoc oracle in A is not the same observation as a contract-rejected request in B. Show each count under its own label.

The primary report also includes **per-scenario** success rates: aggregation must not hide scenarios where the contract adds no benefit or causes extra overhead. Report all attempted episodes; do not suppress runs based on outcomes.

## 4. Independent oracle checklist (review before freezing)

For *every* tool proposal and observed new state:

1. Compare task ID and title to the fixed fixture; do not allow silent edits to unrelated tasks.
2. Validate the ownership/status invariant for every intermediate state.
3. Validate permitted transition edges and version continuity, not just final state.
4. Validate that rejected and no-op requests do not mutate the snapshot.
5. For terminal fixtures, reject any change to `done`.
6. Compare against expected scenario trajectory and required author/caller context.
7. Record whether the scenario goal was met **without repair by the oracle**.
8. For B, separately check command receipt and error precedence against M1; do not derive expected values by calling the implementation under test.
9. For A, preserve the invalid proposal in trace evidence; the independent evaluator labels it invalid without making the direct-state tool enforcing.
10. Flag missing or untrusted actor context as `invalid_harness_setup`, **not** as an agent success/failure; report all setup exclusions transparently before any outcome analysis.

A reviewer must independently verify these expected states and feasibility of fair caller-context injection. Neither ChatGPT-generated assertions nor the M2 replay function alone meet that review requirement.

## 5. Controls still needed before execution

- [ ] Independent M2 PR #1 review, passing CI, and merge.
- [ ] Technical signoff that the two actor contexts in S03/S05 can be administered without hidden runtime features or identity forgery.
- [ ] Confirm whether S04's baseline diagnostic is worth executing; never include it in the paired primary analysis.
- [ ] Finalize the exact agent prompt template and tool descriptions **with identical non-interface instructions**.
- [ ] Freeze the scenario manifest, independent oracle expectations, run order, model/version, budgets, and hashes before launching any episode.
- [ ] Obtain independent approval of the pre-registration and oracle rules.
- [ ] Implement only a minimal instrumented harness after a separate design review.

**No experimental runs, metrics, model invocation, extra production features, or benchmark conclusions are authorized by this draft.**
