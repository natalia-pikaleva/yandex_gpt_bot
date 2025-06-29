import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
import bot.handlers as handlers
from aiogram import BaseMiddleware
from database.db_init import async_session

logging.basicConfig(level=logging.INFO)


class DbSessionMiddleware(BaseMiddleware):
    """
    Middleware для создания и передачи асинхронной сессии базы данных в обработчики.

    При каждом входящем событии создаёт новую сессию async_session,
    добавляет её в словарь data под ключом "session" и передаёт дальше по цепочке обработчиков.

    Это позволяет использовать одну сессию БД на время обработки одного события.
    """

    async def __call__(self, handler, event, data):
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)


async def register_routers(dp: Dispatcher):
    """
    Регистрирует все роутеры (обработчики) в диспетчере.

    Подключает модули с обработчиками команд и сообщений к объекту Dispatcher.

    Args:
        dp (Dispatcher): Экземпляр диспетчера aiogram.
    """
    dp.include_router(handlers.help.router)
    dp.include_router(handlers.start.router)
    dp.include_router(handlers.download_from_Yandex_disk.router)
    dp.include_router(handlers.download_file.router)
    dp.include_router(handlers.reset.router)
    dp.include_router(handlers.search.router)
    dp.include_router(handlers.upload.router)
    dp.include_router(handlers.wiki.router)
    dp.include_router(handlers.message.router)


async def set_commands(bot: Bot):
    """
    Устанавливает список команд бота, отображаемых в интерфейсе Telegram.

    Определяет основные команды с их описаниями, которые будут доступны пользователю в меню.

    Args:
        bot (Bot): Экземпляр бота aiogram.
    """
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="upload", description="Отправить файл для загрузки"),
        BotCommand(command="download_from_yandex_disk", description="Загрузить файл с Яндекс.Диска"),
        BotCommand(command="search_with_ai", description="Поиск с AI"),
        BotCommand(command="search_wiki", description="Поиск в Википедии"),
        BotCommand(command="reset", description="Сбросить текущий контекст"),
        BotCommand(command="help", description="Помощь и инструкции"),
    ]
    await bot.set_my_commands(commands)


async def init_bot(bot: Bot, dp: Dispatcher):
    """
    Инициализирует бота и диспетчер.

    - Регистрирует middleware для работы с сессией базы данных.
    - Устанавливает команды бота.
    - Регистрирует все роутеры (обработчики).

    Args:
        bot (Bot): Экземпляр бота aiogram.
        dp (Dispatcher): Экземпляр диспетчера aiogram.
    """
    dp.message.middleware(DbSessionMiddleware())
    dp.update.middleware(DbSessionMiddleware())
    await set_commands(bot)
    await register_routers(dp)
