"""
forwarder.py — Cinderella-Forwards Core Engine

Handles:
  - Listening to source channel (bot for public, userbot for private)
  - Keyword matching in video/PDF captions
  - 3-second delay between each forward
  - Forwarding to target channel via bot (bot must be admin in target)

Keyword Rules:
  - Max 2 words per keyword (e.g. "Sobiya" or "Sobiya Ji")
  - Case-insensitive match anywhere in caption/filename
  - If keywords_enabled=False → forward ALL videos & PDFs
  - If keywords_enabled=True  → only forward files whose caption contains keyword
"""

import asyncio
import re
import logging

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import MessageMediaType
from pyrogram.errors import FloodWait, ChatWriteForbidden, UserNotParticipant

import globals
from vars import FORWARD_DELAY

logger = logging.getLogger(__name__)

# ── Keyword matching ─────────────────────────────────────────────────────────

def keyword_matches(text: str, keywords: list) -> bool:
    """
    Returns True if ANY keyword found in text (case-insensitive).
    Keyword can be 1 or 2 words. Matches whole-word or substring within caption.
    """
    if not text:
        return False
    text_lower = text.lower()
    for kw in keywords:
        kw_lower = kw.lower().strip()
        # Simple case-insensitive substring match
        # For "Sobiya Ji" — both words as a phrase must appear
        if kw_lower in text_lower:
            return True
    return False


def get_caption_text(message: Message) -> str:
    """Extract all text from message: caption or text or filename."""
    parts = []
    if message.caption:
        parts.append(message.caption)
    if message.text:
        parts.append(message.text)
    # Also check document filename
    if message.document and message.document.file_name:
        parts.append(message.document.file_name)
    if message.video and message.video.file_name:
        parts.append(message.video.file_name)
    return " ".join(parts)


def is_video_or_pdf(message: Message) -> bool:
    """Returns True if message is a video or PDF document."""
    if message.video:
        return True
    if message.document:
        mime = message.document.mime_type or ""
        fname = message.document.file_name or ""
        if "pdf" in mime.lower() or fname.lower().endswith(".pdf"):
            return True
    return False


# ── Forward single message ───────────────────────────────────────────────────

async def forward_single(client: Client, message: Message, target_id: int):
    """Forward a single message to target, with FloodWait handling."""
    try:
        await client.copy_message(
            chat_id     = target_id,
            from_chat_id = message.chat.id,
            message_id  = message.id
        )
        logger.info(f"[Forwarder] Forwarded msg {message.id} → {target_id}")
    except FloodWait as e:
        logger.warning(f"[Forwarder] FloodWait {e.value}s, sleeping...")
        await asyncio.sleep(e.value + 1)
        await client.copy_message(
            chat_id     = target_id,
            from_chat_id = message.chat.id,
            message_id  = message.id
        )
    except ChatWriteForbidden:
        logger.error(f"[Forwarder] Bot is not admin in target chat {target_id}!")
        raise
    except Exception as e:
        logger.error(f"[Forwarder] Failed to forward msg {message.id}: {e}")
        raise


# ── Register forwarder handler ───────────────────────────────────────────────

def register_forwarder_handlers(bot: Client, userbot: Client = None):
    """
    Register message handler on the appropriate client.
    - bot: used for public source channels
    - userbot: used for private source channels (if SESSION_STRING set)
    The handler listens on whichever client can access the source.
    """

    async def handle_message(client: Client, message: Message):
        # Get current settings
        source_id  = globals.get_setting("source_chat_id")
        target_id  = globals.get_setting("target_chat_id")
        kw_enabled = globals.get_setting("keywords_enabled", False)
        keywords   = globals.get_setting("keywords", [])
        delay      = globals.get_setting("forward_delay", FORWARD_DELAY)

        if not source_id or not target_id:
            return  # Not configured yet

        # Only process messages from the configured source
        if message.chat.id != int(source_id):
            return

        # Only forward videos and PDFs
        if not is_video_or_pdf(message):
            return

        # Keyword filter
        if kw_enabled and keywords:
            caption_text = get_caption_text(message)
            if not keyword_matches(caption_text, keywords):
                logger.info(
                    f"[Forwarder] Skipped msg {message.id} — no keyword match in: "
                    f"{caption_text[:80]!r}"
                )
                return

        # Forward with delay
        await asyncio.sleep(delay)

        try:
            if userbot and userbot.is_connected:
                # Userbot forwards (private source), bot copies to target
                await forward_single(userbot, message, target_id)
            else:
                await forward_single(bot, message, target_id)
        except Exception as e:
            logger.error(f"[Forwarder] Forward failed: {e}")

    # ── Register on userbot if available (private source) ────────────────
    if userbot:
        @userbot.on_message(filters.all & ~filters.service)
        async def userbot_handler(client: Client, message: Message):
            await handle_message(client, message)

    # ── Also register on bot (public source) ─────────────────────────────
    @bot.on_message(filters.all & ~filters.command("") & ~filters.service)
    async def bot_handler(client: Client, message: Message):
        # Only handle if source is configured and message is from source chat
        source_id = globals.get_setting("source_chat_id")
        if source_id and message.chat.id == int(source_id):
            await handle_message(client, message)
