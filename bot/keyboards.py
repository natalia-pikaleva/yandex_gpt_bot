from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Загрузить файл", callback_data="upload"),
        InlineKeyboardButton(text="Загрузить файл с Яндекс.Диска", callback_data="download_from_yandex_disk")],
        [InlineKeyboardButton(text="Поиск с AI", callback_data="search_with_ai"),
        InlineKeyboardButton(text="Поиск в Википедии", callback_data="search_wiki")],
        [InlineKeyboardButton(text="Сбросить контекст", callback_data="reset"),
        InlineKeyboardButton(text="Помощь", callback_data="help")]
    ]
)


ask_question_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Задать вопрос", callback_data="/ask_question")
        ]
    ]
)
