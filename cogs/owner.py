"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     APEX GUARD — OWNER / DEV COMMANDS                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
Bot administration, security level control, and diagnostics.
"""

import discord
from discord.ext import commands
from datetime import datetime

from config import BotConfig, SecurityLevel
from utils.database import Database


db = Database()


class Owner(commands.Cog):
    """Owner-only commands for bot control and diagnostics."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="guard")
    async def guard_cmd(self, ctx: commands.Context):
        """Display APEX GUARD status and security level."""
        embed = discord.Embed(
            title="🛡️ APEX GUARD Status",
            color=0xe74c3c,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Security Level", value=self._level_name(self.bot.security_level), inline=True)
        embed.add_field(name="Raid Mode", value="🚨 ACTIVE" if getattr(self.bot, "_raid_mode", False) else "✅ Inactive", inline=True)
        embed.add_field(name="Guilds", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Members", value=sum(g.member_count for g in self.bot.guilds), inline=True)
        embed.add_field(name="Latency", value=f"{self.bot.latency*1000:.1f}ms", inline=True)
        embed.add_field(name="Prefix", value=f"`{BotConfig.PREFIX}`", inline=True)
        embed.set_footer(text="APEX GUARD High-End Security Bot")
        await ctx.send(embed=embed)

    @commands.command(name="security")
    @commands.is_owner()
    async def security_cmd(self, ctx: commands.Context, level: int):
        """Set global security level (0-4)."""
        if not 0 <= level <= 4:
            return await ctx.reply("Level must be 0-4.", delete_after=5)
        self.bot.security_level = level
        await ctx.send(f"🔒 Security level set to **{self._level_name(level)}**.")

    @commands.command(name="blacklist")
    @commands.is_owner()
    async def blacklist_cmd(self, ctx: commands.Context, user_id: int):
        """Globally blacklist a user ID."""
        if not hasattr(self.bot, "blacklisted_ids"):
            self.bot.blacklisted_ids = set()
        self.bot.blacklisted_ids.add(user_id)
        await ctx.send(f"⛔ User `{user_id}` added to global blacklist.")

    @commands.command(name="whitelist")
    @commands.is_owner()
    async def whitelist_cmd(self, ctx: commands.Context, user_id: int):
        """Globally whitelist a user ID (immune to auto-mod)."""
        from config import WHITELISTED_IDS
        WHITELISTED_IDS.add(user_id)
        await ctx.send(f"✅ User `{user_id}` whitelisted globally.")

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cmd(self, ctx: commands.Context, cog: str):
        """Reload a cog module."""
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await ctx.send(f"🔄 Reloaded `cogs.{cog}`")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}", delete_after=5)

    @commands.command(name="load")
    @commands.is_owner()
    async def load_cmd(self, ctx: commands.Context, cog: str):
        try:
            await self.bot.load_extension(f"cogs.{cog}")
            await ctx.send(f"📥 Loaded `cogs.{cog}`")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}", delete_after=5)

    @commands.command(name="unload")
    @commands.is_owner()
    async def unload_cmd(self, ctx: commands.Context, cog: str):
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
            await ctx.send(f"📤 Unloaded `cogs.{cog}`")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}", delete_after=5)

    @commands.command(name="addowner")
    @commands.is_owner()
    async def addowner_cmd(self, ctx: commands.Context, user_id: int):
        """Dynamically add another bot owner without restarting."""
        if user_id not in self.bot.owner_ids:
            self.bot.owner_ids.add(user_id)
            await ctx.send(f"✅ User `{user_id}` added as owner.")
        else:
            await ctx.reply("User is already an owner.", delete_after=5)

    @commands.command(name="removeowner")
    @commands.is_owner()
    async def removeowner_cmd(self, ctx: commands.Context, user_id: int):
        """Dynamically remove a bot owner without restarting."""
        if user_id in self.bot.owner_ids:
            self.bot.owner_ids.remove(user_id)
            await ctx.send(f"✅ User `{user_id}` removed from owners.")
        else:
            await ctx.reply("User is not an owner.", delete_after=5)

    @commands.command(name="owners")
    async def owners_cmd(self, ctx: commands.Context):
        """List all active bot owners."""
        lines = []
        for uid in sorted(self.bot.owner_ids):
            user = self.bot.get_user(uid)
            lines.append(f"• `{uid}` — {f'{user} `{user.name}`' if user else 'Unknown User'}")
        embed = discord.Embed(title="🔒 Bot Owners", color=0x3498db, description="\n".join(lines))
        await ctx.send(embed=embed)

    @commands.command(name="shutdown")
    @commands.is_owner()
    async def shutdown_cmd(self, ctx: commands.Context):
        await ctx.send("🔌 Shutting down APEX GUARD...")
        await self.bot.close()

    @staticmethod
    def _level_name(level: int) -> str:
        names = {
            SecurityLevel.NORMAL: "NORMAL 🟢",
            SecurityLevel.ELEVATED: "ELEVATED 🟡",
            SecurityLevel.HIGH: "HIGH 🟠",
            SecurityLevel.CRITICAL: "CRITICAL 🔴",
            SecurityLevel.DEADLY: "DEADLY ☠️"
        }
        return names.get(level, "UNKNOWN")


async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
