import os
from dotenv import load_dotenv

load_dotenv()

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Discord tokens — one per registered bot application
DISCORD_TOKEN_THINKER   = os.getenv("DISCORD_TOKEN_THINKER")
DISCORD_TOKEN_BUILDER   = os.getenv("DISCORD_TOKEN_BUILDER")
DISCORD_TOKEN_EMPATHIST = os.getenv("DISCORD_TOKEN_EMPATHIST")
DISCORD_TOKEN_PESSIMIST = os.getenv("DISCORD_TOKEN_PESSIMIST")
DISCORD_TOKEN_WILDCARD  = os.getenv("DISCORD_TOKEN_WILDCARD")
DISCORD_TOKEN_LEADER    = os.getenv("DISCORD_TOKEN_LEADER")

# Target channel where agents operate
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", "0"))

# Models
ROUTER_MODEL = "claude-haiku-4-5-20251001"   # cheap classification
AGENT_MODEL  = "claude-sonnet-4-6"           # reasoning & synthesis

# Ordered agent roster (Leader always appended last by router)
AGENT_ORDER = ["Thinker", "Builder", "Empathist", "Pessimist", "Wild Card"]
