"""Independent fixed-oracle regression cases from the M2 review."""

import threading
import unittest

from agent_state_contract import TaskContract


def command(identifier, action, *, actor="agent-a", task="task-001", version=None, title=None):
    result = {
        "command_id": f"cmd-{identifier}",
        "actor_id": actor,
        "type": f"task.{action}",
        "task_id": task,
        "payload": {"title": title} if action == "create" else {},
    }
    if version is not None:
        result["expected_version"] = version
    return result


class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.store = TaskContract()

    def test_expected_snapshots_at_each_transition(self):
        # Fixed oracle: do not derive expected state through production replay.
        cases = [
            (command(1, "create", title="A task"), "todo", None, 1),
            (command(2, "claim", version=1), "in_progress", "agent-a", 2),
            (command(3, "release", version=2), "todo", None, 3),
            (command(4, "claim", actor="agent-b", version=3), "in_progress", "agent-b", 4),
            (command(5, "complete", actor="agent-b", version=4), "done", None, 5),
        ]
        for operation, status, owner, version in cases:
            with self.subTest(status=status, version=version):
                self.assertTrue(self.store.execute(operation)["applied"])
                self.assertEqual(self.store.get("task-001"), {
                    "ok": True,
                    "task": {
                        "task_id": "task-001",
                        "title": "A task",
                        "status": status,
                        "owner_agent_id": owner,
                        "version": version,
                    },
                })
                self.assertEqual(len(self.store.events), version)

    def test_duplicate_after_later_transition_retains_original_receipt(self):
        created = command(1, "create", title="A task")
        self.assertTrue(self.store.execute(created)["applied"])
        self.assertTrue(self.store.execute(command(2, "claim", version=1))["applied"])
        original_history = self.store.events
        self.assertEqual(self.store.execute(created), {
            "ok": True,
            "applied": False,
            "command_id": "cmd-1",
            "task_id": "task-001",
            "version": 1,
            "event_type": "TaskCreated",
        })
        self.assertEqual(self.store.events, original_history)
        self.assertEqual(self.store.get("task-001")["task"]["version"], 2)

    def test_invalid_query_ids_return_errors_not_exceptions(self):
        for bad_id in (None, 0, False, [], {}, " "):
            with self.subTest(task_id=bad_id):
                self.assertEqual(self.store.get(bad_id), {
                    "ok": False, "code": "INVALID_COMMAND",
                })
                self.assertEqual(self.store.events, ())

    def test_same_command_id_across_concurrent_tasks_has_one_winner(self):
        self.assertTrue(self.store.execute(command(1, "create", title="First"))["applied"])
        self.assertTrue(self.store.execute(command(2, "create", task="task-002", title="Second"))["applied"])
        gate = threading.Barrier(3)
        output = []
        output_lock = threading.Lock()

        def worker(task):
            gate.wait()
            result = self.store.execute(command("shared", "claim", task=task, version=1))
            with output_lock:
                output.append(result)

        threads = [threading.Thread(target=worker, args=(task,))
                   for task in ("task-001", "task-002")]
        for thread in threads:
            thread.start()
        gate.wait()
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())

        self.assertEqual(len(output), 2)
        self.assertEqual(sum(x.get("applied", False) for x in output), 1)
        self.assertEqual([x["code"] for x in output if not x["ok"]], ["COMMAND_ID_REUSED"])
        self.assertEqual(len(self.store.events), 3)
        self.assertEqual(sorted(self.store.get(t)["task"]["version"]
                                for t in ("task-001", "task-002")), [1, 2])


if __name__ == "__main__":
    unittest.main()
