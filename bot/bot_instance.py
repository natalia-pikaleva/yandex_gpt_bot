from aiogram import Bot, Dispatcher
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
# Словарь для хранения состояния пользователей (в реальном проекте лучше использовать БД или Redis)
user_states = {}