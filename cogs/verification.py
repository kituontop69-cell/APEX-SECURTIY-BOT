"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     APEX GUARD — VERIFICATION COG                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
Captcha-based verification, alt-gating, and join screening.
"""

import random
import string
import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta

from config import BotConfig, Features
from utils.database import Database
from utils.punishments import PunishmentExecutor


db = Database()


class Verification(commands.Cog):
    """Enterprise-grade member verification with CAPTCHA."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._pending: dict = {}  # user_id -> (code, task)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not Features.CAPTCHA_VERIFICATION:
            return
        if member.bot:
            return

        guild = member.guild
        verif_role_id = await db.get_guild_setting(guild.id, "verified_role", BotConfig.VERIFICATION_ROLE_ID)
        verif_channel_id = await db.get_guild_setting(guild.id, "verification_channel", BotConfig.VERIFICATION_CHANNEL_ID)

        if not verif_role_id or not verif_channel_id:
            return

        channel = guild.get_channel(int(verif_channel_id))
        if not channel:
            return

        # Generate CAPTCHA
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        embed = discord.Embed(
            title="🔐 APEX GUARD Verification",
            description=f"Welcome {member.mention}. Reply with the code below to gain access.",
            color=0x2ecc71,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Your Code", value=f"`{code}`", inline=False)
        embed.set_footer(text=f"Expires in {BotConfig.CAPTCHA_TIMEOUT}s")

        try:
            msg = await channel.send(embed=embed)
        except discord.Forbidden:
            return

        # Timeout task
        async def timeout_task():
            await asyncio.sleep(BotConfig.CAPTCHA_TIMEOUT)
            if member.id in self._pending:
                del self._pending[member.id]
                try:
                    await member.kick(reason="APEX GUARD: Failed verification")
                except discord.Forbidden:
                    pass
                await channel.send(f"⏰ {member.mention} failed verification and was removed.", delete_after=10)

        task = self.bot.loop.create_task(timeout_task())
        self._pending[member.id] = (code, task, channel)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.author.id not in self._pending:
            return

        code, task, channel = self._pending[message.author.id]
        if message.content.strip().upper() == code:
            task.cancel()
            del self._pending[message.author.id]

            # Assign verified role
            guild = message.guild
            verif_role_id = await db.get_guild_setting(guild.id, "verified_role", BotConfig.VERIFICATION_ROLE_ID)
            role = guild.get_role(int(verif_role_id))
            if role:
                try:
                    await message.author.add_roles(role, reason="APEX GUARD verification passed")
                except discord.Forbidden:
                    pass

            await message.add_reaction("✅")
            await message.delete(delay=5)

    @commands.command(name="verifysetup")
    @commands.has_permissions(administrator=True)
    async def verify_setup(self, ctx: commands.Context, role: discord.Role, channel: discord.TextChannel):
        """Configure verification role and channel."""
        await db.set_guild_setting(ctx.guild.id, "verified_role", role.id)
        await db.set_guild_setting(ctx.guild.id, "verification_channel", channel.id)
        await ctx.send(f"✅ Verification configured:\nRole: {role.mention}\nChannel: {channel.mention}")

    @commands.command(name="verifyforce")
    @commands.has_permissions(administrator=True)
    async def verify_force(self, ctx: commands.Context, member: discord.Member):
        """Manually verify a member."""
        verif_role_id = await db.get_guild_setting(ctx.guild.id, "verified_role", BotConfig.VERIFICATION_ROLE_ID)
        role = ctx.guild.get_role(int(verif_role_id))
        if role:
            await member.add_roles(role, reason="Manual verification")
            await ctx.send(f"✅ {member.mention} manually verified.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Verification(bot))
