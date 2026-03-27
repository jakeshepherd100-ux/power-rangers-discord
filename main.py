"""
Power Rangers Multi-Agent Discord Bot
Entry point — launches all six bots in a single asyncio process.

Architecture
============
- The Leader bot is the primary listener.  When a message lands in the
  target channel it orchestrates the full round: router → selected agents
  → Leader synthesis.
- The other five bots are "silent" Discord clients that exist purely to
  post under their own username/avatar.
- All orchestration logic lives here (not in individual bot clients).

Discord setup checklist (do before running):
1. Create six applications in the Developer Portal.
2. For each: create a bot, copy the token, enable MESSAGE CONTENT INTENT.
3. Invite all six bots with: Send Messages, Read Message History,
   Create Public Threads, Send Messages in Threads.
4. Create a #war-room (or similar) channel and copy its ID to .env.
"""

from __future__ import annotations
import asyncio
import discord
import context as ctx
import config
import router as router_module
from agents.thinker   import Thinker
from agents.builder   import Builder
from agents.empathist import Empathist
from agents.pessimist import Pessimist
from agents.wildcard  import WildCard
from agents.leader    import Leader
from agents.alpha     import Alpha

# ── agent instances ──────────────────────────────────────────────────────────

AGENTS = {
    "Thinker":   Thinker(),
    "Builder":   Builder(),
    "Empathist": Empathist(),
    "Pessimist": Pessimist(),
    "Wild Card": WildCard(),
    "Leader":    Leader(),
    "Alpha":     Alpha(),
}

# ── Discord client per bot ────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True

thinker_bot   = discord.Client(intents=intents)
builder_bot   = discord.Client(intents=intents)
empathist_bot = discord.Client(intents=intents)
pessimist_bot = discord.Client(intents=intents)
wildcard_bot  = discord.Client(intents=intents)
leader_bot    = discord.Client(intents=intents)   # primary listener
alpha_bot     = discord.Client(intents=intents)

BOT_MAP: dict[str, discord.Client] = {
    "Thinker":   thinker_bot,
    "Builder":   builder_bot,
    "Empathist": empathist_bot,
    "Pessimist": pessimist_bot,
    "Wild Card": wildcard_bot,
    "Leader":    leader_bot,
    "Alpha":     alpha_bot,
}

# ── helpers ───────────────────────────────────────────────────────────────────

async def post_as(agent_name: str, thread_id: int, text: str) -> None:
    """Send text in a thread using the bot assigned to agent_name.

    Each bot fetches the thread from its own client so the message appears
    under the correct username. Prepends a bold Color — Persona header.
    """
    agent = AGENTS[agent_name]
    header = f"**{agent.DISPLAY_NAME}**\n"
    full_text = header + text

    # Split if message exceeds Discord's 2000-char limit
    chunks = [full_text[i:i+1900] for i in range(0, len(full_text), 1900)]
    bot = BOT_MAP[agent_name]

    # Must fetch from this bot's own connection — not the Leader's thread object
    channel = bot.get_channel(thread_id)
    if channel is None:
        channel = await bot.fetch_channel(thread_id)

    for chunk in chunks:
        await channel.send(chunk)
        await asyncio.sleep(0.5)


async def run_alpha(thread_id: int, thread_ctx: ctx.ThreadContext, user_instruction: str) -> None:
    """
    Run Alpha alone — skip all Rangers. Alpha reads the full thread and
    executes the user's specific instruction.
    """
    agent = AGENTS["Alpha"]
    thread_summary = thread_ctx.build_thread_summary()

    response_text = await asyncio.get_event_loop().run_in_executor(
        None, agent.respond, thread_summary, user_instruction
    )

    thread_ctx.add_response(agent.DISPLAY_NAME, response_text)
    await post_as("Alpha", thread_id, response_text)


async def run_round(
    thread_id: int,
    thread_ctx: ctx.ThreadContext,
    agent_names: list[str],
) -> None:
    """
    Fire each agent in order, post their response, update context, then move on.
    Leader is always last in agent_names.
    """
    for name in agent_names:
        agent = AGENTS[name]
        thread_summary = thread_ctx.build_thread_summary()

        # Run the (blocking) Anthropic call in a thread pool
        response_text = await asyncio.get_event_loop().run_in_executor(
            None, agent.respond, thread_summary
        )

        thread_ctx.add_response(agent.DISPLAY_NAME, response_text)
        await post_as(name, thread_id, response_text)

        # Pace the conversation — feels more natural, avoids Discord rate limits
        await asyncio.sleep(1)


# ── Leader bot: primary listener ──────────────────────────────────────────────

@leader_bot.event
async def on_ready() -> None:
    print(f"[Leader] logged in as {leader_bot.user}")


@leader_bot.event
async def on_message(message: discord.Message) -> None:
    # Ignore messages from any of our own bots
    bot_ids = {b.user.id for b in BOT_MAP.values() if b.user}
    if message.author.id in bot_ids:
        return

    # Only act in the configured channel (or threads that belong to it)
    if isinstance(message.channel, discord.Thread):
        if message.channel.parent_id != config.TARGET_CHANNEL_ID:
            return
    elif message.channel.id != config.TARGET_CHANNEL_ID:
        return

    # ── Determine whether this is a new round or a continuation ──────────────

    is_thread = isinstance(message.channel, discord.Thread)
    thread_id = message.channel.id if is_thread else message.id

    if is_thread:
        # Continuation: user replied inside an existing thread
        thread = message.channel
        thread_ctx = ctx.get(thread_id)
        if thread_ctx is None:
            # Orphaned thread — start fresh
            thread_ctx = ctx.get_or_create(thread_id, message.content)
        else:
            # Update with the new user message so agents see it
            thread_ctx.add_response("User", message.content)
    else:
        # New round: create a thread from the user's message
        thread = await message.create_thread(
            name=message.content[:80] or "War Room",
            auto_archive_duration=1440,
        )
        thread_ctx = ctx.get_or_create(thread.id, message.content)

    # ── Check for @Alpha mention — bypasses Rangers entirely ──────────────────

    alpha_mentioned = (
        alpha_bot.user is not None
        and any(u.id == alpha_bot.user.id for u in message.mentions)
    )

    if alpha_mentioned:
        await run_alpha(thread.id, thread_ctx, message.content)
        return

    # ── Route to Rangers ──────────────────────────────────────────────────────

    full_thread = thread_ctx.build_thread_summary()
    agent_names = await asyncio.get_event_loop().run_in_executor(
        None, router_module.route, full_thread
    )

    # ── Run the round ─────────────────────────────────────────────────────────

    await run_round(thread.id, thread_ctx, agent_names)


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    await asyncio.gather(
        thinker_bot.start(config.DISCORD_TOKEN_THINKER),
        builder_bot.start(config.DISCORD_TOKEN_BUILDER),
        empathist_bot.start(config.DISCORD_TOKEN_EMPATHIST),
        pessimist_bot.start(config.DISCORD_TOKEN_PESSIMIST),
        wildcard_bot.start(config.DISCORD_TOKEN_WILDCARD),
        leader_bot.start(config.DISCORD_TOKEN_LEADER),
        alpha_bot.start(config.DISCORD_TOKEN_ALPHA),
    )


if __name__ == "__main__":
    asyncio.run(main())
