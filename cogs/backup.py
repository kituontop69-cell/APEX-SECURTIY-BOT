"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     APEX GUARD — BACKUP & RECOVERY COG                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
Guild structure backup: roles, channels, permissions, settings.
"""

import json
import discord
from discord.ext import commands
from datetime import datetime

from utils.database import Database


db = Database()


class Backup(commands.Cog):
    """Disaster recovery and guild snapshot system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="backup")
    @commands.has_permissions(administrator=True)
    async def backup_cmd(self, ctx: commands.Context):
        """Create a full JSON backup of guild structure."""
        guild = ctx.guild
        data = {
            "name": guild.name,
            "id": guild.id,
            "timestamp": datetime.utcnow().isoformat(),
            "roles": [],
            "channels": [],
            "categories": []
        }

        for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
            if role.is_default():
                continue
            data["roles"].append({
                "name": role.name,
                "color": str(role.color),
                "hoist": role.hoist,
                "mentionable": role.mentionable,
                "permissions": role.permissions.value,
            })

        for category in guild.categories:
            data["categories"].append({
                "name": category.name,
                "position": category.position,
                "overwrites": self._serialize_overwrites(category.overwrites)
            })

        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                ch_data = {
                    "name": channel.name,
                    "type": "text",
                    "position": channel.position,
                    "category": channel.category.name if channel.category else None,
                    "overwrites": self._serialize_overwrites(channel.overwrites),
                    "slowmode": channel.slowmode_delay,
                    "nsfw": channel.is_nsfw()
                }
            elif isinstance(channel, discord.VoiceChannel):
                ch_data = {
                    "name": channel.name,
                    "type": "voice",
                    "position": channel.position,
                    "category": channel.category.name if channel.category else None,
                    "overwrites": self._serialize_overwrites(channel.overwrites),
                    "bitrate": channel.bitrate,
                    "user_limit": channel.user_limit
                }
            else:
                continue
            data["channels"].append(ch_data)

        json_str = json.dumps(data, indent=2)
        await db.set_guild_setting(guild.id, "backup_data", json_str)

        file = discord.File(fp=__import__("io").BytesIO(json_str.encode()), filename=f"backup_{guild.id}.json")
        embed = discord.Embed(title="💾 Guild Backup Complete", color=0x2ecc71, timestamp=datetime.utcnow())
        embed.add_field(name="Roles", value=len(data["roles"]), inline=True)
        embed.add_field(name="Channels", value=len(data["channels"]), inline=True)
        embed.add_field(name="Categories", value=len(data["categories"]), inline=True)
        await ctx.send(embed=embed, file=file)

    @staticmethod
    def _serialize_overwrites(overwrites):
        result = {}
        for target, perm in overwrites.items():
            result[str(target.id)] = {
                "type": "role" if isinstance(target, discord.Role) else "member",
                "allow": perm.pair()[0].value,
                "deny": perm.pair()[1].value
            }
        return result

    @commands.command(name="restore")
    @commands.has_permissions(administrator=True)
    async def restore_cmd(self, ctx: commands.Context):
        """Restore roles and channels from last backup. DESTRUCTIVE."""
        await ctx.send("⚠️ This is a placeholder. Restoration logic should be implemented with care.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Backup(bot))
