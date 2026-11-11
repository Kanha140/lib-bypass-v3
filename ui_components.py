import discord
from discord.ui import View, Button, Select, Modal, TextInput
import config
import database
from api_client import api

def create_main_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ LIB BYPASS — KEY GENERATION PANEL",
        description=(
            "Welcome to the official **LIB BYPASS** automated license portal!\n\n"
            "Use the interactive buttons below to generate keys, check your balance, or reset HWID.\n\n"
            "📌 **Quick Actions:**\n"
            "🗝️ **Generate Key:** Select duration & generate instantly\n"
            "💳 **My Balance:** View your current credit balance\n"
            "🔄 **HWID Reset:** Reset hardware ID for your key\n"
            "📜 **My Keys:** View your previously generated keys\n"
            "🗑️ **Delete Key:** Delete a license key via API\n\n"
            f"👑 **Recharge Credits:** Contact <@{config.RECHARGE_CONTACT_ID}>\n"
            f"🏷️ **Client Role:** `{config.CLIENT_ROLE_NAME}`"
        ),
        color=config.COLOR_PRIMARY
    )
    embed.set_footer(text="LIB BYPASS • Automated 24/7 Delivery")
    # Glowing cyber lock icon thumbnail
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2092/2092663.png")
    return embed


# ==============================================================================
# MODALS
# ==============================================================================

class GenerateKeyModal(Modal, title="⚡ Generate License Key"):
    username_input = TextInput(
        label="Username / Client Name (Optional)",
        placeholder="e.g. VIP_PLAYER_01 (Leave empty for auto-generate)",
        required=False,
        max_length=64
    )

    def __init__(self, days: int, credits_needed: int):
        super().__init__()
        self.days = days
        self.credits_needed = credits_needed

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        custom_name = self.username_input.value.strip() or None

        # Check reseller status & credits
        if not database.is_reseller(user_id):
            embed = discord.Embed(
                title="❌ Access Denied",
                description=(
                    "You are not registered as an authorized reseller!\n"
                    f"Please contact <@{config.RECHARGE_CONTACT_ID}> to become a reseller or purchase credits."
                ),
                color=config.COLOR_DANGER
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)

        current_credits = database.get_credits(user_id)
        if not database.is_owner(user_id) and current_credits < self.credits_needed:
            embed = discord.Embed(
                title="❌ Insufficient Credits",
                description=(
                    f"You need **{self.credits_needed} Credits** to generate a **{self.days} Day** key.\n"
                    f"Your Current Balance: **{current_credits} Credits**.\n\n"
                    f"Please contact <@{config.RECHARGE_CONTACT_ID}> to recharge your credits."
                ),
                color=config.COLOR_WARNING
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)

        # Deduct credits first
        if not database.deduct_credits(user_id, self.credits_needed):
            embed = discord.Embed(
                title="❌ Transaction Failed",
                description="Unable to deduct credits. Please check your balance.",
                color=config.COLOR_DANGER
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)

        # Call API
        res = await api.create_key(username=custom_name, days=self.days)

        if not res.get("success"):
            # Refund credits if API call fails
            database.refund_credits(user_id, self.credits_needed)
            error_msg = res.get("error", "Unknown API error")
            embed = discord.Embed(
                title="❌ Key Generation Failed",
                description=f"Server returned an error:\n```{error_msg}```\nYour **{self.credits_needed} Credits** have been refunded.",
                color=config.COLOR_DANGER
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)

        # Success response
        data = res.get("data", {})
        license_key = data.get("key") or data.get("licenseKey") or "N/A"
        final_username = data.get("username") or data.get("clientName") or (custom_name if custom_name else license_key)
        expires_at = data.get("expires_at", "N/A")
        remaining_user_credits = database.get_credits(user_id)

        # Record in database
        database.record_generated_key(
            user_id=user_id,
            license_key=license_key,
            username=final_username,
            days=self.days,
            credits_spent=self.credits_needed
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
                    f"⏳ **Duration:** `{self.days} Days`\n"
                    f"📅 **Expiry Date:** `{expires_at}`\n"
                    f"💰 **Credits Deducted:** `{self.credits_needed}`\n"
                    f"💳 **Remaining Credits:** `{'Unlimited (Owner)' if database.is_owner(user_id) else f'{remaining_user_credits} Credits'}`\n\n"
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
                f"⏳ **Duration:** `{self.days} Days`\n"
                f"📅 **Expiry Date:** `{expires_at}`\n"
                f"💰 **Credits Deducted:** `{self.credits_needed}`\n"
                f"💳 **Remaining Balance:** `{'Unlimited (Owner)' if database.is_owner(user_id) else f'{remaining_user_credits} Credits'}`\n\n"
                f"{dm_status_text}"
            ),
            color=config.COLOR_SUCCESS
        )
        embed.set_footer(text="Keep your license key confidential • LIB BYPASS 24/7")

        await interaction.followup.send(embed=embed, ephemeral=True)


