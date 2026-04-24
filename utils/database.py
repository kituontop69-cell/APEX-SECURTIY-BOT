"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     APEX GUARD — DATABASE LAYER                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
Persistent SQLite storage for security events, cases, and guild settings.
"""

import sqlite3
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import aiosqlite

DB_PATH = "data/security.db"


class Database:
    """Async SQLite database manager for security operations."""

    def __init__(self, path: str = DB_PATH):
        self.path = path
        self._lock = asyncio.Lock()

    async def init(self):
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS cases (
                    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    moderator_id INTEGER,
                    action TEXT NOT NULL,
                    reason TEXT,
                    timestamp REAL DEFAULT (strftime('%s','now')),
                    proof TEXT,
                    active INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    security_level INTEGER DEFAULT 0,
                    log_channel INTEGER DEFAULT 0,
                    mute_role INTEGER DEFAULT 0,
                    verified_role INTEGER DEFAULT 0,
                    lockdown INTEGER DEFAULT 0,
                    auto_mod INTEGER DEFAULT 1,
                    welcome_enabled INTEGER DEFAULT 0,
                    anti_alt INTEGER DEFAULT 1,
                    anti_raid INTEGER DEFAULT 1,
                    backup_data TEXT
                );

                CREATE TABLE IF NOT EXISTS user_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    joins INTEGER DEFAULT 0,
                    messages INTEGER DEFAULT 0,
                    warns INTEGER DEFAULT 0,
                    mutes INTEGER DEFAULT 0,
                    kicks INTEGER DEFAULT 0,
                    bans INTEGER DEFAULT 0,
                    last_join REAL DEFAULT 0,
                    last_message REAL DEFAULT 0,
                    reputation_score INTEGER DEFAULT 100
                );

                CREATE TABLE IF NOT EXISTS raid_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    triggered_at REAL DEFAULT (strftime('%s','now')),
                    joined_ids TEXT,
                    action_taken TEXT,
                    resolved INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS blacklists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    target_id INTEGER,
                    target_type TEXT, -- 'user', 'role', 'invite'
                    reason TEXT,
                    added_by INTEGER,
                    added_at REAL DEFAULT (strftime('%s','now'))
                );

                CREATE TABLE IF NOT EXISTS message_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    author_id INTEGER NOT NULL,
                    content TEXT,
                    attachments TEXT,
                    created_at REAL DEFAULT (strftime('%s','now'))
                );

                CREATE INDEX IF NOT EXISTS idx_cases_user ON cases(user_id);
                CREATE INDEX IF NOT EXISTS idx_cases_guild ON cases(guild_id);
                CREATE INDEX IF NOT EXISTS idx_history_user ON user_history(user_id, guild_id);
                CREATE INDEX IF NOT EXISTS idx_msg_author ON message_cache(author_id);
            """)
            await db.commit()

    async def add_case(self, guild_id: int, user_id: int, action: str,
                       moderator_id: Optional[int] = None, reason: str = "No reason provided.",
                       proof: Optional[str] = None) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """INSERT INTO cases (guild_id, user_id, moderator_id, action, reason, proof)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (guild_id, user_id, moderator_id, action, reason, proof)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_cases(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM cases WHERE guild_id=? AND user_id=? ORDER BY timestamp DESC",
                (guild_id, user_id)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_user_history(self, guild_id: int, user_id: int, field: str, increment: int = 1):
        """Atomically increment a field in user_history."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(f"""
                INSERT INTO user_history (guild_id, user_id, {field})
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                {field} = {field} + ?
            """, (guild_id, user_id, increment, increment))
            await db.commit()

    async def get_user_rep(self, guild_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT reputation_score FROM user_history WHERE guild_id=? AND user_id=?",
                (guild_id, user_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 100

    async def set_guild_setting(self, guild_id: int, key: str, value: Any):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"INSERT INTO guild_settings (guild_id, {key}) VALUES (?, ?) "
                f"ON CONFLICT(guild_id) DO UPDATE SET {key}=?",
                (guild_id, value, value)
            )
            await db.commit()

    async def get_guild_setting(self, guild_id: int, key: str, default: Any = None) -> Any:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                f"SELECT {key} FROM guild_settings WHERE guild_id=?",
                (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else default

    async def cache_message(self, guild_id: int, channel_id: int, message_id: int,
                            author_id: int, content: str, attachments: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO message_cache (guild_id, channel_id, message_id, author_id, content, attachments)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (guild_id, channel_id, message_id, author_id, content, attachments)
            )
            await db.commit()

    async def get_recent_messages(self, guild_id: int, author_id: int, seconds: int) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM message_cache
                   WHERE guild_id=? AND author_id=? AND created_at > (strftime('%s','now') - ?)
                   ORDER BY created_at DESC""",
                (guild_id, author_id, seconds)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def purge_old_messages(self, hours: int = 24):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "DELETE FROM message_cache WHERE created_at < (strftime('%s','now') - ?)",
                (hours * 3600,)
            )
            await db.commit()
