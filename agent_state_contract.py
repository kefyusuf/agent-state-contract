"""Minimal in-memory reference implementation of Task Lifecycle Contract v0.1.

Only accepted events are authoritative. Commands have a single serialized
mutation path; snapshots are reconstructed by replay rather than stored as
an independent mutable source. This is not a distributed or durable service.
"""

from copy import deepcopy
from threading import Lock


_EVENT_FROM_COMMAND = {
    "task.create": "TaskCreated",
    "task.claim": "TaskClaimed",
    "task.release": "TaskReleased",
    "task.complete": "TaskCompleted",
}
_COMMAND_FROM_EVENT = {event: command for command, event in _EVENT_FROM_COMMAND.items()}
_EVENT_KEYS = {"command_id", "actor_id", "task_id", "version", "event_type", "data"}
_BASE_KEYS = {"command_id", "actor_id", "type", "task_id", "payload"}


class InvalidEventStream(ValueError):
    """An event stream violates the contract's shape or transition rules."""


def _identifier(value):
    return isinstance(value, str) and bool(value.strip())


def _positive_integer(value):
    return type(value) is int and value > 0


def _valid_command(command):
    if not isinstance(command, dict):
        return False
    if not isinstance(command.get("type"), str) or command["type"] not in _EVENT_FROM_COMMAND:
        return False
    is_create = command["type"] == "task.create"
    required = _BASE_KEYS if is_create else _BASE_KEYS | {"expected_version"}
    if set(command) != required:
        return False
    if not all(_identifier(command[key]) for key in ("command_id", "actor_id", "task_id")):
        return False
    if not is_create and not _positive_integer(command["expected_version"]):
        return False
    payload = command["payload"]
    if not isinstance(payload, dict):
        return False
    if is_create:
        return set(payload) == {"title"} and _identifier(payload["title"])
    return payload == {}


def replay_events(events, task_id):
    """Purely fold a single task's ordered events; reject invalid history.

    Returns a new task dict, or None for empty history. This function is a
    verification helper, not an additional agent-facing query operation.
    """
    if not _identifier(task_id):
        raise InvalidEventStream("Invalid task_id")
    state = None
    seen_ids = set()
    for event in events:
        if not isinstance(event, dict) or set(event) != _EVENT_KEYS:
            raise InvalidEventStream("Invalid event shape")
        if not all(_identifier(event[key]) for key in ("command_id", "actor_id", "task_id")):
            raise InvalidEventStream("Invalid event identity")
        if event["task_id"] != task_id:
            raise InvalidEventStream("Event belongs to another task")
        if event["command_id"] in seen_ids:
            raise InvalidEventStream("Duplicate command ID")
        seen_ids.add(event["command_id"])
        if not _positive_integer(event["version"]):
            raise InvalidEventStream("Invalid event version")
        if not isinstance(event["event_type"], str) or event["event_type"] not in _COMMAND_FROM_EVENT:
            raise InvalidEventStream("Unknown event type")
        if not isinstance(event["data"], dict):
            raise InvalidEventStream("Invalid event data")

        expected_version = 1 if state is None else state["version"] + 1
        if event["version"] != expected_version:
            raise InvalidEventStream("Non-contiguous task versions")
        event_type = event["event_type"]
        if event_type == "TaskCreated":
            if state is not None or set(event["data"]) != {"title"} or not _identifier(event["data"]["title"]):
                raise InvalidEventStream("Invalid creation")
            state = {
                "task_id": task_id,
                "title": event["data"]["title"],
                "status": "todo",
                "owner_agent_id": None,
                "version": 1,
            }
            continue
        if state is None or event["data"] != {}:
            raise InvalidEventStream("Missing creation or unexpected data")
        if event_type == "TaskClaimed":
            if state["status"] != "todo":
                raise InvalidEventStream("Claim requires todo")
            state["status"] = "in_progress"
            state["owner_agent_id"] = event["actor_id"]
        elif event_type in ("TaskReleased", "TaskCompleted"):
            if state["status"] != "in_progress" or state["owner_agent_id"] != event["actor_id"]:
                raise InvalidEventStream("Release/complete requires current owner")
            state["status"] = "todo" if event_type == "TaskReleased" else "done"
            state["owner_agent_id"] = None
        state["version"] = event["version"]
    return state


def _command_from_event(event):
    """Reconstruct the original accepted command for semantic deduplication."""
    kind = _COMMAND_FROM_EVENT[event["event_type"]]
    command = {
        "command_id": event["command_id"],
        "actor_id": event["actor_id"],
        "type": kind,
        "task_id": event["task_id"],
        "payload": deepcopy(event["data"]),
    }
    if kind != "task.create":
        command["expected_version"] = event["version"] - 1
    return command


def _receipt(event, applied):
    return {
        "ok": True,
        "applied": applied,
        "command_id": event["command_id"],
        "task_id": event["task_id"],
        "version": event["version"],
        "event_type": event["event_type"],
    }


def _error(code, **extra):
    return {"ok": False, "code": code, **extra}


class TaskContract:
    """Small serialized command processor, with no database or external deps."""

    def __init__(self):
        self._events = []
        self._lock = Lock()

    @property
    def events(self):
        """Defensive diagnostic snapshot for tests; not an agent query API."""
        with self._lock:
            return tuple(deepcopy(self._events))

    def _derive(self, task_id):
        return replay_events((e for e in self._events if e["task_id"] == task_id), task_id)

    def get(self, task_id):
        """The sole agent-facing query: task.get(task_id)."""
        if not _identifier(task_id):
            return _error("INVALID_COMMAND")
        with self._lock:
            state = self._derive(task_id)
            return {"ok": True, "task": state} if state is not None else _error("TASK_NOT_FOUND")

    def replay(self, task_id):
        """Diagnostic replay used to check current state; not an agent query."""
        return self.get(task_id)

    def execute(self, command):
        """Validate, deduplicate, conditionally transition, append one event."""
        if not _valid_command(command):
            return _error("INVALID_COMMAND")
        with self._lock:
            for previous in self._events:
                if previous["command_id"] == command["command_id"]:
                    if _command_from_event(previous) == command:
                        return _receipt(previous, applied=False)
                    return _error("COMMAND_ID_REUSED")

            kind = command["type"]
            state = self._derive(command["task_id"])
            if kind == "task.create":
                if state is not None:
                    return _error("TASK_ALREADY_EXISTS")
                next_version = 1
            else:
                if state is None:
                    return _error("TASK_NOT_FOUND")
                if command["expected_version"] != state["version"]:
                    return _error("VERSION_CONFLICT", current_version=state["version"])
                if kind == "task.claim":
                    if state["status"] != "todo":
                        return _error("INVALID_TRANSITION")
                else:
                    if state["status"] != "in_progress":
                        return _error("INVALID_TRANSITION")
                    if state["owner_agent_id"] != command["actor_id"]:
                        return _error("NOT_OWNER")
                next_version = state["version"] + 1

            event = {
                "command_id": command["command_id"],
                "actor_id": command["actor_id"],
                "task_id": command["task_id"],
                "version": next_version,
                "event_type": _EVENT_FROM_COMMAND[kind],
                "data": deepcopy(command["payload"]),
            }
            # Our transition checks are the only write path. Replay-valid event
            # formation is independently tested against the same invariants.
            self._events.append(event)
            return _receipt(event, applied=True)