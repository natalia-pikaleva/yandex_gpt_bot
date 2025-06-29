from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import logging

from bot.keyboards import main_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("upload"))
async def cmd_upload(message: Message):
    """
    Обработчик команды /upload.

    Отправляет пользователю инструкцию для загрузки файла с поддерживаемыми форматами.

    Args:
        message (Message): Объект сообщения от пользователя, вызвавшего команду /upload.
    """
    text = "📤 Пожалуйста, отправьте файл (PDF, DOCX, TXT и др.) для загрузки и обработки."
    await message.answer(text, reply_markup=main_keyboard)


@router.callback_query(F.data == "upload")
async def upload(call: CallbackQuery):
    """
    Обработчик нажатия инлайн-кнопки "Загрузить файл".

    Отправляет пользователю инструкцию для загрузки файла с поддерживаемыми форматами.

    Args:
        message (Message): Объект сообщения от пользователя, вызвавшего команду /upload.
    """
    text = "📤 Пожалуйста, отправьте файл (PDF, DOCX, TXT и др.) для загрузки и обработки."
    await call.message.answer(text, reply_markup=main_keyboard)
