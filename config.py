import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
YANDEX_TOKEN = os.getenv('YANDEX_TOKEN', '')
YANDEX_CLIENT_ID = os.getenv('YANDEX_CLIENT_ID', '')
YANDEX_CLIENT_SECRET = os.getenv('YANDEX_CLIENT_SECRET', '')
EMAIL_YANDEX_PASSWORD = os.getenv('EMAIL_YANDEX_PASSWORD', '')
AUTHORIZATION_KEY = os.getenv('AUTHORIZATION_KEY', '')
REDIRECT_URI = os.getenv('REDIRECT_URI', '')
SERTIFICAT_PATH = os.getenv('SERTIFICAT_PATH', '')
DOWNLOADS_DIR = os.getenv('DOWNLOADS_DIR', '')
DATABASE_URL = os.getenv('DATABASE_URL', '')

ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.rtf', '.epub', '.fb2'}
MAX_FILE_SIZE_MB = 10
