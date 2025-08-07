from aiogram.fsm.context import FSMContext
from config import YANDEX_CLIENT_ID
from bot.states import DownloadStates, SearchStates
from sqlalchemy.ext.asyncio import AsyncSession
import os
import logging
from types import SimpleNamespace
from external_services.ai_yandex_gpt import yandex_gpt_request

from database.db_services import file_save, split_and_save_chunks

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
                "❌ Поддерживаются только файлы: .txt, .pdf, .docx, .rtf, .xlsx"
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
        user_file_obj = await file_save(user_id, filename, local_file_path, session)
        if user_file_obj is None:
            raise RuntimeError("Ошибка при сохранении файла в базе данных")

        # Извлекаем текст
        text = extract_text_from_file(local_file_path)
        if not text or text == "Формат файла не поддерживается.":
            raise RuntimeError("Не удалось извлечь текст из файла")

        # Удаляем локальный файл
        try:
            os.remove(local_file_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить локальный файл {local_file_path}: {e}")

        await message_send_func(
            f"✅ Файл '{filename}' готов для анализа системой"
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
        _, ext = os.path.splitext(filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            await message_send_func(
                "❌ Поддерживаются только файлы: .txt, .pdf, .docx, .rtf, .xlsx."
            )
            return

        file_size = os.path.getsize(local_file_path)
        file_size_mb = file_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            await message_send_func(
                f"⚠️ Файл большой ({file_size_mb:.2f} МБ). Обработка может занять время."
            )

        doc_obj = SimpleNamespace(
            file_id=file_id or f"file_{user_id}_{filename}",
            file_name=filename
        )

        user_file_obj = await file_save(user_id, doc_obj, remote_path, session)
        if user_file_obj == 'already_exists':
            await message_send_func(
                f"⚠️ Файл с именем '{filename}' уже был загружен ранее.\n"
                f"Вы можете воспользоваться уже загруженным файлом."
            )
            try:
                os.remove(local_file_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить локальный файл {local_file_path}: {e}")
            return
        elif user_file_obj is None:
            raise RuntimeError("Ошибка при сохранении файла в базе данных")

        # Извлекаем текст
        text = extract_text_from_file(local_file_path)
        if not text or text == "Формат файла не поддерживается.":
            raise RuntimeError("Не удалось извлечь текст из файла")

        # Разбиваем и сохраняем чанки:
        await split_and_save_chunks(user_file_obj, text, session)

        try:
            os.remove(local_file_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить локальный файл {local_file_path}: {e}")

        await message_send_func(
            f"✅ Файл '{filename}' готов для анализа системой. После загрузки всех файлов нажмите Начать анализ документов"
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке файла пользователя {user_id}: {e}")
        try:
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
        except Exception as rm_err:
            logger.warning(f"Не удалось удалить локальный файл после ошибки: {rm_err}")

        await message_send_func(
            "❌ Произошла ошибка при обработке файла. Попробуйте повторить позже."
        )


CHUNKS_PER_STEP = 10  # Кол-во чанков для одного промежуточного резюме


async def summarize_in_steps(ai_answers: list, prompt_text: str, session: AsyncSession):
    summaries = []
    # Разбиваем список ответов на группы по CHUNKS_PER_STEP
    for i in range(0, len(ai_answers), CHUNKS_PER_STEP):
        group = ai_answers[i:i + CHUNKS_PER_STEP]
        group_text = "\n---\n".join(group)

        summary_prompt = (
                prompt_text
                + "\nПожалуйста, сделай краткое резюмирование следующих частей документа:\n\n"
                + group_text
        )
        messages = [
            {"role": "system", "text": prompt_text},
            {"role": "user", "text": summary_prompt},
        ]

        try:
            response = await yandex_gpt_request(
                messages=messages,
                model="yandexgpt-lite",
                temperature=0.1,
                max_tokens=1500,  # Можно уменьшить, чтобы вместить результат
            )
            intermediate_summary = response["result"]["alternatives"][0]["message"]["text"]
            summaries.append(intermediate_summary)
        except Exception as ex:
            # Можно обработать ошибку, например, логировать и продолжать
            summaries.append(f"Ошибка генерации резюме для группы chunk {i}-{i + CHUNKS_PER_STEP}: {ex}")

    # Если резюме получилось более одного, то объединяем и резюмируем итогово
    if len(summaries) > 1:
        final_summary_prompt = (
                prompt_text
                + "\nПожалуйста, на основе ниже приведенных кратких резюме сделай общий итоговый экспертный отчет:\n\n"
                + "\n---\n".join(summaries)
        )
        messages = [
            {"role": "system", "text": prompt_text},
            {"role": "user", "text": final_summary_prompt},
        ]

        try:
            response = await yandex_gpt_request(
                messages=messages,
                model="yandexgpt-lite",
                temperature=0.1,
                max_tokens=2000,
            )
            final_summary = response["result"]["alternatives"][0]["message"]["text"]
        except Exception as ex:
            final_summary = f"Ошибка итогового резюмирования: {ex}"
    else:
        # Если один промежуточный summary — это и есть финал
        final_summary = summaries[0] if summaries else ""

    return final_summary


async def summarize_recursive(ai_texts: list, prompt_text: str, session: AsyncSession,
                              max_group_size: int = 10,
                              max_final_groups: int = 20) -> str:
    """
    Многоступенчатое резюмирование
    ai_texts       — список текстов для резюмирования (ответы или промежуточные сводки)
    prompt_text    — системный промт, который даётся в system-сообщении
    max_group_size — максимальное число текстов на одном промежуточном резюме
    max_final_groups — максимальное допустимое количество групп для финального объединения

    Возвращает итоговое сводное резюме.
    """

    # Если текстов мало или нет, просто объединяем и возвращаем
    if not ai_texts:
        return ""
    if len(ai_texts) <= max_group_size:
        # Формируем запрос на резюмирование одного уровня
        combined_text = "\n---\n".join(ai_texts)
        user_prompt = (
                "Пожалуйста, сделай краткое резюмирование следующих частей документа:\n\n"
                + combined_text
        )
        messages = [
            {"role": "system", "text": prompt_text},
            {"role": "user", "text": user_prompt},
        ]
        try:
            response = await yandex_gpt_request(
                messages=messages,
                model="yandexgpt-lite",
                temperature=0.1,
                max_tokens=1500,
            )
            summary = response["result"]["alternatives"][0]["message"]["text"]
            return summary
        except Exception as ex:
            # Логируем ошибку и возвращаем частичное резюме/пустой результат
            logger.error(f"Ошибка при промежуточном резюмировании: {ex}")
            return ""

    # Разбиваем список текстов на группы max_group_size
    grouped_summaries = []
    for i in range(0, len(ai_texts), max_group_size):
        group_texts = ai_texts[i:i + max_group_size]
        summary = await summarize_recursive(group_texts, prompt_text, max_group_size, max_final_groups, session)
        if summary:
            grouped_summaries.append(summary)

    # Если на этом уровне число групп не превышает max_final_groups, то объединяем их
    if len(grouped_summaries) <= max_final_groups:
        combined_text = "\n---\n".join(grouped_summaries)
        user_prompt = (
                "Пожалуйста, на основе ниже приведённых кратких резюме сделай общий итоговый экспертный отчёт:\n\n"
                + combined_text
        )
        messages = [
            {"role": "system", "text": prompt_text},
            {"role": "user", "text": user_prompt},
        ]
        try:
            response = await yandex_gpt_request(
                messages=messages,
                model="yandexgpt-lite",
                temperature=0.1,
                max_tokens=2000,
            )
            final_summary = response["result"]["alternatives"][0]["message"]["text"]
            return final_summary
        except Exception as ex:
            logger.error(f"Ошибка при финальном резюмировании: {ex}")
            # Возвращаем объединение всех промежуточных резюме без отправки на AI, если хотите
            return combined_text
    else:
        # Если групп слишком много — повторяем резюмирование рекурсивно
        return await summarize_recursive(grouped_summaries, prompt_text, max_group_size, max_final_groups, session)
