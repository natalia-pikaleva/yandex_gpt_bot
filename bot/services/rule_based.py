import re
import logging
from bot.answers_dict import patterns_responses

logger = logging.getLogger(__name__)

default_response = (
    "Я вас понял, но моя задача — автоматический анализ и генерация отчётов по документации.\n"
    "Загрузите файл через /upload, потом используйте /start_analysis. Для помощи введите /help."
)


async def get_rule_based_response(text: str):
    """
    Возвращает ответ на основе правил (паттернов) из словаря patterns_responses.

    Если текст совпадает с одним из паттернов, возвращается соответствующий ответ.
    В противном случае возвращается ответ по умолчанию.

    Args:
        text (str): Входной текст от пользователя.

    Returns:
        str: Ответ на текст.
    """
    text = text.lower()
    for pattern, response in patterns_responses.items():
        if re.search(pattern, text):
            return response
    return default_response
