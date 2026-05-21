"""
generate_session.py — Generate Pyrogram Session String for Userbot

Run this ONCE locally to generate your SESSION_STRING:
  python3 generate_session.py

Then copy the printed session string into your environment variable:
  SESSION_STRING=your_generated_string_here

This is needed for accessing PRIVATE/RESTRICTED source channels.
"""

import asyncio
from pyrogram import Client
from vars import API_ID, API_HASH

print("""
╔══════════════════════════════════════════════════════════╗
║     Cinderella-Forwards — Userbot Session Generator      ║
╠══════════════════════════════════════════════════════════╣
║  This generates a SESSION_STRING for your Telegram       ║
║  account so the bot can access private source channels.  ║
║                                                          ║
║  You will need:                                          ║
║    1. Your mobile number (with country code)             ║
║    2. OTP from Telegram                                  ║
║    3. 2FA password (if enabled)                          ║
╚══════════════════════════════════════════════════════════╝
""")

async def main():
    async with Client(
        ":memory:",
        api_id   = API_ID,
        api_hash = API_HASH
    ) as app:
        session_string = await app.export_session_string()
        print("\n" + "="*60)
        print("✅ YOUR SESSION STRING (copy this to SESSION_STRING env var):")
        print("="*60)
        print(session_string)
        print("="*60)
        print("\n⚠️  Keep this string SECRET. It gives full access to your account.")
        print("   Set it as SESSION_STRING environment variable in your deployment.\n")

asyncio.run(main())
