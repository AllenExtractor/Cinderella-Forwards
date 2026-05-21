"""
settings.py — Cinderella-Forwards Bot Settings

All commands now work in both GROUP and PRIVATE chats.
Full button-based UI with inline menus.
"""

import asyncio
import re

from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)

import globals
import bot_manager
from vars import AUTH_USERS

TIMEOUT = 300

# ── Helpers ──────────────────────────────────────────────────────────────────

def is_auth(user_id: int) -> bool:
    return user_id in AUTH_USERS

def validate_keyword(kw: str) -> bool:
    kw = kw.strip()
    parts = kw.split(" ")
    if len(parts) < 1 or len(parts) > 2:
        return False
    for part in parts:
        if not part:
            return False
        if not re.match(r"^[\w]+$", part, re.UNICODE):
            return False
    return True

# ── Main Settings Menu ────────────────────────────────────────────────────────

def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📡 Set Source", callback_data="set_source"),
            InlineKeyboardButton("🎯 Set Target", callback_data="set_target"),
        ],
        [
            InlineKeyboardButton("🔍 Set Keywords", callback_data="set_keywords"),
            InlineKeyboardButton("🔕 Off Keywords", callback_data="off_keywords"),
        ],
        [
            InlineKeyboardButton("⏱️ Set Delay", callback_data="set_delay"),
            InlineKeyboardButton("📊 View Settings", callback_data="view_settings"),
        ],
        [
            InlineKeyboardButton("🤖 Add Bot", callback_data="add_bot_menu"),
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_home")]
    ])

def add_bot_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Bot (BotFather Token)", callback_data="add_botfather_bot")],
        [InlineKeyboardButton("👤 User Bot (Phone Login)", callback_data="add_user_bot")],
        [InlineKeyboardButton("🔙 Back to Settings", callback_data="open_settings")],
    ])


