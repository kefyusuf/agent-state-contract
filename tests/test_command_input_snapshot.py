"""Regression tests for mutable caller-owned command input (M2)."""

import unittest
from unittest.mock import patch

import agent_state_contract as module
from agent_state_contract import TaskContract


class CommandSnapshotTests(unittest.TestCase):
    def test_payload_mutation_after_validation_does_not_corrupt_event(self):
        original = module._valid_command
        submitted = {
            "command_id": "c1", "actor_id": "agent-a", "type": "task.create",
            "task_id": "T1", "payload": {"title": "Valid title"},
        }

        def validate_then_mutate(arg):
            valid = original(arg)
            if valid:
                submitted["payload"]["title"] = " "
            return valid

        with patch.object(module, "_valid_command", validate_then_mutate):
            result = TaskContract()
            response = result.execute(submitted)

        self.assertTrue(response["ok"])
        self.assertEqual(result.get("T1")["task"]["title"], "Valid title")
        self.assertEqual(result.events[0]["data"], {"title": "Valid title"})

    def test_type_mutation_after_validation_does_not_change_transition(self):
        original = module._valid_command
        submitted = {
            "command_id": "c1", "actor_id": "agent-a", "type": "task.create",
            "task_id": "T1", "payload": {"title": "Valid title"},
        }

        def validate_then_mutate(arg):
            valid = original(arg)
            if valid:
                submitted["type"] = "task.delete"
            return valid

        with patch.object(module, "_valid_command", validate_then_mutate):
            store = TaskContract()
            response = store.execute(submitted)

        self.assertEqual(response, {
            "ok": True, "applied": True, "command_id": "c1", "task_id": "T1",
            "version": 1, "event_type": "TaskCreated",
        })
        self.assertEqual(store.get("T1")["task"]["status"], "todo")


if __name__ == "__main__":
    unittest.main()
