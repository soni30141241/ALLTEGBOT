import os
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import RPCError
from pyrogram import idle
from pyrogram.types import BotCommand
from pyrogram.enums import ChatMemberStatus
from database import Database
from moderation import Moderation

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot.db")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "").strip().lstrip("@")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").strip().lstrip("@")
HELP_URL = os.getenv("HELP_URL", "").strip()

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise RuntimeError("Missing API_ID, API_HASH or BOT_TOKEN environment variables.")

app = Client(
    "group_manager_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

db = Database(DATABASE_PATH)
mod = Moderation(db)
active_tags = set()


async def is_admin(client, chat_id, user_id=None, message=None):
    """Robust admin/owner check, including anonymous admins."""
    if message is not None and getattr(message, "sender_chat", None):
        if message.sender_chat.id == chat_id:
            return True

    if not user_id:
        return False

    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return True
        # Pyrogram versions / Telegram responses may expose string statuses.
        status = str(member.status).lower()
        return status in ("administrator", "creator", "owner")
    except RPCError:
        return False


@app.on_message(filters.new_chat_members)
async def welcome(client, message):
    for user in message.new_chat_members:
        if user.is_bot:
            continue
        await message.reply_text(
            f"👋 Welcome {user.mention} to **{message.chat.title}**!\n"
            "📜 Please read the group rules and enjoy your stay."
        )


def start_keyboard():
    owner_btn = (InlineKeyboardButton("👑 Owner", url=f"https://t.me/{OWNER_USERNAME}")
                 if OWNER_USERNAME else
                 InlineKeyboardButton("👑 Owner", callback_data="owner_info"))
    support_btn = (InlineKeyboardButton("🛟 Support", url=f"https://t.me/{SUPPORT_USERNAME}")
                   if SUPPORT_USERNAME else
                   InlineKeyboardButton("🛟 Support", callback_data="support_info"))
    help_btn = (InlineKeyboardButton("📚 Help", url=HELP_URL)
                if HELP_URL.startswith("http") else
                InlineKeyboardButton("📚 Help", callback_data="help_info"))
    return InlineKeyboardMarkup([[owner_btn, help_btn], [support_btn]])


@app.on_message(filters.command("start", prefixes="/") & (filters.private | filters.group))
async def start_cmd(client, message):
    await message.reply_text(
        "🤖 **WAFA MENTION BOT is Online!**\n\n"
        "👋 Welcome! I can manage your Telegram group.\n\n"
        "🛡️ **Features**\n"
        "• 👋 Welcome messages\n"
        "• ⚠️ Warning system\n"
        "• 🛡️ Abuse protection\n"
        "• 🛑 Anti-spam / anti-flood\n"
        "• 🍔 Optional anti-food filter\n"
        "• 📢 Admin/Owner tagall\n"
        "• 🛑 Cancel running tagall\n\n"
        "📚 Use /help for commands.",
        reply_markup=start_keyboard()
    )


@app.on_callback_query(filters.regex("^(owner_info|support_info|help_info)$"))
async def info_buttons(client, query: CallbackQuery):
    data = query.data
    if data == "owner_info":
        text = (f"👑 **Owner:** @{OWNER_USERNAME}" if OWNER_USERNAME else
                "👑 **Owner button is ready.**\nSet `OWNER_USERNAME` in Railway Variables to add the owner's Telegram link.")
    elif data == "support_info":
        text = (f"🛟 **Support:** @{SUPPORT_USERNAME}" if SUPPORT_USERNAME else
                "🛟 **Support button is ready.**\nSet `SUPPORT_USERNAME` in Railway Variables to add the support Telegram link.")
    else:
        text = ("📚 **Help**\n\n"
                "/tagall, /ping, /all — tag members (Admin/Owner)\n"
                "/cancel, /stop — cancel tagall\n"
                "/warn — warn a replied user\n"
                "/warnings — check warnings\n"
                "/resetwarn — reset warnings\n"
                "/setwarnlimit N — set warning limit\n"
                "/settings — show settings")
    await query.answer()
    await query.message.reply_text(text, disable_web_page_preview=True)


@app.on_message(filters.command("help", prefixes="/") & (filters.private | filters.group))
async def help_cmd(client, message):
    await message.reply_text(
        "🤖 **Group Manager Bot**\n\n"
        "📢 /tagall, /ping, /all [message] — tag group members\n"
        "🛑 /cancel, /stop — cancel running tagall\n"
        "⚠️ /warn — warn replied user\n"
        "📋 /warnings — check warnings\n"
        "♻️ /resetwarn — reset replied user's warnings\n"
        "🔢 /setwarnlimit N — set warning limit\n"
        "⚙️ /settings — show settings\n\n"
        "🛡️ Auto moderation: abuse + anti-spam/flood\n"
        "🍔 Optional food-word filter is available in moderation.py"
    )


@app.on_message(filters.command("warn") & filters.group)
async def warn(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admins only.")
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return await message.reply_text("Reply to a user's message with /warn [reason].")

    user = message.reply_to_message.from_user
    reason = message.text.split(None, 1)[1] if len(message.command) > 1 else "Manual warning"
    count = db.add_warn(message.chat.id, user.id, reason)
    limit = db.get_settings(message.chat.id)["warn_limit"]

    await message.reply_text(
        f"⚠️ {user.mention} warned: **{count}/{limit}**\nReason: {reason}"
    )

    if count >= limit:
        try:
            await client.restrict_chat_member(
                message.chat.id,
                user.id,
                permissions=ChatPermissions(can_send_messages=False),
            )
            await message.reply_text(f"🔇 {user.mention} has been muted.")
        except RPCError:
            await message.reply_text("⚠️ I could not mute the user. Check my admin permissions.")


@app.on_message(filters.command("warnings") & filters.group)
async def warnings(client, message):
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    else:
        target = message.from_user
    count = db.warn_count(message.chat.id, target.id)
    await message.reply_text(f"⚠️ {target.mention} has **{count}** warning(s).")


@app.on_message(filters.command("resetwarn") & filters.group)
async def resetwarn(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admins only.")
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return await message.reply_text("Reply to a user's message with /resetwarn.")

    user = message.reply_to_message.from_user
    db.reset_warns(message.chat.id, user.id)
    await message.reply_text(f"✅ Warnings reset for {user.mention}.")


@app.on_message(filters.command("setwarnlimit") & filters.group)
async def setwarnlimit(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admins only.")
    if len(message.command) != 2 or not message.command[1].isdigit():
        return await message.reply_text("Usage: /setwarnlimit 3")

    limit = max(1, min(20, int(message.command[1])))
    db.set_warn_limit(message.chat.id, limit)
    await message.reply_text(f"✅ Warning limit set to **{limit}**.")


@app.on_message(filters.command("settings") & filters.group)
async def settings(client, message):
    s = db.get_settings(message.chat.id)
    await message.reply_text(
        "⚙️ **Group settings**\n"
        f"Anti-spam/flood: {'ON' if s['anti_spam'] else 'OFF'}\n"
        f"Abuse filter: {'ON' if s['abuse_filter'] else 'OFF'}\n"
        f"Food filter: {'ON' if s['anti_food'] else 'OFF'}\n"
        f"Warn limit: {s['warn_limit']}"
    )


@app.on_message(filters.command(["tagall", "ping", "all"]) & filters.group)
async def tagall(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id if message.from_user else None, message):
        return await message.reply_text("❌ Admins only. Group Admin/Owner required.")

    chat_id = message.chat.id
    if chat_id in active_tags:
        return await message.reply_text("⚠️ A tagall is already running. Use /cancel to stop it.")

    custom = message.text.split(None, 1)[1] if len(message.command) > 1 else "Attention everyone! 📢"
    active_tags.add(chat_id)

    try:
        mentions = []
        seen = set()

        try:
            async for member in client.get_chat_members(chat_id):
                if chat_id not in active_tags:
                    return await message.reply_text("🛑 Tagall cancelled.")

                user = member.user
                if user.is_bot or user.is_deleted or user.id in seen:
                    continue

                seen.add(user.id)
                name = (user.first_name or "User").replace("[", "").replace("]", "")
                mentions.append(f"[{name}](tg://user?id={user.id})")
        except RPCError:
            return await message.reply_text(
                "❌ I could not read the member list. Make sure I am an admin."
            )

        if not mentions:
            return await message.reply_text("No members found.")

        # Send exactly 5 members per message.
        # Example: members 1-5 in message 1, 6-10 in message 2, etc.
        for start in range(0, len(mentions), 5):
            if chat_id not in active_tags:
                return await message.reply_text("🛑 Tagall cancelled.")

            batch = mentions[start:start + 5]
            batch_no = (start // 5) + 1
            text = f"📢 **{custom}**\n\n" if start == 0 else "📢 **Next 5 members**\n\n"
            text += "\n".join(batch)
            await message.reply_text(text, disable_web_page_preview=True)

    finally:
        active_tags.discard(chat_id)


@app.on_message(filters.command(["cancel", "stop"]) & filters.group)
async def cancel_tagall(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id if message.from_user else None, message):
        return await message.reply_text("❌ Admins only. Group Admin/Owner required.")

    chat_id = message.chat.id
    if chat_id not in active_tags:
        return await message.reply_text("ℹ️ No tagall is currently running.")

    active_tags.discard(chat_id)
    await message.reply_text("🛑 **Tagall cancelled.**")


@app.on_message(filters.group & ~filters.service)
async def remember_members(client, message):
    if message.from_user:
        db.save_member(
            message.chat.id,
            message.from_user.id,
            message.from_user.first_name or "User",
        )


@app.on_message(filters.group & ~filters.service)
async def moderate(client, message):
    if not message.from_user or message.from_user.is_bot:
        return

    if await is_admin(client, message.chat.id, message.from_user.id):
        return

    action = mod.check(message)
    if not action:
        return

    try:
        await message.delete()
    except RPCError:
        pass

    warns = db.add_warn(message.chat.id, message.from_user.id, action)
    limit = db.get_settings(message.chat.id)["warn_limit"]

    if warns >= limit:
        try:
            await client.restrict_chat_member(
                message.chat.id,
                message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
            )
            await message.reply_text(
                f"🔇 {message.from_user.mention} muted after {warns} warnings.\nReason: {action}"
            )
        except RPCError:
            await message.reply_text(
                f"⚠️ {message.from_user.mention} warning {warns}/{limit}.\nReason: {action}"
            )
    else:
        await message.reply_text(
            f"⚠️ {message.from_user.mention} warning {warns}/{limit}.\nReason: {action}"
        )


async def setup_commands(client):
    await client.set_bot_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help"),
        BotCommand("tagall", "Tag all members (Admin/Owner)"),
        BotCommand("cancel", "Cancel running tagall"),
        BotCommand("warn", "Warn a replied user"),
        BotCommand("warnings", "Check warnings"),
        BotCommand("resetwarn", "Reset warnings"),
        BotCommand("setwarnlimit", "Set warning limit"),
        BotCommand("settings", "Show group settings"),
    ])
    me = await client.get_me()
    print(f"🤖 Bot online: @{me.username}")
    print("✅ /start and /help handlers loaded.")


async def main():
    print("🤖 Group Manager Bot starting...")
    await app.start()
    await setup_commands(app)
    await idle()
    await app.stop()


if __name__ == "__main__":
    app.run(main())
