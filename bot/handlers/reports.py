from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_services import get_users_files
import html
from sqlalchemy import select
from database.models import FileSummary

router = Router()


@router.message(Command("reports"))
async def reports_list_handler(message: Message, session: AsyncSession):
    user_id = message.from_user.id

    # Загружаем список проанализированных файлов с отчетами
    user_files = await get_users_files(user_id=user_id, session=session)
    # Оставим только те, по которым есть summary
    user_files = [f for f in user_files if getattr(f, 'summary', None) and f.summary.summary]
    if not user_files:
        await message.answer("У вас пока нет готовых отчетов.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{i + 1}. {file.title or (file.file_id[:10])}",
            callback_data=f"report_{file.summary.id}")
        ]
        for i, file in enumerate(user_files)
    ])

    await message.answer(
        "Доступные отчеты по вашим загруженным документам:\n\n" +
        "\n".join([f"{i + 1}. {file.title or file.file_id}" for i, file in enumerate(user_files)]),
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("report_"))
async def report_detail_handler(callback: CallbackQuery, session: AsyncSession):
    file_summary_id = int(callback.data.removeprefix("report_"))

    result = await session.execute(select(FileSummary).where(FileSummary.id == file_summary_id))
    summary = result.scalar_one_or_none()
    if not summary or not summary.summary:
        await callback.message.answer("Отчёт не найден.")
        await callback.answer()
        return

    await callback.message.answer(
        f"<b>Итоговый отчёт по документу №{file_summary_id}:</b>\n\n"
        f"{html.escape(summary.summary)[:3800]}{'...' if len(summary.summary) > 3800 else ''}",
        parse_mode="HTML"
    )
    await callback.answer()

