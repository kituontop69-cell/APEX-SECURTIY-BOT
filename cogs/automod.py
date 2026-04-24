"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     APEX GUARD — AUTOMOD COG                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
Real-time threat detection and auto-moderation engine.
"""

import asyncio
import discord
from discord.ext import commands
from datetime import datetime

from config import BotConfig, Features, Limits, SecurityLevel, WHITELISTED_IDS
from utils.database import Database
from utils.security_checks import (
    tracker, contains_invite, contains_blacklisted, caps_flood,
    emoji_flood, mass_mention, has_token_leak, is_suspicious_url,
    check_alt_account, scan_attachment
)
from utils.punishments import PunishmentExecutor


db = Database()


class AutoMod(commands.Cog):
    """Deadly auto-moderation with zero-tolerance capabilities."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── On Member Join ────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        if member.id in WHITELISTED_IDS:
            return

        guild = member.guild
        tracker.add_join(guild.id)

        # Anti-Raid detection
        if Features.ANTI_RAID and tracker.is_raid(guild.id, BotConfig.RAID_JOIN_THRESHOLD, BotConfig.RAID_DETECTION_WINDOW):
            await self._trigger_raid_lockdown(guild, member)
            return

        # Alt detection
        if Features.ALT_DETECTION:
            is_alt, reason = await check_alt_account(member)
            if is_alt:
                threat_level = 55 if "spammer" not in reason else 95
                await PunishmentExecutor.auto_punish(guild, member, threat_level, f"Alt detected: {reason}")
                await self._log_event(guild, "🛡️ Alt Account Blocked", member, reason)
                return

        # Blacklist check
        if member.id in getattr(self.bot, "blacklisted_ids", set()):
            await PunishmentExecutor.instaban(guild, member, "Global blacklist")
            return

    # ─── On Message ────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.author.id in WHITELISTED_IDS:
            return
        if message.author.guild_permissions.administrator:
            return

        author = message.author
        guild = message.guild
        content = message.content
        threat_score = 0
        reasons = []

        # 1. Token leak detection (DEADLY)
        if Features.TOKEN_LEAK_DETECTION and has_token_leak(content):
            threat_score = 100
            reasons.append("Discord token leak detected")
            await message.delete()
            await PunishmentExecutor.instaban(guild, author, "Posted bot token — critical security breach")
            await self._log_event(guild, "☠️ TOKEN LEAK — INSTABAN", author, content)
            return

        # 2. Blacklisted words / phishing
        if Features.ANTI_PHISHING and contains_blacklisted(content):
            threat_score += 50
            reasons.append("Phishing keyword")

        # 3. Suspicious invites
        if contains_invite(content):
            threat_score += 35
            reasons.append("Unauthorized invite link")

        # 4. Suspicious URLs
        if is_suspicious_url(content):
            threat_score += 30
            reasons.append("URL shortener / suspicious link")

        # 5. Mass mention
        if Features.ANTI_MASS_MENTION and mass_mention(content):
            threat_score += 40
            reasons.append("Mass mention (@everyone/@here)")

        # 6. Caps flood
        if Features.ANTI_CAPITALS_FLOOD and caps_flood(content):
            threat_score += 15
            reasons.append("Caps flood")

        # 7. Emoji flood
        if Features.ANTI_EMOJI_FLOOD and emoji_flood(content):
            threat_score += 15
            reasons.append("Emoji flood")

        # 8. Spam tracking
        if Features.ANTI_SPAM:
            tracker.add_message(author.id, content, guild.id)
            if tracker.is_spam(author.id, BotConfig.SPAM_MESSAGE_THRESHOLD, BotConfig.SPAM_WINDOW):
                threat_score += 45
                reasons.append("Message spam")
            if tracker.repeated_spam(author.id, Limits.REPEATED_MESSAGE_LIMIT):
                threat_score += 30
                reasons.append("Repeated content spam")

        # 9. File scan
        if Features.FILE_SCAN and message.attachments:
            for att in message.attachments:
                bad, reason_file = await scan_attachment(att.filename, att.content_type or "", att.url)
                if bad:
                    threat_score = max(threat_score, 80)
                    reasons.append(f"Dangerous file: {reason_file}")

        # ─── Execute Action ────────────────────────────────────────────────────
        if threat_score >= 100:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            await PunishmentExecutor.instaban(guild, author, " | ".join(reasons))
            await self._log_event(guild, "☠️ ZERO TOLERANCE", author, "\n".join(reasons))
        elif threat_score >= 60:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            await PunishmentExecutor.auto_punish(guild, author, threat_score, " | ".join(reasons))
            await self._log_event(guild, f"🛡️ Auto-Mod Action (Score: {threat_score})", author, "\n".join(reasons))
        elif threat_score >= 30:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            case = await PunishmentExecutor.auto_punish(guild, author, threat_score, " | ".join(reasons))
            await self._log_event(guild, f"⚠️ Auto-Warn (Score: {threat_score})", author, "\n".join(reasons))

        # Cache message for investigations
        await db.cache_message(
            guild.id, message.channel.id, message.id, author.id,
            content, ", ".join([a.url for a in message.attachments]) if message.attachments else ""
        )

    # ─── Raid Lockdown ─────────────────────────────────────────────────────────
    async def _trigger_raid_lockdown(self, guild: discord.Guild, trigger_member: discord.Member):
        self.bot._raid_mode = True
        # Lock all text channels for @everyone
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = False
                await channel.set_permissions(guild.default_role, overwrite=overwrite, reason="APEX GUARD Anti-Raid")

        # Ban recent joiners in raid window
        recent_joins = [
            m for m in guild.members
            if (datetime.utcnow() - m.joined_at).total_seconds() < BotConfig.RAID_DETECTION_WINDOW + 5
            and not m.bot and m.id not in WHITELISTED_IDS
        ]
        for m in recent_joins:
            await PunishmentExecutor.ban(guild, m, "Auto-ban: raid participant")

        await self._log_event(guild, "🚨 RAID LOCKDOWN TRIGGERED", trigger_member,
                              f"Banned {len(recent_joins)} suspected raiders. Server muted for @everyone.")

        # Notify owner
        owner = guild.owner
        if owner:
            try:
                await owner.send(f"🚨 **APEX GUARD RAID ALERT**\nServer: `{guild.name}`\n"
                                 f"Action: Lockdown + {len(recent_joins)} bans.\nUse `!raidoff` to disable.")
            except discord.Forbidden:
                pass

    # ─── Logging Helper ────────────────────────────────────────────────────────
    async def _log_event(self, guild: discord.Guild, title: str, member: discord.Member, details: str):
        log_id = await db.get_guild_setting(guild.id, "log_channel", BotConfig.LOG_CHANNEL_ID)
        if not log_id:
            return
        channel = guild.get_channel(int(log_id))
        if not channel:
            return
        embed = discord.Embed(title=title, color=0xFF0000, timestamp=datetime.utcnow())
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Details", value=details[:1024], inline=False)
        embed.set_footer(text="APEX GUARD Security Bot")
        await channel.send(embed=embed)

    @commands.command(name="raidoff")
    @commands.has_permissions(administrator=True)
    async def raid_off(self, ctx: commands.Context):
        """Disable raid lockdown and restore channel permissions."""
        self.bot._raid_mode = False
        for channel in ctx.guild.channels:
            if isinstance(channel, discord.TextChannel):
                overwrite = channel.overwrites_for(ctx.guild.default_role)
                overwrite.send_messages = None
                await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason="Raid lockdown lifted")
        await ctx.send("✅ Raid lockdown disabled. Channels restored.")

    @commands.command(name="scan")
    @commands.has_permissions(manage_messages=True)
    async def scan_user(self, ctx: commands.Context, member: discord.Member):
        """Deep-scan a user for threats."""
        score = tracker.get_spam_score(member.id)
        cases = await db.get_cases(ctx.guild.id, member.id)
        embed = discord.Embed(title=f"🔍 Threat Scan: {member}", color=0x3498db)
        embed.add_field(name="Threat Score", value=f"`{score}/100`", inline=True)
        embed.add_field(name="Case History", value=f"`{len(cases)}`", inline=True)
        if cases:
            last = cases[0]
            embed.add_field(name="Last Action", value=f"{last['action']} — {last['reason']}", inline=False)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMod(bot))
