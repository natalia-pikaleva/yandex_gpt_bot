from aiogram import Router, F
from aiogram.types import ContentType, Message
from sqlalchemy.ext.asyncio import AsyncSession
import os
import logging

from bot.bot_instance import bot
from external_services.yandex_disk import upload_user_file
from bot.keyboards import main_keyboard
from config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from bot.services.other_helpers import process_and_save_file

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.content_type == ContentType.DOCUMENT)
async def handle_document(
        message: Message,
        session: AsyncSession
):
    """
    Обработчик загрузки документа с проверкой, загрузкой на Яндекс.Диск,
    извлечением текста и сохранением в базе знаний с откатом при ошибках.

    Args:
        message (Message): Сообщение с документом.
        session (AsyncSession): Асинхронная сессия базы данных.
    """
    await message.answer("Обработчик загрузки файла")
    filename = message.document.file_name
    _, ext = os.path.splitext(filename.lower())

    # Проверяем расширение файла
    if ext not in ALLOWED_EXTENSIONS:
        await message.answer(
            "❌ Извините, поддерживаются только текстовые файлы с расширениями: .txt, "
            ".pdf, .docx, .rtf, .epub, .fb2.\n"
            "Пожалуйста, загрузите файл в одном из этих форматов.",
            reply_markup=main_keyboard
        )
        return

    # Проверяем размер файла (в байтах)
    file_size = message.document.file_size  # размер в байтах
    file_size_mb = file_size / (1024 * 1024)

    if file_size_mb > MAX_FILE_SIZE_MB:
        await message.answer(
            f"⚠️ Ваш файл довольно большой ({file_size_mb:.2f} МБ). "
            "Загрузка и обработка могут занять некоторое время, пожалуйста, подождите.",
            reply_markup=main_keyboard
        )

    user_id = message.from_user.id
    document = message.document
    file_id = document.file_id

    # Скачиваем файл из Telegram
    file_info = await bot.get_file(file_id)
    file_path = file_info.file_path
    file = await bot.download_file(file_path)

    with open(filename, 'wb') as f:
        f.write(file.read())

    # Вызываем функцию, которая обработает всю логику при сохранении файла
    remote_path = await upload_user_file(user_id, filename, file_id)
    await process_and_save_file(
        user_id=user_id,
        filename=filename,
        local_file_path=filename,
        remote_path=remote_path,
        session=session,
        message_send_func=message.answer,
        file_id=document.file_id
    )
