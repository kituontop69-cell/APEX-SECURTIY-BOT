"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     APEX GUARD — SECURITY DETECTION ENGINE                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
Core threat detection logic: spam, raid, phishing, alt accounts, token leaks.
"""

import re
import json
import asyncio
from typing import Optional, Tuple, Dict, List
from datetime import datetime, timedelta
from collections import defaultdict, Counter

import aiohttp

from config import (
    Features, Limits, BLACKLISTED_WORDS, SUSPICIOUS_INVITE_PATTERNS,
    SecurityLevel, Punishment, APIs, WHITELISTED_IDS
)


# ─── In-Memory Tracking ────────────────────────────────────────────────────────
class MessageTracker:
    """Track user messages for spam/raid detection."""

    def __init__(self):
        self.join_buffer: Dict[int, List[datetime]] = defaultdict(list)   # guild_id -> joins
        self.msg_buffer: Dict[int, List[Dict]] = defaultdict(list)        # user_id -> msgs
        self.repeated_content: Dict[int, Counter] = defaultdict(Counter)  # user_id -> content counts
        self.mention_buffer: Dict[int, List[datetime]] = defaultdict(list)# user_id -> mention times

    def add_join(self, guild_id: int):
        now = datetime.utcnow()
        buf = self.join_buffer[guild_id]
        buf.append(now)
        # Trim old
        cutoff = now - timedelta(seconds=20)
        self.join_buffer[guild_id] = [t for t in buf if t > cutoff]

    def is_raid(self, guild_id: int, threshold: int = 10, window: int = 10) -> bool:
        now = datetime.utcnow()
        buf = self.join_buffer[guild_id]
        cutoff = now - timedelta(seconds=window)
        recent = [t for t in buf if t > cutoff]
        return len(recent) >= threshold

    def add_message(self, user_id: int, content: str, guild_id: int):
        now = datetime.utcnow()
        entry = {"time": now, "content": content, "guild_id": guild_id}
        buf = self.msg_buffer[user_id]
        buf.append(entry)
        cutoff = now - timedelta(seconds=15)
        self.msg_buffer[user_id] = [b for b in buf if b["time"] > cutoff]
        self.repeated_content[user_id][content.lower()] += 1

    def is_spam(self, user_id: int, threshold: int = 5, window: int = 5) -> bool:
        now = datetime.utcnow()
        buf = self.msg_buffer[user_id]
        cutoff = now - timedelta(seconds=window)
        recent = [b for b in buf if b["time"] > cutoff]
        return len(recent) >= threshold

    def repeated_spam(self, user_id: int, limit: int = 3) -> bool:
        counts = self.repeated_content[user_id]
        if not counts:
            return False
        most_common = counts.most_common(1)[0][1]
        return most_common >= limit

    def get_spam_score(self, user_id: int) -> int:
        """Calculate a dynamic threat score 0-100."""
        score = 0
        buf = self.msg_buffer[user_id]
        now = datetime.utcnow()
        recent = [b for b in buf if b["time"] > now - timedelta(seconds=10)]
        score += min(len(recent) * 10, 40)
        if self.repeated_spam(user_id):
            score += 25
        return min(score, 100)

    def add_mention(self, user_id: int):
        now = datetime.utcnow()
        buf = self.mention_buffer[user_id]
        buf.append(now)
        cutoff = now - timedelta(minutes=1)
        self.mention_buffer[user_id] = [t for t in buf if t > cutoff]

    def mention_flood(self, user_id: int, threshold: int = 8) -> bool:
        return len(self.mention_buffer[user_id]) >= threshold


tracker = MessageTracker()


# ─── Content Analysis ──────────────────────────────────────────────────────────
def contains_invite(text: str) -> bool:
    return any(re.search(pat, text, re.IGNORECASE) for pat in SUSPICIOUS_INVITE_PATTERNS)


def contains_blacklisted(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in BLACKLISTED_WORDS)


def caps_flood(text: str) -> bool:
    if len(text) < 8:
        return False
    caps = sum(1 for c in text if c.isupper())
    return (caps / len(text)) * 100 > Limits.MAX_CAPS_PERCENT


def emoji_flood(text: str) -> bool:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    emojis = emoji_pattern.findall(text)
    return len(emojis) > Limits.MAX_EMOJIS


def mass_mention(text: str) -> bool:
    mentions = text.count("@everyone") + text.count("@here")
    return mentions >= 1  # Strict: any mass mention flagged


def has_token_leak(text: str) -> bool:
    """Detect potential Discord bot token leaks."""
    token_pattern = re.compile(r"[MN][A-Za-z\d]{23}\.[A-Za-z\d]{6}\.[A-Za-z\d]{27}")
    return bool(token_pattern.search(text))


def is_suspicious_url(text: str) -> bool:
    shorteners = ["bit.ly", "tinyurl", "t.co", "goo.gl", "short.link", "is.gd", "ow.ly"]
    lowered = text.lower()
    return any(s in lowered for s in shorteners)


# ─── Alt Detection ─────────────────────────────────────────────────────────────
async def check_alt_account(member) -> Tuple[bool, str]:
    """Heuristic alt detection based on account age, avatar, mutual guilds."""
    reasons = []
    now = datetime.utcnow()
    created = member.created_at
    age_days = (now - created).days

    if age_days < 1:
        reasons.append("Account created within 24 hours")
    elif age_days < 7:
        reasons.append("Account less than 1 week old")

    if member.public_flags.spammer:
        reasons.append("Discord flagged as spammer")

    if not member.avatar:
        reasons.append("No custom avatar")

    # Heuristic: default avatar + new account = likely alt
    is_alt = len(reasons) >= 2 or "spammer" in str(reasons).lower()
    return is_alt, " | ".join(reasons) if reasons else "Clean"


# ─── External Threat Intelligence ──────────────────────────────────────────────
async def check_url_reputation(url: str) -> Tuple[bool, str]:
    """Query VirusTotal or IPQualityScore if API keys provided."""
    if not APIs.VIRUSTOTAL_API:
        return False, "No API key configured"

    try:
        async with aiohttp.ClientSession() as session:
            headers = {"x-apikey": APIs.VIRUSTOTAL_API}
            async with session.get(
                f"https://www.virustotal.com/api/v3/urls/{url}", headers=headers, timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
                    malicious = stats.get("malicious", 0)
                    return malicious > 2, f"VT score: {malicious} malicious"
    except Exception:
        pass
    return False, "Check failed"


# ─── File Scanning ─────────────────────────────────────────────────────────────
async def scan_attachment(filename: str, content_type: str, url: str) -> Tuple[bool, str]:
    """Basic file threat analysis."""
    dangerous_extensions = [".exe", ".bat", ".cmd", ".scr", ".sh", ".dll", ".msi", ".vbs", ".js", ".ps1"]
    if any(filename.lower().endswith(ext) for ext in dangerous_extensions):
        return True, f"Dangerous file extension: {filename}"
    return False, "Clean"
