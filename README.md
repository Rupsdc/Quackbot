# 🤫 Confessions Bot

A self-hosted Discord confessions bot with anonymous submissions, mod logging, and ban tools.

---

## Features

| Command | Who | Description |
|---|---|---|
| `/confess` | Everyone | Opens a popup to submit an anonymous confession |
| `/setup #channel` | Admin | Sets the channel where confessions are posted |
| `/setlog #channel` | Admin | Sets a private mod log (shows who sent each confession) |
| `/removelog` | Admin | Removes the mod log |
| `/confessban @user` | Mod | Bans a user from confessing |
| `/confessunban @user` | Mod | Unbans a user |
| `/confessinfo` | Admin | Shows the bot's current config for this server |

---

## Setup

### 1. Create your Discord bot

1. Go to https://discord.com/developers/applications
2. Click **New Application** → give it a name
3. Go to **Bot** → click **Add Bot**
4. Under **Privileged Gateway Intents**, enable nothing extra (default intents are fine)
5. Copy your **Token** — you'll need this
6. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`
7. Use the generated URL to invite the bot to your server

### 2. Run locally

```bash
pip install -r requirements.txt
export DISCORD_TOKEN=your_token_here
python bot.py
```

### 3. Run on Oracle Cloud (free, 24/7)

1. Create a free Oracle Cloud account → spin up a free AMD VM (Ubuntu)
2. SSH in and run:
```bash
sudo apt update && sudo apt install python3-pip -y
pip3 install -r requirements.txt
pip3 install pm2   # or: sudo npm install -g pm2
export DISCORD_TOKEN=your_token_here
pm2 start bot.py --interpreter python3 --name confessions-bot
pm2 save
pm2 startup
```

The bot will now auto-restart on crashes and survive reboots.

### 4. Updating from GitHub

```bash
git pull
pm2 restart confessions-bot
```

---

## Data

All settings are saved in `data.json` in the same folder. Back this up if you ever migrate servers.
