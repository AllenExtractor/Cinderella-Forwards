# Cinderella-Forwards 🚀

Smart Telegram Video & PDF Forwarder Bot with Keyword Filter

---

## Features

- **Forward Videos & PDFs** from source channel/group → target channel/group
- **Keyword Filter** — only forward files whose caption matches your keywords
- **3-second delay** (configurable) between each forwarded file
- **Public source** — bot joins source channel (no extra setup)
- **Private/Restricted source** — userbot login via SESSION_STRING
- **Bot must be Admin** in target channel/group
- All settings saved persistently (survive restarts)

---

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome message + current config |
| `/setsource` | Set source channel/group ID |
| `/settarget` | Set target channel/group ID |
| `/setkeywords` | Set keyword filter (1-2 words each) |
| `/offkeywords` | Disable keyword filter (forward all) |
| `/setdelay` | Set delay between forwards (seconds) |
| `/viewsettings` | View all current settings |
| `/broadcast` | (Owner only) Broadcast to all users |
| `/broadusers` | (Owner only) View all users/groups |

---

## Keyword Filter Rules

- Each keyword = **1 or 2 words** only
- Example one word: `Sobiya`
- Example two words: `Sobiya Ji`
- Files whose caption/filename contains **ANY** keyword → forwarded
- Files with **no** keyword match → **skipped**
- Use `/offkeywords` → forward ALL videos & PDFs

---

## Setup

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Your bot token from @BotFather |
| `API_ID` | ✅ | From my.telegram.org |
| `API_HASH` | ✅ | From my.telegram.org |
| `OWNER` | ✅ | Your Telegram user ID |
| `AUTH_USERS` | Optional | Comma-separated user IDs with access |
| `CREDIT` | Optional | Credit text shown in /start |
| `SESSION_STRING` | For private sources | Pyrogram session string |
| `FORWARD_DELAY` | Optional | Seconds between forwards (default: 3) |

### Generate SESSION_STRING (for private sources)

```bash
python3 generate_session.py
```

Enter your mobile number, OTP, and 2FA password when prompted.
Copy the printed session string to `SESSION_STRING` env variable.

### Deploy on Render

1. Push this repo to GitHub
2. Create a new **Web Service** on render.com
3. Use the provided `render.yaml`
4. Add all environment variables
5. Deploy!

### Run Locally

```bash
pip install -r requirements.txt
cp sample.env .env
# Edit .env with your values
python3 modules/main.py
```

---

## Source Channel Setup

| Source Type | Setup Required |
|---|---|
| Public channel | Add bot as member of source channel |
| Private channel | Set `SESSION_STRING` (userbot login) |
| Target (any) | Bot must be **Admin** in target channel/group |

---

## Project Structure

```
Cinderella-Forwards/
├── modules/
│   ├── main.py          — Bot entry point, Flask server
│   ├── vars.py          — Environment variables
│   ├── globals.py       — Settings persistence
│   ├── user_store.py    — User/group registry
│   ├── settings.py      — Settings commands
│   ├── forwarder.py     — Core forwarding engine
│   └── broadcast.py     — Broadcast module
├── generate_session.py  — Userbot session generator
├── requirements.txt
├── Dockerfile
├── Procfile
├── render.yaml
└── sample.env
```

---

Made with ❤️ by Team★Toxic
