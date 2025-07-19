from aiogram import Router
from aiogram.types import Message
from aiogram.types import ContentType
from bot.services.rule_based import get_rule_based_response
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message()
async def handle_user_message(message: Message):
    """
    Обработчик текстовых сообщений от пользователя, не связанных с AI и базой знаний.

    Если сообщение не является текстом — предупреждает пользователя.
    Иначе — отвечает rule-based логикой (имитация живого общения).

    Args:
        message (Message): Сообщение от пользователя.
    """
    if message.content_type != ContentType.TEXT:
        await message.answer(
            "Пожалуйста, отправляйте текстовые сообщения или документы "
            "с расширениями: .txt, .pdf, .docx, .rtf, .xlsx"
        )
        return

    text = message.text.lower()
    response = await get_rule_based_response(text)
    await message.answer(response)
