"""
Shared agent logic.

Each agent subclass only needs to define NAME, COLOR, and SYSTEM_PROMPT.
The respond() method handles the Anthropic API call and returns the text.
"""

from __future__ import annotations
import anthropic
import config

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


class BaseAgent:
    NAME: str = "Agent"
    COLOR: str = ""           # e.g. "Blue"
    DISPLAY_NAME: str = ""    # e.g. "Blue — Thinker"  (used in Discord + context)
    SYSTEM_PROMPT: str = ""

    def respond(self, thread_so_far: str) -> str:
        """
        Call the Anthropic API with the full thread so far as the user turn.
        Returns the agent's response text.
        """
        prompt = (
            thread_so_far
            + "\n\n---\nRespond in 3–5 sentences maximum. Be direct. No preamble."
        )
        response = _client.messages.create(
            model=config.AGENT_MODEL,
            max_tokens=350,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
