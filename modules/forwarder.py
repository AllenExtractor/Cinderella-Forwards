"""
forwarder.py — Cinderella-Forwards Core Engine

New features:
  - /forward command triggers bulk historical forwarding
  - Skip message number support
  - Live progress display (like the screenshot)
  - Stop button mid-forwarding
  - Status messages: Started / Completed / Stopped
  - Per-user custom bot support
  - Works in both group and private/DM chats
"""

import asyncio
import re
import logging
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from pyrogram.enums import MessageMediaType
from pyrogram.errors import FloodWait, ChatWriteForbidden, UserNotParticipant

import globals
import bot_manager
from vars import FORWARD_DELAY, AUTH_USERS

logger = logging.getLogger(__name__)

# ── Active forward sessions: chat_id -> asyncio.Task ─────────────────────────
_active_tasks: dict[int, asyncio.Task] = {}
_stop_flags: dict[int, bool] = {}

# ── Keyword matching ──────────────────────────────────────────────────────────

def keyword_matches(text: str, keywords: list) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower().strip() in text_lower:
            return True
    return False


def get_caption_text(message: Message) -> str:
    parts = []
    if message.caption:
        parts.append(message.caption)
    if message.text:
        parts.append(message.text)
    if message.document and message.document.file_name:
        parts.append(message.document.file_name)
    if message.video and message.video.file_name:
        parts.append(message.video.file_name)
    return " ".join(parts)


def is_forwardable(message: Message) -> bool:
    """Videos, PDFs, and text messages."""
    if message.video:
        return True
    if message.document:
        mime = message.document.mime_type or ""
        fname = message.document.file_name or ""
        if "pdf" in mime.lower() or fname.lower().endswith(".pdf"):
            return True
    if message.text:
        return True
    return False


# ── Parse skip number from link or raw number ─────────────────────────────────

def parse_skip_number(text: str) -> int | None:
    """
    Accepts:
      - Raw number: "1148"
      - Private link: https://t.me/c/3746388346/1148
      - Public link: https://t.me/chekreportbro/101
    Returns the message number, or None if invalid.
    """
    text = text.strip()
    # Raw number
    if text.isdigit():
        return int(text)
    # t.me link
    match = re.search(r"t\.me/(?:c/\d+|[\w]+)/(\d+)", text)
    if match:
        return int(match.group(1))
    return None


# ── Live status message builder ───────────────────────────────────────────────

def build_status_text(
    fetched: int,
    remaining: int,
    forwarded: int,
    duplicates: int,
    deleted: int,
    skipped: int,
    filtered: int,
    status: str,
    percentage: float
) -> str:
    bar_len = 20
    filled = int(bar_len * percentage / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    return (
        f"**〔 FORWARD STATUS 〕**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**≫◇ FETCHED MESSAGES:** `{fetched}`\n"
        f"**≫◇ REMAINING MESSAGES:** `{remaining}`\n"
        f"**≫◇ SUCCESSFULLY FORWARDED:** `{forwarded}`\n"
        f"**≫◇ DUPLICATE MESSAGES:** `{duplicates}`\n"
        f"**≫◇ DELETED MESSAGES:** `{deleted}`\n"
        f"**≫◇ SKIPPED MESSAGES:** `{skipped}`\n"
        f"**≫◇ FILTERED MESSAGES:** `{filtered}`\n"
        f"**≫◇ CURRENT STATUS:** `{status}`\n"
        f"**≫◇ PERCENTAGE:** `{percentage:.1f}%`\n"
        f"`[{bar}]`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )


def stop_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛑 Stop Forwarding", callback_data=f"stop_forward:{chat_id}")]
    ])


# ── Main forward engine ───────────────────────────────────────────────────────

