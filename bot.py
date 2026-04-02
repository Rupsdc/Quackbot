import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timezone, timedelta
import pytz
import re

# ──────────────────────────────────────────────
#  Config
# ──────────────────────────────────────────────
TOKEN    = os.environ.get("DISCORD_TOKEN")
GUILD_ID = os.environ.get("GUILD_ID")       # Your server's ID — set this in Railway
DATA_FILE   = "data.json"
EMBED_COLOR = 0x5865F2  # Discord blurple


# ──────────────────────────────────────────────
#  Quack config
# ──────────────────────────────────────────────
QUACK_RESPONSES = [
    (40, "quack"),
    (25, "quack quack"),
    (12, "QUACK"),
    (8,  "quack quack QUACK!!"),
    (5,  "...quack?"),
    (4,  "QUACK QUACK QUACK QUACK QUACK"),
    (3,  "*aggressively quacks in your direction*"),
    (1,  "I AM THE DUCK. THE DUCK IS ME. WE ARE ONE. QUACK."),
    (1,  "🦆💥"),
    (1,  "no"),
]

def pick_quack():
    population = [resp for _, resp in QUACK_RESPONSES]
    weights    = [w    for w, _    in QUACK_RESPONSES]
    return random.choices(population, weights=weights, k=1)[0]


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
# Replace your bot setup and on_ready with this:

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    guild = discord.Object(id=int(GUILD_ID))
    
    # Add all commands to the guild tree explicitly
    for cmd in bot.tree.get_commands():
        bot.tree.add_command(cmd, guild=guild, override=True)
    
    synced = await bot.tree.sync(guild=guild)

    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"⚡ Synced {len(synced)} commands to guild {GUILD_ID}")
    for cmd in synced:
        print(f"   • /{cmd.name}")


