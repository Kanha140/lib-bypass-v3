import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from aiohttp import web
import config
import database
from api_client import api
from ui_components import KeyPanelPersistentView, create_main_panel_embed

# ==============================================================================
# 24/7 KEEP-ALIVE HTTP SERVER (RENDER.COM COMPATIBILITY)
# ==============================================================================

async def handle_ping(request):
    bot_user_str = str(bot.user) if bot.user else "Starting..."
    return web.json_response({
        "status": "online",
        "bot": bot_user_str,
        "message": "LIB BYPASS Bot is running 24/7!"
    })

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    app.router.add_get("/healthz", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[*] 24/7 Web Server active on port {port} (Render compatible)", flush=True)

async def self_ping_loop():
    await bot.wait_until_ready()
    # Render sets RENDER_EXTERNAL_URL automatically (e.g. https://your-service.onrender.com)
    url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("KEEP_ALIVE_URL")
    if not url:
        print("[*] No RENDER_EXTERNAL_URL detected (Running locally).", flush=True)
        return

    print(f"[*] Starting 24/7 Anti-Sleep Keep-Alive loop for {url}", flush=True)
    while not bot.is_closed():
        await asyncio.sleep(600)  # Ping every 10 minutes (prevents 15m idle sleep)
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    print(f"[Keep-Alive] Self-ping status {resp.status}", flush=True)
        except Exception as e:
            print(f"[Keep-Alive] Warning: {e}", flush=True)

# Configure Intents (Standard intents - does not require privileged portal intents)
intents = discord.Intents.default()
intents.guilds = True

class LibBypassBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # Register persistent view so button interactions work after restart
        self.add_view(KeyPanelPersistentView())

        # Start 24/7 keep-alive web server for Render.com
        try:
            await start_web_server()
            self.loop.create_task(self_ping_loop())
        except Exception as e:
            print(f"[!] Web server start note: {e}", flush=True)

        # Sync only globally as single source of truth
        try:
            synced_global = await self.tree.sync()
            print(f"[*] Synced {len(synced_global)} slash commands globally.", flush=True)
        except Exception as e:
            print(f"[!] Global sync warning: {e}", flush=True)

    async def on_ready(self):
        # Clear any old duplicate guild-specific commands from all joined guilds
        for guild in self.guilds:
            try:
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                print(f"[*] Cleared duplicate guild commands for: {guild.name} ({guild.id})", flush=True)
            except Exception as e:
                print(f"[!] Guild command cleanup note: {e}", flush=True)

        print("==================================================", flush=True)
        print(f"[+] Bot logged in as: {self.user} (ID: {self.user.id})", flush=True)
        print(f"[+] Owner ID: {config.OWNER_ID}", flush=True)
        print(f"[+] Panel Channel ID: {config.PANEL_CHANNEL_ID}", flush=True)
        print(f"[+] Credit Pricing: {config.CREDIT_PRICING}", flush=True)
        print("==================================================", flush=True)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="LIB BYPASS • License Portal"
            )
        )


bot = LibBypassBot()


# Helper check: Owner or Admin
def is_admin_or_owner(interaction: discord.Interaction) -> bool:
    if database.is_owner(interaction.user.id):
        return True
    if interaction.user.guild_permissions.administrator:
        return True
    return False


# ==============================================================================
# SLASH COMMAND GROUPS
# ==============================================================================

# 1. /key [generate | delete | info | list]
key_group = app_commands.Group(name="key", description="License key generation and management")

