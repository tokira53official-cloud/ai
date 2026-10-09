"""
SiftNodes AI — private Discord hosting assistant
Owner: NotRyxenYT
Python: 3.10+
No external AI API keys. Uses a local Ollama model over localhost.
"""

import os
import io
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands
import aiohttp

# -------------------- CONFIG --------------------
OWNER_ID = 1520903362667876523
OWNER_NAME = "NotRyxenYT"
BOT_NAME = "SiftNodes AI"
PREFIX = "!"
DATA_DIR = Path(os.getenv("SIFTNODES_DATA_DIR", "siftnodes_data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / "config.json"
HISTORY_DIR = DATA_DIR / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

# Local Ollama server/model. No external API key is used.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "16"))
MAX_RESPONSE_CHARS = 1800
THINKING_TEXT = "🧠 SiftNodes AI is thinking..."

SYSTEM_PROMPT = f"""
You are {BOT_NAME}, a private AI assistant built for NotRyxenYT's SiftNodes hosting project.
Your owner is {OWNER_NAME}. You help with Linux, VPS hosting, Docker, Minecraft hosting,
Discord bots, Python, HTML, CSS, JavaScript, debugging, and general questions.
Reply naturally in the language the user uses, including Hindi/Hinglish.
Be helpful, honest, and clear. Do not claim you ran code, deployed a website, or created
an attachment unless you actually did. When writing code, use correct fenced code blocks.
When a user asks for a complete HTML page, provide a complete working HTML document.
You do not have internet access unless separately configured. Never reveal secrets or tokens.
Do not expose private internal reasoning; give a concise answer or summary of your approach.
"""

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("siftnodes-ai")


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {"ai_channel_id": None, "guild_id": None}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ai_channel_id": None, "guild_id": None}


def save_config(data: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


config = load_config()


def history_path(channel_id: int, user_id: int) -> Path:
    return HISTORY_DIR / f"{channel_id}_{user_id}.json"


def load_history(channel_id: int, user_id: int) -> list:
    path = history_path(channel_id, user_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_history(channel_id: int, user_id: int, messages: list) -> None:
    path = history_path(channel_id, user_id)
    path.write_text(json.dumps(messages[-MAX_HISTORY_MESSAGES:], ensure_ascii=False, indent=2), encoding="utf-8")


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


def is_owner(ctx: commands.Context) -> bool:
    return ctx.author.id == OWNER_ID


async def local_ai_reply(channel_id: int, user_id: int, prompt: str) -> str:
    history = load_history(channel_id, user_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7},
    }
    timeout = aiohttp.ClientTimeout(total=240, connect=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(OLLAMA_URL, json=payload) as response:
            if response.status != 200:
                detail = (await response.text())[:500]
                raise RuntimeError(f"Local AI returned HTTP {response.status}: {detail}")
            result = await response.json()

    answer = result.get("message", {}).get("content", "").strip()
    if not answer:
        raise RuntimeError("The local model returned an empty answer.")

    history.extend([
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": answer},
    ])
    save_history(channel_id, user_id, history)
    return answer


async def send_long_message(channel: discord.abc.Messageable, text: str) -> None:
    # Discord message limit is 2000 chars. Split on line boundaries where possible.
    remaining = text
    while remaining:
        if len(remaining) <= MAX_RESPONSE_CHARS:
            chunk, remaining = remaining, ""
        else:
            cut = remaining.rfind("\n", 0, MAX_RESPONSE_CHARS)
            if cut < 500:
                cut = MAX_RESPONSE_CHARS
            chunk, remaining = remaining[:cut], remaining[cut:].lstrip()
        await channel.send(chunk)


@bot.event
async def on_ready():
    log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id if bot.user else "?")
    log.info("Owner: %s (%s)", OWNER_NAME, OWNER_ID)
    log.info("Local model: %s | Ollama URL: %s", OLLAMA_MODEL, OLLAMA_URL)


@bot.command(name="ai")
async def ai_command(ctx: commands.Context, action: Optional[str] = None, *, value: Optional[str] = None):
    if not is_owner(ctx):
        await ctx.reply("This command is restricted to the bot owner.", mention_author=False)
        return

    action = (action or "help").lower()

    if action == "setup":
        if not value or not value.strip().isdigit():
            await ctx.reply("Usage: `!ai setup <channel-id>`", mention_author=False)
            return
        channel_id = int(value.strip())
        channel = ctx.guild.get_channel(channel_id) if ctx.guild else None
        if channel is None:
            try:
                channel = await bot.fetch_channel(channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                channel = None
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            await ctx.reply("I couldn't find an accessible text channel. Check the channel ID and my permissions.", mention_author=False)
            return
        config["ai_channel_id"] = channel.id
        config["guild_id"] = channel.guild.id
        save_config(config)
        await ctx.reply(
            f"AI chat channel set to {channel.mention}.\n"
            "Members can now chat there without a prefix. Use `!ai status` to check the setup.",
            mention_author=False,
        )
        return

    if action == "status":
        channel_id = config.get("ai_channel_id")
        channel = bot.get_channel(channel_id) if channel_id else None
        await ctx.reply(
            f"**{BOT_NAME} status**\n"
            f"Owner: `{OWNER_NAME}` (`{OWNER_ID}`)\n"
            f"AI channel: {channel.mention if channel else 'Not configured'}\n"
            f"Local model: `{OLLAMA_MODEL}`\n"
            f"Engine: `Ollama (local)`",
            mention_author=False,
        )
        return

    if action == "reset":
        channel_id = config.get("ai_channel_id")
        if channel_id:
            for file in HISTORY_DIR.glob(f"{channel_id}_*.json"):
                try:
                    file.unlink()
                except OSError:
                    log.exception("Unable to remove history file %s", file)
        await ctx.reply("Conversation history for the configured AI channel has been cleared.", mention_author=False)
        return

    await ctx.reply(
        "**SiftNodes AI commands**\n"
        "`!ai setup <channel-id>` — configure the prefix-free chat channel\n"
        "`!ai status` — show current setup\n"
        "`!ai reset` — clear chat history for that channel\n"
        "`!ai help` — show this help",
        mention_author=False,
    )


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.guild is None:
        return

    # Process commands everywhere, but the actual AI chat works only in the configured channel.
    await bot.process_commands(message)

    if message.channel.id != config.get("ai_channel_id"):
        return
    if message.content.startswith(PREFIX):
        return
    if not message.content.strip() and not message.attachments:
        return

    prompt = message.content.strip()
    if message.attachments:
        names = ", ".join(a.filename for a in message.attachments[:5])
        prompt += f"\n\n[Attached file(s): {names}. If you cannot access their contents, ask the user to paste the text.]"

    async with message.channel.typing():
        status_msg = await message.reply(THINKING_TEXT, mention_author=False)
        try:
            answer = await local_ai_reply(message.channel.id, message.author.id, prompt)
            # Replace the thinking indicator with the actual response, then send remaining parts.
            first = answer[:MAX_RESPONSE_CHARS]
            await status_msg.edit(content=first)
            if len(answer) > MAX_RESPONSE_CHARS:
                await send_long_message(message.channel, answer[MAX_RESPONSE_CHARS:].lstrip())
        except asyncio.TimeoutError:
            await status_msg.edit(content="⏳ The local AI took too long. Try again in a moment.")
        except aiohttp.ClientConnectorError:
            await status_msg.edit(
                content=(
                    "I can't reach the local AI engine. Ollama may not be running.\n"
                    "Start Ollama and download the configured model first."
                )
            )
        except Exception as exc:
            log.exception("AI reply failed")
            safe = str(exc).replace("`", "'")[:300]
            await status_msg.edit(content=f"⚠️ AI error: `{safe}`")


def main():
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "Missing Discord token. Set it first:\n"
            "export DISCORD_BOT_TOKEN='YOUR_BOT_TOKEN'\n"
            "python3 bot.py"
        )
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
