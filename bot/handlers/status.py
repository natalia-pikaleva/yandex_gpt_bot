from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_services import get_users_files, get_file_chunks
from database.models import FileSummary

router = Router()

@router.message(Command("status"))
async def status_handler(message: Message, session: AsyncSession):
    user_id = message.from_user.id

    # Загружаем все файлы пользователя
    user_files = await get_users_files(user_id=user_id, session=session)
    if not user_files:
        await message.answer("У вас пока нет загруженных документов.")
        return

    status_msg = ""
    for user_file in user_files:
        title = user_file.title or user_file.file_id
        # Получаем чанки
        chunks = await get_file_chunks(user_file.file_id, session=session)
        total = len(chunks)
        if total == 0:
            status = "❔ Не разбит на части (ошибка загрузки)"
        else:
            done = sum(1 for c in chunks if c.processed)
            if done == 0:
                status = "⏳ Ждёт запуска анализа"
            elif 0 < done < total:
                status = f"🔄 В процессе ({done}/{total} блоков обработано)"
            else:
                # Проверяем, есть ли summary
                summary = getattr(user_file, "summary", None)
                if summary and summary.summary:
                    status = "✅ Анализ завершён"
                else:
                    status = "✅ Анализ завершён (отчёт готовится)"
        status_msg += f"📄 <b>{title}</b>\nСтатус: {status}\n\n"
        # Если файл полностью обработан — покажи фрагмент summary
        if getattr(user_file, "summary", None) and user_file.summary and user_file.summary.summary:
            short_report = user_file.summary.summary[:500]
            status_msg += f"📝 Фрагмент отчёта:\n{short_report}...\n\n"

    await message.answer(
        status_msg if status_msg else "Нет загруженных документов.",
        parse_mode="HTML"
    )
