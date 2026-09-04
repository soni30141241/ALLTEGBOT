# 🤖 Telegram Group Manager Bot

Ready-to-deploy Telegram group management bot using Pyrogram.

## Features

- 👋 Welcome message
- ⚠️ Warning system
- 🔇 Automatic mute after warning limit
- 🛡️ Abuse filter
- 🛑 Anti-spam / anti-flood
- 🍔 Optional food-word filter
- 📢 `/tagall` reads the current Telegram member list
- ⚙️ Group settings
- 💾 SQLite database
- 🚀 Railway deployment with Dockerfile
- 🔐 Secrets via environment variables

## Environment variables

Required:

```text
API_ID
API_HASH
BOT_TOKEN
```

Optional:

```text
DATABASE_PATH=bot.db
```

## Railway deployment

1. Upload this repository to GitHub.
2. In Railway, create a new service from the GitHub repository.
3. Railway will detect the `Dockerfile`.
4. Add `API_ID`, `API_HASH`, and `BOT_TOKEN` under Variables.
5. Deploy.
6. Add the bot to your Telegram group.
7. Give the bot administrator permissions, especially **Delete Messages** and **Restrict Members**.

Railway's current build system supports Python and Dockerfiles; using the included Dockerfile avoids relying on a specific `runtime.txt`/Mise Python download. See Railway's build configuration documentation for customization options.

## Commands

- `/start` — bot online/status message

```text
/help
/tagall [message] — Admin/Owner only
/cancel — stop running tagall (Admin/Owner only)
/warn
/warnings
/resetwarn
/setwarnlimit 3
/settings
```

`/warn` and `/resetwarn` should be used as a reply to the target user's message.

## Important

The bot can only tag members that Telegram exposes through `get_chat_members`. Make the bot an administrator in the group.

The abuse/food word lists in `moderation.py` are examples. Edit them to match your group's rules.

Do not commit real API credentials or bot tokens to GitHub.


## Reference / Credits
This project implements similar member-mention behavior to the TeLe TiPs PingAllBot project. See: https://github.com/teletips/PingAllBot-TeLeTiPs

The upstream project is licensed under AGPL-3.0. This bot is an independent implementation and does not copy its source code.


### Start buttons
The /start message includes Owner, Help, and Support buttons. Set `OWNER_USERNAME`, `SUPPORT_USERNAME`, and optionally `HELP_URL` in Railway Variables to make them open directly.
