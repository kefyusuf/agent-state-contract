"""Executable acceptance criteria for the Task Lifecycle v0.1 contract."""

import random
import threading
import unittest

from agent_state_contract import InvalidEventStream, TaskContract, replay_events


def make_command(number, action, *, actor="agent-a", task="task-001", version=None, title=None):
    command = {
        "command_id": f"cmd-{number}",
        "actor_id": actor,
        "type": f"task.{action}",
        "task_id": task,
        "payload": {"title": title} if action == "create" else {},
    }
    if version is not None:
        command["expected_version"] = version
    return command


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.store = TaskContract()

    def create(self):
        return self.store.execute(make_command(1, "create", title="Fix race condition"))

    def claim(self):
        self.create()
        return self.store.execute(make_command(2, "claim", version=1))

    def assert_error(self, response, code):
        self.assertEqual(response, {"ok": False, "code": code})

    def test_fourteen_step_acceptance_sequence(self):
        s = self.store
        accepted = self.create()
        self.assertEqual(accepted, {"ok": True, "applied": True, "command_id": "cmd-1", "task_id": "task-001", "version": 1, "event_type": "TaskCreated"})
        claim = make_command(2, "claim", version=1)
        self.assertEqual(s.execute(claim)["version"], 2)
        stale = s.execute(make_command(3, "claim", actor="agent-b", version=1))
        self.assertEqual(stale, {"ok": False, "code": "VERSION_CONFLICT", "current_version": 2})
        self.assert_error(s.execute(make_command(4, "release", actor="agent-b", version=2)), "NOT_OWNER")
        self.assertEqual(s.execute(claim), {"ok": True, "applied": False, "command_id": "cmd-2", "task_id": "task-001", "version": 2, "event_type": "TaskClaimed"})
        self.assertEqual(s.execute(make_command(5, "release", version=2))["version"], 3)
        self.assertEqual(s.execute(make_command(6, "claim", actor="agent-b", version=3))["version"], 4)
        complete = make_command(7, "complete", actor="agent-b", version=4)
        self.assertEqual(s.execute(complete)["version"], 5)
        self.assert_error(s.execute(make_command(8, "complete", actor="agent-b", version=5)), "INVALID_TRANSITION")
        self.assertFalse(s.execute(complete)["applied"])
        self.assert_error(s.execute(make_command(7, "release", actor="agent-b", version=4)), "COMMAND_ID_REUSED")
        self.assert_error(s.execute(make_command(9, "create", title="Another title")), "TASK_ALREADY_EXISTS")
        self.assert_error(s.execute({"type": "task.delete"}), "INVALID_COMMAND")
        expected = {"ok": True, "task": {"task_id": "task-001", "title": "Fix race condition", "status": "done", "owner_agent_id": None, "version": 5}}
        self.assertEqual(s.get("task-001"), expected)
        self.assertEqual(s.replay("task-001"), expected)
        self.assertEqual(len(s.events), 5)

    def test_missing_task_query_and_command(self):
        self.assert_error(self.store.get("missing"), "TASK_NOT_FOUND")
        self.assert_error(self.store.execute(make_command(2, "claim", version=1)), "TASK_NOT_FOUND")

    def test_create_rejects_blank_title_without_reserving_command_id(self):
        self.assert_error(self.store.execute(make_command(1, "create", title="   ")), "INVALID_COMMAND")
        self.assertTrue(self.create()["applied"])
        self.assertEqual(len(self.store.events), 1)

    def test_preserves_original_title_text(self):
        self.store.execute(make_command(1, "create", title="  Keep spaces  "))
        self.assertEqual(self.store.get("task-001")["task"]["title"], "  Keep spaces  ")

    def test_claim_after_owner_claim_with_current_version_is_invalid(self):
        self.claim()
        self.assert_error(self.store.execute(make_command(3, "claim", actor="agent-b", version=2)), "INVALID_TRANSITION")

    def test_release_and_complete_of_todo_are_invalid(self):
        self.create()
        self.assert_error(self.store.execute(make_command(2, "release", version=1)), "INVALID_TRANSITION")
        self.assert_error(self.store.execute(make_command(3, "complete", version=1)), "INVALID_TRANSITION")

    def test_terminal_done_cannot_transition(self):
        self.claim()
        self.store.execute(make_command(3, "complete", version=2))
        for action in ("claim", "release", "complete"):
            with self.subTest(action=action):
                self.assert_error(self.store.execute(make_command(f"4-{action}", action, version=3)), "INVALID_TRANSITION")

    def test_command_id_is_global_across_tasks(self):
        self.create()
        self.assert_error(self.store.execute(make_command(1, "create", task="task-002", title="Other")), "COMMAND_ID_REUSED")

    def test_repeated_accepted_command_ignores_current_version(self):
        self.claim()
        original = make_command(1, "create", title="Fix race condition")
        self.assertEqual(self.store.execute(original)["version"], 1)
        self.assertFalse(self.store.execute(original)["applied"])
        self.assertEqual(len(self.store.events), 2)

    def test_rejected_command_id_can_be_retried(self):
        self.create()
        rejected = make_command(2, "claim", version=99)
        self.assertEqual(self.store.execute(rejected)["code"], "VERSION_CONFLICT")
        accepted = make_command(2, "claim", version=1)
        self.assertTrue(self.store.execute(accepted)["applied"])

    def test_semantic_comparison_ignores_dict_property_order(self):
        original = make_command(1, "create", title="Fix race condition")
        self.store.execute(original)
        same = dict(reversed(list(original.items())))
        self.assertFalse(self.store.execute(same)["applied"])

    def test_unknown_fields_and_wrong_schemas_are_rejected(self):
        valid = make_command(1, "create", title="OK")
        variants = [
            {**valid, "extra": 1},
            {**valid, "expected_version": None},
            {**valid, "expected_version": 1},
            {**valid, "actor_id": ""},
            {**valid, "task_id": ""},
            {**valid, "command_id": "  "},
            {**valid, "payload": {"title": "OK", "extra": 1}},
            {**valid, "payload": {"title": 42}},
            {**valid, "type": "task.delete"},
            ["not", "a", "dict"],
            None,
            make_command(2, "claim", version=True),
            make_command(2, "claim", version=0),
            make_command(2, "claim"),
            {**make_command(2, "claim", version=1), "payload": {"title": "No"}},
        ]
        for case in variants:
            with self.subTest(case=case):
                self.assert_error(self.store.execute(case), "INVALID_COMMAND")
        self.assertEqual(len(self.store.events), 0)

    def test_non_scalar_command_type_is_invalid_not_exception(self):
        for kind in ([], {}, {"claim": True}):
            with self.subTest(kind=kind):
                command = {**make_command(1, "create", title="Valid"), "type": kind}
                self.assert_error(self.store.execute(command), "INVALID_COMMAND")

    def test_independent_task_versions_and_replay(self):
        self.create()
        second = make_command(2, "create", task="task-002", title="Second")
        self.store.execute(second)
        self.store.execute(make_command(3, "claim", task="task-002", version=1))
        self.assertEqual(self.store.get("task-001")["task"]["version"], 1)
        self.assertEqual(self.store.get("task-002")["task"]["version"], 2)
        self.assertEqual(self.store.replay("task-001"), self.store.get("task-001"))
        self.assertEqual(self.store.replay("task-002"), self.store.get("task-002"))

    def test_deterministic_sequence_preserves_invariants(self):
        self.create()
        rng = random.Random(12345)
        for sequence in range(2, 302):
            before = self.store.get("task-001")["task"]
            count_before = len(self.store.events)
            action = rng.choice(("claim", "release", "complete"))
            actor = rng.choice(("agent-a", "agent-b", "agent-c"))
            version = rng.choice((before["version"], max(1, before["version"] - 1)))
            result = self.store.execute(make_command(sequence, action, actor=actor, version=version))
            after = self.store.get("task-001")["task"]
            self.assertEqual(self.store.replay("task-001")["task"], after)
            self.assertEqual(len(self.store.events), count_before + int(result["ok"]))
            self.assertEqual(after["version"], before["version"] + int(result["ok"]))
            self.assertIn(after["status"], ("todo", "in_progress", "done"))
            self.assertEqual(after["owner_agent_id"] is None, after["status"] != "in_progress")

    def test_stale_precedes_not_owner(self):
        self.claim()
        self.assertEqual(self.store.execute(make_command(3, "release", actor="agent-b", version=1))["code"], "VERSION_CONFLICT")
        self.assertEqual(self.store.execute(make_command(4, "release", actor="agent-b", version=2))["code"], "NOT_OWNER")

    def test_read_has_no_side_effect(self):
        self.create()
        before = self.store.events
        self.store.get("task-001")
        self.store.replay("task-001")
        self.assertEqual(self.store.events, before)

    def test_exposed_state_and_events_are_defensive_copies(self):
        self.create()
        returned = self.store.get("task-001")
        returned["task"]["title"] = "tampered"
        returned_events = self.store.events
        returned_events[0]["data"]["title"] = "tampered"
        self.assertEqual(self.store.get("task-001")["task"]["title"], "Fix race condition")

    def test_two_threads_cannot_both_claim_one_task(self):
        self.create()
        gate = threading.Barrier(3)
        results = []
        lock = threading.Lock()
        def worker(actor):
            gate.wait()
            result = self.store.execute(make_command(actor, "claim", actor=actor, version=1))
            with lock:
                results.append(result)
        threads = [threading.Thread(target=worker, args=(actor,)) for actor in ("agent-a", "agent-b")]
        for thread in threads:
            thread.start()
        gate.wait()
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(sorted(result["ok"] for result in results), [False, True])
        self.assertEqual({result.get("code") for result in results if not result["ok"]}, {"VERSION_CONFLICT"})
        self.assertEqual(self.store.get("task-001")["task"]["version"], 2)
        self.assertEqual(len(self.store.events), 2)


