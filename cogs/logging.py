"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     APEX GUARD — ADVANCED LOGGING COG                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
Comprehensive audit trail: message edits, deletions, member updates, invites.
"""

import discord
from discord.ext import commands
from datetime import datetime

from config import BotConfig
from utils.database import Database


db = Database()


class AdvancedLogging(commands.Cog):
    """Forensic-grade event logging."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _get_log_channel(self, guild: discord.Guild):
        log_id = await db.get_guild_setting(guild.id, "log_channel", BotConfig.LOG_CHANNEL_ID)
        return guild.get_channel(int(log_id)) if log_id else None

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        channel = await self._get_log_channel(message.guild)
        if not channel:
            return
        embed = discord.Embed(title="🗑️ Message Deleted", color=0xe74c3c, timestamp=datetime.utcnow())
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Content", value=message.content[:1024] or "[No text content]", inline=False)
        if message.attachments:
            embed.add_field(name="Attachments", value="\n".join([a.url for a in message.attachments]), inline=False)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        channel = await self._get_log_channel(before.guild)
        if not channel:
            return
        embed = discord.Embed(title="✏️ Message Edited", color=0xf1c40f, timestamp=datetime.utcnow())
        embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Before", value=before.content[:1024] or "[Empty]", inline=False)
        embed.add_field(name="After", value=after.content[:1024] or "[Empty]", inline=False)
        embed.add_field(name="Jump", value=f"[Go to message]({after.jump_url})", inline=False)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not before.guild:
            return
        channel = await self._get_log_channel(before.guild)
        if not channel:
            return

        if before.nick != after.nick:
            embed = discord.Embed(title="📝 Nickname Changed", color=0x9b59b6, timestamp=datetime.utcnow())
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            embed.add_field(name="Before", value=before.nick or "[None]", inline=True)
            embed.add_field(name="After", value=after.nick or "[None]", inline=True)
            await channel.send(embed=embed)

        if before.roles != after.roles:
            added = set(after.roles) - set(before.roles)
            removed = set(before.roles) - set(after.roles)
            if added or removed:
                embed = discord.Embed(title="🛡️ Role Update", color=0x3498db, timestamp=datetime.utcnow())
                embed.set_author(name=str(after), icon_url=after.display_avatar.url)
                if added:
                    embed.add_field(name="Added", value=" ".join([r.mention for r in added]), inline=False)
                if removed:
                    embed.add_field(name="Removed", value=" ".join([r.mention for r in removed]), inline=False)
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = await self._get_log_channel(member.guild)
        if not channel:
            return
        embed = discord.Embed(title="👤 Member Left", color=0x95a5a6, timestamp=datetime.utcnow())
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined At", value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "N/A", inline=True)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        channel = await self._get_log_channel(invite.guild)
        if not channel:
            return
        embed = discord.Embed(title="🔗 Invite Created", color=0x2ecc71, timestamp=datetime.utcnow())
        embed.add_field(name="Code", value=f"`{invite.code}`", inline=True)
        embed.add_field(name="Channel", value=invite.channel.mention, inline=True)
        embed.add_field(name="Inviter", value=invite.inviter.mention if invite.inviter else "Unknown", inline=True)
        embed.add_field(name="Expires", value=str(invite.max_age) + "s" if invite.max_age else "Never", inline=True)
        await channel.send(embed=embed)

    @commands.command(name="setlog")
    @commands.has_permissions(administrator=True)
    async def setlog_cmd(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.set_guild_setting(ctx.guild.id, "log_channel", channel.id)
        await ctx.send(f"✅ Log channel set to {channel.mention}")


async def setup(bot: commands.Bot):
    await bot.add_cog(AdvancedLogging(bot))
