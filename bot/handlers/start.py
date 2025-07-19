from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext

from database.db_services import save_user_if_not_exists

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command('start'))
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    """
    Обработчик команды /start — приветствует пользователя и предоставляет основную информацию о возможностях бота.

    Отправляет приветственное сообщение с кратким описанием функционала:
    - Загрузка документов для создания базы знаний
    - Получение помощи через /help
    - Поиск информации в Википедии через /search_wiki
    - Подключение к облачному хранилищу (пока Яндекс.Диск)

    Также предлагает начать с загрузки файла или задать вопрос с помощью кнопки.

    Args:
        message (Message): Объект сообщения от пользователя, вызвавшего команду /start.
    """
    user_id = message.from_user.id
    await save_user_if_not_exists(session=session, user_id=user_id)
    await state.clear()

    text = (
        "👋 Добро пожаловать!\n\n"
        "Я — ваш AI-ассистент по технической документации и стандартам.\n\n"
        "Как это работает?\n"
        "1️⃣ Загрузите один или несколько документов с помощью команды /upload, либо воспользуйтесь командой /download_from_yandex_disk для загрузки с Яндекс.Диска.\n"
        "2️⃣ После загрузки всех файлов используйте команду /start_analysis — я проведу автоматический экспертный анализ ваших документов по встроенному чек-листу.\n"
        "3️⃣ Как только анализ завершится, вы получите подробный отчёт. Все отчёты всегда доступны через команду /reports.\n\n"
        "⏳ Узнать статус обработки можно с помощью команды /status.\n"
        "❓ Для получения справки напишите /help.\n\n"
        "Начните с загрузки файлов, чтобы приступить к анализу вашей документации!"
    )

    await message.answer(text)
