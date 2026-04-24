"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     APEX GUARD — PUNISHMENT EXECUTOR                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
Handles warns, mutes, kicks, softbans, bans, and instabans with surgical precision.
"""

import asyncio
import discord
from datetime import datetime, timedelta
from typing import Optional

from utils.database import Database
from config import BotConfig, Punishment


db = Database()


class PunishmentExecutor:
    """Execute moderation actions with logging and case creation."""

    @staticmethod
    async def warn(guild: discord.Guild, member: discord.Member, reason: str,
                   moderator: Optional[discord.Member] = None) -> int:
        case_id = await db.add_case(guild.id, member.id, Punishment.WARN, moderator.id if moderator else None, reason)
        try:
            embed = discord.Embed(
                title="⚠️ Warning Received",
                description=f"You were warned in **{guild.name}**.",
                color=0xFFA500,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            await member.send(embed=embed)
        except discord.Forbidden:
            pass
        return case_id

    @staticmethod
    async def mute(guild: discord.Guild, member: discord.Member, duration: int,
                   reason: str, moderator: Optional[discord.Member] = None) -> int:
        """Duration in seconds."""
        case_id = await db.add_case(guild.id, member.id, Punishment.MUTE, moderator.id if moderator else None, reason)
        
        mute_role = discord.utils.get(guild.roles, name="Muted")
        if not mute_role:
            # Attempt to create mute role with overridden perms
            try:
                mute_role = await guild.create_role(name="Muted", reason="APEX GUARD auto-mute role")
                for channel in guild.channels:
                    await channel.set_permissions(mute_role, send_messages=False, add_reactions=False, speak=False)
            except discord.Forbidden:
                return -1
        
        await member.add_roles(mute_role, reason=f"APEX GUARD Mute | Case #{case_id}: {reason}")
        
        try:
            embed = discord.Embed(
                title="🔇 Muted",
                description=f"You were muted in **{guild.name}** for {duration}s.",
                color=0xFF4500,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            await member.send(embed=embed)
        except discord.Forbidden:
            pass
        
        # Schedule unmute
        asyncio.create_task(PunishmentExecutor._schedule_unmute(guild, member, mute_role, duration))
        return case_id

    @staticmethod
    async def _schedule_unmute(guild: discord.Guild, member: discord.Member, mute_role: discord.Role, duration: int):
        await asyncio.sleep(duration)
        try:
            if member and mute_role in member.roles:
                await member.remove_roles(mute_role, reason="APEX GUARD auto-unmute")
        except discord.NotFound:
            pass

    @staticmethod
    async def kick(guild: discord.Guild, member: discord.Member, reason: str,
                   moderator: Optional[discord.Member] = None) -> int:
        case_id = await db.add_case(guild.id, member.id, Punishment.KICK, moderator.id if moderator else None, reason)
        try:
            embed = discord.Embed(
                title="👢 Kicked",
                description=f"You were kicked from **{guild.name}**.",
                color=0xFF0000,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            await member.send(embed=embed)
        except discord.Forbidden:
            pass
        await member.kick(reason=f"APEX GUARD Kick | Case #{case_id}: {reason}")
        return case_id

    @staticmethod
    async def softban(guild: discord.Guild, member: discord.Member, reason: str,
                      moderator: Optional[discord.Member] = None) -> int:
        case_id = await db.add_case(guild.id, member.id, Punishment.SOFTBAN, moderator.id if moderator else None, reason)
        try:
            await member.send(f"You were softbanned from **{guild.name}**. Reason: {reason}")
        except discord.Forbidden:
            pass
        await guild.ban(member, reason=f"APEX GUARD Softban | Case #{case_id}: {reason}", delete_message_days=1)
        await asyncio.sleep(1)
        await guild.unban(member, reason="APEX GUARD softban complete")
        return case_id

    @staticmethod
    async def ban(guild: discord.Guild, member: discord.Member, reason: str,
                  moderator: Optional[discord.Member] = None, delete_days: int = 1) -> int:
        case_id = await db.add_case(guild.id, member.id, Punishment.BAN, moderator.id if moderator else None, reason)
        try:
            embed = discord.Embed(
                title="🔨 Banned",
                description=f"You were banned from **{guild.name}**.",
                color=0x8B0000,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            embed.add_field(name="Appeal", value="Contact server staff if you believe this was an error.", inline=False)
            await member.send(embed=embed)
        except discord.Forbidden:
            pass
        await guild.ban(member, reason=f"APEX GUARD Ban | Case #{case_id}: {reason}", delete_message_days=delete_days)
        return case_id

    @staticmethod
    async def instaban(guild: discord.Guild, member: discord.Member, reason: str) -> int:
        """Zero-tolerance instant ban. No appeal info sent."""
        case_id = await db.add_case(guild.id, member.id, Punishment.INSTABAN, None, reason)
        try:
            await member.send("You have been permanently removed due to a critical security threat.")
        except discord.Forbidden:
            pass
        await guild.ban(member, reason=f"APEX GUARD INSTABAN | Case #{case_id}: {reason}", delete_message_days=7)
        return case_id

    @staticmethod
    async def auto_punish(guild: discord.Guild, member: discord.Member, threat_level: int, reason: str):
        """Automatically select punishment based on threat level (0-100)."""
        if threat_level >= 90:
            return await PunishmentExecutor.instaban(guild, member, reason)
        elif threat_level >= 75:
            return await PunishmentExecutor.ban(guild, member, reason)
        elif threat_level >= 60:
            return await PunishmentExecutor.softban(guild, member, reason)
        elif threat_level >= 45:
            return await PunishmentExecutor.kick(guild, member, reason)
        elif threat_level >= 30:
            return await PunishmentExecutor.mute(guild, member, BotConfig.SPAM_MUTE_DURATION, reason)
        else:
            return await PunishmentExecutor.warn(guild, member, reason)
