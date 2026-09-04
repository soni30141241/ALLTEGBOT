# Telegram Group Manager Bot

A Pyrogram-based Telegram group management bot with:

- Welcome messages
- Warning system
- Auto moderation
- Abuse filter
- Anti-spam/flood detection
- Optional anti-food keyword filter
- `/tagall` member mentions
- SQLite database
- Railway/Heroku-friendly worker setup

## Environment variables

Set:

- `API_ID`
- `API_HASH`
- `BOT_TOKEN`
- `DATABASE_PATH` (optional, default `bot.db`)

Never commit your real `.env` or bot token.

## Local run

```bash
pip install -r requirements.txt
python bot.py
```

## Telegram setup

1. Create a bot with BotFather and copy the token.
2. Get API ID/API HASH from my.telegram.org.
3. Add the bot to your group.
4. Make the bot an administrator with permission to delete messages and restrict users.
5. Members are saved when they send messages, so `/tagall` can mention known members.

## Commands

- `/help`
- `/tagall [message]`
- `/warn` (reply to a user)
- `/warnings`
- `/resetwarn` (admin, reply)
- `/setwarnlimit N`
- `/settings`

## Notes

The anti-food filter is disabled by default (`anti_food=0`). The keyword lists in `moderation.py` are intentionally simple and should be customized for your group.

This project uses SQLite for simplicity. For multiple workers or high traffic, use a proper shared database such as PostgreSQL and add migrations.