# ──────────────────────────────────────────────
#  Quack listener
# ──────────────────────────────────────────────
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if "quack" in message.content.lower():
        await message.channel.send(pick_quack())

    await bot.process_commands(message)


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

        if interaction.user.id in gd["banned_users"]:
            await interaction.response.send_message(
                "❌ You have been banned from submitting confessions in this server.",
                ephemeral=True,
            )
            return

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

        gd["confession_count"] += 1
        confession_number = gd["confession_count"]
        save_data(data)

        embed = discord.Embed(
            title=f"💬 Confession #{confession_number}",
            description=self.confession.value,
            color=EMBED_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Submit your own with /confess")
        await channel.send(embed=embed)

        log_channel_id = gd.get("log_channel")
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                log_embed = discord.Embed(
                    title=f"📋 Confession #{confession_number} — Mod Log",
                    description=self.confession.value,
                    color=0xFF6B6B,
                    timestamp=datetime.now(timezone.utc),
                )
                log_embed.add_field(
                    name="Submitted by",
                    value=f"||{interaction.user.mention} (`{interaction.user}` | ID: `{interaction.user.id}`)||",
                    inline=False,
                )
                log_embed.set_footer(text="This log is only visible to moderators.")
                await log_channel.send(embed=log_embed)

        await interaction.response.send_message(
            f"✅ Your confession has been submitted anonymously as **Confession #{confession_number}**!",
            ephemeral=True,
        )


# ──────────────────────────────────────────────
#  Confession slash commands
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


@bot.tree.command(name="setlog", description="Set a private mod log channel for confession authors. (Admin only)")
@app_commands.describe(channel="The private mod channel for logs")
@app_commands.checks.has_permissions(administrator=True)
async def setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    data = load_data()
    gd = guild_data(data, interaction.guild_id)
    gd["log_channel"] = channel.id
    save_data(data)
    await interaction.response.send_message(
        f"✅ Mod log channel set to {channel.mention}.", ephemeral=True
    )


@bot.tree.command(name="removelog", description="Remove the mod log channel. (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def removelog(interaction: discord.Interaction):
    data = load_data()
    gd = guild_data(data, interaction.guild_id)
    gd["log_channel"] = None
    save_data(data)
    await interaction.response.send_message(
        "✅ Mod log channel removed.", ephemeral=True
    )


@bot.tree.command(name="confessban", description="Ban a user from submitting confessions. (Admin only)")
@app_commands.describe(user="The user to ban from confessing")
@app_commands.checks.has_permissions(administrator=True)
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


@bot.tree.command(name="confessunban", description="Unban a user from submitting confessions. (Admin only)")
@app_commands.describe(user="The user to unban")
@app_commands.checks.has_permissions(administrator=True)
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

    confession_channel = f"<#{gd['confession_channel']}>" if gd.get("confession_channel") else "Not set"
    log_channel        = f"<#{gd['log_channel']}>"        if gd.get("log_channel")        else "Not set"
    banned_count       = len(gd.get("banned_users", []))
    total              = gd.get("confession_count", 0)

    embed = discord.Embed(title="⚙️ Confession Bot — Server Config", color=EMBED_COLOR)
    embed.add_field(name="Confession Channel", value=confession_channel, inline=True)
    embed.add_field(name="Mod Log Channel",    value=log_channel,        inline=True)
    embed.add_field(name="Total Confessions",  value=str(total),         inline=True)
    embed.add_field(name="Banned Users",       value=str(banned_count),  inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ──────────────────────────────────────────────
#  Inactivity slash commands (Admin only)
# ──────────────────────────────────────────────

@bot.tree.command(
    name="lowest_activity",
    description="List the 10 members with the fewest messages in the last 30 days. (Admin only)"
)
@app_commands.checks.has_permissions(administrator=True)
async def lowest_activity(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)

    now               = datetime.now(timezone.utc)
    threshold_30_days = now - timedelta(days=30)
    threshold_7_days  = now - timedelta(days=7)

    eligible_members = [
        m for m in interaction.guild.members
        if not m.bot and (not m.joined_at or m.joined_at <= threshold_7_days)
    ]

    if not eligible_members:
        await interaction.followup.send("No eligible members found.", ephemeral=True)
        return

    message_counts = {m: 0 for m in eligible_members}

    for channel in interaction.guild.text_channels:
        if channel.permissions_for(interaction.guild.me).read_message_history:
            async for msg in channel.history(limit=None, after=threshold_30_days):
                if msg.author in message_counts:
                    message_counts[msg.author] += 1

    sorted_members = sorted(message_counts.items(), key=lambda x: x[1])
    lowest_10      = sorted_members[:10]

    embed = discord.Embed(
        title="📉 Lowest Activity — Last 30 Days",
        description="Members who joined more than 7 days ago, sorted by message count.",
        color=0xFF6B6B,
        timestamp=datetime.now(timezone.utc),
    )
    lines = "\n".join(
        f"`{rank}.` {member.display_name} — **{count}** messages"
        for rank, (member, count) in enumerate(lowest_10, start=1)
    )
    embed.add_field(name="Rankings", value=lines or "No data.", inline=False)
    embed.set_footer(text="Excludes bots and members who joined in the last 7 days.")

    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(
    name="send_invite",
    description="DM a permanent invite link to a member. (Admin only)"
)
@app_commands.describe(member="The member to send the invite to")
@app_commands.checks.has_permissions(administrator=True)
async def send_invite(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(ephemeral=True)
    try:
        invite = await interaction.guild.text_channels[0].create_invite(max_age=0, unique=True)
        await member.send(
            f"Hi {member.name}, you have been kicked due to inactivity, but here's a permanent invite "
            f"to rejoin **{interaction.guild.name}** if you still want to: {invite.url}"
        )
        await interaction.followup.send(
            f"✅ Invite sent to {member.display_name}.", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission to DM this member.", ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {e}", ephemeral=True)


@bot.tree.command(
    name="inactivity_kick",
    description="Send a member an invite then kick them after 10 seconds. (Admin only)"
)
@app_commands.describe(member="The member to invite-and-kick")
@app_commands.checks.has_permissions(administrator=True)
async def inactivity_kick(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(ephemeral=True)
    try:
        invite = await interaction.guild.text_channels[0].create_invite(max_age=0, unique=True)
        await member.send(
            f"Hi {member.name}, you have been kicked due to inactivity, but here's a permanent invite "
            f"to rejoin **{interaction.guild.name}** if you still want to: {invite.url}"
        )
        await interaction.followup.send(
            f"✅ Invite sent to {member.display_name}. Kicking in 10 seconds...",
            ephemeral=True,
        )
        await asyncio.sleep(10)
        await member.kick(reason="Inactivity kick.")
        await interaction.channel.send(
            f"👢 {member.display_name} has been kicked for inactivity."
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission to DM or kick this member.", ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {e}", ephemeral=True)


# ──────────────────────────────────────────────
#  Timezone slash commands
# ──────────────────────────────────────────────

@bot.tree.command(name="settimezone", description="Save your timezone so others can check your local time.")
@app_commands.describe(timezone="Your timezone (e.g. America/New_York, Europe/London, Asia/Tokyo)")
async def settimezone(interaction: discord.Interaction, timezone: str):
    if timezone not in pytz.all_timezones:
        matches = [tz for tz in pytz.all_timezones if timezone.lower() in tz.lower()][:5]
        hint = f"\nDid you mean: `{'`, `'.join(matches)}`?" if matches else ""
        await interaction.response.send_message(
            f"❌ `{timezone}` is not a valid timezone.{hint}\n"
            f"Find yours at <https:// />",
            ephemeral=True,
        )
        return

    data = load_data()
    gd = guild_data(data, interaction.guild_id)
    if "timezones" not in gd:
        gd["timezones"] = {}
    gd["timezones"][str(interaction.user.id)] = timezone
    save_data(data)

    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    await interaction.response.send_message(
        f"✅ Timezone set to **{timezone}**. Your current local time is **{now.strftime('%I:%M %p')}**.",
        ephemeral=True,
    )


@bot.tree.command(name="time", description="See what time it currently is for a member.")
@app_commands.describe(member="The member whose local time you want to see")
async def time_for_user(interaction: discord.Interaction, member: discord.Member):
    data = load_data()
    gd = guild_data(data, interaction.guild_id)
    timezones = gd.get("timezones", {})
    tz_str = timezones.get(str(member.id))

    if not tz_str:
        await interaction.response.send_message(
            f"❌ {member.display_name} hasn't set their timezone yet. They can use `/settimezone`.",
            ephemeral=True,
        )
        return

    tz = pytz.timezone(tz_str)
    now = datetime.now(tz)

    embed = discord.Embed(
        title=f"🕐 Local time for {member.display_name}",
        color=EMBED_COLOR,
    )
    embed.add_field(name="Time",     value=now.strftime("%I:%M %p"),     inline=True)
    embed.add_field(name="Date",     value=now.strftime("%A, %B %d %Y"), inline=True)
    embed.add_field(name="Timezone", value=f"`{tz_str}`",                inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)

    await interaction.response.send_message(embed=embed)


def parse_time(time_str: str):
    """Parse time strings like 3pm, 15:00, 3:30pm, 15:30 — returns (hour, minute) or raises ValueError."""
    time_str = time_str.strip().lower()

    m = re.fullmatch(r'(\d{1,2})(?::(\d{2}))?(am|pm)', time_str)
    if m:
        hour, minute, period = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if not (1 <= hour <= 12) or not (0 <= minute <= 59):
            raise ValueError("Invalid time")
        if period == "pm" and hour != 12:
            hour += 12
        if period == "am" and hour == 12:
            hour = 0
        return hour, minute

    m = re.fullmatch(r'(\d{1,2}):(\d{2})', time_str)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError("Invalid time")
        return hour, minute

    raise ValueError("Unrecognised format")


@bot.tree.command(name="timefor", description="Convert a time into every timezone members have registered.")
@app_commands.describe(
    time="The time to convert (e.g. 3pm, 15:00, 3:30pm)",
    timezone="The timezone this time is in (e.g. America/New_York)",
)
async def timefor(interaction: discord.Interaction, time: str, timezone: str):
    if timezone not in pytz.all_timezones:
        matches = [tz for tz in pytz.all_timezones if timezone.lower() in tz.lower()][:5]
        hint = f"\nDid you mean: `{'`, `'.join(matches)}`?" if matches else ""
        await interaction.response.send_message(
            f"❌ `{timezone}` is not a valid timezone.{hint}\n"
            f"Find yours at <https://kevinnovak.github.io/Time-Zone-Picker/>",
            ephemeral=True,
        )
        return

    try:
        hour, minute = parse_time(time)
        source_tz  = pytz.timezone(timezone)
        now_source = datetime.now(source_tz)
        source_dt  = source_tz.localize(
            now_source.replace(hour=hour, minute=minute, second=0, microsecond=0)
        )
    except ValueError:
        await interaction.response.send_message(
            "❌ Couldn't parse that time. Try formats like `3pm`, `15:00`, or `3:30pm`.",
            ephemeral=True,
        )
        return

    data = load_data()
    gd   = guild_data(data, interaction.guild_id)
    registered = gd.get("timezones", {})

    if not registered:
        await interaction.response.send_message(
            "❌ No members have registered their timezone yet. Use `/settimezone` first.",
            ephemeral=True,
        )
        return

    seen_tzs = {}
    for uid, tz_str in registered.items():
        if tz_str in seen_tzs:
            continue
        member = interaction.guild.get_member(int(uid))
        if not member:
            continue
        converted = source_dt.astimezone(pytz.timezone(tz_str))
        seen_tzs[tz_str] = (member.display_name, converted)

    if not seen_tzs:
        await interaction.response.send_message(
            "❌ No members with registered timezones found in this server.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title=f"🌍 Time Conversion — {source_dt.strftime('%I:%M %p')} {timezone}",
        color=EMBED_COLOR,
    )
    lines = []
    for tz_str, (display_name, converted) in sorted(seen_tzs.items(), key=lambda x: x[1][1].utcoffset()):
        lines.append(f"`{tz_str}` — **{converted.strftime('%I:%M %p')}** *(e.g. {display_name})*")

    embed.description = "\n".join(lines)
    embed.set_footer(text="Showing all unique timezones registered in this server.")

    await interaction.response.send_message(embed=embed)


# ──────────────────────────────────────────────
#  Global error handler
# ──────────────────────────────────────────────
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ You don't have permission to use this command."
    else:
        msg = f"❌ An error occurred: {error}"

    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


# ──────────────────────────────────────────────
#  Run
# ──────────────────────────────────────────────
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is not set!")
    if not GUILD_ID:
        raise ValueError("GUILD_ID environment variable is not set!")
    bot.run(TOKEN)
