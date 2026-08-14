import os
import sys
import time
import qrcode
import threading
import base64
import asyncio
from io import BytesIO
from datetime import datetime
from flask import Flask, render_template, send_file, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv

# Telethon imports
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

# ==================== CONFIG ====================
TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID', 6))
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH', 'eb066057c0321c1533836873b37168ad')
TELEGRAM_PHONE = os.getenv('TELEGRAM_PHONE', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
MONGODB_URI = os.getenv('MONGODB_URI')
PORT = int(os.getenv('PORT', 5000))
DEFAULT_TARGET = os.getenv('DEFAULT_TARGET', '')

if not MONGODB_URI:
    print("❌ MONGODB_URI not set")
    sys.exit(1)

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client['whatsapp_bot']
        self.settings = self.db['settings']
        self.bridges = self.db['bridges']
        print("✅ MongoDB Connected")

    def save_qr(self, qr_data):
        self.settings.update_one(
            {'key': 'qr_code'},
            {'$set': {'value': qr_data, 'timestamp': datetime.now()}},
            upsert=True
        )

    def get_qr(self):
        data = self.settings.find_one({'key': 'qr_code'})
        return data.get('value') if data else None

    def save_target(self, target):
        self.settings.update_one(
            {'key': 'target'},
            {'$set': {'value': target, 'updated': datetime.now()}},
            upsert=True
        )

    def get_target(self):
        data = self.settings.find_one({'key': 'target'})
        return data.get('value') if data else DEFAULT_TARGET

    def save_auth(self, status):
        self.settings.update_one(
            {'key': 'auth'},
            {'$set': {'value': status, 'updated': datetime.now()}},
            upsert=True
        )

    def get_auth(self):
        data = self.settings.find_one({'key': 'auth'})
        return data.get('value') if data else False

    def add_bridge(self, tg_chat_id, wa_target, chat_title=""):
        self.bridges.update_one(
            {'tg_chat_id': str(tg_chat_id)},
            {'$set': {
                'tg_chat_id': str(tg_chat_id),
                'wa_target': wa_target,
                'chat_title': chat_title,
                'updated': datetime.now()
            }},
            upsert=True
        )

    def remove_bridge(self, tg_chat_id):
        self.bridges.delete_one({'tg_chat_id': str(tg_chat_id)})

    def get_bridge(self, tg_chat_id):
        doc = self.bridges.find_one({'tg_chat_id': str(tg_chat_id)})
        return doc.get('wa_target') if doc else None

    def get_all_bridges(self):
        return list(self.bridges.find({}))

    def save_session(self, session_data):
        self.settings.update_one(
            {'key': 'session'},
            {'$set': {'value': session_data, 'updated': datetime.now()}},
            upsert=True
        )

    def get_session(self):
        data = self.settings.find_one({'key': 'session'})
        return data.get('value') if data else None

# ==================== WHATSAPP CONTROLLER ====================
class WhatsAppController:
    def __init__(self, db):
        self.db = db
        self.driver = None
        self.is_connected = False
        self.qr_ready = False

    def start_driver(self):
        """Start Chrome driver"""
        try:
            options = Options()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--remote-debugging-port=9222')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # Heroku check
            if 'DYNO' in os.environ:
                chrome_bin = os.environ.get('GOOGLE_CHROME_BIN', '/app/.apt/opt/google/chrome/chrome')
                if os.path.exists(chrome_bin):
                    options.binary_location = chrome_bin
                
                chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/app/.chromedriver/bin/chromedriver')
                if os.path.exists(chromedriver_path):
                    try:
                        service = Service(executable_path=chromedriver_path)
                        self.driver = webdriver.Chrome(service=service, options=options)
                        return True
                    except Exception as err:
                        print(f"⚠️ Default Heroku ChromeDriver failed ({err}), matching exact browser version...")

                # Auto-detect exact installed Chrome version
                try:
                    import subprocess
                    out = subprocess.check_output([options.binary_location, '--version']).decode('utf-8')
                    version = out.strip().split()[-1].split('.')[0]
                    service = Service(ChromeDriverManager(driver_version=version).install())
                except Exception:
                    service = Service(ChromeDriverManager().install())
            else:
                service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=options)
            return True
        except Exception as e:
            print(f"❌ Driver error: {e}")
            return False

    def get_qr(self):
        """Get WhatsApp QR code"""
        try:
            if not self.driver:
                if not self.start_driver():
                    return None
            
            self.driver.get('https://web.whatsapp.com')
            time.sleep(5)
            
            # Wait for QR code
            wait = WebDriverWait(self.driver, 30)
            qr_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-ref]'))
            )
            
            qr_ref = qr_element.get_attribute('data-ref')
            if qr_ref:
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(qr_ref)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                
                self.db.save_qr(img_base64)
                self.qr_ready = True
                
                threading.Thread(target=self.check_login, daemon=True).start()
                return img_base64
        except Exception as e:
            print(f"❌ QR error: {e}")
            return None

    def check_login(self):
        """Check if user scanned QR"""
        try:
            print("⏳ Waiting for QR scan...")
            wait = WebDriverWait(self.driver, 120)
            
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[contenteditable="true"][title="Search input textbox"]'))
            )
            
            self.is_connected = True
            self.db.save_auth(True)
            print("✅ WhatsApp Connected!")
            
        except Exception as e:
            print(f"❌ Login timeout: {e}")
            self.is_connected = False

    def send_message(self, to_target, message):
        """Send message to WhatsApp contact or group"""
        if not self.is_connected:
            return False
        try:
            search = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[contenteditable="true"][title="Search input textbox"]'))
            )
            # Clear search bar
            search.send_keys(Keys.CONTROL + "a")
            search.send_keys(Keys.BACKSPACE)
            time.sleep(0.5)
            
            search.send_keys(to_target)
            time.sleep(2)
            search.send_keys(Keys.ENTER)
            time.sleep(2)
            
            msg = self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"][title="Type a message"]')
            msg.send_keys(message)
            msg.send_keys(Keys.ENTER)
            return True
        except Exception as e:
            print(f"❌ Send error: {e}")
            return False

