"""
Thread context manager.

Tracks every agent response posted in a given Discord thread so that
each subsequent agent receives the full conversation history.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class ThreadContext:
    """State for one debate round (one Discord thread)."""

    # The user's original message text
    original_message: str = ""

    # Ordered list of (agent_name, response_text) tuples posted so far
    agent_responses: List[tuple[str, str]] = field(default_factory=list)

    def add_response(self, agent_name: str, text: str) -> None:
        self.agent_responses.append((agent_name, text))

    def build_thread_summary(self) -> str:
        """
        Returns a formatted string of the full thread so far, suitable for
        passing as a single user message to each agent.

        Each prior agent response is capped at 300 chars to keep context tight
        and token cost low as the thread grows.
        """
        RESPONSE_CAP = 300
        parts = [f"[User]: {self.original_message}"]
        for name, text in self.agent_responses:
            truncated = text if len(text) <= RESPONSE_CAP else text[:RESPONSE_CAP] + "…"
            parts.append(f"[{name}]: {truncated}")
        return "\n\n".join(parts)

    def is_empty(self) -> bool:
        return len(self.agent_responses) == 0


# Global registry: thread_id (int) → ThreadContext
_contexts: dict[int, ThreadContext] = {}


def get_or_create(thread_id: int, original_message: str = "") -> ThreadContext:
    if thread_id not in _contexts:
        _contexts[thread_id] = ThreadContext(original_message=original_message)
    return _contexts[thread_id]


def get(thread_id: int) -> ThreadContext | None:
    return _contexts.get(thread_id)


def clear(thread_id: int) -> None:
    _contexts.pop(thread_id, None)
