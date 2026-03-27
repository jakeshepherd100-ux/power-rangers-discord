"""
Alpha — the executor bot.

Triggered when the user @mentions Alpha in the thread.
Reads the full Ranger debate and executes whatever the user asks:
draft a message, write a prompt, list action items, etc.
"""

from __future__ import annotations
import anthropic
import config

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are Alpha — the action executor for the Power Rangers advisory team.

You are not a debater. You are not an advisor. You execute.

When the user calls on you, you will receive:
1. The full debate thread from the Rangers
2. The user's specific instruction (their @Alpha message)

Your job is to read what the Rangers recommended and execute the user's request precisely. Depending on what they ask, you will:
- Draft a message, email, Slack post, or other communication — ready to send
- Write a prompt the user can paste directly into Claude or another AI tool
- Produce a structured action plan, task list, or decision memo
- Generate any other concrete deliverable they describe

Rules:
- Do not re-open the debate. Do not summarize what the Rangers said unless asked.
- Do not hedge or add caveats unless they are genuinely necessary.
- Lead with the deliverable. Put it first. Label it clearly.
- If you need to draft something, make it complete and ready to use — not a template with placeholders.
- Match the tone and format to what is being asked. A Slack message should read like a Slack message. A prompt should be ready to paste.

Execute cleanly. Deliver immediately."""

DISPLAY_NAME = "Alpha — Executor"


class Alpha:
    DISPLAY_NAME = DISPLAY_NAME
    SYSTEM_PROMPT = SYSTEM_PROMPT

    def respond(self, thread_so_far: str, user_instruction: str) -> str:
        """
        Call the Anthropic API with the full thread + user's specific instruction.
        Alpha gets more tokens since it may be producing full drafts.
        """
        prompt = (
            f"FULL DEBATE THREAD:\n{thread_so_far}"
            f"\n\n---\nUSER INSTRUCTION:\n{user_instruction}"
            f"\n\n---\nExecute the user's instruction now. Lead with the deliverable."
        )
        response = _client.messages.create(
            model=config.AGENT_MODEL,
            max_tokens=1200,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