# ==================== FLASK WEB ====================
app = Flask(__name__)
db = Database()
wa = WhatsAppController(db)

@app.route('/')
def home():
    if not wa.is_connected and not wa.qr_ready:
        threading.Thread(target=wa.get_qr, daemon=True).start()
    return render_template('qr.html')

@app.route('/qr')
def get_qr():
    qr = db.get_qr()
    if not qr and not wa.is_connected and not wa.qr_ready:
        threading.Thread(target=wa.get_qr, daemon=True).start()
        time.sleep(2)
        qr = db.get_qr()
    if qr:
        qr_data = base64.b64decode(qr)
        return send_file(BytesIO(qr_data), mimetype='image/png')
    return "QR not ready", 404

@app.route('/qr-base64')
def get_qr_base64():
    qr = db.get_qr()
    if not qr and not wa.is_connected and not wa.qr_ready:
        threading.Thread(target=wa.get_qr, daemon=True).start()
    return jsonify({'qr': qr})

@app.route('/status')
def get_status():
    return jsonify({
        'connected': wa.is_connected,
        'qr_ready': wa.qr_ready,
        'auth': db.get_auth(),
        'bridges_count': len(db.get_all_bridges())
    })

# ==================== TELETHON USERBOT ====================
class TelethonUserbot:
    def __init__(self, api_id, api_hash, phone, wa, db):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.wa = wa
        self.db = db
        saved_session = db.get_session()
        self.session = StringSession(saved_session if saved_session else '')
        self.client = TelegramClient(self.session, self.api_id, self.api_hash)

    def setup_handlers(self):
        @self.client.on(events.NewMessage)
        async def message_handler(event):
            chat_id_str = str(event.chat_id)
            text = event.raw_text or ""
            
            # --- Command Handlers ---
            if text.startswith(('.id', '/id')):
                chat = await event.get_chat()
                title = getattr(chat, 'title', getattr(chat, 'first_name', 'Private Chat'))
                response = f"🆔 **Chat Info:**\n• **Title:** {title}\n• **Chat ID:** `{chat_id_str}`"
                await event.reply(response)
                return

            if text.startswith(('.addbridge', '/addbridge')):
                parts = text.split(maxsplit=2)
                if len(parts) < 3:
                    await event.reply("⚠️ **Usage:** `.addbridge <tg_chat_id> <wa_target_name_or_number>`")
                    return
                tg_id = parts[1]
                wa_target = parts[2]
                self.db.add_bridge(tg_id, wa_target, chat_title="Mapped Chat")
                await event.reply(f"✅ **Bridge added!**\nTelegram Chat `{tg_id}` ➡️ WhatsApp Target `{wa_target}`")
                return

            if text.startswith(('.delbridge', '/delbridge')):
                parts = text.split(maxsplit=1)
                if len(parts) < 2:
                    await event.reply("⚠️ **Usage:** `.delbridge <tg_chat_id>`")
                    return
                tg_id = parts[1]
                self.db.remove_bridge(tg_id)
                await event.reply(f"🗑️ **Bridge deleted for Telegram Chat `{tg_id}`**")
                return

            if text.startswith(('.listbridges', '/listbridges')):
                bridges = self.db.get_all_bridges()
                if not bridges:
                    await event.reply("ℹ️ No active bridge mappings.")
                    return
                msg = "🌉 **Active Telegram ➡️ WhatsApp Bridges:**\n\n"
                for b in bridges:
                    msg += f"• `{b.get('tg_chat_id')}` ➡️ `{b.get('wa_target')}`\n"
                await event.reply(msg)
                return

            if text.startswith(('.status', '/status')):
                status = "✅ Connected" if self.wa.is_connected else "❌ Disconnected"
                await event.reply(f"📱 **WhatsApp Web:** {status}")
                return

            if text.startswith(('.qr', '/qr')):
                await event.reply("⏳ Generating WhatsApp QR code...")
                qr = self.wa.get_qr()
                if qr:
                    qr_data = base64.b64decode(qr)
                    await self.client.send_file(
                        event.chat_id,
                        BytesIO(qr_data),
                        caption="📱 Scan this QR with WhatsApp Web"
                    )
                else:
                    await event.reply("❌ Failed to generate QR")
                return

            # --- Bridge Forwarding ---
            wa_target = self.db.get_bridge(chat_id_str)
            if not wa_target:
                # Check default target if configured
                default_target = self.db.get_target()
                if default_target and event.is_private:
                    wa_target = default_target
                else:
                    return

            if not self.wa.is_connected:
                print("⚠️ Message received but WhatsApp is not connected.")
                return

            # Obtain sender and chat title
            chat = await event.get_chat()
            chat_title = getattr(chat, 'title', getattr(chat, 'first_name', 'Group'))
            sender = await event.get_sender()
            sender_name = getattr(sender, 'first_name', 'User') if sender else 'User'

            formatted_msg = f"[{chat_title}] {sender_name}: {text}" if text else f"[{chat_title}] {sender_name} sent a media attachment."
            
            print(f"🔄 Forwarding from Telegram ({chat_title}) to WhatsApp ({wa_target})...")
            success = self.wa.send_message(wa_target, formatted_msg)
            if success:
                print(f"✅ Message forwarded to WhatsApp ({wa_target})")
            else:
                print(f"❌ Failed forwarding to WhatsApp ({wa_target})")

    async def start(self):
        self.setup_handlers()
        print("⚡ Connecting Telethon Telegram Userbot...")
        if self.phone:
            await self.client.start(phone=self.phone)
        else:
            await self.client.start()

        session_str = self.client.session.save()
        if session_str:
            self.db.save_session(session_str)
            print("💾 Telethon Session saved to MongoDB!")

        print("✅ Telethon Userbot Connected & Listening!")
        await self.client.run_until_disconnected()

# ==================== MAIN ====================
if __name__ == '__main__':
    print("🚀 Starting WhatsApp-Telegram Bridge (Telethon Userbot Edition)...")
    
    # Run Flask server in daemon thread
    def run_flask():
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Run Telethon asyncio loop
    userbot = TelethonUserbot(TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, wa, db)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(userbot.start())
