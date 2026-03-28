# Confessions Bot

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

All settings are saved in `data.json` in the same folder. Back this up if you ever migrate servers.
