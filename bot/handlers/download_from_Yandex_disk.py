from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from external_services.yandex_disk import download_file
from bot.states import DownloadStates
from bot.services.other_helpers import send_yandex_oauth, process_and_save_file
from database.db_services import get_yandex_token
from config import DOWNLOADS_DIR, YANDEX_CLIENT_ID, REDIRECT_URI
from bot.keyboards import main_keyboard

router = Router()

logger = logging.getLogger(__name__)

def build_yandex_oauth_url(user_id: int) -> str:
    return (
        "https://oauth.yandex.ru/authorize"
        f"?response_type=code&client_id={YANDEX_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={user_id}"
    )


@router.callback_query(F.data == "download_from_yandex_disk")
async def download_start(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обрабатывает нажатие пользователем инлайн-кнопки "Загрузить файл с Яндекс.Диска".

    Если токен уже есть, уведомляет пользователя и переводит в состояние ожидания пути к файлу.
    Иначе отправляет ссылку для авторизации и переводит в состояние ожидания OAuth.

    Args:
        call (CallbackQuery): Callback-запрос от пользователя.
        state (FSMContext): Контекст FSM.
        session (AsyncSession): Асинхронная сессия БД.

    Returns:
        None
    """
    user_id = call.from_user.id
    token = await get_yandex_token(session, user_id)

    if token and token.strip():
        logger.info('Токен существует, ждем ссылку на файл')
        await call.message.answer(
            "Отправьте ссылку на файл на вашем Яндекс.Диске.",
            reply_markup=main_keyboard
        )
        await state.set_state(DownloadStates.waiting_for_path)
    else:
        logger.info('Токена в базе нет, просим авторизоваться')

        oauth_url = build_yandex_oauth_url(user_id)
        text = (
            "Для подключения Яндекс.Диска перейдите по <a href=\"{url}\">ссылке на авторизацию на Яндекс.Диск</a> и предоставьте доступ.\n\n"
            "После успешной авторизации возвращайтесь в бота."
        ).format(url=oauth_url)

        await call.message.answer(
            text,
            reply_markup=main_keyboard,
            parse_mode="HTML"
        )
        await state.set_state(DownloadStates.waiting_for_oauth)


@router.message(Command('download_from_yandex_disk'))
async def cmd_download_start(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обрабатывает команду /download_from_yandex_disk.

    Если токен уже есть, уведомляет пользователя и переводит в состояние ожидания пути к файлу.
    Иначе отправляет ссылку для авторизации и переводит в состояние ожидания OAuth.

    Args:
        message (Message): Сообщение пользователя.
        state (FSMContext): Контекст FSM.
        session (AsyncSession): Асинхронная сессия БД.

    Returns:
        None
    """
    user_id = message.from_user.id
    token = await get_yandex_token(session, user_id)

    if token and token.strip():
        logger.info('Токен существует, ждем ссылку на файл')

        await message.answer(
            "Отправьте ссылку на файл на вашем Яндекс.Диске.",
            reply_markup=main_keyboard
        )
        await state.set_state(DownloadStates.waiting_for_path)
    else:
        logger.info('Токена в базе нет, просим авторизоваться')

        oauth_url = build_yandex_oauth_url(user_id)
        text = (
            "Для подключения Яндекс.Диска перейдите по ссылке и предоставьте доступ:\n"
            f"{oauth_url}\n\n"
            "После успешной авторизации возвращайтесь в бота."
        )
        await message.answer(text, reply_markup=main_keyboard)
        await state.set_state(DownloadStates.waiting_for_oauth)


@router.message(DownloadStates.waiting_for_oauth)
async def process_oauth_token(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик сообщений пользователя в состоянии ожидания авторизации через Яндекс.Диск.

    Обрабатывает сообщение пользователя в состоянии ожидания авторизации Яндекс.Диска.
    Если токен уже есть — сразу обрабатывает сообщение как путь к файлу.
    Если токена нет — просит авторизоваться.

    Args:
        message (Message): Сообщение пользователя в Telegram.
        state (FSMContext): Контекст конечного автомата состояний пользователя.
        session (AsyncSession): Асинхронная сессия для работы с базой данных.

    Returns:
        None
    """

    user_id = message.from_user.id
    token = await get_yandex_token(session, user_id)
    if token and token.strip():
        # Сразу считаем, что пользователь отправил путь к файлу
        path = message.text.strip()
        await state.update_data(file_path=path)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Загрузить файл", callback_data="send_file")],
            [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
        ])

        await state.set_state(DownloadStates.waiting_for_confirm)
        await message.answer(f"Вы ввели путь:\n{path}\nНажмите кнопку, чтобы загрузить файл.", reply_markup=keyboard)

    else:
        await message.answer(
            "Токен не найден. Пожалуйста, авторизуйтесь через ссылку или отправьте файл с устройства."
        )


@router.message(DownloadStates.waiting_for_path)
async def process_oauth_token(message: Message, state: FSMContext):
    path = message.text.strip()
    await state.update_data(file_path=path)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Загрузить файл", callback_data="send_file")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
    ])

    await state.set_state(DownloadStates.waiting_for_confirm)
    await message.answer(f"Вы ввели путь:\n{path}\nНажмите кнопку, чтобы загрузить файл.", reply_markup=keyboard)


@router.callback_query(F.data == "send_file", DownloadStates.waiting_for_confirm)
async def send_file_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обрабатывает нажатие инлайн-кнопки "Загрузить файл" для скачивания файла с Яндекс.Диска.

    Получает путь к файлу и OAuth-токен из FSMContext, скачивает файл с Яндекс.Диска во временную директорию,
    затем вызывает функцию обработки и сохранения файла в базе знаний. В случае ошибки информирует пользователя.

    Args:
        callback (CallbackQuery): Callback-запрос от пользователя.
        state (FSMContext): Контекст конечного автомата состояний пользователя.
        session (AsyncSession): Асинхронная сессия для работы с базой данных.
    """
    user_id = callback.from_user.id
    data = await state.get_data()
    path = data.get("file_path")
    token = await get_yandex_token(session, user_id)
    if not path or not token:
        await callback.message.answer("Не найден путь к файлу или токен. Начните заново.")
        await state.clear()
        return

    await callback.answer()

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    local_file = os.path.join(DOWNLOADS_DIR, path.split("/")[-1])

    # Скачиваем файл с Яндекс.Диска
    success = await download_file(path, local_file, token)
    if not success:
        await callback.message.answer("Не удалось скачать файл. Проверьте путь и попробуйте снова.")
        await state.clear()
        return

    user_id = callback.from_user.id
    filename = os.path.basename(local_file)
    await process_and_save_file(
        user_id=user_id,
        filename=os.path.basename(local_file),
        local_file_path=local_file,
        remote_path=path,  # путь на Яндекс.Диске пользователя
        session=session,
        message_send_func=callback.message.answer,
        file_id=f"yadisk_{user_id}_{os.path.basename(local_file)}"
    )