def register_settings_handlers(bot: Client):

    # ── /settings ─────────────────────────────────────────────────────────────
    @bot.on_message(filters.command("settings") & (filters.group | filters.private))
    async def settings_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if not is_auth(user_id):
            await m.reply_text(f"<blockquote>🙅 Not authorized. Your ID: `{user_id}`</blockquote>")
            return
        await m.reply_text(
            "⚙️ **Cinderella-Forwards Settings**\n\nChoose what to configure:",
            reply_markup=settings_keyboard()
        )

    # ── Open Settings ─────────────────────────────────────────────────────────
    @bot.on_callback_query(filters.regex("^open_settings$"))
    async def open_settings_cb(client: Client, cq: CallbackQuery):
        user_id = cq.from_user.id
        if not is_auth(user_id):
            await cq.answer("🙅 Not authorized!", show_alert=True)
            return
        await cq.message.edit_text(
            "⚙️ **Cinderella-Forwards Settings**\n\nChoose what to configure:",
            reply_markup=settings_keyboard()
        )
        await cq.answer()

    # ── Set Source ────────────────────────────────────────────────────────────
    @bot.on_callback_query(filters.regex("^set_source$"))
    async def set_source_cb(client: Client, cq: CallbackQuery):
        user_id = cq.from_user.id
        if not is_auth(user_id):
            await cq.answer("🙅 Not authorized!", show_alert=True)
            return
        await cq.answer()
        await cq.message.edit_text(
            "**📡 Set Source Channel/Group**\n\n"
            "Send the **Source Chat ID** (numeric):\n"
            "<blockquote>Example: `-1001234567890`\n"
            "• Public channel → bot must be a member\n"
            "• Private channel → add User Bot via 🤖 Add Bot\n"
            "Send /cancel to abort.</blockquote>"
        )
        try:
            reply: Message = await bot.listen(cq.message.chat.id, timeout=TIMEOUT)
        except asyncio.TimeoutError:
            await cq.message.edit_text("⏰ Timeout.", reply_markup=settings_keyboard())
            return

        if reply.text and reply.text.strip().lower() == "/cancel":
            await reply.delete()
            await cq.message.edit_text("❌ Cancelled.", reply_markup=settings_keyboard())
            return

        raw = reply.text.strip() if reply.text else ""
        await reply.delete()

        try:
            source_id = int(raw)
        except ValueError:
            await cq.message.edit_text("❌ Invalid ID. Must be numeric.", reply_markup=settings_keyboard())
            return

        globals.set_setting("source_chat_id", source_id)
        await cq.message.edit_text(
            f"✅ **Source Chat updated!**\n\n<blockquote>📡 Source: `{source_id}`</blockquote>",
            reply_markup=settings_keyboard()
        )

    # ── Set Target ────────────────────────────────────────────────────────────
    @bot.on_callback_query(filters.regex("^set_target$"))
    async def set_target_cb(client: Client, cq: CallbackQuery):
        user_id = cq.from_user.id
        if not is_auth(user_id):
            await cq.answer("🙅 Not authorized!", show_alert=True)
            return
        await cq.answer()
        await cq.message.edit_text(
            "**🎯 Set Target Channel/Group**\n\n"
            "Send the **Target Chat ID** (numeric):\n"
            "<blockquote>Example: `-1009876543210`\n"
            "⚠️ Bot must be **Admin** in the target channel/group.\n"
            "Send /cancel to abort.</blockquote>"
        )
        try:
            reply: Message = await bot.listen(cq.message.chat.id, timeout=TIMEOUT)
        except asyncio.TimeoutError:
            await cq.message.edit_text("⏰ Timeout.", reply_markup=settings_keyboard())
            return

        if reply.text and reply.text.strip().lower() == "/cancel":
            await reply.delete()
            await cq.message.edit_text("❌ Cancelled.", reply_markup=settings_keyboard())
            return

        raw = reply.text.strip() if reply.text else ""
        await reply.delete()

        try:
            target_id = int(raw)
        except ValueError:
            await cq.message.edit_text("❌ Invalid ID. Must be numeric.", reply_markup=settings_keyboard())
            return

        globals.set_setting("target_chat_id", target_id)
        await cq.message.edit_text(
            f"✅ **Target Chat updated!**\n\n<blockquote>🎯 Target: `{target_id}`</blockquote>",
            reply_markup=settings_keyboard()
        )

    # ── Set Keywords ──────────────────────────────────────────────────────────
    @bot.on_callback_query(filters.regex("^set_keywords$"))
    async def set_keywords_cb(client: Client, cq: CallbackQuery):
        user_id = cq.from_user.id
        if not is_auth(user_id):
            await cq.answer("🙅 Not authorized!", show_alert=True)
            return
        await cq.answer()
        await cq.message.edit_text(
            "**🔍 Set Keyword Filter**\n\n"
            "Send keywords — **one per line**:\n"
            "<blockquote>• Max 2 words per keyword\n"
            "• Example:\n`Sobiya`\n`Sobiya Ji`\n`Batch01`\n\n"
            "Send /cancel to abort.</blockquote>"
        )
        try:
            reply: Message = await bot.listen(cq.message.chat.id, timeout=TIMEOUT)
        except asyncio.TimeoutError:
            await cq.message.edit_text("⏰ Timeout.", reply_markup=settings_keyboard())
            return

        if reply.text and reply.text.strip().lower() == "/cancel":
            await reply.delete()
            await cq.message.edit_text("❌ Cancelled.", reply_markup=settings_keyboard())
            return

        raw = reply.text.strip() if reply.text else ""
        await reply.delete()

        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        invalid = [l for l in lines if not validate_keyword(l)]
        if invalid:
            inv_str = "\n".join(f"`{i}`" for i in invalid)
            await cq.message.edit_text(
                f"❌ **Invalid keywords:**\n{inv_str}\n\nMax 2 words each.",
                reply_markup=settings_keyboard()
            )
            return

        globals.set_setting("keywords", lines)
        globals.set_setting("keywords_enabled", True)
        kw_str = "\n".join(f"• `{k}`" for k in lines)
        await cq.message.edit_text(
            f"✅ **Keywords set!**\n\n<blockquote>🔍 Active:\n{kw_str}</blockquote>",
            reply_markup=settings_keyboard()
        )

    # ── Off Keywords ──────────────────────────────────────────────────────────
    @bot.on_callback_query(filters.regex("^off_keywords$"))
    async def off_keywords_cb(client: Client, cq: CallbackQuery):
        user_id = cq.from_user.id
        if not is_auth(user_id):
            await cq.answer("🙅 Not authorized!", show_alert=True)
            return
        globals.set_setting("keywords_enabled", False)
        await cq.answer("✅ Keywords disabled!", show_alert=False)
        await cq.message.edit_text(
            "✅ **Keywords filter disabled.**\n\n"
            "<blockquote>All videos & PDFs from source will be forwarded.</blockquote>",
            reply_markup=settings_keyboard()
        )

    # ── Set Delay ─────────────────────────────────────────────────────────────
    @bot.on_callback_query(filters.regex("^set_delay$"))
    async def set_delay_cb(client: Client, cq: CallbackQuery):
        user_id = cq.from_user.id
        if not is_auth(user_id):
            await cq.answer("🙅 Not authorized!", show_alert=True)
            return
        await cq.answer()
        await cq.message.edit_text(
            "**⏱️ Set Forward Delay**\n\n"
            "Send delay in **seconds** between each file:\n"
            "<blockquote>Default: `3`\nRange: 1–60\nSend /cancel to abort.</blockquote>"
        )
        try:
            reply: Message = await bot.listen(cq.message.chat.id, timeout=TIMEOUT)
        except asyncio.TimeoutError:
            await cq.message.edit_text("⏰ Timeout.", reply_markup=settings_keyboard())
            return

        if reply.text and reply.text.strip().lower() == "/cancel":
            await reply.delete()
            await cq.message.edit_text("❌ Cancelled.", reply_markup=settings_keyboard())
            return

        raw = reply.text.strip() if reply.text else ""
        await reply.delete()

        try:
            delay = int(raw)
            if delay < 1 or delay > 60:
                raise ValueError
        except ValueError:
            await cq.message.edit_text("❌ Enter a number between 1 and 60.", reply_markup=settings_keyboard())
            return

        globals.set_setting("forward_delay", delay)
        await cq.message.edit_text(
            f"✅ **Delay updated!**\n\n<blockquote>⏱️ Forward Delay: `{delay}s`</blockquote>",
            reply_markup=settings_keyboard()
        )

    # ── View Settings ─────────────────────────────────────────────────────────
    @bot.on_callback_query(filters.regex("^view_settings$"))
    async def view_settings_cb(client: Client, cq: CallbackQuery):
        user_id = cq.from_user.id
        if not is_auth(user_id):
            await cq.answer("🙅 Not authorized!", show_alert=True)
            return

        source_id  = globals.get_setting("source_chat_id", "Not set")
        target_id  = globals.get_setting("target_chat_id", "Not set")
        kw_enabled = globals.get_setting("keywords_enabled", False)
        keywords   = globals.get_setting("keywords", [])
        delay      = globals.get_setting("forward_delay", 3)

        kw_status = "🟢 ON" if kw_enabled else "🔴 OFF"
        kw_list   = ", ".join(f"`{k}`" for k in keywords) if keywords else "none"

        bot_tok   = bot_manager.get_bot_token(user_id)
        sess_str  = bot_manager.get_session_string(user_id)

        text = (
            "**⚙️ Current Settings**\n\n"
            f"<blockquote>"
            f"📡 Source: `{source_id}`\n"
            f"🎯 Target: `{target_id}`\n"
            f"⏱️ Delay: `{delay}s`\n"
            f"🔍 Keywords: {kw_status} → {kw_list}\n"
            f"🤖 Custom Bot: {'✅ Set' if bot_tok else '❌ Not set'}\n"
            f"👤 User Bot: {'✅ Set' if sess_str else '❌ Not set'}"
            f"</blockquote>"
        )
        await cq.message.edit_text(text, reply_markup=settings_keyboard())
        await cq.answer()

    # ── Add Bot Menu ──────────────────────────────────────────────────────────
    @bot.on_callback_query(filters.regex("^add_bot_menu$"))
    async def add_bot_menu_cb(client: Client, cq: CallbackQuery):
        user_id = cq.from_user.id
        if not is_auth(user_id):
            await cq.answer("🙅 Not authorized!", show_alert=True)
            return
        await cq.message.edit_text(
            "🤖 **Add Bot**\n\n"
            "Choose what to add:\n\n"
            "<blockquote>**Bot** — Your custom bot token from @BotFather (used as sender)\n"
            "**User Bot** — Login via phone number (used to read private sources)</blockquote>",
            reply_markup=add_bot_keyboard()
        )
        await cq.answer()

    # ── Add BotFather Bot ─────────────────────────────────────────────────────
    @bot.on_callback_query(filters.regex("^add_botfather_bot$"))
    async def add_botfather_cb(client: Client, cq: CallbackQuery):
        user_id = cq.from_user.id
        if not is_auth(user_id):
            await cq.answer("🙅 Not authorized!", show_alert=True)
            return
        await cq.answer()
        await cq.message.edit_text(
            "🤖 **Add Your Bot**\n\n"
            "Send your **BotFather Token**:\n"
            "<blockquote>Example: `123456789:AAGQVElsB...`\n"
            "⚠️ Token must be working and not revoked.\n"
            "Send /cancel to abort.</blockquote>"
        )
        try:
            reply: Message = await bot.listen(cq.message.chat.id, timeout=TIMEOUT)
        except asyncio.TimeoutError:
            await cq.message.edit_text("⏰ Timeout.", reply_markup=add_bot_keyboard())
            return

        if reply.text and reply.text.strip() == "/cancel":
            await reply.delete()
            await cq.message.edit_text("❌ Cancelled.", reply_markup=add_bot_keyboard())
            return

        token = reply.text.strip() if reply.text else ""
        await reply.delete()
        await cq.message.edit_text("⏳ Validating token...")

        ok, info = await bot_manager.validate_bot_token(token)
        if not ok:
            await cq.message.edit_text(
                f"❌ **Invalid token!**\n\n<blockquote>{info}</blockquote>",
                reply_markup=add_bot_keyboard()
            )
            return

        bot_manager.save_bot_token(user_id, token)

        # Send confirmation to user
        try:
            await bot.send_message(
                user_id,
                f"✅ **Bot Added Successfully!**\n\n"
                f"<blockquote>Bot: {info}\n"
                f"Token: `{token[:20]}...`</blockquote>\n\n"
                f"Your bot is now ready to use for forwarding!"
            )
        except Exception:
            pass

        await cq.message.edit_text(
            f"✅ **Bot Added!**\n\n<blockquote>🤖 {info}\nToken verified ✅</blockquote>",
            reply_markup=settings_keyboard()
        )

    # ── Add User Bot ──────────────────────────────────────────────────────────
    @bot.on_callback_query(filters.regex("^add_user_bot$"))
    async def add_user_bot_cb(client: Client, cq: CallbackQuery):
        user_id = cq.from_user.id
        if not is_auth(user_id):
            await cq.answer("🙅 Not authorized!", show_alert=True)
            return
        await cq.answer()
        await cq.message.edit_text("👤 **User Bot Login**\n\n⏳ Starting phone login flow...")

        ok, result = await bot_manager.login_userbot_flow(bot, user_id, cq.message.chat.id)
        if ok:
            bot_manager.save_session_string(user_id, result)
            await cq.message.edit_text(
                "✅ **User Bot Added Successfully!**\n\n"
                "<blockquote>Your session has been saved.\n"
                "Check your Saved Messages for the session string.</blockquote>",
                reply_markup=settings_keyboard()
            )
        else:
            await cq.message.edit_text(
                f"❌ **Login Failed**\n\n<blockquote>{result}</blockquote>",
                reply_markup=add_bot_keyboard()
            )

    # ── Legacy text commands (kept for compatibility) ─────────────────────────
    @bot.on_message(filters.command("setsource") & (filters.group | filters.private))
    async def setsource_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if not is_auth(user_id):
            await m.reply_text(f"<blockquote>🙅 Not authorized. Your ID: `{user_id}`</blockquote>")
            return
        await m.reply_text("Please use ⚙️ /settings → Set Source for a better experience.")

    @bot.on_message(filters.command("settarget") & (filters.group | filters.private))
    async def settarget_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if not is_auth(user_id):
            await m.reply_text(f"<blockquote>🙅 Not authorized. Your ID: `{user_id}`</blockquote>")
            return
        await m.reply_text("Please use ⚙️ /settings → Set Target for a better experience.")

    @bot.on_message(filters.command("viewsettings") & (filters.group | filters.private))
    async def viewsettings_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if not is_auth(user_id):
            await m.reply_text(f"<blockquote>🙅 Not authorized. Your ID: `{user_id}`</blockquote>")
            return

        source_id  = globals.get_setting("source_chat_id", "Not set")
        target_id  = globals.get_setting("target_chat_id", "Not set")
        kw_enabled = globals.get_setting("keywords_enabled", False)
        keywords   = globals.get_setting("keywords", [])
        delay      = globals.get_setting("forward_delay", 3)

        kw_status = "🟢 ON" if kw_enabled else "🔴 OFF"
        kw_list   = ", ".join(f"`{k}`" for k in keywords) if keywords else "none"

        await m.reply_text(
            f"**⚙️ Current Settings**\n\n"
            f"<blockquote>"
            f"📡 Source: `{source_id}`\n"
            f"🎯 Target: `{target_id}`\n"
            f"⏱️ Delay: `{delay}s`\n"
            f"🔍 Keywords: {kw_status} → {kw_list}"
            f"</blockquote>"
        )

    @bot.on_message(filters.command("setkeywords") & (filters.group | filters.private))
    async def setkeywords_cmd(client: Client, m: Message):
        await m.reply_text("Please use ⚙️ /settings → Set Keywords.")

    @bot.on_message(filters.command("offkeywords") & (filters.group | filters.private))
    async def offkeywords_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if not is_auth(user_id):
            await m.reply_text(f"<blockquote>🙅 Not authorized.</blockquote>")
            return
        globals.set_setting("keywords_enabled", False)
        await m.reply_text("✅ Keywords disabled. All files will be forwarded.")

    @bot.on_message(filters.command("setdelay") & (filters.group | filters.private))
    async def setdelay_cmd(client: Client, m: Message):
        await m.reply_text("Please use ⚙️ /settings → Set Delay.")

    @bot.on_message(filters.command("addbot") & (filters.group | filters.private))
    async def addbot_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if not is_auth(user_id):
            await m.reply_text(f"<blockquote>🙅 Not authorized.</blockquote>")
            return
        await m.reply_text(
            "🤖 **Add Bot**\n\nChoose what to add:",
            reply_markup=add_bot_keyboard()
        )
