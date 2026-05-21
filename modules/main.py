"""
main.py — Cinderella-Forwards Bot (v2)

NEW FEATURES:
  • /forward command — bulk forward historical messages with skip support
  • /settings — fully button-based settings menu
  • /addbot — add your custom Bot (BotFather token) or User Bot (phone login)
  • Works in both GROUP and PRIVATE/DM chats
  • Live forwarding progress with percentage bar
  • Stop button during forwarding
  • Forwarding started / completed / stopped notifications

COMMANDS:
  /start        — Welcome
  /settings     — Full settings panel (button UI)
  /forward      — Start bulk forwarding
  /addbot       — Add custom bot/userbot
  /viewsettings — Quick view settings
  /offkeywords  — Disable keyword filter
  /broadcast    — (Owner) Broadcast message
  /broadusers   — (Owner) View all users
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

# ── Images ─────────────────────────────────────────────────────────────────────
image_list = [
    "https://graph.org/file/417cc7326cab9036c0152-f6a281db2a6975dfa9.jpg",
    "https://graph.org/file/033121ad32291bcaddd01-d91ae4a1f7ca9378fc.jpg",
    "https://graph.org/file/45f48779e0aa39709d1e8-4c024567d60f6ec5c2.jpg",
    "https://graph.org/file/6ccdd92af77784c9d367e-a4ba6f10456656bbbd.jpg",
    "https://graph.org/file/b23084c3e9124e14e18ec-d385f8f9c8b1635a2e.jpg",
]

# ── Init Bot ───────────────────────────────────────────────────────────────────
bot = Client(
    "cinderella_forwards_bot",
    api_id    = API_ID,
    api_hash  = API_HASH,
    bot_token = BOT_TOKEN
)

# ── Init Userbot ───────────────────────────────────────────────────────────────
userbot = None
if SESSION_STRING:
    userbot = Client(
        "cinderella_forwards_userbot",
        api_id         = API_ID,
        api_hash       = API_HASH,
        session_string = SESSION_STRING
    )
    logger.info("[Bot] Global userbot session loaded.")
else:
    logger.info("[Bot] No global SESSION_STRING — per-user userbots only.")


# ── Home keyboard ──────────────────────────────────────────────────────────────
def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="open_settings"),
            InlineKeyboardButton("▶️ Start Forward", callback_data="start_forward_hint"),
        ],
        [
            InlineKeyboardButton("🤖 Add Bot", callback_data="add_bot_menu"),
            InlineKeyboardButton("📖 Help", callback_data="help_info"),
        ],
        [
            InlineKeyboardButton("🔍 Developer", url="https://t.me/CinderellaContactBot"),
            InlineKeyboardButton("👑 Owner", url=f"tg://openmessage?user_id={OWNER}"),
        ],
    ])


# ── /start ─────────────────────────────────────────────────────────────────────
@bot.on_message(filters.command("start") & (filters.group | filters.private))
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
            f"• 📡 Forward **Videos, PDFs & Text** from source → target\n"
            f"• 🔍 Keyword filter — forward only matching files\n"
            f"• ⏱️ Configurable delay between forwards\n"
            f"• 🔐 Private source via Userbot\n"
            f"• 🤖 Use your own bot for forwarding\n\n"
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
            f"I forward files from one channel to another with smart filtering!\n\n"
            f"<blockquote>You are **not authorized**.\n"
            f"Contact owner to get access.\n"
            f"Your ID: `{user_id}`</blockquote>\n\n"
            f"💬 Contact: [{CREDIT}](tg://openmessage?user_id={OWNER}) 🔓"
        )

    await client.send_photo(
        chat_id      = m.chat.id,
        photo        = random.choice(image_list),
        caption      = caption,
        reply_markup = get_start_keyboard()
    )


# ── Start forward hint ─────────────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("start_forward_hint"))
async def start_forward_hint_cb(client, cq):
    await cq.answer(
        "Use /forward command to start bulk forwarding!\nMake sure source & target are set in ⚙️ Settings first.",
        show_alert=True
    )


# ── Help callback ──────────────────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("help_info"))
async def help_info_cb(client, cq):
    text = (
        "**📖 Cinderella-Forwards — Help**\n\n"
        "**Commands (Auth Users):**\n"
        "• `/start` — Welcome & home\n"
        "• `/settings` — Full settings panel\n"
        "• `/forward` — Start bulk forwarding\n"
        "• `/addbot` — Add custom bot/userbot\n"
        "• `/viewsettings` — Quick view settings\n"
        "• `/offkeywords` — Disable keyword filter\n\n"
        "**Owner Commands:**\n"
        "• `/broadcast` — Broadcast message\n"
        "• `/broadusers` — View all users\n\n"
        "**How Forwarding Works:**\n"
        "<blockquote>"
        "• /forward → asks for skip number → starts forwarding\n"
        "• Skip: send message number to skip older messages\n"
        "• Send `none` to forward everything\n"
        "• Live progress shown with percentage bar\n"
        "• 🛑 Stop button available during forwarding\n"
        "• Bot notifies target when done"
        "</blockquote>"
    )
    await cq.message.edit_caption(
        caption      = text,
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ])
    )
    await cq.answer()


@bot.on_callback_query(filters.regex("back_home"))
async def back_home_cb(client, cq):
    first = cq.from_user.first_name if cq.from_user else "Friend"
    caption = (
        f"**Hello 👑 {first}!**\n\n"
        f"➠ I am **Cinderella-Forwards Bot**\n\n"
        f"Use the buttons below to configure and start forwarding!\n\n"
        f"➠ Made By : [{CREDIT}](tg://openmessage?user_id={OWNER}) 🦁"
    )
    try:
        await cq.message.edit_media(
            InputMediaPhoto(
                media   = random.choice(image_list),
                caption = caption
            ),
            reply_markup=get_start_keyboard()
        )
    except Exception:
        try:
            await cq.message.edit_caption(
                caption      = caption,
                reply_markup = get_start_keyboard()
            )
        except Exception:
            pass
    await cq.answer()


# ── Register all handlers ──────────────────────────────────────────────────────
register_settings_handlers(bot)
register_broadcast_handlers(bot)
register_forwarder_handlers(bot, userbot)


# ── Flask (for Render.com) ─────────────────────────────────────────────────────
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
  <h2 style="color:#e040fb">Cinderella-Forwards Bot v2 — Running ✅</h2>
  <p style="color:#aaa">Smart Forwarder • Button UI • Custom Bots • Live Progress</p>
  <p style="color:#666">Powered by Team★Toxic</p>
</body>
</html>
"""

@flask_app.route("/health")
def health():
    return {"status": "ok", "bot": "Cinderella-Forwards v2"}, 200


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

    logger.info("[Bot] Starting Cinderella-Forwards Bot v2...")

    if userbot:
        logger.info("[Bot] Starting global userbot client...")
        bot.run(userbot.start())
    else:
        bot.run()
