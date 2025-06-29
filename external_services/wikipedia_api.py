import wikipediaapi
import logging
from aiogram.utils.markdown import hlink

logger = logging.getLogger(__name__)

# Инициализация объекта Wikipedia с указанием языка и user_agent
wiki = wikipediaapi.Wikipedia(
    language='ru',  # язык, например 'ru' для русского
    user_agent='MyTelegramBot/1.0 (your_email@example.com)'
)


async def get_wikipedia_summary_with_link(query: str):
    """
    Выполняет поиск статьи в Википедии по заданному запросу и возвращает краткое содержание с ссылкой на полную статью.

    Args:
        query (str): Запрос для поиска в Википедии.

    Returns:
        str: Текст с кратким описанием статьи и кликабельной ссылкой на полную статью,
             либо сообщение об отсутствии статьи по запросу.
    """
    try:
        page = wiki.page(query)
        if page.exists():
            summary = page.summary[0:500]
            if len(page.summary) > 500:
                summary += "..."
            url = page.fullurl  # ссылка на полную статью

            # Формируем текст с кликабельной ссылкой
            text = (
                f"📚 Информация из Википедии по запросу «{query}»:\n\n"
                f"{summary}\n\n"
                f"{hlink('Читать полностью', url)}"
            )
            return text
        else:
            return f"❌ По запросу «{query}» ничего не найдено в Википедии."
    except Exception as ex:
        logger.error("Error during getting data from Wikipedia: %s", str(ex))
