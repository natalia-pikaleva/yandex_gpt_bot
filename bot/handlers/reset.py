from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import main_keyboard
from database.db_services import delete_dialog_history
from bot.bot_instance import user_states

router = Router()
logger = logging.getLogger(__name__)


async def process_reset(user_id: int, send_func, session: AsyncSession):
    """
    Общая логика сброса контекста пользователя.

    Args:
        user_id (int): Telegram user_id пользователя.
        send_func (Callable): Функция отправки сообщения (message.answer или call.message.answer).
        session (AsyncSession): Асинхронная сессия для работы с базой данных.
    """
    # 1. Удаляем историю диалога пользователя из базы
    result = await delete_dialog_history(user_id, session)
    if result:
        await send_func("Произошла ошибка при сбросе истории. Попробуйте позже.",
                        reply_markup=main_keyboard)
        return

    # 2. Сбрасываем состояние пользователя в памяти
    if user_id in user_states:
        user_states[user_id] = None

    text = "♻️ Контекст успешно сброшен. Вы можете начать новую сессию."
    await send_func(text, reply_markup=main_keyboard)


@router.message(Command("reset"))
async def cmd_reset(message: Message, session: AsyncSession):
    """
    Обработчик команды /reset для сброса контекста пользователя.

    Args:
        message (Message): Сообщение от пользователя.
        session (AsyncSession): Асинхронная сессия для работы с базой данных.
    """
    user_id = message.from_user.id
    await process_reset(user_id, message.answer, session)


@router.callback_query(F.data == "reset")
async def reset_callback(call: CallbackQuery, session: AsyncSession):
    """
    Обработчик нажатия инлайн-кнопки "Сбросить контекст".

    Args:
        call (CallbackQuery): Callback-запрос от пользователя.
        session (AsyncSession): Асинхронная сессия для работы с базой данных.
    """
    user_id = call.from_user.id
    await process_reset(user_id, call.message.answer, session)
    await call.answer()  # закрыть "часики" на кнопке
