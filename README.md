# Telegram-WhatsApp Bridge (Telethon Userbot Edition) 🔗

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

A powerful bridge that forwards messages from **any Telegram group, channel, or direct chat** to **WhatsApp Web contacts or WhatsApp Groups**—without needing Telegram Bot admin rights!

## ✨ Features

- ⚡ **Telethon Userbot**: Connects as your personal Telegram account—no bot or chat admin permissions required.
- 🌉 **Multi-Bridge Mapping**: Map specific Telegram groups/channels to specific WhatsApp contacts or WhatsApp Groups.
- 📱 **WhatsApp Group Support**: Send to phone numbers or search for WhatsApp Group names (e.g. `"Work Group"`).
- 💾 **Permanent MongoDB Session**: Telethon userbot and WhatsApp sessions are stored in MongoDB Atlas, persisting across Heroku restarts.
- 🕹️ **Saved Messages Commands**: Control mapping via `.id`, `.addbridge`, `.listbridges`, `.delbridge`, `.status`, `.qr`.

---

## 🚀 One-Click Heroku Deployment

Click the button below to deploy directly to Heroku:

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

### Heroku Setup Steps:
1. Click the **Deploy to Heroku** button above.
2. Fill in your `MONGODB_URI` connection string (from MongoDB Atlas).
3. Fill in your `TELEGRAM_PHONE` (e.g. `+923001234567`).
4. Click **Deploy App**.
5. Once deployed, go to the **Resources** tab and enable the **`worker`** dyno.
6. Open logs (`heroku logs --tail -a your-app-name`) to complete the one-time Telethon login code.
