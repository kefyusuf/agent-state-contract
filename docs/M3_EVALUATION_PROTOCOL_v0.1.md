# M3 — Controlled Evaluation Protocol v0.1

**Status:** Pre-registration draft; **NOT authorized to execute** until M2 PR #1 has passed independent review, current CI, and merge gates.
**Date:** 2026-11-02
**Repository:** `kefyusuf/agent-state-contract`
**M2 baseline:** `PROJECT_BASELINE_v0.1.md`; Task Lifecycle v0.1 only.
**Change policy:** This document is an experimental design, not an expansion of the runtime contract.
**Candidate fixtures and oracle:** [`M3_SCENARIO_MANIFEST_DRAFT_v0.1.md`](M3_SCENARIO_MANIFEST_DRAFT_v0.1.md) — proposed only, not yet frozen.

## 1. Question and falsifiable claims

**Primary research question:** For agents asked to perform the *same Task Lifecycle tasks*, does access to an explicit command/state contract change task outcomes and the effort needed to understand permitted modifications compared with a conventional direct-state-edit interface?

Three separate hypotheses must not be conflated:

- **H1 (system-level enforcement):** A validated command boundary prevents invariant-violating writes that an unrestricted direct-edit path might permit. This is a guardrail result, not evidence that the agent reasons better.
- **H2 (agent execution):** Given identical task rules and goals, the contracted interface changes end-to-end correct completion and recovery after rejected requests.
- **H3 (agent effort):** The contracted interface changes measured input/output tokens, investigation reads/searches, action attempts, and elapsed time. The direction of the effect is **unknown**.

**Null or unfavorable outcomes are valid.** If commands increase overhead without increasing completion reliability, report that and do not widen the product to rescue the hypothesis.

## 2. Fixed boundaries

- Only `task.create`, `task.claim`, `task.release`, `task.complete`, and `task.get` as defined by M1.
- One Task Lifecycle domain with `todo`, `in_progress`, and terminal `done`.
- Synthetic task titles, actor IDs, and task IDs; no real customer data.
- One process per episode; fresh state for each episode. No persistence, distributed coordination, server, web app, MCP, shared brain, scheduler, or general-purpose agent framework.
- **No modification** of the frozen v0.1 semantics to favor either arm.
- The M2 implementation is an evaluation subject, not the independent success oracle.

Design work may proceed while PR #1 is open; benchmark execution and any new integration code require the M2 gate to close.

## 3. Two arms and comparison limits

| Aspect | A — direct state edit (baseline) | B — explicit contract |
| --- | --- | --- |
| Goal and domain rules | Identical task instructions and invariants | Identical task instructions and invariants |
| Read access | Read a task snapshot through minimal test-harness operation | `task.get` |
| Modification | Replace the synthetic task snapshot directly, with no transition enforcement | Invoke one of four validated commands |
| State structure | Same visible task fields | Same visible task fields |
| Evaluation | Independent oracle checks final state and forbidden intermediate states | Same independent oracle |
| Mutation evidence | Harness records every proposed direct edit | Harness records every proposed command and its response |

The baseline is **deliberately permissive**. It is not a representative sample of all existing architectures. Therefore:
1. Lower invariant violations in B would mainly demonstrate boundary enforcement, not superior agent cognition.
2. Compare **common** outcomes (completed objective, final state, invariant integrity, tokens, time, and investigation events).
3. Report rejected commands separately from invalid direct writes; **never** equate them.
4. The baseline harness must not secretly enforce the M1 command rules. Its independent evaluator may mark episodes unsuccessful.
5. A result from this small synthetic benchmark does not generalize to real repositories without a later separate study.

No real agent/provider is selected or integrated by this design document.

## 4. Fixed scenarios and expected outcomes

Each scenario begins from a fresh and explicitly declared fixture. The success oracle is written from M1 requirements, **not** computed using `TaskContract.replay` or the runtime under test.

| ID | Task requested from agent | Required oracle checks |
| --- | --- | --- |
| S01 | Create T1, claim as A, complete as A | `done`, no owner; correct number of successful state transitions |
| S02 | Let A claim T1; B has a stale claim attempt | No simultaneous owners, B cannot replace A, task remains `in_progress` with A |
| S03 | B attempts to complete A-owned T1; A then completes | B does not change state; final `done` and no owner. Requires predefined, trusted synthetic caller-context switching |
| S04 | Retry an accepted command after later activity, then reuse its ID with changed contents | Contract-specific idempotency and command-ID semantics; **diagnostic only, excluded from paired-primary comparison** |
| S05 | A claims, releases, B claims, B completes | Correct intermediate statuses and final `done`; no ownership leak. Requires predefined, trusted synthetic caller-context switching |
| S06 | Attempt to change terminal `done` task | No new state transition; task stays `done` |

For B, compare accepted/rejected command receipts to M1's fixed expected error precedence. For A, record *all* proposals and independently check every resulting intermediate snapshot. This secondary detail is arm-specific and must not be collapsed into a shared "invalid operations" percentage.

A scenario manifest must fix exact initial snapshots, actor identities, task IDs, expected outcomes, prompt text, and allowed tool descriptions **before** execution. The companion draft proposes fixtures and independently specified oracles but is **not yet frozen**. No changing scenarios after seeing results.

**Comparability correction:** S04 tests command-ID and duplicate-receipt semantics that a direct-state-edit baseline does not expose. Its ten episodes are diagnostic, not comparable in a common primary outcome. Do not pool S04 with the five matched scenarios for success, relative tokens, or duration. The primary paired population is S01/S02/S03/S05/S06. The synthetic actor handoff for S03/S05 must be justified and controlled before those scenarios are executable.

