"""
Router agent.

Reads the current thread (or single message) and returns an ordered list
of agent names to invoke.  Leader is always appended last.
"""

from __future__ import annotations
import json
import anthropic
import config

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

_SYSTEM_PROMPT = """You are a routing agent for a six-agent debate system. The agents are: Thinker, Builder, Empathist, Pessimist, Wild Card. (The Leader always runs last and is never part of your routing decision.)

Given a message or thread, output a JSON array of agent names to invoke, in this order if selected: ["Thinker", "Builder", "Empathist", "Pessimist", "Wild Card"].

Routing rules:
- Thinker: invoke if the premise seems shaky, the frame seems wrong, or there is a structural gap in the reasoning
- Builder: invoke if a solution or workflow is being proposed and execution feasibility hasn't been addressed
- Empathist: invoke if people, personnel, or team dynamics are involved and the human experience hasn't been modeled
- Pessimist: invoke if a plan is forming without downside analysis, OR if any AI/prompt/agent workflow is being discussed without cost or efficiency consideration
- Wild Card: invoke if the problem seems stuck, the answer seems obvious with no alternatives considered, or a reframe would unlock progress

On continuation (full thread provided): only invoke agents who have something genuinely new to add given what has already been said. Do not re-invoke an agent whose perspective has already been fully represented.

Return ONLY a valid JSON array. No explanation. No preamble. Example: ["Thinker", "Pessimist"]"""


def route(message_or_thread: str) -> list[str]:
    """
    Returns the ordered list of agents to invoke (Leader always last).
    Falls back to all agents if the model returns unparseable output.
    """
    response = _client.messages.create(
        model=config.ROUTER_MODEL,
        max_tokens=256,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": message_or_thread}],
    )

    raw = response.content[0].text.strip()

    try:
        agents = json.loads(raw)
        if not isinstance(agents, list):
            raise ValueError("not a list")
        # Normalise names and filter to valid ones
        valid = set(config.AGENT_ORDER)
        agents = [a for a in agents if a in valid]
        # Preserve canonical order
        agents = [a for a in config.AGENT_ORDER if a in agents]
    except (json.JSONDecodeError, ValueError):
        # Fallback: invoke everyone
        agents = list(config.AGENT_ORDER)

    # Leader always runs last
    agents.append("Leader")
    return agents
