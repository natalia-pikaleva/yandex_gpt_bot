from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext
from bot.states import SearchStates
from database.db_services import save_dialog_history, find_relevant_knowledge
from database.db_services import get_users_files

from external_services.ai_assistant import get_access_token, generate_answer
from bot.keyboards import main_keyboard

router = Router()

logger = logging.getLogger(__name__)


async def prompt_user_to_select_books(user_id, state, message, session: AsyncSession):
    """
    Отправляет пользователю список загруженных книг для выбора источников поиска знаний.

    Если у пользователя нет загруженных книг, информирует его об этом и завершает обработку.
    В случае наличия книг формирует нумерованный список, отправляет его пользователю
    и переводит FSM в состояние ожидания выбора книг.

    Args:
        message (Message): Сообщение пользователя, инициировавшее выбор книг.
        state (FSMContext): Контекст конечного автомата состояний пользователя.
        user_files (list[UserFile]): Список файлов, загруженных пользователем.

    Returns:
        None
    """
    user_files = await get_users_files(user_id, session)

    if not user_files:
        await message.answer("У вас пока нет загруженных книг.")
        return

    book_list = "\n".join([f"{i + 1}. {file.title or file.file_id}" for i, file in enumerate(user_files)])
    await message.answer(
        f"Выберите книги для поиска знаний:\n{book_list}\n\n"
        "Отправьте номера через запятую (например, 1,3), или напишите 'все' для поиска по всем книгам."
    )
    await state.update_data(user_files=user_files)
    await state.set_state(SearchStates.waiting_for_book_selection)


@router.message(Command("search_with_ai"))
async def cmd_search(message: Message, session: AsyncSession, state: FSMContext):
    """
    Обработчик команды /search with AI.

    Запрашивает у пользователя, по каким загруженным книгам выполнять интеллектуальный поиск.
    Отправляет список доступных книг и переводит пользователя в состояние выбора книг.

    Args:
        message (Message): Сообщение пользователя с командой /search with AI.
        session (AsyncSession): Асинхронная сессия для работы с базой данных.
        state (FSMContext): Контекст конечного автомата состояний пользователя.
    """
    user_id = message.from_user.id
    await prompt_user_to_select_books(user_id, state, message, session)


@router.callback_query(F.data == "search_with_ai")
async def search(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    """
    Обработчик нажатия инлайн-кнопки "Поиск с AI".

    Запрашивает у пользователя, по каким загруженным книгам выполнять интеллектуальный поиск.
    Отправляет список доступных книг и переводит пользователя в состояние выбора книг.

    Args:
        message (Message): Сообщение пользователя с командой /search with AI.
        session (AsyncSession): Асинхронная сессия для работы с базой данных.
        state (FSMContext): Контекст конечного автомата состояний пользователя.
    """
    user_id = call.from_user.id
    await prompt_user_to_select_books(user_id, state, call.message, session)


@router.message(SearchStates.waiting_for_book_selection)
async def handle_book_selection(message: Message, state: FSMContext):
    """
    Обработчик выбора книг для поиска знаний.

    Принимает от пользователя номера выбранных книг (или "все"), проверяет корректность ввода,
    сохраняет выбранные file_id во временное состояние и переводит пользователя в состояние ожидания вопроса.

    Args:
        message (Message): Сообщение пользователя с выбором книг.
        state (FSMContext): Контекст конечного автомата состояний пользователя.
    """
    data = await state.get_data()
    user_files = data['user_files']
    user_input = message.text.strip().lower()

    if user_input == "все":
        selected_file_ids = [f.file_id for f in user_files]
    else:
        try:
            selected_indices = [int(i.strip()) - 1 for i in user_input.split(",")]
            selected_file_ids = [user_files[i].file_id for i in selected_indices if 0 <= i < len(user_files)]
        except Exception:
            await message.answer("Некорректный ввод. Попробуйте ещё раз.")
            return

    if not selected_file_ids:
        await message.answer("Вы не выбрали ни одной книги. Попробуйте ещё раз.")
        return

    await state.update_data(selected_file_ids=selected_file_ids)
    await message.answer("Введите ваш вопрос.")
    await state.set_state(SearchStates.waiting_for_question)


@router.message(SearchStates.waiting_for_question)
async def handle_user_question(message: Message, session: AsyncSession, state: FSMContext):
    """
    Обработчик вопроса пользователя после выбора книг.

    Выполняет семантический поиск релевантных фрагментов знаний только по выбранным книгам,
    формирует контекст, отправляет запрос к AI (GigaChat), возвращает ответ пользователю,
    сохраняет историю диалога и сбрасывает состояние.

    Args:
        message (Message): Сообщение пользователя с вопросом.
        session (AsyncSession): Асинхронная сессия для работы с базой данных.
        state (FSMContext): Контекст конечного автомата состояний пользователя.
    """
    user_id = message.from_user.id
    data = await state.get_data()
    selected_file_ids = data['selected_file_ids']

    # 1. Семантический поиск только по выбранным книгам
    context_fragments = await find_relevant_knowledge(
        message.text, user_id, session, selected_file_ids
    )
    context = "\n\n".join(context_fragments)

    # 2. Получаем access_token для GigaChat
    access_token = await get_access_token()  # асинхронная версия

    # 3. Запрашиваем ответ у GigaChat
    answer = await generate_answer(access_token, message.text, context)

    # 4. Отправляем ответ пользователю
    await message.answer(answer, reply_markup=main_keyboard)

    # 5. Сохраняем вопрос и ответ (опционально)
    await save_dialog_history(user_id, message.text, answer, session)

    # Сброс состояния
    await state.clear()
