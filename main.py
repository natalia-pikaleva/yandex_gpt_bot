import asyncio
from bot.bot_init import init_bot
from bot.bot_instance import bot, dp
from database.db_init import init_db


async def main():
    """
    Основная асинхронная функция запуска бота.

    Выполняет:
    1. Инициализацию базы данных (создание таблиц при необходимости).
    2. Инициализацию бота и регистрация обработчиков.
    3. Запуск процесса опроса Telegram для получения обновлений.
    """
    await init_db()
    await init_bot(bot, dp)
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Start bot")
    asyncio.run(main())
    # import nltk
    # nltk.download('punkt')
