import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
APP_PASSWORD_HASH = os.getenv("APP_PASSWORD_HASH", "")
TEACHER_PASSWORD_HASH = os.getenv("TEACHER_PASSWORD_HASH", "")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "change-me")
SESSION_EXPIRY_DAYS = int(os.getenv("SESSION_EXPIRY_DAYS", "30"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_TEACHER_ID = os.getenv("TELEGRAM_TEACHER_ID", "")

SIGNAL_API_URL = os.getenv("SIGNAL_API_URL", "http://localhost:8101")
SIGNAL_PHONE_NUMBER = os.getenv("SIGNAL_PHONE_NUMBER", "")
SIGNAL_TEACHER_NUMBER = os.getenv("SIGNAL_TEACHER_NUMBER", "")

DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "data/korean_app.db")
AUDIO_PATH = BASE_DIR / os.getenv("AUDIO_PATH", "data/audio")

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8100"))
