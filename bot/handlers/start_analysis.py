from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_services import get_users_files, get_file_chunks, save_chunk_ai_response, save_file_summary
from external_services.yandex_disk import download_prompt_from_yandex
from external_services.ai_yandex_gpt import yandex_gpt_request
from bot.services.other_helpers import summarize_recursive
import aiofiles
from config import PROMPT_REMOTE_PATH, PROMPT_LOCAL_PATH
import asyncio
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start_analysis"))
async def start_analysis(message: Message, session: AsyncSession):
    user_id = message.from_user.id
    logger.info(f"Начат анализ для пользователя {user_id}")
    await message.answer("Запущен анализ ваших файлов...")

    # 1. Получаем все файлы пользователя
    user_files = await get_users_files(user_id=user_id, session=session)
    logger.info(f"Найдено {len(user_files)} файлов пользователя {user_id}")

    if not user_files:
        await message.answer("Вы ещё не загрузили ни одного файла. Загрузите документацию, чтобы начать анализ.")
        logger.info(f"Пользователь {user_id} не загрузил ни одного файла")
        return

    # 2. Получаем свежий промт с Яндекс.Диска
    success = await download_prompt_from_yandex(local_prompt_path=PROMPT_LOCAL_PATH, remote_prompt_path=PROMPT_REMOTE_PATH)
    if not success:
        await message.answer("Не удалось скачать текущий промт с Яндекс.Диска.")
        logger.error(f"Не удалось скачать промт для пользователя {user_id}")
        return
    logger.info("Промт успешно скачан с Яндекс.Диска")

    # 3. Загружаем промт из файла
    try:
        async with aiofiles.open(PROMPT_LOCAL_PATH, "r", encoding="utf-8") as f:
            prompt_text = await f.read()
        logger.info("Промт успешно загружен из файла")
    except Exception as ex:
        await message.answer("Не удалось загрузить основной промт для анализа (ошибка чтения).")
        logger.error(f"Ошибка чтения промта: {ex}")
        return

    files_in_progress = []
    files_done = []

    for user_file in user_files:
        logger.info(f"Начинается обработка файла: {user_file.title or user_file.file_id}")
        chunks = await get_file_chunks(user_file.file_id, session=session)
        if not chunks:
            msg = f"Файл {user_file.title or user_file.file_id}: нет разбивки на блоки, обратитесь к администратору."
            await message.answer(msg)
            logger.warning(f"{msg}")
            continue
        if all(chunk.processed for chunk in chunks):
            files_done.append(user_file.title or user_file.file_id)
            logger.info(f"Файл {user_file.title or user_file.file_id} уже обработан полностью.")
            continue

        files_in_progress.append(user_file.title or user_file.file_id)
        await message.answer(f"⏳ Анализирую файл: {user_file.title or user_file.file_id}...")

        # 4. Анализ чанков
        for idx, chunk in enumerate(chunks, start=1):
            if chunk.processed:
                logger.info(f"Чанк {idx}/{len(chunks)} файла {user_file.title or user_file.file_id} уже обработан, пропуск.")
                continue
            logger.info(f"Отправка чанка {idx}/{len(chunks)} файла {user_file.title or user_file.file_id} на AI")

            messages = [
                {"role": "system", "text": prompt_text},
                {"role": "user", "text": chunk.content}
            ]

            try:
                response = await yandex_gpt_request(
                    messages=messages,
                    model="yandexgpt-lite",
                    temperature=0.1,
                    max_tokens=1500,
                )
                ai_answer = response["result"]["alternatives"][0]["message"]["text"]
                await save_chunk_ai_response(chunk.id, ai_answer, session=session)
                logger.info(f"Чанк {idx}/{len(chunks)} файла {user_file.title or user_file.file_id} успешно обработан и сохранён.")
            except Exception as ex:
                logger.error(f"Ошибка анализа чанка {idx} файла {user_file.file_id}: {ex}")
                await message.answer(
                    f"❌ Ошибка анализа чанка файла {user_file.title or user_file.file_id}: {ex}"
                )
            await asyncio.sleep(0.2)
        await session.commit()
        logger.info(f"Все чанки файла {user_file.title or user_file.file_id} обработаны и сохранены.")

        # 5. Итоговое резюмирование
        try:
            ai_answers = [chunk.ai_response for chunk in chunks if chunk.ai_response]
            logger.info(f"Начинается итоговое резюмирование для файла {user_file.title or user_file.file_id}. Количество ответов: {len(ai_answers)}")
            if ai_answers:
                final_summary = await summarize_recursive(ai_answers, prompt_text, max_group_size=10, max_final_groups=20, session=session)
                await save_file_summary(user_file.file_id, final_summary, session=session)
                await session.commit()
                await message.answer(
                    f"✅ Анализ завершён для файла: {user_file.title or user_file.file_id}.\n\n"
                    f"Отчет:\n\n{final_summary[:3800]}{'...' if len(final_summary) > 3800 else ''}"
                )
                logger.info(f"Итоговый отчёт для файла {user_file.title or user_file.file_id} успешно сохранён и отправлен пользователю.")
            else:
                logger.warning(f"Для файла {user_file.title or user_file.file_id} отсутствуют ответы AI для итогового резюмирования.")
        except Exception as ex:
            logger.error(f"Ошибка создания общего отчёта для файла {user_file.file_id}: {ex}")
            await message.answer(f"❌ Ошибка создания общего отчета: {ex}")

    if not files_in_progress:
        await message.answer("Все ваши файлы уже были проанализированы.")
        logger.info(f"Пользователь {user_id} уже проанализировал все свои файлы.")
