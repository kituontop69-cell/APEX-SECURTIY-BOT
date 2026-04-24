"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     APEX GUARD — HIGH-END DISCORD SECURITY BOT               ║
║                              Configuration Module                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
Professional, feature-loaded, deadly security configuration.
"""

import os

# ─── Core Bot Settings ─────────────────────────────────────────────────────────
class BotConfig:
    """Immutable core configuration."""
    TOKEN = os.getenv("DISCORD_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    PREFIX = os.getenv("BOT_PREFIX", "!")
    OWNER_IDS = list(map(int, os.getenv("OWNER_IDS", "0").split(",")))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
    ERROR_CHANNEL_ID = int(os.getenv("ERROR_CHANNEL_ID", "0"))
    
    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/security.db")
    
    # Anti-Spam / Raid
    RAID_DETECTION_WINDOW = int(os.getenv("RAID_WINDOW", "10"))
    RAID_JOIN_THRESHOLD = int(os.getenv("RAID_THRESHOLD", "10"))
    SPAM_MESSAGE_THRESHOLD = int(os.getenv("SPAM_THRESHOLD", "5"))
    SPAM_WINDOW = int(os.getenv("SPAM_WINDOW", "5"))
    SPAM_MUTE_DURATION = int(os.getenv("SPAM_MUTE", "300"))
    
    # Verification
    VERIFICATION_ROLE_ID = int(os.getenv("VERIF_ROLE_ID", "0"))
    VERIFICATION_CHANNEL_ID = int(os.getenv("VERIF_CHANNEL_ID", "0"))
    CAPTCHA_TIMEOUT = int(os.getenv("CAPTCHA_TIMEOUT", "300"))
    
    # Lockdown
    LOCKDOWN_ROLE_OVERRIDE = True

# ─── Security Levels ───────────────────────────────────────────────────────────
class SecurityLevel:
    """Escalating security tiers."""
    NORMAL = 0
    ELEVATED = 1
    HIGH = 2
    CRITICAL = 3
    DEADLY = 4

# ─── Punishment Tiers ──────────────────────────────────────────────────────────
class Punishment:
    """Configurable punishment escalation."""
    WARN = "warn"
    MUTE = "mute"
    KICK = "kick"
    SOFTBAN = "softban"
    BAN = "ban"
    INSTABAN = "instaban"

# ─── Whitelist / Blacklist ─────────────────────────────────────────────────────
WHITELISTED_IDS = set()
BLACKLISTED_IDS = set()
BLACKLISTED_WORDS = [
    "discord.gg/", "discord.com/invite", "@everyone scam",
    "free nitro", "steam gift", "gift card", "csgo skins free"
]
SUSPICIOUS_INVITE_PATTERNS = [
    r"discord\.gg/[a-zA-Z0-9]{2,}",
    r"discord\.com/invite/[a-zA-Z0-9]{2,}",
    r"dsc\.gg/[a-zA-Z0-9]+",
    r"discord\.me/[a-zA-Z0-9]+",
]

# ─── API Keys (Optional) ───────────────────────────────────────────────────────
class APIs:
    """Optional external threat intelligence."""
    VIRUSTOTAL_API = os.getenv("VIRUSTOTAL_API", "")
    IPQUALITYSCORE_API = os.getenv("IPQUALITY_API", "")

# ─── Feature Flags ─────────────────────────────────────────────────────────────
class Features:
    """Toggle high-end modules."""
    ANTI_RAID = True
    ANTI_SPAM = True
    ANTI_PHISHING = True
    ANTI_NSFW = True
    ANTI_MASS_MENTION = True
    ANTI_CAPITALS_FLOOD = True
    ANTI_EMOJI_FLOOD = True
    ANTI_LINK = False
    AUTO_DEHOIST = True
    AUTO_ROLE = True
    CAPTCHA_VERIFICATION = True
    LOGGING_ADVANCED = True
    BACKUP_GUILD = True
    THREAT_INTELLIGENCE = True
    PRESENCE_TRACKING = True
    ALT_DETECTION = True
    TOKEN_LEAK_DETECTION = True
    FILE_SCAN = True
    # Extra Deadly
    ANTI_NUKE = True
    WEBHOOK_PROTECTION = True
    VOICE_LOCKDOWN = True
    DM_RAID_SHIELD = True
    ANTI_MASS_ROLE = True
    ANTI_BOT_ADD = True

# ─── Anti-Nuke Thresholds ──────────────────────────────────────────────────────
class AntiNukeLimits:
    """Destructive action thresholds within window (seconds)."""
    CHANNEL_DELETE_LIMIT = 3
    CHANNEL_DELETE_WINDOW = 10
    ROLE_DELETE_LIMIT = 3
    ROLE_DELETE_WINDOW = 10
    WEBHOOK_CREATE_LIMIT = 2
    WEBHOOK_CREATE_WINDOW = 10
    ROLE_ASSIGN_LIMIT = 5
    ROLE_ASSIGN_WINDOW = 10
    BOT_ADD_WINDOW = 10
    PUNISHMENT = "ban"

# ─── Cooldowns & Limits ────────────────────────────────────────────────────────
class Limits:
    """Rate limits and thresholds."""
    COMMAND_COOLDOWN = 3
    MAX_MENTIONS = 5
    MAX_LINES = 15
    MAX_ATTACHMENTS = 4
    MAX_CHARACTERS = 2000
    MAX_CAPS_PERCENT = 70
    MAX_EMOJIS = 8
    MAX_NEWLINES = 10
    REPEATED_MESSAGE_LIMIT = 3
    URL_SHORTENER_BLOCK = True
