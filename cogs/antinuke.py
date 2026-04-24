"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     APEX GUARD — ANTI-NUKE & DEADLY SHIELD                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
Prevents mass destruction: channel/role deletion, webhook spam, mass role
assignment, unauthorized bot additions, voice lockdown, and DM raid floods.
"""

import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from collections import defaultdict, deque

from config import Features, AntiNukeLimits, WHITELISTED_IDS
from utils.punishments import PunishmentExecutor


# ─── In-memory burst trackers ──────────────────────────────────────────────────
class BurstTracker:
    """Track rapid destructive actions per guild/per user."""

    def __init__(self, window: int):
        self.window = window
        self._data: dict = defaultdict(lambda: deque())

    def add(self, guild_id: int, user_id: int):
        now = datetime.utcnow()
        key = (guild_id, user_id)
        self._data[key].append(now)
        # trim old
        cutoff = now - timedelta(seconds=self.window)
        while self._data[key] and self._data[key][0] < cutoff:
            self._data[key].popleft()

    def count(self, guild_id: int, user_id: int) -> int:
        key = (guild_id, user_id)
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window)
        while self._data[key] and self._data[key][0] < cutoff:
            self._data[key].popleft()
        return len(self._data[key])

    def reset(self, guild_id: int, user_id: int):
        self._data[(guild_id, user_id)].clear()


channel_del_tracker = BurstTracker(AntiNukeLimits.CHANNEL_DELETE_WINDOW)
role_del_tracker = BurstTracker(AntiNukeLimits.ROLE_DELETE_WINDOW)
webhook_tracker = BurstTracker(AntiNukeLimits.WEBHOOK_CREATE_WINDOW)
role_assign_tracker = BurstTracker(AntiNukeLimits.ROLE_ASSIGN_WINDOW)


class AntiNuke(commands.Cog):
    """Zero-tolerance protection against server destruction and covert raids."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── Helpers ───────────────────────────────────────────────────────────────
    async def _punish(self, guild: discord.Guild, member: discord.Member, reason: str):
        """Execute anti-nuke punishment based on config."""
        if member.id in WHITELISTED_IDS or member.id == guild.owner_id:
            return
        if AntiNukeLimits.PUNISHMENT == "ban":
            await PunishmentExecutor.instaban(guild, member, reason)
        elif AntiNukeLimits.PUNISHMENT == "kick":
            await PunishmentExecutor.kick(guild, member, reason)
        elif AntiNukeLimits.PUNISHMENT == "strip":
            # Strip all roles except @everyone
            try:
                await member.edit(roles=[], reason=f"APEX GUARD strip: {reason}")
            except discord.Forbidden:
                pass
        await self._alert(guild, f"☠️ ANTI-NUKE TRIGGERED", member, reason)

    async def _alert(self, guild: discord.Guild, title: str, member: discord.Member, details: str):
        """Send alert to system channel or first available text channel."""
        target = guild.system_channel
        if not target or not target.permissions_for(guild.me).send_messages:
            target = discord.utils.find(
                lambda c: isinstance(c, discord.TextChannel) and c.permissions_for(guild.me).send_messages,
                guild.text_channels
            )
        if target:
            embed = discord.Embed(title=title, color=0x000000, timestamp=datetime.utcnow())
            embed.add_field(name="Target", value=f"{member.mention} (`{member.id}`)", inline=False)
            embed.add_field(name="Reason", value=details, inline=False)
            embed.set_footer(text="APEX GUARD Anti-Nuke")
            await target.send(embed=embed)

    # ─── Anti Channel Delete ───────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not Features.ANTI_NUKE:
            return
        guild = channel.guild
        await asyncio.sleep(0.5)

        async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                actor = entry.user
                if actor.bot or actor.id in WHITELISTED_IDS or actor.id == guild.owner_id:
                    return
                channel_del_tracker.add(guild.id, actor.id)
                if channel_del_tracker.count(guild.id, actor.id) >= AntiNukeLimits.CHANNEL_DELETE_LIMIT:
                    await self._punish(guild, actor, f"Mass channel deletion ({channel_del_tracker.count(guild.id, actor.id)} channels)")
                break

    # ─── Anti Role Delete ──────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        if not Features.ANTI_NUKE:
            return
        guild = role.guild
        await asyncio.sleep(0.5)

        async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.role_delete):
            if entry.target.id == role.id:
                actor = entry.user
                if actor.bot or actor.id in WHITELISTED_IDS or actor.id == guild.owner_id:
                    return
                role_del_tracker.add(guild.id, actor.id)
                if role_del_tracker.count(guild.id, actor.id) >= AntiNukeLimits.ROLE_DELETE_LIMIT:
                    await self._punish(guild, actor, f"Mass role deletion ({role_del_tracker.count(guild.id, actor.id)} roles)")
                break

    # ─── Webhook Protection ────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        if not Features.WEBHOOK_PROTECTION:
            return
        guild = channel.guild
        await asyncio.sleep(0.5)

        async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.webhook_create):
            actor = entry.user
            if actor.bot or actor.id in WHITELISTED_IDS or actor.id == guild.owner_id:
                return
            webhook_tracker.add(guild.id, actor.id)
            if webhook_tracker.count(guild.id, actor.id) >= AntiNukeLimits.WEBHOOK_CREATE_LIMIT:
                await self._punish(guild, actor, f"Unauthorized webhook creation ({webhook_tracker.count(guild.id, actor.id)} webhooks)")
            break

    # ─── Anti Mass Role Assignment ─────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not Features.ANTI_MASS_ROLE:
            return
        if before.roles == after.roles:
            return
        guild = after.guild
        added = set(after.roles) - set(before.roles)
        if not added:
            return
        await asyncio.sleep(0.5)

        async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                actor = entry.user
                if actor.bot or actor.id in WHITELISTED_IDS or actor.id == guild.owner_id:
                    return
                role_assign_tracker.add(guild.id, actor.id)
                if role_assign_tracker.count(guild.id, actor.id) >= AntiNukeLimits.ROLE_ASSIGN_LIMIT:
                    await self._punish(guild, actor, f"Mass role assignment ({role_assign_tracker.count(guild.id, actor.id)} actions)")
                break

    # ─── Anti Bot Add ──────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not Features.ANTI_BOT_ADD:
            return
        if not member.bot:
            return
        guild = member.guild
        await asyncio.sleep(0.5)

        async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.bot_add):
            if entry.target.id == member.id:
                actor = entry.user
                if actor.id in WHITELISTED_IDS or actor.id == guild.owner_id:
                    return
                # Immediately remove unauthorized bot and punish adder
                try:
                    await member.kick(reason="APEX GUARD: Unauthorized bot addition")
                except discord.Forbidden:
                    pass
                await PunishmentExecutor.ban(guild, actor, "Added unauthorized bot to server")
                await self._alert(guild, "🤖 Unauthorized Bot Removed", actor, f"Bot `{member}` was kicked and adder banned.")
                break

    # ─── Voice Channel Lockdown ────────────────────────────────────────────────
    @commands.command(name="voicelock")
    @commands.has_permissions(administrator=True)
    async def voice_lock_cmd(self, ctx: commands.Context, channel: discord.VoiceChannel = None):
        """Disconnect all members from a voice channel and lock it."""
        targets = [channel] if channel else ctx.guild.voice_channels
        for vc in targets:
            for member in vc.members:
                try:
                    await member.move_to(None, reason="APEX GUARD voice lockdown")
                except discord.Forbidden:
                    pass
            overwrite = vc.overwrites_for(ctx.guild.default_role)
            overwrite.connect = False
            overwrite.speak = False
            try:
                await vc.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason="Voice lockdown")
            except discord.Forbidden:
                continue
        await ctx.send("🔇 **Voice channels locked.** All users disconnected.")

    @commands.command(name="voiceunlock")
    @commands.has_permissions(administrator=True)
    async def voice_unlock_cmd(self, ctx: commands.Context, channel: discord.VoiceChannel = None):
        """Restore voice channel permissions."""
        targets = [channel] if channel else ctx.guild.voice_channels
        for vc in targets:
            overwrite = vc.overwrites_for(ctx.guild.default_role)
            overwrite.connect = None
            overwrite.speak = None
            try:
                await vc.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason="Voice lockdown lifted")
            except discord.Forbidden:
                continue
        await ctx.send("🔊 **Voice channels unlocked.**")

    # ─── DM Raid Shield ────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not Features.DM_RAID_SHIELD:
            return
        if message.guild is not None:
            return  # only DMs
        if message.author.bot:
            return
        # Simple heuristic: if user sends >5 DMs in 30s, ignore/block
        # Track globally (since DMs have no guild)
        key = message.author.id
        now = datetime.utcnow()
        if not hasattr(self.bot, "_dm_tracker"):
            self.bot._dm_tracker = defaultdict(lambda: deque())
        self.bot._dm_tracker[key].append(now)
        cutoff = now - timedelta(seconds=30)
        while self.bot._dm_tracker[key] and self.bot._dm_tracker[key][0] < cutoff:
            self.bot._dm_tracker[key].popleft()
        if len(self.bot._dm_tracker[key]) > 5:
            # Stop responding to DM spam
            return
        # Optional: reply with warning once
        if len(self.bot._dm_tracker[key]) == 5:
            try:
                await message.author.send("⚠️ APEX GUARD: Excessive DMs detected. Further messages ignored.")
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiNuke(bot))
