import os
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions
from pyrogram.errors import RPCError
from database import Database
from moderation import Moderation

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = Client("group_manager_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = Database(os.getenv("DATABASE_PATH", "bot.db"))
mod = Moderation(db)

async def is_admin(client, chat_id, user_id):
    try:
        m = await client.get_chat_member(chat_id, user_id)
        return m.status in ("administrator", "owner")
    except RPCError:
        return False

@app.on_message(filters.new_chat_members)
async def welcome(client, message):
    for user in message.new_chat_members:
        if not user.is_bot:
            await message.reply_text(
                f"👋 Welcome {user.mention} to **{message.chat.title}**!\n"
                "Please read the group rules and enjoy your stay."
            )

@app.on_message(filters.group & ~filters.service)
async def moderate(client, message):
    if not message.from_user:
        return
    if await is_admin(client, message.chat.id, message.from_user.id):
        return
    action = mod.check(message)
    if action:
        try:
            await message.delete()
        except RPCError:
            pass
        warns = db.add_warn(message.chat.id, message.from_user.id, action)
        limit = db.get_settings(message.chat.id)["warn_limit"]
        if warns >= limit:
            try:
                await client.restrict_chat_member(
                    message.chat.id, message.from_user.id,
                    permissions=ChatPermissions(can_send_messages=False)
                )
                await message.reply_text(
                    f"🔇 {message.from_user.mention} muted after {warns} warnings."
                )
            except RPCError:
                pass
        else:
            await client.send_message(
                message.chat.id,
                f"⚠️ {message.from_user.mention} received a warning ({warns}/{limit}).\nReason: {action}"
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
    await message.reply_text(f"⚠️ {user.mention} warned: {count}/{limit}\nReason: {reason}")

@app.on_message(filters.command("warnings") & filters.group)
async def warnings(client, message):
    target = message.reply_to_message.from_user if message.reply_to_message and message.reply_to_message.from_user else message.from_user
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

@app.on_message(filters.command("tagall") & filters.group)
async def tagall(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admins only.")
    text = message.text.split(None, 1)[1] if len(message.command) > 1 else "Attention everyone!"
    users = db.get_members(message.chat.id)
    if not users:
        return await message.reply_text("No saved members yet. Members are saved when they send messages.")
    chunks, current = [], f"📢 **{text}**\n\n"
    for user_id, name in users:
        mention = f"[{name}](tg://user?id={user_id})"
        if len(current) + len(mention) + 2 > 3800:
            chunks.append(current)
            current = ""
        current += mention + " "
    if current.strip():
        chunks.append(current)
    for chunk in chunks:
        await message.reply_text(chunk, disable_web_page_preview=True)

@app.on_message(filters.group & ~filters.service)
async def remember_members(client, message):
    if message.from_user:
        db.save_member(message.chat.id, message.from_user.id, message.from_user.first_name or "User")

@app.on_message(filters.command("setwarnlimit") & filters.group)
async def setwarnlimit(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admins only.")
    if len(message.command) != 2 or not message.command[1].isdigit():
        return await message.reply_text("Usage: /setwarnlimit 3")
    limit = max(1, min(20, int(message.command[1])))
    db.set_warn_limit(message.chat.id, limit)
    await message.reply_text(f"✅ Warning limit set to {limit}.")

@app.on_message(filters.command("settings") & filters.group)
async def settings(client, message):
    s = db.get_settings(message.chat.id)
    await message.reply_text(
        "⚙️ **Group settings**\n"
        f"Anti-spam: {'ON' if s['anti_spam'] else 'OFF'}\n"
        f"Abuse filter: {'ON' if s['abuse_filter'] else 'OFF'}\n"
        f"Anti-food: {'ON' if s['anti_food'] else 'OFF'}\n"
        f"Warn limit: {s['warn_limit']}"
    )

@app.on_message(filters.command("help") & filters.group)
async def help_cmd(client, message):
    await message.reply_text(
        "🤖 **Group Manager Bot**\n\n"
        "/tagall [message] — mention saved members\n"
        "/warn — warn a replied user\n"
        "/warnings — check warnings\n"
        "/resetwarn — reset warnings\n"
        "/setwarnlimit N — set warning limit\n"
        "/settings — show settings\n\n"
        "Auto moderation: abuse, spam/flood and configurable food-word filter."
    )

app.run()
