# 🛡️ APEX GUARD — High-End Discord Security Bot

> **Professional · Feature-Loaded · Deadly**

APEX GUARD is a top-tier, enterprise-grade Discord security bot engineered for servers that demand absolute protection. Built with Python and `discord.py`, it delivers real-time threat detection, automated moderation, forensic logging, and surgical lockdown capabilities.

---

## ⚡ Key Features

| Feature | Description |
|---------|-------------|
| **Anti-Raid** | Detects mass-join waves and auto-triggers lockdown + mass-ban |
| **Anti-Spam** | Message rate-limiting, repeated-content detection, dynamic threat scoring |
| **Anti-Phishing** | Blacklisted keyword scanning + suspicious invite link detection |
| **Token Leak Detection** | Instantly detects and destroys leaked Discord bot tokens |
| **Alt Account Detection** | Heuristic analysis of account age, avatar, and spam flags |
| **Auto-Moderation** | Caps flood, emoji flood, mass-mention, file-scan triggers |
| **CAPTCHA Verification** | Role-gated join verification with timed challenges |
| **Surgical Lockdown** | Server-wide or role-specific channel lockdown with snapshots |
| **Advanced Logging** | Message edits/deletions, role changes, nicknames, invites |
| **Case System** | Persistent SQLite case tracking for all moderation actions |
| **Guild Backup** | Full JSON export of roles, channels, categories, and overwrites |
| **Threat Intelligence** | Optional VirusTotal URL reputation checking |
| **Escalating Security Levels** | NORMAL → ELEVATED → HIGH → CRITICAL → **DEADLY** |

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and insert your bot token and owner IDs
```

### 3. Run
```bash
python bot.py
```

---

## 🔒 Security Levels

| Level | Name | Behavior |
|-------|------|----------|
| 0 | NORMAL | Standard protection |
| 1 | ELEVATED | Stricter filters, enhanced logging |
| 2 | HIGH | Auto-mod active, verification enforced |
| 3 | CRITICAL | Server lockdown, manual approval |
| 4 | **DEADLY** | Zero tolerance — instant action on any threat |

---

## 🛠️ Command Reference

### Auto-Moderation
| Command | Permission | Description |
|---------|-----------|-------------|
| `!scan @user` | Manage Messages | Deep-scan a user's threat score and case history |
| `!raidoff` | Administrator | Disable raid lockdown and restore channels |

### Moderation
| Command | Permission | Description |
|---------|-----------|-------------|
| `!warn @user reason` | Manage Messages | Issue a warning |
| `!mute @user 10m reason` | Moderate Members | Temporarily mute a user |
| `!unmute @user` | Moderate Members | Remove mute role |
| `!kick @user reason` | Kick Members | Remove user from server |
| `!ban @user reason` | Ban Members | Permanently ban user |
| `!softban @user reason` | Ban Members | Ban + delete 24h messages, then unban |
| `!instaban @user reason` | Administrator | Zero-tolerance instant ban |
| `!cases @user` | Manage Messages | View user's case history |
| `!purge 50 @user` | Manage Messages | Bulk delete messages |
| `!slowmode 5` | Manage Channels | Set channel slowmode |

### Verification
| Command | Permission | Description |
|---------|-----------|-------------|
| `!verifysetup @role #channel` | Administrator | Configure CAPTCHA verification |
| `!verifyforce @user` | Administrator | Manually verify a member |

### Lockdown
| Command | Permission | Description |
|---------|-----------|-------------|
| `!lockdown #channel` | Administrator | Lock channel(s) for @everyone |
| `!unlock #channel` | Administrator | Restore from lockdown snapshot |
| `!lockrole @role` | Administrator | Mute a role server-wide |
| `!unlockrole @role` | Administrator | Unmute a role server-wide |

### Logging
| Command | Permission | Description |
|---------|-----------|-------------|
| `!setlog #channel` | Administrator | Set security event log channel |

### Backup
| Command | Permission | Description |
|---------|-----------|-------------|
| `!backup` | Administrator | Export guild structure to JSON |

### Owner
| Command | Permission | Description |
|---------|-----------|-------------|
| `!guard` | Anyone | Display bot status and security level |
| `!security 4` | Bot Owner | Set global security level (0-4) |
| `!blacklist 123456` | Bot Owner | Globally blacklist a user ID |
| `!whitelist 123456` | Bot Owner | Globally whitelist a user ID |
| `!reload automod` | Bot Owner | Hot-reload a cog |
| `!shutdown` | Bot Owner | Gracefully shut down the bot |

---

## 📁 Project Structure

```
DiscordSecurityBot/
├── bot.py                 # Main entry point
├── config.py              # Central configuration & security levels
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
├── README.md              # This file
├── data/                  # SQLite DB & logs
│   ├── security.db
│   └── bot.log
├── utils/
│   ├── database.py        # Async SQLite ORM
│   ├── security_checks.py # Threat detection engine
│   └── punishments.py     # Punishment executor
└── cogs/
    ├── automod.py         # Real-time auto-moderation
    ├── moderation.py      # Manual mod commands
    ├── verification.py    # CAPTCHA gate system
    ├── lockdown.py        # Lockdown & snapshots
    ├── logging.py         # Forensic audit logs
    ├── backup.py          # Guild backup & recovery
    └── owner.py           # Owner/admin diagnostics
```

---

## ⚠️ Permissions Required

Ensure your bot has these gateway intents enabled in the [Discord Developer Portal](https://discord.com/developers/applications):

- ✅ Presence Intent
- ✅ Server Members Intent
- ✅ Message Content Intent

**Bot Permissions:**
- Administrator *(recommended for full functionality)*
- Or individually: Ban Members, Kick Members, Manage Messages, Manage Channels, Manage Roles, Manage Nicknames, Moderate Members

---

## 🧠 Threat Scoring

APEX GUARD calculates a dynamic threat score (0–100) per user based on:
- Message velocity & repetition
- Phishing keywords & suspicious URLs
- Unauthorized invite links
- Caps / emoji flooding
- Mass mentions
- Dangerous file attachments
- Discord token leaks *(instant 100)*

Punishments auto-escalate from **Warn → Mute → Kick → Softban → Ban → INSTABAN**.

---

## 📜 License

This project is provided as-is for educational and security-hardening purposes. Use responsibly.

---

**Built with precision. Deployed with confidence.**
*APEX GUARD — Your server's last line of defense.*
