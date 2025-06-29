from aiogram.fsm.context import FSMContext
from config import YANDEX_CLIENT_ID
from bot.states import DownloadStates, SearchStates
from sqlalchemy.ext.asyncio import AsyncSession
import os
import logging
from types import SimpleNamespace

from database.db_services import file_save, save_knowledge_entries
from bot.services.text_processing import extract_text_from_file
from config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)


async def send_yandex_oauth(state: FSMContext, send_func):
    """
    Отправляет пользователю инструкцию и ссылку для авторизации на Яндекс.Диске.

    Переводит пользователя в состояние ожидания ввода OAuth-токена.

    Args:
        state (FSMContext): Контекст конечного автомата состояний пользователя.
        send_func (Callable): Функция отправки сообщения пользователю (например, message.answer).
    """
    oauth_url = (
        f"https://oauth.yandex.ru/authorize?response_type=token&client_id={YANDEX_CLIENT_ID}"
    )
    text = (
        "Для доступа к вашему Яндекс.Диску, пожалуйста, авторизуйтесь по ссылке:\n"
        f"{oauth_url}\n\n"
        "После авторизации скопируйте токен из адресной строки браузера (после #access_token=...) "
        "и отправьте его сюда одним сообщением."
    )
    await state.set_state(DownloadStates.waiting_for_oauth)
    await send_func(text)


async def process_and_save_file_from_disk(
        user_id: int,
        filename: str,
        local_file_path: str,
        session: AsyncSession,
        message_send_func
):
    """
    Обрабатывает файл, скачанный с Яндекс.Диска: сохраняет его в базе данных и индексирует содержимое.

    Args:
        user_id (int): Telegram user_id пользователя.
        filename (str): Имя файла.
        local_file_path (str): Локальный путь к скачанному файлу.
        session (AsyncSession): Асинхронная сессия базы данных.
        message_send_func (Callable): Функция для отправки сообщений пользователю.
    """
    try:
        # Проверяем расширение
        _, ext = os.path.splitext(filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            await message_send_func(
                "❌ Поддерживаются только файлы: .txt, .pdf, .docx, .rtf, .epub, .fb2."
            )
            return

        # Проверяем размер файла
        file_size = os.path.getsize(local_file_path)
        file_size_mb = file_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            await message_send_func(
                f"⚠️ Файл большой ({file_size_mb:.2f} МБ). Обработка может занять время."
            )

        # Сохраняем информацию о файле в базе данных
        # Здесь file_id можно сгенерировать, например, через uuid или хеш
        file_id_db = await file_save(user_id, filename, local_file_path, session)
        if file_id_db is None:
            raise RuntimeError("Ошибка при сохранении файла в базе данных")

        # Извлекаем текст
        text = extract_text_from_file(local_file_path)
        if not text or text == "Формат файла не поддерживается.":
            raise RuntimeError("Не удалось извлечь текст из файла")

        # Сохраняем знания
        await save_knowledge_entries(user_id, file_id_db, text, session)

        # Удаляем локальный файл
        try:
            os.remove(local_file_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить локальный файл {local_file_path}: {e}")

        await message_send_func(
            f"✅ Файл '{filename}' успешно загружен и проиндексирован.\n"
            f"Теперь вы можете задавать вопросы по содержимому.",
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке файла с Яндекс.Диска: {e}")
        try:
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
        except Exception as rm_err:
            logger.warning(f"Не удалось удалить локальный файл после ошибки: {rm_err}")

        await message_send_func(
            "❌ Произошла ошибка при обработке файла. Попробуйте повторить позже."
        )


async def process_and_save_file(
        user_id: int,
        filename: str,
        local_file_path: str,
        remote_path: str,
        session: AsyncSession,
        message_send_func,
        *,
        file_id: str = None
):
    """
    Универсальная функция для обработки и сохранения файла из любого источника (Telegram, Яндекс.Диск).

    - Проверяет расширение и размер файла.
    - Сохраняет информацию о файле в базе данных.
    - Извлекает и индексирует текст.
    - Удаляет локальный файл после обработки.
    - Откатывает изменения при ошибках.

    Args:
        user_id (int): Telegram user_id пользователя.
        filename (str): Имя файла.
        local_file_path (str): Локальный путь к файлу.
        remote_path (str): Путь к файлу на удалённом хранилище (или None для Telegram).
        session (AsyncSession): Сессия базы данных.
        message_send_func (Callable): Функция для отправки сообщений пользователю.
        file_id (str, optional): Уникальный идентификатор файла (если нет — будет сгенерирован).
    """
    try:
        # Проверяем расширение
        _, ext = os.path.splitext(filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            await message_send_func(
                "❌ Поддерживаются только файлы: .txt, .pdf, .docx, .rtf, .epub, .fb2."
            )
            return

        # Проверяем размер файла
        file_size = os.path.getsize(local_file_path)
        file_size_mb = file_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            await message_send_func(
                f"⚠️ Файл большой ({file_size_mb:.2f} МБ). Обработка может занять время."
            )

        # Создаем "документ" для file_save
        doc_obj = SimpleNamespace(
            file_id=file_id or f"file_{user_id}_{filename}",
            file_name=filename
        )

        # Сохраняем информацию о файле в базе данных
        file_id_db = await file_save(user_id, doc_obj, remote_path, session)
        if file_id_db == 'already_exists':
            await message_send_func(
                f"⚠️ Файл с именем '{filename}' уже был загружен ранее.\n"
                f"Вы можете воспользоваться уже загруженным файлом."
            )
            try:
                os.remove(local_file_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить локальный файл {local_file_path}: {e}")
            return
        elif file_id_db is None:
            raise RuntimeError("Ошибка при сохранении файла в базе данных")

        # Извлекаем текст
        text = extract_text_from_file(local_file_path)
        if not text or text == "Формат файла не поддерживается.":
            raise RuntimeError("Не удалось извлечь текст из файла")

        # Сохраняем знания
        await save_knowledge_entries(user_id, file_id_db, text, session)

        # Удаляем локальный файл
        try:
            os.remove(local_file_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить локальный файл {local_file_path}: {e}")

        await message_send_func(
            f"✅ Файл '{filename}' успешно загружен и проиндексирован.\n"
            f"Теперь вы можете задавать вопросы по содержимому.",
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке файла пользователя {user_id}: {e}")
        # Откат: удаление файла из базы знаний и БД (если реализовано)
        # Откат: удаление локального файла
        try:
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
        except Exception as rm_err:
            logger.warning(f"Не удалось удалить локальный файл после ошибки: {rm_err}")

        await message_send_func(
            "❌ Произошла ошибка при обработке файла. Попробуйте повторить позже."
        )