@key_group.command(name="generate", description="Generate a new license key using credits")
@app_commands.describe(
    days="Select validity period for the key",
    username="Optional custom username/client label"
)
@app_commands.choices(days=[
    app_commands.Choice(name="1 Day (1 Credit)", value=1),
    app_commands.Choice(name="3 Days (3 Credits)", value=3),
    app_commands.Choice(name="7 Days (7 Credits)", value=7),
    app_commands.Choice(name="15 Days (14 Credits)", value=15),
    app_commands.Choice(name="30 Days (25 Credits)", value=30),
])
async def key_generate(interaction: discord.Interaction, days: app_commands.Choice[int], username: str = None):
    await interaction.response.defer(ephemeral=True)
    user_id = interaction.user.id
    selected_days = days.value
    cost = config.CREDIT_PRICING.get(selected_days, selected_days)

    if not database.is_reseller(user_id):
        embed = discord.Embed(
            title="❌ Access Restricted",
            description=f"You are not registered as an authorized reseller!\nPlease contact <@{config.RECHARGE_CONTACT_ID}> to purchase credits.",
            color=config.COLOR_DANGER
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    current_balance = database.get_credits(user_id)
    if not database.is_owner(user_id) and current_balance < cost:
        embed = discord.Embed(
            title="❌ Insufficient Credits",
            description=(
                f"Required: **{cost} Credits** for {selected_days} Days.\n"
                f"Your Balance: **{current_balance} Credits**.\n\n"
                f"Please contact <@{config.RECHARGE_CONTACT_ID}> to recharge."
            ),
            color=config.COLOR_WARNING
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    # Deduct credits
    if not database.deduct_credits(user_id, cost):
        embed = discord.Embed(
            title="❌ Error",
            description="Failed to deduct credits. Please check your balance.",
            color=config.COLOR_DANGER
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    # Call upstream API
    res = await api.create_key(username=username, days=selected_days)
    if not res.get("success"):
        database.refund_credits(user_id, cost)
        err = res.get("error", "Failed to generate key from cloud API.")
        embed = discord.Embed(
            title="❌ Generation Failed",
            description=f"Server returned error:\n```{err}```\nYour {cost} Credits have been refunded.",
            color=config.COLOR_DANGER
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    data = res.get("data", {})
    license_key = data.get("key") or data.get("licenseKey") or "N/A"
    final_username = data.get("username") or data.get("clientName") or (username if username else license_key)
    expires_at = data.get("expires_at", "N/A")
    rem_credits = database.get_credits(user_id)

    database.record_generated_key(
        user_id=user_id,
        license_key=license_key,
        username=final_username,
        days=selected_days,
        credits_spent=cost
    )

    # Attempt to DM the user the license key
    dm_sent = False
    try:
        dm_embed = discord.Embed(
            title="🛡️ LIB BYPASS — YOUR LICENSE KEY",
            description=(
                "Here is your newly generated license key details:\n\n"
                f"**🔑 License Key:**\n```\n{license_key}\n```\n"
                f"👤 **Username / Client:** `{final_username}`\n"
                f"⏳ **Duration:** `{selected_days} Days`\n"
                f"📅 **Expiry Date:** `{expires_at}`\n"
                f"💰 **Credits Deducted:** `{cost}`\n"
                f"💳 **Remaining Credits:** `{'Unlimited (Owner)' if database.is_owner(user_id) else f'{rem_credits} Credits'}`\n\n"
                "⚠️ *Please store this key securely. Do not share your private key.*"
            ),
            color=config.COLOR_PRIMARY
        )
        dm_embed.set_footer(text="LIB BYPASS • Automated 24/7 Delivery")
        await interaction.user.send(embed=dm_embed)
        dm_sent = True
    except Exception:
        dm_sent = False

    dm_status_text = "📩 **Direct Message:** Key sent to your DMs! ✅" if dm_sent else "⚠️ **Direct Message:** Could not DM (please enable DMs from server members)."

    embed = discord.Embed(
        title="🎉 License Key Generated Successfully!",
        description=(
            f"**🔑 License Key:**\n```\n{license_key}\n```\n"
            f"👤 **Username / Client:** `{final_username}`\n"
            f"⏳ **Duration:** `{selected_days} Days`\n"
            f"📅 **Expires At:** `{expires_at}`\n"
            f"💰 **Credits Deducted:** `{cost}`\n"
            f"💳 **Remaining Balance:** `{'Unlimited (Owner)' if database.is_owner(user_id) else f'{rem_credits} Credits'}`\n\n"
            f"{dm_status_text}"
        ),
        color=config.COLOR_SUCCESS
    )
    embed.set_footer(text="Keep your key private • LIB BYPASS 24/7")
    await interaction.followup.send(embed=embed, ephemeral=True)


@key_group.command(name="delete", description="Permanently delete / revoke a license key")
@app_commands.describe(key_or_username="Enter license key or assigned username to revoke")
async def key_delete(interaction: discord.Interaction, key_or_username: str):
    await interaction.response.defer(ephemeral=True)

    if not database.is_reseller(interaction.user.id):
        embed = discord.Embed(
            title="❌ Access Restricted",
            description=f"Only authorized resellers can delete keys. Contact <@{config.RECHARGE_CONTACT_ID}>.",
            color=config.COLOR_DANGER
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    res = await api.delete_key(key_or_username.strip())
    if res.get("success"):
        database.mark_key_deleted(key_or_username.strip())
        embed = discord.Embed(
            title="✅ License Key Revoked",
            description=f"Successfully deleted license key `{key_or_username}`.",
            color=config.COLOR_SUCCESS
        )
    else:
        err = res.get("error", "Key not found or deletion failed.")
        embed = discord.Embed(
            title="❌ Deletion Failed",
            description=f"Could not delete `{key_or_username}`:\n```{err}```",
            color=config.COLOR_DANGER
        )
    await interaction.followup.send(embed=embed, ephemeral=True)


@key_group.command(name="info", description="Get status, duration, and expiry details of a key")
@app_commands.describe(key_or_username="Enter license key or username")
async def key_info(interaction: discord.Interaction, key_or_username: str):
    await interaction.response.defer(ephemeral=True)

    if not database.is_reseller(interaction.user.id):
        embed = discord.Embed(
            title="❌ Access Restricted",
            description="Only authorized resellers can view key info.",
            color=config.COLOR_DANGER
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    res = await api.get_key_info(key_or_username.strip())
    if res.get("success"):
        data = res.get("data", {})
        embed = discord.Embed(
            title="ℹ️ License Key Information",
            description=(
                f"**🔑 Key:** `{data.get('key') or data.get('licenseKey') or key_or_username}`\n"
                f"👤 **Username:** `{data.get('username', 'N/A')}`\n"
                f"🎮 **Game:** `{data.get('gameType', 'FF')}`\n"
                f"⏳ **Duration:** `{data.get('duration_days', 'N/A')} Days`\n"
                f"📅 **Created At:** `{data.get('createdAt', data.get('created_at', 'N/A'))}`\n"
                f"⌛ **Expires At:** `{data.get('expires_at', 'N/A')}`\n"
                f"🔒 **HWID Bound:** `{'Yes' if data.get('hwid') else 'No (Unbound)'}`\n"
                f"🟢 **Status:** `{data.get('status', 'ACTIVE')}`"
            ),
            color=config.COLOR_INFO
        )
    else:
        err = res.get("error", "Key not found.")
        embed = discord.Embed(
            title="❌ Key Not Found",
            description=f"Could not find information for `{key_or_username}`:\n```{err}```",
            color=config.COLOR_DANGER
        )
    await interaction.followup.send(embed=embed, ephemeral=True)


bot.tree.add_command(key_group)


# 2. /reset [hwid]
reset_group = app_commands.Group(name="reset", description="Reset HWID binding commands")

@reset_group.command(name="hwid", description="Reset hardware ID (HWID) binding for a license key")
@app_commands.describe(key_or_username="Enter license key or username to unbind HWID")
async def reset_hwid(interaction: discord.Interaction, key_or_username: str):
    await interaction.response.defer(ephemeral=True)

    if not database.is_reseller(interaction.user.id):
        embed = discord.Embed(
            title="❌ Access Restricted",
            description=f"Only authorized resellers can reset HWID. Contact <@{config.RECHARGE_CONTACT_ID}>.",
            color=config.COLOR_DANGER
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    res = await api.reset_hwid(key_or_username.strip())
    if res.get("success"):
        embed = discord.Embed(
            title="✅ HWID Reset Successful",
            description=(
                f"Hardware ID for `{key_or_username}` has been reset successfully!\n"
                "The user can now login on their new device."
            ),
            color=config.COLOR_SUCCESS
        )
    else:
        err = res.get("error", "Reset failed or key not found.")
        embed = discord.Embed(
            title="❌ HWID Reset Failed",
            description=f"Could not reset HWID for `{key_or_username}`:\n```{err}```",
            color=config.COLOR_DANGER
        )
    await interaction.followup.send(embed=embed, ephemeral=True)

bot.tree.add_command(reset_group)


# 3. /reseller [add | remove | balance]
reseller_group = app_commands.Group(name="reseller", description="Admin commands to manage resellers and credits")

@reseller_group.command(name="add", description="[Admin] Add a new reseller and assign credits")
@app_commands.describe(
    user="The Discord user to register as a reseller",
    credits="Initial credit amount to grant (default: 0)"
)
async def reseller_add(interaction: discord.Interaction, user: discord.User, credits: int = 0):
    await interaction.response.defer(ephemeral=True)

    if not is_admin_or_owner(interaction):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only Bot Owner or Server Administrators can add resellers.",
            color=config.COLOR_DANGER
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    database.add_reseller(user.id, credits=credits, added_by=interaction.user.id)
    new_bal = database.get_credits(user.id)

    # Send welcome DM to the new reseller
    dm_sent = False
    try:
        dm_embed = discord.Embed(
            title="🎉 Welcome to LIB BYPASS Reseller Program!",
            description=(
                f"Hello {user.mention}! You have been registered as an authorized reseller by {interaction.user.mention}.\n\n"
                f"💰 **Credits Granted:** `{credits} Credits`\n"
                f"💳 **Total Balance:** `{new_bal} Credits`\n\n"
                "📌 **Quick Actions:**\n"
                "• Head over to the panel channel to generate keys.\n"
                "• Use the interactive buttons or `/key generate`.\n"
                "• Check your current balance anytime with `/balance`."
            ),
            color=config.COLOR_SUCCESS
        )
        dm_embed.set_footer(text="LIB BYPASS • Automated License Portal")
        await user.send(embed=dm_embed)
        dm_sent = True
    except Exception:
        dm_sent = False

    dm_note = "📩 **DM Status:** Reseller notified via DM! ✅" if dm_sent else "⚠️ **DM Status:** Could not DM (user DMs may be closed)."

    embed = discord.Embed(
        title="✅ Reseller Registered Successfully",
        description=(
            f"👤 **Reseller:** {user.mention} (`{user.id}`)\n"
            f"💰 **Credits Granted:** `{credits}`\n"
            f"💳 **Total Credit Balance:** `{new_bal} Credits`\n"
            f"👑 **Added By:** {interaction.user.mention}\n\n"
            f"{dm_note}"
        ),
        color=config.COLOR_SUCCESS
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


@reseller_group.command(name="remove", description="[Admin] Remove a reseller and revoke/delete all their keys")
@app_commands.describe(user="The Discord user to remove")
async def reseller_remove(interaction: discord.Interaction, user: discord.User):
    await interaction.response.defer(ephemeral=True)

    if not is_admin_or_owner(interaction):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only Bot Owner or Server Administrators can remove resellers.",
            color=config.COLOR_DANGER
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    if not database.is_reseller(user.id):
        embed = discord.Embed(
            title="⚠️ User Not Found",
            description=f"User {user.mention} was not found in the reseller database.",
            color=config.COLOR_WARNING
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    # 1. Fetch all active keys generated by this reseller
    user_keys = database.get_all_user_active_keys(user.id)
    deleted_keys_count = 0
    failed_keys = []

    # 2. Delete every key from Cloud API
    for k in user_keys:
        target_key = k.get("license_key") or k.get("username")
        if target_key:
            res = await api.delete_key(target_key)
            if res.get("success"):
                deleted_keys_count += 1
            else:
                failed_keys.append(target_key)

    # 3. Mark all keys as DELETED in local database
    database.delete_all_user_keys_db(user.id)

    # 4. Remove reseller record
    database.remove_reseller(user.id)

    # 5. Format response embed
    desc = (
        f"👤 **Reseller Removed:** {user.mention} (`{user.id}`)\n"
        f"🗑️ **Total Keys Revoked & Deleted:** `{deleted_keys_count}` / `{len(user_keys)}`\n"
        f"👑 **Action Taken By:** {interaction.user.mention}\n\n"
        "All license keys belonging to this reseller have been wiped from Cloud Sync."
    )
    if failed_keys:
        desc += f"\n⚠️ *Note: {len(failed_keys)} keys were already expired/removed on cloud.*"

    embed = discord.Embed(
        title="✅ Reseller Removed & All Keys Revoked",
        description=desc,
        color=config.COLOR_SUCCESS
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

bot.tree.add_command(reseller_group)


# 4. /credit add [user] [credits]
credit_group = app_commands.Group(name="credit", description="Credit management commands")

@credit_group.command(name="add", description="[Admin] Add extra credits to a reseller")
@app_commands.describe(
    user="The reseller to receive extra credits",
    credits="Number of credits to add"
)
async def credit_add(interaction: discord.Interaction, user: discord.User, credits: int):
    await interaction.response.defer(ephemeral=True)

    if not is_admin_or_owner(interaction):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only Bot Owner or Server Administrators can add credits.",
            color=config.COLOR_DANGER
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    if credits <= 0:
        embed = discord.Embed(
            title="❌ Invalid Amount",
            description="Credit amount must be greater than 0.",
            color=config.COLOR_WARNING
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    new_balance = database.add_credits(user.id, credits)

    # Send DM to user about credited balance
    dm_sent = False
    try:
        dm_embed = discord.Embed(
            title="💳 Credits Added to Your Account!",
            description=(
                f"Hello {user.mention}! Extra credits have been added to your reseller balance:\n\n"
                f"➕ **Credits Added:** `+{credits}`\n"
                f"💰 **New Total Balance:** `{new_balance} Credits`\n"
                f"👑 **Added By:** {interaction.user.mention}"
            ),
            color=config.COLOR_SUCCESS
        )
        dm_embed.set_footer(text="LIB BYPASS • Automated License Portal")
        await user.send(embed=dm_embed)
        dm_sent = True
    except Exception:
        dm_sent = False

    dm_note = "📩 **DM Status:** User notified via DM! ✅" if dm_sent else "⚠️ **DM Status:** Could not DM user."

    embed = discord.Embed(
        title="💳 Extra Credits Added Successfully",
        description=(
            f"👤 **Reseller:** {user.mention} (`{user.id}`)\n"
            f"➕ **Credits Added:** `+{credits}`\n"
            f"💰 **New Total Balance:** `{new_balance} Credits`\n\n"
            f"{dm_note}"
        ),
        color=config.COLOR_SUCCESS
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

bot.tree.add_command(credit_group)


# 5. /set channel panel
set_group = app_commands.Group(name="set", description="Setup and configuration commands")
channel_group = app_commands.Group(name="channel", description="Channel configuration", parent=set_group)

@channel_group.command(name="panel", description="Deploy the interactive Key Generation Panel into the channel")
@app_commands.describe(channel="Target channel to post panel (optional, defaults to configured panel channel or current)")
async def set_channel_panel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    await interaction.response.defer(ephemeral=True)

    if not is_admin_or_owner(interaction):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only Bot Owner or Server Administrators can deploy the panel.",
            color=config.COLOR_DANGER
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    target_channel = channel or bot.get_channel(config.PANEL_CHANNEL_ID) or interaction.channel
    if not isinstance(target_channel, discord.TextChannel):
        embed = discord.Embed(
            title="❌ Invalid Channel",
            description="Please specify a valid text channel.",
            color=config.COLOR_DANGER
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

    panel_embed = create_main_panel_embed()
    panel_view = KeyPanelPersistentView()

    try:
        await target_channel.send(embed=panel_embed, view=panel_view)
        embed = discord.Embed(
            title="✅ Panel Deployed Successfully!",
            description=f"The interactive key generation panel is now active in {target_channel.mention}.",
            color=config.COLOR_SUCCESS
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Deployment Failed",
            description=f"Could not send panel to {target_channel.mention}:\n```{str(e)}```",
            color=config.COLOR_DANGER
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

bot.tree.add_command(set_group)


# 6. Global Standalone Commands for convenience
@bot.tree.command(name="balance", description="Check your reseller credit balance and generation stats")
async def check_balance(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    user_id = interaction.user.id

    is_res = database.is_reseller(user_id)
    is_own = database.is_owner(user_id)
    credits = database.get_credits(user_id)
    user_keys = database.get_user_keys(user_id, limit=100)

    role_status = "👑 Server Owner (Unlimited)" if is_own else ("✅ Active Reseller" if is_res else "❌ Not a Reseller")

    embed = discord.Embed(
        title="💳 Reseller Account Balance",
        color=config.COLOR_PRIMARY
    )
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="Account Status", value=f"`{role_status}`", inline=True)
    embed.add_field(
        name="Available Credits",
        value=f"**{'∞ Unlimited' if is_own else f'{credits} Credits'}**",
        inline=True
    )
    embed.add_field(name="Keys Generated", value=f"**{len(user_keys)}**", inline=True)

    if is_own:
        profile_res = await api.get_profile()
        if profile_res.get("success"):
            pdata = profile_res.get("data", {})
            upstream_info = (
                f"• Upstream Account: `{pdata.get('username', 'N/A')}`\n"
                f"• Status: `{pdata.get('status', 'N/A')}`\n"
                f"• Remaining Quota: `{pdata.get('remainingQuota', 'N/A')}` / `{pdata.get('creditsLimit', 'N/A')}`\n"
                f"• Upstream Server Credits: `{pdata.get('upstreamServerCredits', 'N/A')}`"
            )
            embed.add_field(name="☁️ Upstream Cloud API Stats", value=upstream_info, inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)


if __name__ == "__main__":
    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("[!] ERROR: Please set your valid DISCORD_TOKEN in .env before running the bot.")
        print("[!] Example: DISCORD_TOKEN=MTA... in d:\\LIBBYPASSMAINBOT\\.env")
    else:
        bot.run(config.DISCORD_TOKEN)
