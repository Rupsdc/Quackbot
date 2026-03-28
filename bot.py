import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime

# ──────────────────────────────────────────────
#  Config
# ──────────────────────────────────────────────
TOKEN = os.environ.get("DISCORD_TOKEN")   # Set this as an environment variable
DATA_FILE = "data.json"
EMBED_COLOR = 0x5865F2                     # Discord blurple


# ──────────────────────────────────────────────
#  Data helpers
# ──────────────────────────────────────────────
def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def guild_data(data: dict, guild_id: int) -> dict:
    """Return (and lazily create) the config block for a guild."""
    key = str(guild_id)
    if key not in data:
        data[key] = {
            "confession_channel": None,
            "log_channel": None,
            "banned_users": [],
            "confession_count": 0,
        }
    return data[key]


# ──────────────────────────────────────────────
#  Bot setup
# ──────────────────────────────────────────────
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("Slash commands synced.")


# ──────────────────────────────────────────────
#  Modal — shown to the user when they /confess
# ──────────────────────────────────────────────
class ConfessionModal(discord.ui.Modal, title="Submit a Confession"):
    confession = discord.ui.TextInput(
        label="Your confession",
        style=discord.TextStyle.paragraph,
        placeholder="Type your anonymous confession here...",
        min_length=1,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        gd = guild_data(data, interaction.guild_id)

        # Check ban
        if interaction.user.id in gd["banned_users"]:
            await interaction.response.send_message(
                "❌ You have been banned from submitting confessions in this server.",
                ephemeral=True,
            )
            return

        # Check channel configured
        channel_id = gd.get("confession_channel")
        if not channel_id:
            await interaction.response.send_message(
                "❌ No confession channel has been set up yet. Ask an admin to run `/setup`.",
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message(
                "❌ The confession channel no longer exists. Ask an admin to run `/setup` again.",
                ephemeral=True,
            )
            return

        # Increment counter
        gd["confession_count"] += 1
        confession_number = gd["confession_count"]
        save_data(data)

        # Build public embed
        embed = discord.Embed(
            title=f"💬 Confession #{confession_number}",
            description=self.confession.value,
            color=EMBED_COLOR,
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text="Submit your own with /confess")

        await channel.send(embed=embed)

        # Log embed (shows who sent it — mods only)
        log_channel_id = gd.get("log_channel")
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                log_embed = discord.Embed(
                    title=f"📋 Confession #{confession_number} — Mod Log",
                    description=self.confession.value,
                    color=0xFF6B6B,
                    timestamp=datetime.utcnow(),
                )
                log_embed.add_field(
                    name="Submitted by",
                    value=f"{interaction.user.mention} (`{interaction.user}` | ID: `{interaction.user.id}`)",
                    inline=False,
                )
                log_embed.set_footer(text="This log is only visible to moderators.")
                await log_channel.send(embed=log_embed)

        await interaction.response.send_message(
            f"✅ Your confession has been submitted anonymously as **Confession #{confession_number}**!",
            ephemeral=True,
        )


# ──────────────────────────────────────────────
#  Slash Commands
# ──────────────────────────────────────────────

@bot.tree.command(name="confess", description="Submit an anonymous confession.")
async def confess(interaction: discord.Interaction):
    data = load_data()
    gd = guild_data(data, interaction.guild_id)

    if interaction.user.id in gd["banned_users"]:
        await interaction.response.send_message(
            "❌ You have been banned from submitting confessions in this server.",
            ephemeral=True,
        )
        return

    if not gd.get("confession_channel"):
        await interaction.response.send_message(
            "❌ No confession channel has been set up yet. Ask an admin to run `/setup`.",
            ephemeral=True,
        )
        return

    await interaction.response.send_modal(ConfessionModal())


@bot.tree.command(name="setup", description="Set the channel where confessions will be posted. (Admin only)")
@app_commands.describe(channel="The channel to post confessions in")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, channel: discord.TextChannel):
    data = load_data()
    gd = guild_data(data, interaction.guild_id)
    gd["confession_channel"] = channel.id
    save_data(data)
    await interaction.response.send_message(
        f"✅ Confession channel set to {channel.mention}.", ephemeral=True
    )


@bot.tree.command(name="setlog", description="Set a private mod log channel that shows who submitted each confession. (Admin only)")
@app_commands.describe(channel="The private mod channel for logs")
@app_commands.checks.has_permissions(administrator=True)
async def setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    data = load_data()
    gd = guild_data(data, interaction.guild_id)
    gd["log_channel"] = channel.id
    save_data(data)
    await interaction.response.send_message(
        f"✅ Mod log channel set to {channel.mention}. Confession authors will be logged there.",
        ephemeral=True,
    )


@bot.tree.command(name="removelog", description="Remove the mod log channel. (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def removelog(interaction: discord.Interaction):
    data = load_data()
    gd = guild_data(data, interaction.guild_id)
    gd["log_channel"] = None
    save_data(data)
    await interaction.response.send_message(
        "✅ Mod log channel removed. Confessions will no longer be logged.", ephemeral=True
    )


@bot.tree.command(name="confessban", description="Ban a user from submitting confessions. (Mod only)")
@app_commands.describe(user="The user to ban from confessing")
@app_commands.checks.has_permissions(manage_messages=True)
async def confessban(interaction: discord.Interaction, user: discord.Member):
    data = load_data()
    gd = guild_data(data, interaction.guild_id)

    if user.id in gd["banned_users"]:
        await interaction.response.send_message(
            f"⚠️ {user.mention} is already banned from confessing.", ephemeral=True
        )
        return

    gd["banned_users"].append(user.id)
    save_data(data)
    await interaction.response.send_message(
        f"✅ {user.mention} has been banned from submitting confessions.", ephemeral=True
    )


@bot.tree.command(name="confessunban", description="Unban a user from submitting confessions. (Mod only)")
@app_commands.describe(user="The user to unban")
@app_commands.checks.has_permissions(manage_messages=True)
async def confessunban(interaction: discord.Interaction, user: discord.Member):
    data = load_data()
    gd = guild_data(data, interaction.guild_id)

    if user.id not in gd["banned_users"]:
        await interaction.response.send_message(
            f"⚠️ {user.mention} is not banned from confessing.", ephemeral=True
        )
        return

    gd["banned_users"].remove(user.id)
    save_data(data)
    await interaction.response.send_message(
        f"✅ {user.mention} has been unbanned and can confess again.", ephemeral=True
    )


@bot.tree.command(name="confessinfo", description="Show the current confession setup for this server. (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def confessinfo(interaction: discord.Interaction):
    data = load_data()
    gd = guild_data(data, interaction.guild_id)

    confession_channel = (
        f"<#{gd['confession_channel']}>" if gd.get("confession_channel") else "Not set"
    )
    log_channel = (
        f"<#{gd['log_channel']}>" if gd.get("log_channel") else "Not set"
    )
    banned_count = len(gd.get("banned_users", []))
    total = gd.get("confession_count", 0)

    embed = discord.Embed(title="⚙️ Confession Bot — Server Config", color=EMBED_COLOR)
    embed.add_field(name="Confession Channel", value=confession_channel, inline=True)
    embed.add_field(name="Mod Log Channel", value=log_channel, inline=True)
    embed.add_field(name="Total Confessions", value=str(total), inline=True)
    embed.add_field(name="Banned Users", value=str(banned_count), inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ──────────────────────────────────────────────
#  Error handling
# ──────────────────────────────────────────────
@setup.error
@setlog.error
@removelog.error
@confessban.error
@confessunban.error
@confessinfo.error
async def permission_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ An error occurred: {error}", ephemeral=True
        )


# ──────────────────────────────────────────────
#  Run
# ──────────────────────────────────────────────
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is not set!")
    bot.run(TOKEN)
