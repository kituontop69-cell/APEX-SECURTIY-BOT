"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     APEX GUARD — MODERATION COMMANDS                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
Professional moderation toolkit with case tracking and advanced logging.
"""

import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta

from config import BotConfig
from utils.database import Database
from utils.punishments import PunishmentExecutor


db = Database()


class Moderation(commands.Cog):
    """High-end moderation commands for security staff."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── Utilities ─────────────────────────────────────────────────────────────
    def _mod_check(self, ctx: commands.Context, target: discord.Member) -> bool:
        if target.id == ctx.guild.owner_id:
            return False
        if target.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return False
        return True

    # ─── Warn ──────────────────────────────────────────────────────────────────
    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason"):
        if not self._mod_check(ctx, member):
            return await ctx.reply("🔒 You cannot moderate this user.", delete_after=5)
        case_id = await PunishmentExecutor.warn(ctx.guild, member, reason, ctx.author)
        embed = discord.Embed(title="⚠️ Warn Issued", color=0xFFA500, timestamp=datetime.utcnow())
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
        embed.set_footer(text=f"Moderator: {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ─── Mute ──────────────────────────────────────────────────────────────────
    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute_cmd(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason"):
        """Duration format: 10m, 2h, 1d"""
        if not self._mod_check(ctx, member):
            return await ctx.reply("🔒 You cannot moderate this user.", delete_after=5)
        seconds = self._parse_duration(duration)
        if seconds <= 0:
            return await ctx.reply("❌ Invalid duration. Use `10m`, `2h`, `1d`.", delete_after=5)
        case_id = await PunishmentExecutor.mute(ctx.guild, member, seconds, reason, ctx.author)
        embed = discord.Embed(title="🔇 User Muted", color=0xFF4500, timestamp=datetime.utcnow())
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Duration", value=duration, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
        await ctx.send(embed=embed)

    # ─── Unmute ────────────────────────────────────────────────────────────────
    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Manual unmute"):
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if mute_role and mute_role in member.roles:
            await member.remove_roles(mute_role, reason=reason)
            await ctx.send(f"🔊 {member.mention} has been unmuted.")
        else:
            await ctx.reply("User is not muted.", delete_after=5)

    # ─── Kick ──────────────────────────────────────────────────────────────────
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason"):
        if not self._mod_check(ctx, member):
            return await ctx.reply("🔒 You cannot moderate this user.", delete_after=5)
        case_id = await PunishmentExecutor.kick(ctx.guild, member, reason, ctx.author)
        embed = discord.Embed(title="👢 User Kicked", color=0xFF0000, timestamp=datetime.utcnow())
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
        await ctx.send(embed=embed)

    # ─── Ban ───────────────────────────────────────────────────────────────────
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason"):
        if not self._mod_check(ctx, member):
            return await ctx.reply("🔒 You cannot moderate this user.", delete_after=5)
        case_id = await PunishmentExecutor.ban(ctx.guild, member, reason, ctx.author)
        embed = discord.Embed(title="🔨 User Banned", color=0x8B0000, timestamp=datetime.utcnow())
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
        await ctx.send(embed=embed)

    # ─── Softban ───────────────────────────────────────────────────────────────
    @commands.command(name="softban")
    @commands.has_permissions(ban_members=True)
    async def softban_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason"):
        if not self._mod_check(ctx, member):
            return await ctx.reply("🔒 You cannot moderate this user.", delete_after=5)
        case_id = await PunishmentExecutor.softban(ctx.guild, member, reason, ctx.author)
        embed = discord.Embed(title="🔨 User Softbanned", color=0x8B0000, timestamp=datetime.utcnow())
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
        embed.set_footer(text="Messages deleted (1 day)")
        await ctx.send(embed=embed)

    # ─── Instaban ──────────────────────────────────────────────────────────────
    @commands.command(name="instaban")
    @commands.has_permissions(administrator=True)
    async def instaban_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Zero tolerance"):
        case_id = await PunishmentExecutor.instaban(ctx.guild, member, reason)
        embed = discord.Embed(title="☠️ INSTABAN EXECUTED", color=0x000000, timestamp=datetime.utcnow())
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
        await ctx.send(embed=embed)

    # ─── Cases ─────────────────────────────────────────────────────────────────
    @commands.command(name="cases")
    @commands.has_permissions(manage_messages=True)
    async def cases_cmd(self, ctx: commands.Context, member: discord.Member):
        cases = await db.get_cases(ctx.guild.id, member.id)
        if not cases:
            return await ctx.reply("No cases found for this user.", delete_after=5)
        embed = discord.Embed(title=f"📁 Case History: {member}", color=0x3498db)
        for case in cases[:10]:
            ts = datetime.fromtimestamp(case["timestamp"]).strftime("%Y-%m-%d %H:%M")
            embed.add_field(
                name=f"Case #{case['case_id']} — {case['action'].upper()} ({ts})",
                value=f"Reason: {case['reason']}",
                inline=False
            )
        await ctx.send(embed=embed)

    # ─── Purge ─────────────────────────────────────────────────────────────────
    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge_cmd(self, ctx: commands.Context, limit: int = 10, member: discord.Member = None):
        if limit > 500:
            return await ctx.reply("Max purge limit is 500.", delete_after=5)
        def check(m):
            return m.author == member if member else True
        deleted = await ctx.channel.purge(limit=limit, check=check)
        await ctx.send(f"🗑️ Purged {len(deleted)} messages.", delete_after=5)

    # ─── Slowmode ──────────────────────────────────────────────────────────────
    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode_cmd(self, ctx: commands.Context, seconds: int = 0):
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"⏱️ Slowmode set to `{seconds}s`.")

    # ─── Helper ────────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_duration(duration: str) -> int:
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        if duration[-1].lower() in units:
            try:
                return int(duration[:-1]) * units[duration[-1].lower()]
            except ValueError:
                return 0
        try:
            return int(duration)
        except ValueError:
            return 0


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
