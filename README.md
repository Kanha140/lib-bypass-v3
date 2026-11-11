# 🛡️ LIB BYPASS — Automated Discord Reseller & License Bot

A complete, high-performance Discord Bot built with `discord.py` that connects directly to the Cloud License API (`https://br-lib-bypass-resselers.vercel.app/api/v1`) with full support for interactive UI buttons, duration selection dropdowns, modals, and credit balance management.

---

## ⚡ Features & Features Matrix

### 🔘 Interactive Control Panel (Buttons & Modals)
- **🔑 Generate Key**: Opens ephemeral duration dropdown (`1 Day`, `3 Days`, `7 Days`, `15 Days`, `30 Days`), then opens a modal for custom username (optional) and generates key.
- **💳 My Balance**: Checks available reseller credit balance and generated key count. (Bot Owner sees full upstream Cloud API quota and balance).
- **🔄 HWID Reset**: Opens an interactive modal to instantly reset hardware ID binding for any key or username.
- **📜 My Keys**: Lists all generated license keys with creation dates, duration, and status.
- **🗑️ Delete Key**: Opens a modal to revoke/delete a key from the cloud API.

### 💰 Credit Pricing Structure
| Duration | Credit Cost |
| :--- | :--- |
| **1 Day** | **1 Credit** |
| **3 Days** | **3 Credits** |
| **7 Days** | **7 Credits** |
| **15 Days** | **14 Credits** |
| **30 Days** | **25 Credits** |

---

## 💻 Slash Commands

| Command | Usage | Description |
| :--- | :--- | :--- |
| `/set channel panel [channel]` | Owner / Admin | Deploys the persistent interactive Key Generation Panel into the channel. |
| `/key generate [days] [username]` | Reseller / Owner | Generates a license key with chosen days and optional username. |
| `/key delete [key_or_username]` | Reseller / Owner | Revokes and permanently deletes a license key. |
| `/key info [key_or_username]` | Reseller / Owner | Checks expiry, status, and HWID binding of a key. |
| `/reset hwid [key_or_username]` | Reseller / Owner | Resets the HWID binding for a license key. |
| `/reseller add [user] [credits]` | Owner / Admin | Registers a user as a reseller and grants initial credits. |
| `/reseller remove [user]` | Owner / Admin | Removes reseller permissions from a user. |
| `/extra credit_add [user] [credits]` | Owner / Admin | Adds extra credits to an existing reseller. |
| `/credit add [user] [credits]` | Owner / Admin | Shortcut alias to add credits to any reseller. |
| `/balance` | Everyone | View your current credit balance and stats. |

---

## ⚙️ Setup & Configuration

### 1. Configure `.env`
Open [`.env`](file:///d:/LIBBYPASSMAINBOT/.env) and fill in your Discord Bot Token:
```env
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
API_KEY=AK-FF-9EA4-29B4-9BCC-62C3
API_BASE_URL=https://br-lib-bypass-resselers.vercel.app/api/v1
OWNER_ID=1517167262421749791
PANEL_CHANNEL_ID=1569384490365624482
GUILD_ID=1526068642372915373
RECHARGE_CONTACT_ID=1567775510065324165
CLIENT_ROLE_NAME=Bypass Lib All FF
```

### 2. Enable Discord Bot Privileged Intents
In the [Discord Developer Portal](https://discord.com/developers/applications):
1. Navigate to **Bot** tab.
2. Enable:
   - **Server Members Intent** (ON)
   - **Message Content Intent** (ON)

### 3. Start the Bot
Run the bot using:
```powershell
python main.py
```
Or double click [`run.bat`](file:///d:/LIBBYPASSMAINBOT/run.bat).

### 4. Deploy the Panel
In Discord, execute:
```
/set channel panel
```
The panel with all interactive buttons will be posted!