class HWIDResetModal(Modal, title="🔄 Reset HWID Binding"):
    key_input = TextInput(
        label="License Key or Username",
        placeholder="Enter license key or assigned username",
        required=True,
        max_length=128
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        target = self.key_input.value.strip()
        res = await api.reset_hwid(target)

        if res.get("success"):
            embed = discord.Embed(
                title="✅ HWID Reset Successful",
                description=(
                    f"Successfully reset HWID for:\n`{target}`\n\n"
                    "The license key can now be bound to a new device."
                ),
                color=config.COLOR_SUCCESS
            )
        else:
            err = res.get("error", "Key not found or reset failed.")
            embed = discord.Embed(
                title="❌ HWID Reset Failed",
                description=f"Could not reset HWID for `{target}`:\n```{err}```",
                color=config.COLOR_DANGER
            )
        await interaction.followup.send(embed=embed, ephemeral=True)


class DeleteKeyModal(Modal, title="🗑️ Delete / Revoke License"):
    key_input = TextInput(
        label="License Key or Username to Revoke",
        placeholder="Enter license key or assigned username",
        required=True,
        max_length=128
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        target = self.key_input.value.strip()
        res = await api.delete_key(target)

        if res.get("success"):
            database.mark_key_deleted(target)
            embed = discord.Embed(
                title="✅ Key Revoked & Deleted",
                description=f"License key `{target}` has been permanently revoked from cloud API.",
                color=config.COLOR_SUCCESS
            )
        else:
            err = res.get("error", "Key not found or delete failed.")
            embed = discord.Embed(
                title="❌ Key Deletion Failed",
                description=f"Could not delete `{target}`:\n```{err}```",
                color=config.COLOR_DANGER
            )
        await interaction.followup.send(embed=embed, ephemeral=True)


# ==============================================================================
# KEY GENERATION SELECT VIEW (Image 2)
# ==============================================================================

class DurationSelect(Select):
    def __init__(self):
        options = []
        for plan in config.PLAN_OPTIONS:
            options.append(discord.SelectOption(
                label=plan["label"],
                value=str(plan["value"]),
                description=plan["description"],
                emoji="⚡"
            ))

        super().__init__(
            placeholder="Select key duration / plan...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="select_duration_dropdown"
        )

    async def callback(self, interaction: discord.Interaction):
        days = int(self.values[0])
        cost = config.CREDIT_PRICING.get(days, days)
        # Open the modal to ask for optional username
        await interaction.response.send_modal(GenerateKeyModal(days=days, credits_needed=cost))


class DurationSelectView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(DurationSelect())


# ==============================================================================
# MAIN PERSISTENT PANEL VIEW (Image 1)
# ==============================================================================

class KeyPanelPersistentView(View):
    def __init__(self):
        super().__init__(timeout=None)  # None makes it persistent across bot restarts

    @discord.ui.button(
        label="Generate Key",
        emoji="🔑",
        style=discord.ButtonStyle.primary,
        custom_id="btn_panel_generate_key"
    )
    async def generate_key_btn(self, interaction: discord.Interaction, button: Button):
        # Check reseller permission upfront
        if not database.is_reseller(interaction.user.id):
            embed = discord.Embed(
                title="❌ Access Restricted",
                description=(
                    "You are not registered as an authorized reseller!\n\n"
                    f"👑 Please contact <@{config.RECHARGE_CONTACT_ID}> to purchase credits or obtain reseller access."
                ),
                color=config.COLOR_DANGER
            )
            if interaction.response.is_done():
                return await interaction.followup.send(embed=embed, ephemeral=True)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(
            title="⚡ Select Key Duration",
            description="Choose the duration of the key you wish to create from the dropdown below:",
            color=config.COLOR_INFO
        )
        if interaction.response.is_done():
            await interaction.followup.send(
                embed=embed,
                view=DurationSelectView(),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=embed,
                view=DurationSelectView(),
                ephemeral=True
            )

    @discord.ui.button(
        label="My Balance",
        emoji="💳",
        style=discord.ButtonStyle.secondary,
        custom_id="btn_panel_my_balance"
    )
    async def my_balance_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        is_res = database.is_reseller(user_id)
        is_own = database.is_owner(user_id)
        credits = database.get_credits(user_id)

        user_keys = database.get_user_keys(user_id, limit=100)
        total_created = len(user_keys)

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
        embed.add_field(name="Keys Generated", value=f"**{total_created}**", inline=True)

        # If owner, also show API upstream statistics
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

        embed.set_footer(text=f"Recharge contact: @{config.RECHARGE_CONTACT_ID}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="HWID Reset",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="btn_panel_hwid_reset"
    )
    async def hwid_reset_btn(self, interaction: discord.Interaction, button: Button):
        if not database.is_reseller(interaction.user.id):
            embed = discord.Embed(
                title="❌ Access Restricted",
                description=f"Only authorized resellers can reset HWID. Contact <@{config.RECHARGE_CONTACT_ID}>.",
                color=config.COLOR_DANGER
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_modal(HWIDResetModal())

    @discord.ui.button(
        label="My Keys",
        emoji="📜",
        style=discord.ButtonStyle.secondary,
        custom_id="btn_panel_my_keys"
    )
    async def my_keys_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        keys = database.get_user_keys(user_id, limit=8)
        if not keys:
            embed = discord.Embed(
                title="📜 My Generated Keys",
                description="You haven't generated any keys yet via this bot.",
                color=config.COLOR_WARNING
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)

        embed = discord.Embed(
            title=f"📜 Generated Keys ({len(keys)} most recent)",
            color=config.COLOR_PRIMARY
        )

        for k in keys:
            st = "🟢 " if k["status"] == "ACTIVE" else "🔴 "
            embed.add_field(
                name=f"{st} `{k['username'] or k['license_key'][:15] + '...'}`",
                value=(
                    f"**Key:** `{k['license_key']}`\n"
                    f"**Plan:** {k['days']} Days | **Cost:** {k['credits_spent']} Credits\n"
                    f"**Date:** {k['created_at']}"
                ),
                inline=False
            )

        embed.set_footer(text="Showing recent keys from local registry")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Delete Key",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="btn_panel_delete_key"
    )
    async def delete_key_btn(self, interaction: discord.Interaction, button: Button):
        if not database.is_reseller(interaction.user.id):
            embed = discord.Embed(
                title="❌ Access Restricted",
                description=f"Only authorized resellers can delete keys. Contact <@{config.RECHARGE_CONTACT_ID}>.",
                color=config.COLOR_DANGER
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_modal(DeleteKeyModal())
