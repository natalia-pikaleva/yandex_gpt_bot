import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
YANDEX_TOKEN = os.getenv('YANDEX_TOKEN', '')
YANDEX_CLIENT_ID = os.getenv('YANDEX_CLIENT_ID', '')
YANDEX_CLIENT_SECRET = os.getenv('YANDEX_CLIENT_SECRET', '')
EMAIL_YANDEX_PASSWORD = os.getenv('EMAIL_YANDEX_PASSWORD', '')
REDIRECT_URI = os.getenv('REDIRECT_URI', '')

PROMPT_REMOTE_PATH = "/prompt.txt"
PROMPT_LOCAL_PATH = "prompt.txt"

SERTIFICAT_PATH = os.getenv('SERTIFICAT_PATH', '')
DOWNLOADS_DIR = os.getenv('DOWNLOADS_DIR', '')
DATABASE_URL = os.getenv('DATABASE_URL', '')

ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.rtf', '.xlsx'}
MAX_FILE_SIZE_MB = 10

YANDEX_GPT_ID = os.getenv('YANDEX_GPT_ID', '')
YANDEX_GPT_API_KEY = os.getenv('YANDEX_GPT_API_KEY', '')
FOLDER_ID = os.getenv('FOLDER_ID', '')