async def run_forward(
    main_bot: Client,
    user_bot: Client,
    notify_chat: int,
    source_id: int,
    target_id: int,
    skip_msg_id: int,
    status_msg: Message,
    user_id: int,
    use_custom_bot: bool
):
    """
    Bulk forward engine. Reads history from source, skips up to skip_msg_id,
    forwards matching messages to target with live progress updates.
    """
    kw_enabled = globals.get_setting("keywords_enabled", False)
    keywords   = globals.get_setting("keywords", [])
    delay      = globals.get_setting("forward_delay", FORWARD_DELAY)

    reader = user_bot  # userbot reads source
    sender = main_bot  # main bot sends to target (or custom bot if set)

    # Try custom bot for sending
    if use_custom_bot:
        custom_bot = await bot_manager.get_or_create_bot(user_id)
        if custom_bot:
            sender = custom_bot

    # Send "started" notification
    try:
        started_msg = await sender.send_message(
            target_id,
            "🚀 **Cinderella-Forwards — Forwarding Started!**\n\n"
            f"📡 Source → 🎯 Target\n"
            f"⏱️ Running... please wait."
        )
    except Exception as e:
        logger.warning(f"[Forwarder] Could not send start message to target: {e}")
        started_msg = None

    # Collect messages from source
    all_messages = []
    async for msg in reader.get_chat_history(source_id):
        all_messages.append(msg)

    all_messages.reverse()  # oldest first

    # Apply skip
    if skip_msg_id > 0:
        all_messages = [m for m in all_messages if m.id >= skip_msg_id]

    total = len(all_messages)
    fetched = total
    forwarded = 0
    duplicates = 0
    deleted_count = 0
    skipped = 0
    filtered = 0
    last_update = 0

    _stop_flags[notify_chat] = False

    for i, msg in enumerate(all_messages):
        # Check stop flag
        if _stop_flags.get(notify_chat, False):
            break

        remaining = total - i - 1
        percentage = ((i + 1) / total * 100) if total > 0 else 100

        # Filter
        if not is_forwardable(msg):
            deleted_count += 1
            continue

        if kw_enabled and keywords:
            caption_text = get_caption_text(msg)
            if not keyword_matches(caption_text, keywords):
                filtered += 1
                # Update status every 10 messages
                if i - last_update >= 10 or i == total - 1:
                    try:
                        await status_msg.edit_text(
                            build_status_text(fetched, remaining, forwarded, duplicates, deleted_count, skipped, filtered, "filtering...", percentage),
                            reply_markup=stop_keyboard(notify_chat)
                        )
                        last_update = i
                    except Exception:
                        pass
                continue

        # Forward
        await asyncio.sleep(delay)

        if _stop_flags.get(notify_chat, False):
            break

        try:
            await sender.copy_message(
                chat_id=target_id,
                from_chat_id=msg.chat.id,
                message_id=msg.id
            )
            forwarded += 1
        except FloodWait as e:
            logger.warning(f"[Forwarder] FloodWait {e.value}s")
            await asyncio.sleep(e.value + 1)
            try:
                await sender.copy_message(
                    chat_id=target_id,
                    from_chat_id=msg.chat.id,
                    message_id=msg.id
                )
                forwarded += 1
            except Exception as e2:
                logger.error(f"[Forwarder] Retry failed: {e2}")
                skipped += 1
        except Exception as e:
            logger.error(f"[Forwarder] Forward failed msg {msg.id}: {e}")
            skipped += 1

        # Live update every 5 messages
        if i - last_update >= 5 or i == total - 1:
            try:
                await status_msg.edit_text(
                    build_status_text(fetched, remaining, forwarded, duplicates, deleted_count, skipped, filtered, "forwarding...", percentage),
                    reply_markup=stop_keyboard(notify_chat)
                )
                last_update = i
            except Exception:
                pass

    # Done
    was_stopped = _stop_flags.get(notify_chat, False)
    final_status = "stopped ⛔" if was_stopped else "completed ✅"
    final_pct = (forwarded / fetched * 100) if fetched > 0 else 100

    try:
        await status_msg.edit_text(
            build_status_text(fetched, 0, forwarded, duplicates, deleted_count, skipped, filtered, final_status, final_pct if not was_stopped else final_pct)
        )
    except Exception:
        pass

    # Completion notification to target
    if was_stopped:
        notif_text = (
            "⛔ **Forwarding Stopped!**\n\n"
            f"📊 Forwarded `{forwarded}` / `{fetched}` messages\n"
            "— Cinderella-Forwards 🌸"
        )
    else:
        notif_text = (
            "✅ **Forwarding Completed!**\n\n"
            f"📊 Successfully forwarded `{forwarded}` messages\n"
            f"🔍 Filtered: `{filtered}` | ⏭️ Skipped: `{skipped}`\n"
            "— Cinderella-Forwards 🌸"
        )

    try:
        await sender.send_message(target_id, notif_text)
    except Exception as e:
        logger.warning(f"[Forwarder] Could not send completion message: {e}")

    # Clean up task
    _active_tasks.pop(notify_chat, None)
    _stop_flags.pop(notify_chat, None)


# ── Register handlers ─────────────────────────────────────────────────────────

