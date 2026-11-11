import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot Credentials
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

# Upstream API Configuration
API_KEY = os.getenv("API_KEY", "AK-FF-300D-7842-11C7-7FDE")
API_BASE_URL = os.getenv("API_BASE_URL", "https://br-lib-bypass-resselers.vercel.app/api/v1").rstrip("/")

# Discord Server / Guild & Channel IDs
raw_owner_ids = os.getenv("OWNER_IDS") or os.getenv("OWNER_ID") or "1551003408226459693,1378068938847424522,1559978348103471275"
OWNER_IDS = [int(x.strip()) for x in str(raw_owner_ids).split(",") if x.strip()]
OWNER_ID = int(os.getenv("OWNER_ID", "1551003408226459693"))
PANEL_CHANNEL_ID = int(os.getenv("PANEL_CHANNEL_ID", "1570102018519990443"))
GUILD_ID = int(os.getenv("GUILD_ID", "1559978348103471275"))
RECHARGE_CONTACT_ID = os.getenv("RECHARGE_CONTACT_ID", "1551003408226459693")
CLIENT_ROLE_NAME = os.getenv("CLIENT_ROLE_NAME", "LIB V2")

# Credit Pricing Matrix
# Duration (Days) -> Required Credits
CREDIT_PRICING = {
    1: 1,
    3: 3,
    7: 7,
    15: 14,
    30: 25,
}

# Plan Labels for Dropdown & UI
PLAN_OPTIONS = [
    {"label": "1 Day", "value": 1, "credits": 1, "description": "1 Day Validity • 1 Credit"},
    {"label": "3 Days", "value": 3, "credits": 3, "description": "3 Days Validity • 3 Credits"},
    {"label": "7 Days", "value": 7, "credits": 7, "description": "7 Days Validity • 7 Credits"},
    {"label": "15 Days", "value": 15, "credits": 14, "description": "15 Days Validity • 14 Credits"},
    {"label": "30 Days", "value": 30, "credits": 25, "description": "30 Days Validity • 25 Credits"},
]

# Embed Colors
COLOR_PRIMARY = 0x00A8FF   # Vivid Electric Blue / Cyan
COLOR_SUCCESS = 0x00FF88   # Emerald Green
COLOR_WARNING = 0xFFA500   # Amber / Orange
COLOR_DANGER = 0xFF3366    # Neon Red
COLOR_INFO = 0x5865F2      # Discord Blurple