## 5. Matched execution

1. Complete the M2 independent review and merge first.
2. Freeze the M2 source SHA, scenario manifest SHA, model identifier/version, inference settings, tool descriptions, and token/time budgets.
3. Use one agent model and the same system instructions, task goals, maximum steps, and budget across both arms. Arm-specific tool instructions may differ only to explain the available interface.
4. Plan **six scenarios × five repetitions × two arms = 60 episodes** total. **50** are primary paired episodes (S01/S02/S03/S05/S06); **10** are S04 arm-specific diagnostic episodes, excluded from aggregate paired comparisons. Use paired seeds where supported; where not supported, explicitly report non-determinism.
5. Counterbalance arm order across pairs to reduce ordering/caching bias. Do not carry state, conversation history, examples, or previous outcomes between episodes.
6. No human repair during an episode. Record all failures, API errors, and timeouts, including those excluded from a separately reported *valid-run* analysis.
7. Preserve raw tool call and response traces locally in a structured record. Do not commit provider secrets, raw credentials, or private prompts.
8. A human reviewer should audit the frozen scenario manifest and a sample of traces before accepting the report.

The experiment is **exploratory**: 5 paired repeats per scenario are insufficient for strong statistical or universal claims.

## 6. Metrics, exact denominators, and reporting

**Primary endpoint — correct episode completion:** count of episodes whose *full observed trajectory* satisfies the independent state invariants and scenario goal, divided by **all attempted episodes in the five genuinely comparable scenarios** (S01/S02/S03/S05/S06: 25 attempted per arm, 50 total). Count timeouts and tool/model errors as failures. Report the scenarios individually. S04's 10 attempted episodes must be presented separately as a contract-specific diagnostic without aggregate paired claims.

**Secondary measures (all reported even if unfavorable):**
- **Invariant violations:** number of episodes with one or more forbidden intermediate or final states; use one binary episode-level rate as well as total violations.
- **Recovery:** proportion of episodes that reach a correct final state after a failed attempt (with denominator = episodes exhibiting a failed attempt), if any.
- **Token usage:** provider-reported prompt/input and completion/output tokens per episode, plus total; missing usage is `null` and must not be inferred.
- **Exploration reads:** count of state/document/search operations not necessary to execute the requested state transition; classifications must be rule-based and frozen in advance. In this tiny domain, the metric may be uninformative.
- **Elapsed time:** wall-clock seconds measured around the same episode boundary for both arms.
- **Tool calls and state-change proposals:** count each; also report command rejections for B and rejected-by-oracle direct edits for A **separately**.
- **Contract overhead:** input tokens and tool-description bytes provided only because of the contract, explicitly identified rather than hidden.

Each report must show per-scenario raw counts, paired results, medians or distributions for costs, and missingness. Do not use a lone combined "efficiency score" or report unsupported statistical significance.

## 7. Minimum run record (JSONL, one line per episode)

```json
{
  "run_id": "s01-r01-a",
  "scenario_id": "S01",
  "repeat": 1,
  "arm": "direct",
  "model_id": "record-exact-version-at-run-time",
  "source_sha": "record-pinned-m2-sha",
  "manifest_sha": "record-frozen-manifest-sha",
  "started_at": "ISO-8601",
  "duration_seconds": null,
  "status": "completed",
  "goal_satisfied": null,
  "invariants_preserved": null,
  "input_tokens": null,
  "output_tokens": null,
  "exploration_reads": null,
  "tool_calls": null,
  "mutation_attempts": null,
  "failed_attempts": null,
  "failure_reason": null
}
```

Allowed episode status values are `completed`, `timeout`, `tool_error`, and `model_error`. Unavailable metrics remain `null`. Per-call traces are separate artifacts keyed by `run_id`; evaluation results cannot be silently changed after recording.

## 8. Decision rules (locked before running)

- **M3 execution gate:** No run until M2 PR #1 is merged after independent review and passing CI.
- **Protocol integrity gate:** Both arms share the task rubric and have complete, independently checked oracle fixtures and a frozen manifest; the S03/S05 synthetic caller contexts are securely assigned by the test adapter, not by a model's asserted identity; S04 is labeled non-comparable. If these conditions are not met, stop and revise the protocol **before** collecting outcomes.
- **Safety gate:** Contract arm must exhibit zero *accepted* state invariant violations across test and benchmark runs. Any such failure is a defect investigation, not a reason to discard the episode.
- **Evidence gate:** Report completion rate alongside token, time, and exploration costs. A guardrail-only gain must not be described as a gain in agent reasoning or token efficiency.
- **Product decision:** Continue with the same narrow contract only if the study demonstrates a useful reliability/complexity trade-off; otherwise document the negative result and stop or revise the hypothesis explicitly.

No percentage improvement, speed-up, token reduction, or cross-language portability is promised.

## 9. Explicit hold list

Deferred, not approved: external agents or provider SDKs, CLI benchmark runner, new APIs/adapters, model comparisons, cross-language ports, production state storage, additional workflow domains, optimization of event scanning, and packaging.

**Next approved action:** independent review/merge of M2 PR #1, then independent review of the candidate fixture/oracle draft, resolution of caller-context and S04 comparability concerns, and freezing of scenario manifest and expected outputs. Implementation decisions for a minimal harness require a separate review at that point.
