"""
settings.py — Cinderella-Forwards Bot Settings

Commands (group only, AUTH_USERS only):
  /setsource    — Set source channel/group ID to forward FROM
  /settarget    — Set target channel/group ID to forward TO
  /setkeywords  — Set keyword filter (max 2 words, 1 or 2 space-separated words)
  /offkeywords  — Disable keyword filter (forward all videos & PDFs)
  /viewsettings — Show current settings
  /setdelay     — Set delay in seconds between forwards (default: 3)
"""

import asyncio
import re

from pyrogram import Client, filters
from pyrogram.types import Message

import globals
from vars import AUTH_USERS

TIMEOUT = 300

# ── Keyword validation ──────────────────────────────────────────────────────
def validate_keyword(kw: str) -> bool:
    """Max 2 words, each word alphanumeric (letters/digits), separated by single space."""
    kw = kw.strip()
    parts = kw.split(" ")
    if len(parts) < 1 or len(parts) > 2:
        return False
    for part in parts:
        if not part:
            return False
        # Allow letters, digits, underscores
        if not re.match(r"^[\w]+$", part, re.UNICODE):
            return False
    return True


def register_settings_handlers(bot: Client):

    # ── /setsource ──────────────────────────────────────────────────────────
    @bot.on_message(filters.command("setsource") & filters.group)
    async def setsource_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if user_id not in AUTH_USERS:
            await m.reply_text(f"<blockquote>🙅 Not authorized. Your ID: `{user_id}`</blockquote>")
            return

        await m.delete()
        editable = await client.send_message(
            m.chat.id,
            "**⚙️ Set Source Channel/Group**\n\n"
            "Send the **Source Chat ID** (channel or group) from which to forward.\n"
            "<blockquote>Example: `-1001234567890`\n"
            "• If public channel — bot only needed\n"
            "• If private — userbot session required (set SESSION_STRING in env)\n"
            "Send /cancel to abort.</blockquote>"
        )

        try:
            reply: Message = await bot.listen(m.chat.id, timeout=TIMEOUT)
        except asyncio.TimeoutError:
            await editable.edit("⏰ Timeout. Use /setsource to try again.")
            return

        if reply.text and reply.text.strip().lower() == "/cancel":
            await reply.delete()
            await editable.edit("❌ Cancelled.")
            return

        raw = reply.text.strip() if reply.text else ""
        await reply.delete()

        try:
            source_id = int(raw)
        except ValueError:
            await editable.edit("❌ Invalid ID. Must be a numeric chat ID like `-1001234567890`.")
            return

        globals.set_setting("source_chat_id", source_id)
        await editable.edit(
            f"✅ **Source Chat updated!**\n\n"
            f"<blockquote>📡 Source Chat ID:\n`{source_id}`</blockquote>"
        )

    # ── /settarget ──────────────────────────────────────────────────────────
    @bot.on_message(filters.command("settarget") & filters.group)
    async def settarget_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if user_id not in AUTH_USERS:
            await m.reply_text(f"<blockquote>🙅 Not authorized. Your ID: `{user_id}`</blockquote>")
            return

        await m.delete()
        editable = await client.send_message(
            m.chat.id,
            "**⚙️ Set Target Channel/Group**\n\n"
            "Send the **Target Chat ID** where files will be forwarded TO.\n"
            "<blockquote>Example: `-1009876543210`\n"
            "⚠️ Bot must be **Admin** in the target channel/group.\n"
            "Send /cancel to abort.</blockquote>"
        )

        try:
            reply: Message = await bot.listen(m.chat.id, timeout=TIMEOUT)
        except asyncio.TimeoutError:
            await editable.edit("⏰ Timeout. Use /settarget to try again.")
            return

        if reply.text and reply.text.strip().lower() == "/cancel":
            await reply.delete()
            await editable.edit("❌ Cancelled.")
            return

        raw = reply.text.strip() if reply.text else ""
        await reply.delete()

        try:
            target_id = int(raw)
        except ValueError:
            await editable.edit("❌ Invalid ID. Must be a numeric chat ID like `-1009876543210`.")
            return

        globals.set_setting("target_chat_id", target_id)
        await editable.edit(
            f"✅ **Target Chat updated!**\n\n"
            f"<blockquote>🎯 Target Chat ID:\n`{target_id}`</blockquote>"
        )

    # ── /setkeywords ────────────────────────────────────────────────────────
    @bot.on_message(filters.command("setkeywords") & filters.group)
    async def setkeywords_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if user_id not in AUTH_USERS:
            await m.reply_text(f"<blockquote>🙅 Not authorized. Your ID: `{user_id}`</blockquote>")
            return

        await m.delete()
        editable = await client.send_message(
            m.chat.id,
            "**⚙️ Set Keyword Filter**\n\n"
            "Send one or more keywords, **one per line**.\n"
            "<blockquote>Rules:\n"
            "• Each keyword = 1 or 2 words only\n"
            "• Max 2 words per keyword (e.g. `Sobiya` or `Sobiya Ji`)\n"
            "• Files where caption contains ANY keyword will be forwarded\n"
            "• Other files will be SKIPPED\n\n"
            "Example:\n`Sobiya`\n`Sobiya Ji`\n`Batch01`\n\n"
            "Use /offkeywords to disable filtering.\n"
            "Send /cancel to abort.</blockquote>"
        )

        try:
            reply: Message = await bot.listen(m.chat.id, timeout=TIMEOUT)
        except asyncio.TimeoutError:
            await editable.edit("⏰ Timeout. Use /setkeywords to try again.")
            return

        if reply.text and reply.text.strip().lower() == "/cancel":
            await reply.delete()
            await editable.edit("❌ Cancelled.")
            return

        raw = reply.text.strip() if reply.text else ""
        await reply.delete()

        if not raw:
            await editable.edit("❌ Empty input. Use /setkeywords to try again.")
            return

        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        invalid = [l for l in lines if not validate_keyword(l)]
        if invalid:
            inv_str = "\n".join(f"`{i}`" for i in invalid)
            await editable.edit(
                f"❌ **Invalid keywords:**\n{inv_str}\n\n"
                "Each keyword must be 1 or 2 words only (letters/digits/underscore).\n"
                "Use /setkeywords to try again."
            )
            return

        globals.set_setting("keywords", lines)
        globals.set_setting("keywords_enabled", True)

        kw_str = "\n".join(f"• `{k}`" for k in lines)
        await editable.edit(
            f"✅ **Keywords set!**\n\n"
            f"<blockquote>🔍 Active Keywords:\n{kw_str}\n\n"
            f"Only videos & PDFs whose caption contains these keywords will be forwarded.</blockquote>"
        )

    # ── /offkeywords ────────────────────────────────────────────────────────
    @bot.on_message(filters.command("offkeywords") & filters.group)
    async def offkeywords_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if user_id not in AUTH_USERS:
            await m.reply_text(f"<blockquote>🙅 Not authorized. Your ID: `{user_id}`</blockquote>")
            return

        globals.set_setting("keywords_enabled", False)
        await m.reply_text(
            "✅ **Keywords filter disabled.**\n\n"
            "<blockquote>All videos & PDFs from source will be forwarded.</blockquote>"
        )

    # ── /setdelay ───────────────────────────────────────────────────────────
    @bot.on_message(filters.command("setdelay") & filters.group)
    async def setdelay_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if user_id not in AUTH_USERS:
            await m.reply_text(f"<blockquote>🙅 Not authorized. Your ID: `{user_id}`</blockquote>")
            return

        await m.delete()
        editable = await client.send_message(
            m.chat.id,
            "**⚙️ Set Forward Delay**\n\n"
            "Send the **delay in seconds** between each forwarded file.\n"
            "<blockquote>Default: `3` seconds\n"
            "Example: `3` or `5`\n"
            "Send /cancel to abort.</blockquote>"
        )

        try:
            reply: Message = await bot.listen(m.chat.id, timeout=TIMEOUT)
        except asyncio.TimeoutError:
            await editable.edit("⏰ Timeout. Use /setdelay to try again.")
            return

        if reply.text and reply.text.strip().lower() == "/cancel":
            await reply.delete()
            await editable.edit("❌ Cancelled.")
            return

        raw = reply.text.strip() if reply.text else ""
        await reply.delete()

        try:
            delay = int(raw)
            if delay < 1 or delay > 60:
                raise ValueError
        except ValueError:
            await editable.edit("❌ Invalid. Enter a number between 1 and 60.")
            return

        globals.set_setting("forward_delay", delay)
        await editable.edit(
            f"✅ **Delay updated!**\n\n"
            f"<blockquote>⏱️ Forward Delay: `{delay}` seconds</blockquote>"
        )

    # ── /viewsettings ───────────────────────────────────────────────────────
    @bot.on_message(filters.command("viewsettings") & filters.group)
    async def viewsettings_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if user_id not in AUTH_USERS:
            await m.reply_text(f"<blockquote>🙅 Not authorized. Your ID: `{user_id}`</blockquote>")
            return

        source_id    = globals.get_setting("source_chat_id", "Not set")
        target_id    = globals.get_setting("target_chat_id", "Not set")
        kw_enabled   = globals.get_setting("keywords_enabled", False)
        keywords     = globals.get_setting("keywords", [])
        delay        = globals.get_setting("forward_delay", 3)

        kw_status = "🟢 ON" if kw_enabled else "🔴 OFF (forward all)"
        if keywords and kw_enabled:
            kw_list = "\n".join(f"  • `{k}`" for k in keywords)
        else:
            kw_list = "  (none set)"

        text = (
            "**⚙️ Cinderella-Forwards — Current Settings**\n\n"
            f"<blockquote>"
            f"📡 **Source Chat ID:** `{source_id}`\n\n"
            f"🎯 **Target Chat ID:** `{target_id}`\n\n"
            f"⏱️ **Forward Delay:** `{delay}` seconds\n\n"
            f"🔍 **Keyword Filter:** {kw_status}\n"
            f"**Keywords:**\n{kw_list}"
            f"</blockquote>\n\n"
            "Use /setsource, /settarget, /setkeywords, /offkeywords, /setdelay to update."
        )
        await m.reply_text(text)