def register_forwarder_handlers(bot: Client, userbot: Client = None):

    def is_auth(user_id: int) -> bool:
        return user_id in AUTH_USERS

    # ── /forward ─────────────────────────────────────────────────────────────
    @bot.on_message(filters.command("forward") & (filters.group | filters.private))
    async def forward_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if not is_auth(user_id):
            await m.reply_text(f"<blockquote>🙅 Not authorized. Your ID: `{user_id}`</blockquote>")
            return

        # Check if already forwarding
        if m.chat.id in _active_tasks and not _active_tasks[m.chat.id].done():
            await m.reply_text("⚠️ A forwarding session is already running in this chat.\nPress **🛑 Stop** first.")
            return

        source_id = globals.get_setting("source_chat_id")
        target_id = globals.get_setting("target_chat_id")

        if not source_id or not target_id:
            await m.reply_text(
                "❌ **Source or Target not set!**\n\n"
                "Use ⚙️ Settings → Set Source / Set Target first."
            )
            return

        source_id = int(source_id)
        target_id = int(target_id)

        # Determine reader client
        user_specific_session = bot_manager.get_session_string(user_id)
        user_specific_bot = bot_manager.get_bot_token(user_id)

        # Figure out reader
        reader = None
        if user_specific_session:
            reader = await bot_manager.get_or_create_userbot(user_id)
        if reader is None and userbot and userbot.is_connected:
            reader = userbot
        if reader is None:
            # Try using bot itself (public source only)
            reader = client

        # Check bot permissions in target
        await m.reply_text("🔍 Checking permissions...")

        # Verify sender is admin in target
        sender = client
        if user_specific_bot:
            custom = await bot_manager.get_or_create_bot(user_id)
            if custom:
                sender = custom

        try:
            chat_member = await sender.get_chat_member(target_id, "me")
            from pyrogram.enums import ChatMemberStatus
            if chat_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                await m.reply_text(
                    "❌ **Bot is not admin in target chat!**\n\n"
                    "Please make the bot admin in the target channel/group first."
                )
                return
        except Exception as e:
            # Non-fatal for groups where bot might still have rights
            logger.warning(f"[Forwarder] Admin check failed: {e}")

        # Ask skip number
        skip_prompt = await m.reply_text(
            "⏭️ **Skip Messages?**\n\n"
            "Send the **message number** to start forwarding from that point.\n"
            "<blockquote>• For private channel: just send the message number (e.g. `1148`)\n"
            "• For public channel: just send the message number (e.g. `101`)\n"
            "• To forward everything: send `none`</blockquote>"
        )

        try:
            skip_reply = await bot.listen(m.chat.id, timeout=120)
        except asyncio.TimeoutError:
            await skip_prompt.edit("⏰ Timeout. Use /forward to try again.")
            return

        skip_text = skip_reply.text.strip() if skip_reply.text else "none"
        await skip_reply.delete()

        skip_msg_id = 0
        if skip_text != "none":
            parsed = parse_skip_number(skip_text)
            if parsed is None:
                await skip_prompt.edit(
                    "❌ Invalid input. Send a number like `1148` or `none`.\n"
                    "Use /forward to try again."
                )
                return
            skip_msg_id = parsed

        await skip_prompt.delete()

        # Show initial status
        status_msg = await m.reply_text(
            build_status_text(0, 0, 0, 0, 0, 0, 0, "starting...", 0),
            reply_markup=stop_keyboard(m.chat.id)
        )

        # Launch background task
        task = asyncio.create_task(
            run_forward(
                main_bot=bot,
                user_bot=reader,
                notify_chat=m.chat.id,
                source_id=source_id,
                target_id=target_id,
                skip_msg_id=skip_msg_id,
                status_msg=status_msg,
                user_id=user_id,
                use_custom_bot=bool(user_specific_bot)
            )
        )
        _active_tasks[m.chat.id] = task

    # ── Stop button ───────────────────────────────────────────────────────────
    @bot.on_callback_query(filters.regex(r"^stop_forward:(\-?\d+)$"))
    async def stop_forward_cb(client: Client, cq: CallbackQuery):
        chat_id = int(cq.data.split(":")[1])
        user_id = cq.from_user.id if cq.from_user else 0

        if not is_auth(user_id):
            await cq.answer("🙅 Not authorized!", show_alert=True)
            return

        if chat_id in _active_tasks and not _active_tasks[chat_id].done():
            _stop_flags[chat_id] = True
            await cq.answer("⛔ Stop signal sent!", show_alert=False)
            await cq.message.edit_reply_markup(reply_markup=None)
        else:
            await cq.answer("No active forwarding session.", show_alert=True)

    # ── Live listener (new messages from source) ──────────────────────────────
    if userbot:
        @userbot.on_message(filters.all & ~filters.service)
        async def userbot_live(client: Client, message: Message):
            await _handle_live(bot, client, message)

    @bot.on_message(filters.all & ~filters.command("") & ~filters.service)
    async def bot_live(client: Client, message: Message):
        source_id = globals.get_setting("source_chat_id")
        if source_id and message.chat.id == int(source_id):
            await _handle_live(client, client, message)


async def _handle_live(bot: Client, reader: Client, message: Message):
    """Handle real-time new messages from source."""
    source_id  = globals.get_setting("source_chat_id")
    target_id  = globals.get_setting("target_chat_id")
    kw_enabled = globals.get_setting("keywords_enabled", False)
    keywords   = globals.get_setting("keywords", [])
    delay      = globals.get_setting("forward_delay", FORWARD_DELAY)

    if not source_id or not target_id:
        return
    if message.chat.id != int(source_id):
        return
    if not is_forwardable(message):
        return

    if kw_enabled and keywords:
        if not keyword_matches(get_caption_text(message), keywords):
            return

    await asyncio.sleep(delay)

    try:
        await bot.copy_message(
            chat_id=int(target_id),
            from_chat_id=message.chat.id,
            message_id=message.id
        )
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        try:
            await bot.copy_message(
                chat_id=int(target_id),
                from_chat_id=message.chat.id,
                message_id=message.id
            )
        except Exception:
            pass
    except Exception as e:
        logger.error(f"[Live] Forward failed: {e}")
