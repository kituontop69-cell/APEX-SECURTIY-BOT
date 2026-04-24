"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            A P E X   G U A R D   —   H I G H - E N D   S E C U R I T Y       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# CREATE DATA DIRECTORY BEFORE LOGGING
os.makedirs("data", exist_ok=True)

import discord
from discord.ext import commands, tasks

from config import BotConfig, Features, SecurityLevel
from utils.database import Database
from utils.security_checks import tracker


# ─── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, BotConfig.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler("data/bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("APEX GUARD")

# ─── Bot Intents ───────────────────────────────────────────────────────────────
intents = discord.Intents.all()
intents.presences = True
intents.members = True
intents.message_content = True
intents.guilds = True

# ─── Bot Class ─────────────────────────────────────────────────────────────────
class ApexGuard(commands.Bot):
    """High-end security bot with enterprise-grade protection."""

    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(BotConfig.PREFIX),
            intents=intents,
            case_insensitive=True,
            owner_ids=set(BotConfig.OWNER_IDS),
            help_command=None,
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for threats · !guard help"
            )
        )
        self.start_time = datetime.utcnow()
        self.db = Database()
        self.security_level = SecurityLevel.NORMAL
        self._lockdown = False
        self._raid_mode = False

    async def setup_hook(self):
        await self.db.init()
        logger.info("Database initialized.")

        cogs = [
            "cogs.automod",
            "cogs.moderation",
            "cogs.verification",
            "cogs.lockdown",
            "cogs.logging",
            "cogs.backup",
            "cogs.owner",
            "cogs.antinuke",
            "cogs.phone_tracker"
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load {cog}: {e}")

        self.purge_old_messages.start()
        self.presence_monitor.start()

    async def on_ready(self):
        logger.info(f"APEX GUARD online as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        logger.info(f"Watching {sum(g.member_count for g in self.guilds)} members")

    async def on_guild_join(self, guild: discord.Guild):
        logger.info(f"Joined guild: {guild.name} ({guild.id})")
        await self.db.set_guild_setting(guild.id, "security_level", SecurityLevel.NORMAL)

    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.NotOwner):
            await ctx.reply("🔒 **Owner only.**", delete_after=5)
        elif isinstance(error, commands.MissingPermissions):
            await ctx.reply(f"🔒 You need: `{', '.join(error.missing_permissions)}`", delete_after=5)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"⏳ Cooldown: `{error.retry_after:.1f}s`", delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"❓ Missing argument: `{error.param.name}`", delete_after=5)
        else:
            logger.error(f"Command error in {ctx.command}: {error}")
            await ctx.reply("⚠️ An error occurred. It has been logged.", delete_after=5)

    @tasks.loop(hours=6)
    async def purge_old_messages(self):
        await self.db.purge_old_messages(hours=24)
        logger.debug("Purged old message cache.")

    @tasks.loop(minutes=1)
    async def presence_monitor(self):
        pass

    async def is_owner(self, user: discord.abc.User) -> bool:
        """Override discord.py's default owner check to use our custom owner_ids set."""
        return user.id in self.owner_ids

    async def close(self):
        logger.info("Shutting down APEX GUARD...")
        await super().close()
```


# ─── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot = ApexGuard()
    try:
        bot.run(BotConfig.TOKEN, reconnect=True)
    except discord.LoginFailure:
        logger.critical("Invalid Discord token. Set DISCORD_BOT_TOKEN environment variable.")
        sys.exit(1)
