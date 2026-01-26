import os
from pathlib import Path
from dotenv import load_dotenv
import pytz

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PIN = os.getenv("ADMIN_PIN", "0000")
DB_PATH = BASE_DIR / "coffee_shop.db"
WEB_APP_URL = "https://akku-2325.github.io/coffee-frontend/frontend/?update=1"
TZ = pytz.timezone("Asia/Almaty")