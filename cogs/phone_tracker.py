"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  APEX GUARD — PHONE TRACKING MODULE                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
Secure phone number location lookup & call log management system.
PRIVATE USE ONLY - FOR AUTHORIZED PERSONNEL ONLY.
"""

import discord
from discord.ext import commands
from datetime import datetime
import re
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from typing import List, Dict, Optional
import aiosqlite

class PhoneTracker(commands.Cog):
    """Phone number tracking and call log management system."""

    def __init__(self, bot):
        self.bot = bot
        self.phone_regex = re.compile(r'^\+?[1-9][0-9]{7,14}$')

    async def init_phone_tables(self):
        """Initialize database tables for phone tracking."""
        async with aiosqlite.connect("data/security.db") as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS phone_numbers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT UNIQUE NOT NULL,
                    owner_name TEXT,
                    location TEXT,
                    carrier TEXT,
                    timezone TEXT,
                    country_code TEXT,
                    national_format TEXT,
                    last_checked REAL DEFAULT 0,
                    added_by INTEGER NOT NULL,
                    added_at REAL DEFAULT (strftime('%s','now')),
                    notes TEXT
                );

                CREATE TABLE IF NOT EXISTS call_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_id INTEGER NOT NULL,
                    call_type TEXT NOT NULL, -- INCOMING, OUTGOING, MISSED
                    contact_name TEXT,
                    contact_number TEXT,
                    timestamp REAL NOT NULL,
                    duration INTEGER DEFAULT 0, -- seconds
                    location_at_call TEXT,
                    network_type TEXT,
                    signal_strength INTEGER,
                    battery_level INTEGER,
                    notes TEXT,
                    FOREIGN KEY (phone_id) REFERENCES phone_numbers(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS phone_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    phone_number TEXT,
                    timestamp REAL DEFAULT (strftime('%s','now')),
                    ip_address TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_phone_number ON phone_numbers(phone_number);
                CREATE INDEX IF NOT EXISTS idx_call_log_phone ON call_logs(phone_id);
            """)
            await db.commit()

    @commands.group(name="phone", invoke_without_command=True)
    @commands.is_owner()
    async def phone_group(self, ctx):
        """Phone number tracking commands."""
        embed = discord.Embed(
            title="📱 Phone Tracking System",
            description="Secure phone location and call log management",
            color=0x2f3136,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Commands", value="""
`!phone track <number>` - Lookup phone number location
`!phone logs <number>` - View full call history
`!phone addlog <number> <type> <contact> <duration>` - Add call log entry
`!phone list` - List all tracked numbers
`!phone remove <number>` - Stop tracking number
        """, inline=False)
        embed.set_footer(text="PRIVATE USE ONLY • AUTHORIZED ACCESS")
        await ctx.send(embed=embed)

    @phone_group.command(name="track")
    @commands.is_owner()
    async def track_phone(self, ctx, *, phone_number: str):
        """Track location and details of a phone number."""
        
        # Audit log
        await self.bot.db.execute(
            "INSERT INTO phone_audit_log (user_id, action, phone_number) VALUES (?, ?, ?)",
            (ctx.author.id, "LOOKUP", phone_number)
        )

        try:
            # Parse phone number
            parsed = phonenumbers.parse(phone_number, None)
            
            if not phonenumbers.is_valid_number(parsed):
                return await ctx.reply("❌ Invalid phone number format")

            # Get information
            location = geocoder.description_for_number(parsed, "en")
            carrier_name = carrier.name_for_number(parsed, "en")
            time_zones = timezone.time_zones_for_number(parsed)
            national_format = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
            international_format = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            country_code = phonenumbers.region_code_for_number(parsed)
            
            # Store in database
            async with aiosqlite.connect("data/security.db") as db:
                await db.execute("""
                    INSERT OR REPLACE INTO phone_numbers 
                    (phone_number, location, carrier, timezone, country_code, national_format, last_checked, added_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    phone_number,
                    location,
                    carrier_name,
                    time_zones[0] if time_zones else "Unknown",
                    country_code,
                    national_format,
                    datetime.utcnow().timestamp(),
                    ctx.author.id
                ))
                await db.commit()

            # Create response embed
            embed = discord.Embed(
                title="📱 Phone Number Location Report",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="📞 Phone Number", value=f"""
**International:** {international_format}
**National:** {national_format}
**Country Code:** +{parsed.country_code} ({country_code})
            """, inline=False)
            
            embed.add_field(name="📍 Location Information", value=f"""
**Region:** {location}
**Timezone:** {time_zones[0] if time_zones else 'Unknown'}
**Carrier:** {carrier_name if carrier_name else 'Unknown'}
            """, inline=False)
            
            embed.add_field(name="ℹ️ Details", value=f"""
**Valid:** ✅ Yes
**Possible:** {phonenumbers.is_possible_number(parsed)}
**Number Type:** {phonenumbers.number_type(parsed).name}
            """, inline=False)
            
            embed.set_footer(text=f"Requested by {ctx.author} • PRIVATE USE ONLY")
            
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.reply(f"⚠️ Error tracking number: {str(e)}")

    @phone_group.command(name="logs")
    @commands.is_owner()
    async def view_call_logs(self, ctx, *, phone_number: str):
        """View complete call logs for a phone number."""
        
        async with aiosqlite.connect("data/security.db") as db:
            db.row_factory = aiosqlite.Row
            
            # Get phone ID
            cursor = await db.execute("SELECT id, phone_number FROM phone_numbers WHERE phone_number = ?", (phone_number,))
            phone = await cursor.fetchone()
            
            if not phone:
                return await ctx.reply("❌ Phone number not found in tracking list")
            
            # Get all call logs
            cursor = await db.execute("""
                SELECT * FROM call_logs 
                WHERE phone_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 50
            """, (phone['id'],))
            
            logs = await cursor.fetchall()

        embed = discord.Embed(
            title=f"📞 Call Log History • {phone_number}",
            description=f"Total {len(logs)} call records found",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )

        if not logs:
            embed.description = "⚠️ No call logs found for this number"
            return await ctx.send(embed=embed)

        call_summary = ""
        incoming = 0
        outgoing = 0
        missed = 0
        total_duration = 0

        for log in logs:
            call_time = datetime.fromtimestamp(log['timestamp']).strftime("%d/%m/%Y %H:%M")
            duration = f"{log['duration']//60}m {log['duration']%60}s" if log['duration'] > 0 else "N/A"
            
            if log['call_type'] == "INCOMING":
                icon = "📥"
                incoming += 1
            elif log['call_type'] == "OUTGOING":
                icon = "📤"
                outgoing += 1
            else:
                icon = "❌"
                missed += 1
            
            total_duration += log['duration']
            
            call_summary += f"{icon} **{call_time}** | `{log['contact_name']}` {log['contact_number']} | {duration}\n"

        embed.add_field(name="📊 Summary", value=f"""
📥 Incoming: {incoming}
📤 Outgoing: {outgoing}
❌ Missed: {missed}
⏱️ Total Talk Time: {total_duration//60} minutes
        """, inline=False)

        embed.add_field(name="📋 Call History", value=call_summary[:1024], inline=False)
        embed.set_footer(text=f"Requested by {ctx.author} • PRIVATE AND CONFIDENTIAL")
        
        await ctx.send(embed=embed)

    @phone_group.command(name="addlog")
    @commands.is_owner()
    async def add_call_log(self, ctx, phone_number: str, call_type: str, contact: str, duration: int, *, notes: str = ""):
        """
        Add call log entry
        Call types: INCOMING, OUTGOING, MISSED
        Duration in seconds
        """
        
        call_type = call_type.upper()
        if call_type not in ["INCOMING", "OUTGOING", "MISSED"]:
            return await ctx.reply("❌ Invalid call type. Use: INCOMING, OUTGOING, MISSED")

        async with aiosqlite.connect("data/security.db") as db:
            cursor = await db.execute("SELECT id FROM phone_numbers WHERE phone_number = ?", (phone_number,))
            phone = await cursor.fetchone()
            
            if not phone:
                return await ctx.reply("❌ Phone number not tracked. Use !phone track first")
            
            await db.execute("""
                INSERT INTO call_logs 
                (phone_id, call_type, contact_name, contact_number, timestamp, duration, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                phone[0],
                call_type,
                contact,
                phone_number,
                datetime.utcnow().timestamp(),
                duration,
                notes
            ))
            await db.commit()

        await ctx.reply(f"✅ Call log entry added successfully for {phone_number}")

    @phone_group.command(name="list")
    @commands.is_owner()
    async def list_tracked_numbers(self, ctx):
        """List all currently tracked phone numbers."""
        
        async with aiosqlite.connect("data/security.db") as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM phone_numbers ORDER BY added_at DESC")
            numbers = await cursor.fetchall()

        embed = discord.Embed(
            title="📱 Tracked Phone Numbers",
            description=f"Total {len(numbers)} numbers being tracked",
            color=0x9b59b6,
            timestamp=datetime.utcnow()
        )

        for num in numbers:
            last_check = datetime.fromtimestamp(num['last_checked']).strftime("%d/%m/%Y %H:%M")
            embed.add_field(
                name=f"{num['phone_number']}",
                value=f"📍 {num['location']}\n📡 {num['carrier']}\n⏰ Last checked: {last_check}",
                inline=False
            )

        await ctx.send(embed=embed)

    @phone_group.command(name="remove")
    @commands.is_owner()
    async def remove_number(self, ctx, *, phone_number: str):
        """Stop tracking a phone number and delete all logs."""
        
        async with aiosqlite.connect("data/security.db") as db:
            await db.execute("DELETE FROM call_logs WHERE phone_id IN (SELECT id FROM phone_numbers WHERE phone_number = ?)", (phone_number,))
            await db.execute("DELETE FROM phone_numbers WHERE phone_number = ?", (phone_number,))
            await db.commit()

        await ctx.reply(f"✅ Phone number {phone_number} removed from tracking")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.init_phone_tables()
        self.bot.logger.info("✅ Phone Tracker module loaded successfully")


async def setup(bot):
    await bot.add_cog(PhoneTracker(bot))