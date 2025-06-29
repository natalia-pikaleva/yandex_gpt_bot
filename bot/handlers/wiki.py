from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from external_services.wikipedia_api import get_wikipedia_summary_with_link
from bot.states import WikiSearchStates

router = Router()


@router.message(Command("search_wiki"))
async def cmd_search_wiki(message: Message, state: FSMContext):
    """
    Обработчик команды /search_wiki.

    Отправляет пользователю приглашение ввести запрос для поиска информации в Википедии
    и переводит пользователя в состояние ожидания ввода запроса.

    Args:
        message (Message): Объект сообщения от пользователя.
        state (FSMContext): Контекст конечного автомата состояний для управления состояниями пользователя.
    """
    await message.answer("🔍 Пожалуйста, введите текст для поиска в Википедии.")
    await state.set_state(WikiSearchStates.waiting_for_query)


@router.callback_query(F.data == "search_wiki")
async def search_wiki(call: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия инлайн-кнопки "Поиск в Википедии".

    Отправляет пользователю инструкцию для загрузки файла с поддерживаемыми форматами.

    Args:
        message (Message): Объект сообщения от пользователя, вызвавшего команду /upload.
    """
    await call.message.answer("🔍 Пожалуйста, введите текст для поиска в Википедии.")
    await state.set_state(WikiSearchStates.waiting_for_query)


@router.message(WikiSearchStates.waiting_for_query)
async def process_wiki_query(message: Message, state: FSMContext):
    """
    Обработчик текстового сообщения в состоянии ожидания запроса к Википедии.

    Получает текст запроса от пользователя, выполняет поиск в Википедии с помощью
    функции get_wikipedia_summary_with_link, отправляет пользователю результат и
    сбрасывает состояние ожидания.

    Args:
        message (Message): Объект сообщения с текстом запроса.
        state (FSMContext): Контекст конечного автомата состояний для управления состояниями пользователя.
    """
    query = message.text.strip()
    response = await get_wikipedia_summary_with_link(query)
    await message.answer(response, parse_mode="HTML")
    await state.clear()  # Сбрасываем состояние после обработки
