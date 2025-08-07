from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_services import get_users_files, get_file_chunks, save_chunk_ai_response, save_file_summary
from external_services.yandex_disk import download_prompt_from_yandex
from external_services.ai_yandex_gpt import yandex_gpt_request
from bot.services.other_helpers import summarize_in_steps
import aiofiles
from config import PROMPT_REMOTE_PATH, PROMPT_LOCAL_PATH
import asyncio
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start_analysis"))
async def start_analysis(message: Message, session: AsyncSession):
    user_id = message.from_user.id

    # 1. Получаем все файлы пользователя
    user_files = await get_users_files(user_id=user_id, session=session)

    if not user_files:
        await message.answer(
            "Вы ещё не загрузили ни одного файла. Загрузите документацию, чтобы начать анализ."
        )
        return

    # 2. Получаем свежий промт с Яндекс.диска
    success = await download_prompt_from_yandex(
        local_prompt_path=PROMPT_LOCAL_PATH,
        remote_prompt_path=PROMPT_REMOTE_PATH
    )
    if not success:
        await message.answer("Не удалось скачать текущий промт с Яндекс.Диска.")
        return

    # 3. Загружаем промт из файла
    try:
        async with aiofiles.open(PROMPT_LOCAL_PATH, "r", encoding="utf-8") as f:
            prompt_text = await f.read()
    except Exception as ex:
        await message.answer("Не удалось загрузить основной промт для анализа (ошибка чтения).")
        return

    await message.answer("Промт успешно загружен")
    files_in_progress = []
    files_done = []
    for user_file in user_files:
        # Получаем все чанки файла (если уже обработаны - пропускаем)
        chunks = await get_file_chunks(user_file.file_id, session=session)
        if not chunks:
            await message.answer(
                f"Файл {user_file.title or user_file.file_id}: нет разбивки на блоки, обратитесь к администратору."
            )
            continue
        if all(chunk.processed for chunk in chunks):
            files_done.append(user_file.title or user_file.file_id)
            continue

        files_in_progress.append(user_file.title or user_file.file_id)
        await message.answer(f"⏳ Анализирую файл: {user_file.title or user_file.file_id}...")

        # 4. Поочередно анализируем каждый чанк, если он еще не обработан
        for chunk in chunks:
            if chunk.processed:
                continue
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
            except Exception as ex:
                logger.error(f"Ошибка анализа чанка файла {user_file.file_id}: {ex}")
                await message.answer(
                    f"❌ Ошибка анализа чанка файла {user_file.title or user_file.file_id}: {ex}"
                )
            await asyncio.sleep(0.2)
        await session.commit()

        # 5. Итоговое резюмирование по всем ответам AI для чанков
        # Собираем ответы по чанкам
        try:
            ai_answers = [chunk.ai_response for chunk in chunks if chunk.ai_response]
            if ai_answers:
                final_summary = await summarize_in_steps(ai_answers, prompt_text, session)
                await save_file_summary(user_file.file_id, final_summary, session=session)
                await session.commit()
                await message.answer(
                    f"✅ Анализ завершён для файла: {user_file.title or user_file.file_id}.\n\n"
                    f"Отчет:\n\n{final_summary[:3800]}{'...' if len(final_summary) > 3800 else ''}"
                )

        except Exception as ex:
            await message.answer(f"❌ Ошибка создания общего отчета: {ex}")

    if not files_in_progress:
        await message.answer("Все ваши файлы уже были проанализированы.")
