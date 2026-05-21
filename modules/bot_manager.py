"""
bot_manager.py — Per-user custom Bot & Userbot management

Each user can register:
  1. Their own Bot (via BotFather token) — used for forwarding
  2. Their own Userbot (via phone number login) — used for reading private sources

Data stored in bot_store.json
"""

import json
import os
import asyncio
import logging

from pyrogram import Client
from pyrogram.errors import (
    ApiIdInvalid, PhoneNumberInvalid, PhoneCodeInvalid,
    PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid,
    AccessTokenInvalid, AuthKeyUnregistered
)

from vars import API_ID, API_HASH

logger = logging.getLogger(__name__)

_STORE = "bot_store.json"

# ── Storage ──────────────────────────────────────────────────────────────────

def _load() -> dict:
    if os.path.exists(_STORE):
        try:
            with open(_STORE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save(data: dict):
    with open(_STORE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id: int) -> dict:
    return _load().get(str(user_id), {})

def set_user_data(user_id: int, data: dict):
    store = _load()
    store[str(user_id)] = data
    _save(store)

def get_bot_token(user_id: int) -> str:
    return get_user_data(user_id).get("bot_token", "")

def get_session_string(user_id: int) -> str:
    return get_user_data(user_id).get("session_string", "")

def save_bot_token(user_id: int, token: str):
    data = get_user_data(user_id)
    data["bot_token"] = token
    set_user_data(user_id, data)

def save_session_string(user_id: int, session: str):
    data = get_user_data(user_id)
    data["session_string"] = session
    set_user_data(user_id, data)


# ── Active clients cache ─────────────────────────────────────────────────────
# Maps user_id -> {"bot": Client | None, "userbot": Client | None}
_active = {}

async def get_or_create_bot(user_id: int) -> Client | None:
    token = get_bot_token(user_id)
    if not token:
        return None
    if user_id in _active and _active[user_id].get("bot"):
        c = _active[user_id]["bot"]
        if c.is_connected:
            return c
    try:
        c = Client(
            f"user_bot_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=token,
            in_memory=True
        )
        await c.start()
        if user_id not in _active:
            _active[user_id] = {}
        _active[user_id]["bot"] = c
        logger.info(f"[BotManager] Started bot for user {user_id}")
        return c
    except Exception as e:
        logger.error(f"[BotManager] Failed to start bot for {user_id}: {e}")
        return None

async def get_or_create_userbot(user_id: int) -> Client | None:
    session = get_session_string(user_id)
    if not session:
        return None
    if user_id in _active and _active[user_id].get("userbot"):
        c = _active[user_id]["userbot"]
        if c.is_connected:
            return c
    try:
        c = Client(
            f"userbot_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session,
            in_memory=True
        )
        await c.start()
        if user_id not in _active:
            _active[user_id] = {}
        _active[user_id]["userbot"] = c
        logger.info(f"[BotManager] Started userbot for user {user_id}")
        return c
    except Exception as e:
        logger.error(f"[BotManager] Failed to start userbot for {user_id}: {e}")
        return None

async def stop_user_clients(user_id: int):
    if user_id in _active:
        for name, client in _active[user_id].items():
            try:
                if client and client.is_connected:
                    await client.stop()
            except Exception:
                pass
        del _active[user_id]


# ── Bot token validation ─────────────────────────────────────────────────────

async def validate_bot_token(token: str) -> tuple[bool, str]:
    """Returns (success, bot_username_or_error)"""
    try:
        c = Client(
            "tmp_validate",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=token,
            in_memory=True
        )
        await c.start()
        me = await c.get_me()
        await c.stop()
        return True, f"@{me.username}"
    except AccessTokenInvalid:
        return False, "Invalid bot token (revoked or wrong)"
    except Exception as e:
        return False, str(e)


# ── Userbot login via phone ──────────────────────────────────────────────────

async def login_userbot_flow(main_bot: Client, user_id: int, chat_id: int) -> tuple[bool, str]:
    """
    Interactive phone-number login flow.
    Returns (success, session_string_or_error)
    """
    TIMEOUT = 300

    # Ask phone
    ask = await main_bot.send_message(
        chat_id,
        "📱 **Enter your phone number** in international format:\n"
        "<blockquote>Example: `+91 9512345678`\n"
        "Send /cancel to abort.</blockquote>"
    )
    try:
        reply = await main_bot.listen(chat_id, timeout=TIMEOUT)
    except asyncio.TimeoutError:
        await ask.delete()
        return False, "⏰ Timeout"

    if reply.text and reply.text.strip() == "/cancel":
        await reply.delete()
        await ask.delete()
        return False, "❌ Cancelled"

    phone = reply.text.strip()
    await reply.delete()
    await ask.edit("⏳ Sending OTP...")

    client = Client(
        f"userbot_login_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    )
    await client.connect()

    try:
        code_obj = await client.send_code(phone)
    except ApiIdInvalid:
        await client.disconnect()
        await ask.edit("❌ API_ID/API_HASH invalid.")
        return False, "API invalid"
    except PhoneNumberInvalid:
        await client.disconnect()
        await ask.edit("❌ Phone number invalid. No Telegram account found.")
        return False, "Phone invalid"
    except Exception as e:
        await client.disconnect()
        await ask.edit(f"❌ Error: {e}")
        return False, str(e)

    # Ask OTP
    await ask.edit(
        "🔑 **Enter the OTP** you received from Telegram:\n"
        "<blockquote>Format: `1 2 3 4 5` (with spaces)\n"
        "Send /cancel to abort.</blockquote>"
    )
    try:
        otp_reply = await main_bot.listen(chat_id, timeout=TIMEOUT)
    except asyncio.TimeoutError:
        await client.disconnect()
        await ask.delete()
        return False, "⏰ OTP Timeout"

    if otp_reply.text and otp_reply.text.strip() == "/cancel":
        await otp_reply.delete()
        await ask.delete()
        await client.disconnect()
        return False, "❌ Cancelled"

    otp = otp_reply.text.strip().replace(" ", "")
    await otp_reply.delete()
    await ask.edit("⏳ Verifying OTP...")

    try:
        await client.sign_in(phone, code_obj.phone_code_hash, otp)
    except PhoneCodeInvalid:
        await client.disconnect()
        await ask.edit("❌ Wrong OTP. Try again with /addbot")
        return False, "Wrong OTP"
    except PhoneCodeExpired:
        await client.disconnect()
        await ask.edit("❌ OTP expired. Try again with /addbot")
        return False, "OTP expired"
    except SessionPasswordNeeded:
        # 2FA
        await ask.edit(
            "🔐 **2-Step Verification enabled.**\n"
            "Send your **2FA password**:\n"
            "<blockquote>Send /cancel to abort.</blockquote>"
        )
        try:
            pass_reply = await main_bot.listen(chat_id, timeout=TIMEOUT)
        except asyncio.TimeoutError:
            await client.disconnect()
            await ask.delete()
            return False, "⏰ 2FA Timeout"

        if pass_reply.text and pass_reply.text.strip() == "/cancel":
            await pass_reply.delete()
            await ask.delete()
            await client.disconnect()
            return False, "❌ Cancelled"

        password = pass_reply.text.strip()
        await pass_reply.delete()
        await ask.edit("⏳ Checking 2FA password...")

        try:
            await client.check_password(password=password)
        except PasswordHashInvalid:
            await client.disconnect()
            await ask.edit("❌ Wrong 2FA password. Try /addbot again.")
            return False, "Wrong 2FA"
        except Exception as e:
            await client.disconnect()
            await ask.edit(f"❌ 2FA error: {e}")
            return False, str(e)
    except Exception as e:
        await client.disconnect()
        await ask.edit(f"❌ Sign-in error: {e}")
        return False, str(e)

    # Export session
    try:
        session_string = await client.export_session_string()
        # Send to saved messages
        await client.send_message("me", f"✅ **Cinderella-Forwards Userbot Added!**\n\n`{session_string}`\n\n⚠️ Don't share this with anyone!")
        await client.disconnect()
        await ask.edit("✅ **User Bot added successfully!** Session saved to your Saved Messages.")
        return True, session_string
    except Exception as e:
        await client.disconnect()
        await ask.edit(f"❌ Session export failed: {e}")
        return False, str(e)
