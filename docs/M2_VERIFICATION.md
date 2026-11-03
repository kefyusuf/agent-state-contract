# M2 — Local Verification Record

**Date:** 2026-11-01  
**Scope:** Task Lifecycle Contract v0.1 only  
**Implementation:** Python standard library, one implementation module, three unittest modules  
**Environment:** Python 3.13.5 (local test runner)

## Scope choices

1. Python was selected as a dependency-free **reference implementation language**, not as a mandatory language for future adopters.
2. The authoritative record is a single in-memory list of accepted events. There is no separately mutable canonical state. `task.get` folds the matching task's event history.
3. The command processing lock serializes calls **inside one Python process only**; it is not distributed locking, durability, or cross-process safety.
4. `TaskContract.events` is a diagnostic snapshot (deep-copied), **not** an agent-facing read API. The only agent-facing read remains `task.get`.
5. `replay_events` is a pure verification helper, not an event-sourcing framework or a new mutable interface.

## Test-first execution evidence

| Phase | Evidence | Result |
| --- | --- | --- |
| RED | `RED_test_output.txt` | Test suite failed to import missing implementation module |
| GREEN | `GREEN_test_output.txt` | Initial 21 tests passed |
| Additional RED | `RED_regression_output.txt` | Malformed non-scalar command/event types exposed 6 errors across two test methods |
| Fix + verify | `FINAL_test_output.txt` | All 25 tests passed; source compiled successfully |

The initial 25 test methods included subtests, a separate 300-operation deterministic invariant sequence, and a two-thread same-version claim test. Subsequent review added four fixed-oracle and concurrency/ID regressions, plus two mutable-command-input regressions, totaling **31 published tests**.

## Contract review

- Exactly four mutating commands and one agent-facing query: **satisfied**.
- Validated command envelopes and unknown-field rejection: **satisfied by tests**.
- Duplicate accepted commands do not append events: **satisfied by tests**.
- Rejected commands append no events and do not reserve command IDs: **satisfied by tests**.
- Per-task versions start at one and increment on accepted changes: **satisfied by tests**.
- Task owner/status invariants and terminal state: **satisfied by tests**.
- Duplicate claims evaluated in the same process yield one accepted owner: **satisfied by tests**.
- Replay of well-formed histories and rejection of invalid histories: **satisfied by tests**.
- State and event snapshots cannot be altered by modifying returned dictionaries: **satisfied by tests**.

## M2.4 deterministic differential-model audit (2026-11-03)

- Source: `tests/test_differential_model.py`, now part of the standard `unittest discover` suite.
- The test uses a separate, test-only reference state model rather than calling the implementation's replay or transition helpers.
- Initial 9,375-attempt corpus operated on only five synthetic task IDs and became dominated by duplicate/rejected commands as tasks reached the terminal state. Its raw attempt count should **not** be presented as broad transition coverage.
- Checks exact command receipts, per-task snapshots after every command, and accepted event counts; includes duplicate IDs, stale versions, invalid envelopes, ownership and terminal transitions.
- Local inclusion check: test discovery succeeded. GitHub Actions run [41588060129](https://github.com/kefyusuf/agent-state-contract/actions/runs/41588060129) passed **32 tests** on both Python 3.10 and 3.13, including this one differential test method.
- This is regression evidence for one fixed corpus, **not** an independent human review, exhaustive proof, LLM benchmark, or demonstrated token savings.

## M2.5 balanced live-transition differential audit (2026-11-03)

- Revised `tests/test_differential_model.py` to retain **25 deterministic seeds × 375 attempts = 9,375** while creating fresh tasks when prior ones become terminal, then exercising live claim, release, and complete transitions. Existing invalid-command, stale-version, ownership, and deduplication checks remain.
- **RED:** explicit coverage floors added to the previous generator failed; only 368 new accepted commands occurred across the corpus, below the 3,000-command minimum.
- **GREEN (local verification):** 5,483 new accepted commands, including 1,352 successful releases and 614 successful completions, plus 1,115 idempotent duplicate receipts. All seven defined error types occurred. These values are descriptive of the deterministic test corpus, not production reliability metrics.
- The test now asserts minimum coverage floors (new accepted commands ≥3,000, releases ≥350, completions ≥350, duplicates ≥600, and each defined error observed). It samples all known tasks periodically and checks the selected task after each attempt.
- GitHub Actions run [41589895007](https://github.com/kefyusuf/agent-state-contract/actions/runs/41589895007) **success** on Python 3.10 and 3.13 with the updated model-audit test. No v0.1 application code or contract semantics were changed.
- This is better exercise of the *synthetic* state machine, **not** an independent review, formal proof, agent benchmark, or evidence of gains in tokens or architecture rediscovery.

## Remaining limits and risks

- No external agent, LLM, or provider was invoked. The actor identity is test-supplied and must be injected by a trusted adapter in any future integration.
- No persistence, network API, real distributed concurrency, authorization or authentication.
- Event folds and command-ID lookups scan in-memory history. Complexity/scaling is deliberately **not** optimized or benchmarked.
- Unit tests are evidence only for the tested scenarios, not formal verification or universal absence of failures.
- The research hypothesis about token use, architecture rediscovery and real agent reliability has **not been tested**.

## Repository and release gate (updated 2026-11-03)

- Repository: https://github.com/kefyusuf/agent-state-contract
- Branch: `feat/m2-task-contract`
- PR: https://github.com/kefyusuf/agent-state-contract/pull/1
- Initial M2 commit: `c015d51a352d219871b588eb7411a910bef553c4`
- Initial GitHub Actions run `41351574644`: **success**, 25 tests on Python 3.10 and 3.13.
- M2.1 verification run `41353287871`: **success**, 29 tests on Python 3.10 and 3.13.
- M2.2 verification run [`41405814008`](https://github.com/kefyusuf/agent-state-contract/actions/runs/41405814008): **success**, **31 tests** on Python 3.10 and 3.13; commit `e2cae3de001c0beb6dd1c9fde36a1da40c055858`.
- M2.4 differential audit run [`41588060129`](https://github.com/kefyusuf/agent-state-contract/actions/runs/41588060129): **success**, **32 tests** on both Python versions; test integration commit `ed5525df8a4a8aaa371ae73e2c4e9c79f08c2740`.
- Review gate: **pending**. GitHub has no independent submitted approval; do not merge until reviewed.
- Fixed-oracle, concurrent global-ID, and mutable caller-command input regressions are included. The latest successful CI run is the authoritative reproducible evidence for this branch.

The original RED/GREEN output files were not committed with the reference implementation; the narrative above records the historical local workflow. The current tests and GitHub Actions runs are reproducible evidence for the published branch.

## Independent review checklist (still pending)

The reviewer should examine the **latest** head commit rather than infer approval from successful tests:

1. Does `execute()` process a stable copy of the user-owned envelope and payload after validation, with its stated single-process limits?
2. Do the four commands, version/error precedence, accepted-command ID deduplication, and ownership invariants match `PROJECT_BASELINE_v0.1.md`?
3. Can a rejected or duplicated command append an event or modify an already accepted task?
4. Do the new regression tests assert fixed expected state and receipts without treating `replay()` as an independent oracle?
5. Are the omitted guarantees (durability, trusted actor authentication, distributed consistency, real-agent gains) clearly stated?

**Gate:** An independent GitHub review with an approval decision and a green CI result for the reviewed head are required before merge. A review checklist or self-review comment does **not** satisfy this gate.

**Next action:** Obtain independent review of PR #1 and verify CI again before merge. M3 code and execution remain out of scope until that gate closes.
