"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     APEX GUARD — LOCKDOWN COG                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
Server-wide and channel-specific lockdown with granular restore snapshots.
"""

import json
import discord
from discord.ext import commands
from datetime import datetime

from utils.database import Database


db = Database()


class Lockdown(commands.Cog):
    """Surgical lockdown capabilities for emergency scenarios."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._snapshots: dict = {}  # guild_id -> {channel_id: overwrite_dict}

    @commands.command(name="lockdown")
    @commands.has_permissions(administrator=True)
    async def lockdown_cmd(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Lockdown a channel or the entire server."""
        targets = [channel] if channel else ctx.guild.text_channels
        snapshot = {}
        for ch in targets:
            overwrite = ch.overwrites_for(ctx.guild.default_role)
            snapshot[ch.id] = {
                "send_messages": overwrite.send_messages,
                "add_reactions": overwrite.add_reactions,
                "attach_files": overwrite.attach_files,
                "embed_links": overwrite.embed_links,
            }
            overwrite.send_messages = False
            overwrite.add_reactions = False
            try:
                await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Lockdown by {ctx.author}")
            except discord.Forbidden:
                continue
        self._snapshots[ctx.guild.id] = snapshot
        await ctx.send(f"🔒 **Lockdown active** for {'this channel' if channel else 'all channels'}.")

    @commands.command(name="unlock")
    @commands.has_permissions(administrator=True)
    async def unlock_cmd(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Restore permissions from lockdown snapshot."""
        snapshot = self._snapshots.get(ctx.guild.id, {})
        if not snapshot:
            return await ctx.reply("No lockdown snapshot found.", delete_after=5)

        targets = [channel] if channel else ctx.guild.text_channels
        for ch in targets:
            data = snapshot.get(ch.id)
            if not data:
                continue
            overwrite = ch.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = data["send_messages"]
            overwrite.add_reactions = data["add_reactions"]
            overwrite.attach_files = data["attach_files"]
            overwrite.embed_links = data["embed_links"]
            try:
                await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason="Lockdown lifted")
            except discord.Forbidden:
                continue
        await ctx.send(f"🔓 **Lockdown lifted** for {'this channel' if channel else 'all channels'}.")

    @commands.command(name="lockrole")
    @commands.has_permissions(administrator=True)
    async def lockrole_cmd(self, ctx: commands.Context, role: discord.Role):
        """Prevent a specific role from sending messages server-wide."""
        for ch in ctx.guild.text_channels:
            overwrite = ch.overwrites_for(role)
            overwrite.send_messages = False
            try:
                await ch.set_permissions(role, overwrite=overwrite, reason=f"Role lockdown by {ctx.author}")
            except discord.Forbidden:
                continue
        await ctx.send(f"🔒 Role {role.mention} muted server-wide.")

    @commands.command(name="unlockrole")
    @commands.has_permissions(administrator=True)
    async def unlockrole_cmd(self, ctx: commands.Context, role: discord.Role):
        """Restore a role's send permission server-wide."""
        for ch in ctx.guild.text_channels:
            overwrite = ch.overwrites_for(role)
            overwrite.send_messages = None
            try:
                await ch.set_permissions(role, overwrite=overwrite, reason="Role lockdown lifted")
            except discord.Forbidden:
                continue
        await ctx.send(f"🔓 Role {role.mention} unmuted server-wide.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Lockdown(bot))
