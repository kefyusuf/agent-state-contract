# M3 — Controlled Evaluation Protocol v0.1

**Status:** Pre-registration draft; **NOT authorized to execute** until M2 PR #1 has passed independent review, current CI, and merge gates.
**Date:** 2026-11-02
**Repository:** `kefyusuf/agent-state-contract`
**M2 baseline:** `PROJECT_BASELINE_v0.1.md`; Task Lifecycle v0.1 only.
**Change policy:** This document is an experimental design, not an expansion of the runtime contract.
**Candidate fixtures and oracle:** [`M3_SCENARIO_MANIFEST_DRAFT_v0.1.md`](M3_SCENARIO_MANIFEST_DRAFT_v0.1.md) — proposed only, not yet frozen.
**Machine-readable expected outcomes:** [`M3_ORACLE_VECTORS_DRAFT_v0.1.json`](M3_ORACLE_VECTORS_DRAFT_v0.1.json) — public for reviewer inspection, but **must be inaccessible to evaluated agents during episodes**. This requires explicit tool/file/network isolation; merely withholding a file from the prompt is insufficient. Expected values require independent audit.
**Agent-facing interface and prompt candidates:** [`M3_ARM_INTERFACES_DRAFT_v0.1.md`](M3_ARM_INTERFACES_DRAFT_v0.1.md) — paired goal texts, minimal tool surfaces, and host-controlled identity. Draft; not frozen or executable.

## 1. Question and falsifiable claims

**Primary research question:** For agents asked to perform the *same Task Lifecycle tasks*, does access to an explicit command/state contract change task outcomes and the effort needed to understand permitted modifications compared with a conventional direct-state-edit interface?

Three separate hypotheses must not be conflated:

- **H1 (system-level enforcement):** A validated command boundary prevents invariant-violating writes that an unrestricted direct-edit path might permit. This is a guardrail result, not evidence that the agent reasons better.
- **H2 (agent execution):** Given identical task rules and goals, the contracted interface changes end-to-end correct completion and recovery after rejected requests.
- **H3 (agent effort):** The contracted interface changes measured input/output tokens, task-state reads, action attempts, and elapsed time. The direction of the effect is **unknown**. This tool-isolated study does **not** measure repository architecture rediscovery.

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
| S03 | B attempts to complete an A-owned task | No successful mutation; task remains `in_progress`, owner A, unchanged version. B is the fixed caller for the entire episode |
| S04 | Retry an accepted command after later activity, then reuse its ID with changed contents | Contract-specific idempotency and command-ID semantics; **diagnostic only, excluded from paired-primary comparison** |
| S05 | A claims, releases, reclaims, and completes | Correct intermediate statuses and final `done`; no ownership leak. A is the fixed caller for the entire episode |
| S06 | Attempt to change terminal `done` task | No new state transition; task stays `done` |

For B, compare accepted/rejected command receipts to M1's fixed expected error precedence. For A, record *all* proposals and independently check every resulting intermediate snapshot. This secondary detail is arm-specific and must not be collapsed into a shared "invalid operations" percentage.

A scenario manifest must fix exact initial snapshots, actor identities, task IDs, expected outcomes, prompt text, and allowed tool descriptions **before** execution. The companion draft proposes fixtures and independently specified oracles but is **not yet frozen**. No changing scenarios after seeing results.

**Comparability correction:** S04 tests command-ID and duplicate-receipt semantics that a direct-state-edit baseline does not expose. Run S04 **only in the contract arm** as a five-episode diagnostic. Never pool it with the five matched scenarios for success, relative tokens, or duration. The paired-primary population is S01/S02/S03/S05/S06. S03 uses B throughout, and S05 uses A throughout; no within-episode actor switching is required.

## 5. Matched execution

1. Complete the M2 independent review and merge first.
2. Freeze the M2 source SHA, scenario manifest SHA, model identifier/version, inference settings, tool descriptions, and token/time budgets.
3. Use one agent model and the same system instructions, task goals, maximum steps, and budget across both arms. Arm-specific tool instructions may differ only to explain the available interface.
4. Plan **55 episodes total**: five primary scenarios × five repetitions × two arms = **50 matched episodes**, plus one contract-only diagnostic scenario (S04) × five repetitions = **5 episodes**. Pair seeds only for the 50 comparable episodes where supported; otherwise report non-determinism. No baseline S04 runs are planned.
5. Counterbalance arm order across pairs to reduce ordering/caching bias. Do not carry state, conversation history, examples, or previous outcomes between episodes.
6. No human repair during an episode. Record all failures, API errors, and timeouts, including those excluded from a separately reported *valid-run* analysis.
7. Preserve raw tool call and response traces locally in a structured record. Do not commit provider secrets, raw credentials, or private prompts.
8. A human reviewer should audit the frozen scenario manifest and a sample of traces before accepting the report.

