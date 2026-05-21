"""
main.py — Cinderella-Forwards Bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COMMANDS (GROUP only, AUTH_USERS):
  /start         — Welcome message with feature list
  /setsource     — Set source channel/group ID (to forward FROM)
  /settarget     — Set target channel/group ID (to forward TO)
  /setkeywords   — Set keyword filter (1 or 2 word keywords)
  /offkeywords   — Disable keyword filter (forward all)
  /setdelay      — Set delay in seconds between forwards
  /viewsettings  — View current settings

COMMANDS (PRIVATE, OWNER only):
  /broadcast     — Broadcast to all users/groups
  /broadusers    — View all registered users/groups

HOW IT WORKS:
  • Bot monitors source channel/group for videos & PDFs
  • If keyword filter ON  → only files with matching keyword in caption are forwarded
  • If keyword filter OFF → all videos & PDFs are forwarded
  • 3s delay (configurable) between each forwarded file
  • Public source  → regular bot handles it (bot must be added to source)
  • Private source → userbot (SESSION_STRING) handles reading;
                     bot must be admin in TARGET

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import random
import asyncio
import threading
import logging

from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
)
from pyromod import listen

import globals
import user_store
from vars import API_ID, API_HASH, BOT_TOKEN, OWNER, CREDIT, AUTH_USERS, SESSION_STRING
from settings  import register_settings_handlers
from broadcast import register_broadcast_handlers
from forwarder import register_forwarder_handlers

logging.basicConfig(
    format="[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Images ────────────────────────────────────────────────────────────────────
image_list = [
    "https://graph.org/file/417cc7326cab9036c0152-f6a281db2a6975dfa9.jpg",
    "https://graph.org/file/033121ad32291bcaddd01-d91ae4a1f7ca9378fc.jpg",
    "https://graph.org/file/45f48779e0aa39709d1e8-4c024567d60f6ec5c2.jpg",
    "https://graph.org/file/6ccdd92af77784c9d367e-a4ba6f10456656bbbd.jpg",
    "https://graph.org/file/b23084c3e9124e14e18ec-d385f8f9c8b1635a2e.jpg",
]

# ── Initialize Bot ────────────────────────────────────────────────────────────
bot = Client(
    "cinderella_forwards_bot",
    api_id    = API_ID,
    api_hash  = API_HASH,
    bot_token = BOT_TOKEN
)

# ── Initialize Userbot (only if SESSION_STRING is set) ────────────────────────
userbot = None
if SESSION_STRING:
    userbot = Client(
        "cinderella_forwards_userbot",
        api_id        = API_ID,
        api_hash      = API_HASH,
        session_string = SESSION_STRING
    )
    logger.info("[Bot] Userbot session loaded from SESSION_STRING.")
else:
    logger.info("[Bot] No SESSION_STRING — userbot disabled. Only public sources supported.")


# ── Start keyboard ─────────────────────────────────────────────────────────────
def get_start_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 Set Source",   switch_inline_query_current_chat="/setsource"),
         InlineKeyboardButton("🎯 Set Target",   switch_inline_query_current_chat="/settarget")],
        [InlineKeyboardButton("🔍 Set Keywords", switch_inline_query_current_chat="/setkeywords"),
         InlineKeyboardButton("🔕 Off Keywords", switch_inline_query_current_chat="/offkeywords")],
        [InlineKeyboardButton("⏱️ Set Delay",    switch_inline_query_current_chat="/setdelay"),
         InlineKeyboardButton("📊 View Settings",switch_inline_query_current_chat="/viewsettings")],
        [InlineKeyboardButton("📢 Help & Info",  callback_data="help_info")],
        [InlineKeyboardButton("🔍 Developer", url="https://t.me/CinderellaContactBot"),
         InlineKeyboardButton("👑 Owner",     url=f"tg://openmessage?user_id={OWNER}")],
    ])


# ── /start ────────────────────────────────────────────────────────────────────
@bot.on_message(filters.command("start"))
async def start_cmd(client: Client, m: Message):
    user_id = m.from_user.id if m.from_user else 0
    user_store.register_user(user_id)
    if m.chat.id != user_id:
        user_store.register_group(m.chat.id)

    is_auth = user_id in AUTH_USERS
    first   = m.from_user.first_name if m.from_user else "Friend"

    source_id = globals.get_setting("source_chat_id", "Not set")
    target_id = globals.get_setting("target_chat_id", "Not set")
    kw_on     = globals.get_setting("keywords_enabled", False)
    keywords  = globals.get_setting("keywords", [])
    delay     = globals.get_setting("forward_delay", 3)

    kw_status = "🟢 ON" if kw_on else "🔴 OFF"
    kw_list   = ", ".join(f"`{k}`" for k in keywords) if keywords else "none"

    if is_auth:
        caption = (
            f"**Hello Dear 👑 {first}!**\n\n"
            f"➠ I am **Cinderella-Forwards Bot** 🚀\n\n"
            f"**✨ What I do:**\n"
            f"• 📡 Forward **Videos & PDFs** from source → target\n"
            f"• 🔍 Keyword filter — only forward matching files\n"
            f"• ⏱️ Configurable delay between forwards\n"
            f"• 🔐 Private source support via Userbot\n\n"
            f"**📊 Current Config:**\n"
            f"<blockquote>"
            f"📡 Source: `{source_id}`\n"
            f"🎯 Target: `{target_id}`\n"
            f"⏱️ Delay: `{delay}s`\n"
            f"🔍 Keywords: {kw_status} → {kw_list}"
            f"</blockquote>\n\n"
            f"➠ Made By : [{CREDIT}](tg://openmessage?user_id={OWNER}) 🦁"
        )
    else:
        caption = (
            f"**Hello 🫣 {first}!**\n\n"
            f"➠ I am **Cinderella-Forwards Bot**\n\n"
            f"I forward Videos & PDFs from one channel to another "
            f"with smart keyword filtering!\n\n"
            f"<blockquote>You are currently **not authorized**.\n"
            f"Contact the owner to get access.\n"
            f"Your User ID: `{user_id}`</blockquote>\n\n"
            f"💬 Contact: [{CREDIT}](tg://openmessage?user_id={OWNER}) 🔓"
        )

    await client.send_photo(
        chat_id      = m.chat.id,
        photo        = random.choice(image_list),
        caption      = caption,
        reply_markup = get_start_keyboard()
    )


# ── Help callback ──────────────────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("help_info"))
async def help_info_cb(client, callback_query):
    text = (
        "**📖 Cinderella-Forwards — Help**\n\n"
        "**Group Commands (Auth Users):**\n"
        "• `/setsource` — Set source channel/group ID\n"
        "• `/settarget` — Set target channel/group ID\n"
        "• `/setkeywords` — Set keyword filter (1-2 words each)\n"
        "• `/offkeywords` — Disable keyword filter\n"
        "• `/setdelay` — Set delay between forwards (seconds)\n"
        "• `/viewsettings` — View current settings\n\n"
        "**Private Commands (Owner only):**\n"
        "• `/broadcast` — Broadcast a message\n"
        "• `/broadusers` — View all users/groups\n\n"
        "**How Forwarding Works:**\n"
        "<blockquote>"
        "• Bot monitors source channel for new Videos & PDFs\n"
        "• If keywords ON → only files with matching caption are forwarded\n"
        "• If keywords OFF → ALL videos & PDFs are forwarded\n"
        "• 3s delay (default) between each file\n"
        "• Public source → bot must be joined to source\n"
        "• Private source → set SESSION_STRING env variable\n"
        "• Target → bot must be Admin in target channel/group"
        "</blockquote>"
    )
    await callback_query.message.edit_caption(
        caption      = text,
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ])
    )
    await callback_query.answer()


@bot.on_callback_query(filters.regex("back_home"))
async def back_home_cb(client, callback_query):
    first = callback_query.from_user.first_name if callback_query.from_user else "Friend"
    caption = (
        f"**Hello 👑 {first}!**\n\n"
        f"➠ I am **Cinderella-Forwards Bot**\n\n"
        f"Use the buttons below to configure forwarding!\n\n"
        f"➠ Made By : [{CREDIT}](tg://openmessage?user_id={OWNER}) 🦁"
    )
    try:
        await callback_query.message.edit_media(
            InputMediaPhoto(
                media   = random.choice(image_list),
                caption = caption
            ),
            reply_markup=get_start_keyboard()
        )
    except Exception:
        await callback_query.message.edit_caption(
            caption      = caption,
            reply_markup = get_start_keyboard()
        )
    await callback_query.answer()


# ── Register all handlers ──────────────────────────────────────────────────────
register_settings_handlers(bot)
register_broadcast_handlers(bot)
register_forwarder_handlers(bot, userbot)


# ── Flask web server (for Render.com) ─────────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return """
<!DOCTYPE html>
<html>
<body style="background:#0d0d0d;color:#fff;font-family:monospace;text-align:center;padding:60px">
  <pre style="color:#e040fb;font-size:13px">
  ██████╗██╗███╗  ██╗██████╗ ███████╗██████╗ ███████╗██╗     ██╗      █████╗ 
 ██╔════╝██║████╗ ██║██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██║     ██╔══██╗
 ██║     ██║██╔██╗██║██║  ██║█████╗  ██████╔╝█████╗  ██║     ██║     ███████║
 ██║     ██║██║╚████║██║  ██║██╔══╝  ██╔══██╗██╔══╝  ██║     ██║     ██╔══██║
 ╚██████╗██║██║ ╚███║██████╔╝███████╗██║  ██║███████╗███████╗███████╗██║  ██║
  ╚═════╝╚═╝╚═╝  ╚══╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝
  </pre>
  <h2 style="color:#e040fb">Cinderella-Forwards Bot — Running ✅</h2>
  <p style="color:#aaa">Smart Video & PDF Forwarder with Keyword Filter</p>
  <p style="color:#666">Powered by Team★Toxic</p>
</body>
</html>
"""

@flask_app.route("/health")
def health():
    return {"status": "ok", "bot": "Cinderella-Forwards"}, 200


def run_flask():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    running_under_gunicorn = (
        "gunicorn" in sys.modules
        or os.environ.get("SERVER_SOFTWARE", "").startswith("gunicorn")
    )

    if not running_under_gunicorn:
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logger.info(f"[Bot] Flask started on port {os.environ.get('PORT', 8000)}")
    else:
        logger.info("[Bot] Gunicorn detected — skipping internal Flask server.")

    logger.info("[Bot] Starting Cinderella-Forwards Bot...")

    # Start userbot first (if configured)
    if userbot:
        logger.info("[Bot] Starting userbot client...")
        bot.run(userbot.start())
    else:
        bot.run()