class ReplayValidationTests(unittest.TestCase):
    def setUp(self):
        store = TaskContract()
        store.execute(make_command(1, "create", title="A task"))
        store.execute(make_command(2, "claim", version=1))
        self.valid = list(store.events)

    def assert_bad(self, events):
        with self.assertRaises(InvalidEventStream):
            replay_events(events, "task-001")

    def test_valid_replay_returns_current_state(self):
        self.assertEqual(replay_events(self.valid, "task-001")["version"], 2)

    def test_missing_creation_or_version_gap_or_duplicate(self):
        self.assert_bad(self.valid[1:])
        self.assert_bad([{**self.valid[0], "version": 2}])
        self.assert_bad([self.valid[0], {**self.valid[1], "version": 3}])
        self.assert_bad([self.valid[0], self.valid[0]])

    def test_invalid_ownership_or_transition(self):
        self.assert_bad([self.valid[0], {**self.valid[1], "event_type": "TaskReleased"}])
        self.assert_bad([self.valid[0], self.valid[1], {**self.valid[1], "version": 3, "command_id": "cmd-3", "event_type": "TaskCompleted", "actor_id": "agent-b"}])
        self.assert_bad([self.valid[0], {**self.valid[1], "event_type": "Unknown"}])

    def test_invalid_event_fields_and_payload(self):
        self.assert_bad([{**self.valid[0], "extra": "unknown"}])
        self.assert_bad([{**self.valid[0], "data": {"title": ""}}])
        self.assert_bad([{**self.valid[0], "task_id": "other"}])
        self.assert_bad([{**self.valid[0], "version": True}])
        self.assert_bad([{**self.valid[0], "command_id": ""}])

    def test_non_scalar_event_type_is_invalid_not_exception(self):
        for kind in ([], {}, {"Created": True}):
            with self.subTest(kind=kind):
                self.assert_bad([{**self.valid[0], "event_type": kind}])

    def test_replay_empty_history_is_missing(self):
        self.assertIsNone(replay_events([], "task-001"))


if __name__ == "__main__":
    unittest.main()