The experiment is **exploratory**: 5 paired repeats per scenario are insufficient for strong statistical or universal claims.

## 6. Metrics, exact denominators, and reporting

**Primary endpoint — correct episode completion:** count of episodes satisfying **all three** predeclared conditions: (i) the *full observed state trajectory* preserves invariants and achieves the scenario's required state objective, (ii) any required state-read evidence actually occurred in the trace, and (iii) the final response correctly reports the task outcome or reason no legal change occurred. Divide by **all attempted episodes in the five genuinely comparable scenarios** (S01/S02/S03/S05/S06: 25 attempted per arm, 50 total). Count timeouts and tool/model errors as failures. Report scenarios individually. S04's 5 contract-only episodes are diagnostic only, with no cross-arm comparison.

**Mandatory observation checks:** S02, S03, and S06 each require at least one successful current-state `task_get` call **after fixture setup** (not a stale observation), plus a correct explanation of the currently owned or terminal status. Without both, unchanged state alone is insufficient for success. S01 and S05 require the specified ordered transitions and an accurate completion report; S04 requires the two specified contract calls, unchanged state, and accurate receipt reporting. Apply the same observation and final-report rubric to both arms of each paired scenario.

**Secondary measures (all reported even if unfavorable):**
- **Invariant violations:** number of episodes with one or more forbidden intermediate or final states; use one binary episode-level rate as well as total violations.
- **Recovery:** proportion of episodes that reach a correct final state after a failed attempt (with denominator = episodes exhibiting a failed attempt), if any.
- **Token usage:** provider-reported prompt/input and completion/output tokens per episode, plus total; missing usage is `null` and must not be inferred.
- **Task-state reads:** count of `task_get` calls per episode; distinguish required observation reads (S02/S03/S06) from additional reads. A read is not automatically wasteful: recovery or safety checks may justify extras. The experiment exposes no repository/document/search tools, so **architecture rediscovery cannot be measured** and must not appear as an efficacy claim.
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
  "required_read_satisfied": null,
  "final_report_accurate": null,
  "state_reads": null,
  "input_tokens": null,
  "output_tokens": null,
  "tool_calls": null,
  "mutation_attempts": null,
  "failed_attempts": null,
  "failure_reason": null
}
```

Allowed episode status values are `completed`, `timeout`, `tool_error`, and `model_error`. Unavailable metrics remain `null`. Per-call traces are separate artifacts keyed by `run_id`; evaluation results cannot be silently changed after recording.

## 8. Decision rules (locked before running)

- **M3 execution gate:** No run until M2 PR #1 is merged after independent review and passing CI.
- **Protocol integrity gate:** Both arms share the task rubric and have complete, independently checked oracle fixtures and a frozen manifest; each episode has exactly one fixed trusted synthetic caller identity supplied by its harness, never by a model's asserted identity; S04 is contract-only and non-comparable. If these conditions are not met, stop and revise the protocol **before** collecting outcomes.
- **Safety gate:** Contract arm must exhibit zero *accepted* state invariant violations across test and benchmark runs. Any such failure is a defect investigation, not a reason to discard the episode.
- **Evidence gate:** Report completion rate alongside token, time, and exploration costs. A guardrail-only gain must not be described as a gain in agent reasoning or token efficiency.
- **Product decision:** Continue with the same narrow contract only if the study demonstrates a useful reliability/complexity trade-off; otherwise document the negative result and stop or revise the hypothesis explicitly.

No percentage improvement, speed-up, token reduction, or cross-language portability is promised.

## 9. Explicit hold list

Deferred, not approved: external agents or provider SDKs, CLI benchmark runner, new APIs/adapters, model comparisons, cross-language ports, production state storage, additional workflow domains, optimization of event scanning, and packaging.

**Next approved action:** independent review/merge of M2 PR #1, then independent review of the revised candidate fixture/oracle draft, confirmation of fixed actor identity per episode, and freezing of the manifest and expected outputs. Implementation decisions for a minimal harness require a separate review at that point.

## 10. Pre-registration simplification record (2026-11-02)

Before any benchmark execution, two design constraints were tightened:

1. **One trusted actor per episode.** S03 now asks fixed actor B to evaluate an unauthorized completion without switching to A afterward. S05 uses fixed actor A for claim → release → reclaim → complete. This removes unnecessary caller-context switching infrastructure; M2's existing unit tests still cover two distinct actor identities and ownership handoff.
2. **No meaningless baseline diagnostics.** S04 tests deduplication receipts unique to the command contract, so only the B contract arm runs it. The exploratory allocation is **50 paired + 5 contract-only = 55 episodes**. This preserves primary paired denominators while avoiding baseline calls with no equivalent command-ID semantics.

No observations were collected before these changes. Both protocol and scenario-manifest documents remain **drafts pending independent review**. No new runtime behavior was approved.

## 11. Evaluation integrity preflight — access and identity boundaries

**Protocol amendment before data collection:** The public repository contains both the runtime under test and the proposed answer key. If an evaluated agent can read the oracle, source tests, fixtures, GitHub pages, or run artifacts that disclose expected answers, the result cannot support the claimed comparison. Similarly, `actor_id` in the Python command envelope is not a trusted caller identity by itself.

Before executing any benchmark episode, an independently reviewed minimal harness plan must demonstrate all of the following:

1. **Agent allowlist:** Each arm receives only its fixed task prompt, identical Task Lifecycle rules, applicable interface description, and ordinary tool results. Do not expose `docs/M3_ORACLE_VECTORS_DRAFT_v0.1.json`, the evaluator, scenario expected snapshots, test source, or prior episode traces. No repository browsing, search, web access, or arbitrary file-read tools during the episode. A repo document needed for domain rules must be supplied as a separate, reviewed excerpt with the oracle excluded.
2. **Independent scoring boundary:** The scorer runs **outside** the agent-accessible context. It reads the complete immutable tool trace only after the episode and never supplies intermediate scoring hints to either arm. Log attempted direct edits and command responses; do not silently repair invalid edits.
3. **Host-controlled actor:** For each episode, fix `trusted_actor_id` in the harness, not the model prompt alone. The contract-arm adapter must force that identity into `execute()` or reject mismatched model-provided `actor_id` before it reaches the runtime. The direct-edit arm must have the **same** host actor identity, logged separately from any proposed snapshot fields. Neither arm can change its trusted actor by generating a tool argument.
4. **Preflight checks:** Confirm an attempted oracle/repository read is unavailable to the agent; confirm a command with a forged actor cannot execute as the forged identity; confirm the scorer has not supplied expected outputs to the agent. These are **setup qualification checks**, performed only after the M2 gate and **not counted as benchmark episodes**. If any check fails, mark `invalid_harness_setup`, repair before collecting observations, and report the failure.
5. **Fixture isolation:** Initialize each episode's seed state outside the agent session; do not provide the model the seed event log or prior run history unless a scenario explicitly permits an earlier observation. Retain a versioned, hashed manifest outside the accessible tool surface.

These preflight controls do not add production authentication, a new API, or general agent infrastructure to the Task Lifecycle contract. The adapter is a narrowly scoped measurement boundary whose implementation remains **unapproved until M2 review/merge and an independent harness design review**.

## 12. Observation and final-report scoring amendment (2026-11-02)

The initial draft was vulnerable to **no-op false positives**: an agent could leave an already protected task unchanged and be scored correct without checking the current state or identifying why a mutation was illegal. Before running any episodes, the primary success rubric now requires observable state-read evidence for S02, S03, and S06, and an accurate terminal report. A read from a stale fixture, an unverified assertion in the final text, or a scorer-generated explanation does not count. S01/S05 still require the complete ordered state trajectory.

The `task_get` read exists in both arms, so this evidence rule is symmetric. Classify failed/unavailable reads separately and do not assign correctness to a model merely for abstaining. The contract-only S04 requires its two diagnostic requests and accurate receipts.

**Measurement limitation:** This study deliberately denies repository browsing. It can evaluate state-use efficiency but **cannot** validate the broader architecture-rediscovery portion of the product hypothesis. Do not invent repository-discovery savings or treat raw state-read counts as architectural understanding.

These are prospective specification corrections. No model invocation, benchmark run, or observed outcome preceded them; the protocol remains a draft until the independent review gate closes.
