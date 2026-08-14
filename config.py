import os
from dotenv import load_dotenv

load_dotenv()

# ٹیلیگرام کنفیگریشن
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID', 6))
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH', 'eb066057c0321c1533836873b37168ad')
TELEGRAM_PHONE = os.getenv('TELEGRAM_PHONE', '')

# مونگو ڈی بی کنفیگریشن
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DB_NAME = 'whatsapp_bot'
COLLECTION_NAME = 'sessions'

# واٹس ایپ کنفیگریشن
DEFAULT_TARGET = os.getenv('DEFAULT_TARGET', '')  # مثلاً 923001234567

# ایڈمن آئی ڈیز (کاما سے الگ کریں)
ADMIN_IDS = os.getenv('ADMIN_IDS', '').split(',') if os.getenv('ADMIN_IDS') else []

# پورٹ نمبر
PORT = int(os.getenv('PORT', 5000))
