"""
broadcast.py — Cinderella-Forwards Broadcast Module

Commands (PRIVATE, OWNER only):
  /broadcast  — Broadcast a message to all users/groups
  /broadusers — View all registered users/groups
"""

import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid

import user_store
from vars import OWNER

TIMEOUT = 300


def register_broadcast_handlers(bot: Client):

    @bot.on_message(filters.command("broadcast") & filters.private)
    async def broadcast_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if user_id != OWNER:
            await m.reply_text("🙅 Owner only command.")
            return

        editable = await m.reply_text(
            "**📢 Broadcast**\n\n"
            "Reply to or send a message to broadcast.\n"
            "<blockquote>Send /cancel to abort.</blockquote>"
        )

        try:
            reply: Message = await bot.listen(m.chat.id, timeout=TIMEOUT)
        except asyncio.TimeoutError:
            await editable.edit("⏰ Timeout.")
            return

        if reply.text and reply.text.strip().lower() == "/cancel":
            await reply.delete()
            await editable.edit("❌ Cancelled.")
            return

        targets = user_store.get_all_targets()
        done, fail = 0, 0

        await editable.edit(f"📤 Broadcasting to {len(targets)} targets...")

        for chat_id in targets:
            try:
                await reply.copy(chat_id)
                done += 1
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    await reply.copy(chat_id)
                    done += 1
                except Exception:
                    fail += 1
            except (InputUserDeactivated, UserIsBlocked, PeerIdInvalid):
                fail += 1
            except Exception:
                fail += 1
            await asyncio.sleep(0.3)

        await editable.edit(
            f"✅ **Broadcast done!**\n\n"
            f"<blockquote>✔️ Success: `{done}`\n❌ Failed: `{fail}`</blockquote>"
        )

    @bot.on_message(filters.command("broadusers") & filters.private)
    async def broadusers_cmd(client: Client, m: Message):
        user_id = m.from_user.id if m.from_user else 0
        if user_id != OWNER:
            await m.reply_text("🙅 Owner only command.")
            return

        users  = user_store.get_all_users()
        groups = user_store.get_all_groups()

        text = (
            f"**📊 Registered Targets**\n\n"
            f"<blockquote>👤 Users: `{len(users)}`\n"
            f"👥 Groups: `{len(groups)}`\n"
            f"📦 Total: `{len(users) + len(groups)}`</blockquote>"
        )
        await m.reply_text(text)
