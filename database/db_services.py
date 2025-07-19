from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from sqlalchemy.orm import selectinload
from database.models import UserFile, User, FileChunk, FileSummary
import numpy as np
from sqlalchemy import select, update
import logging

from bot.services.text_processing import split_text_into_semantic_chunks
from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_for_book_selection = State()
    waiting_for_question = State()


logger = logging.getLogger(__name__)


async def file_save(user_id: int, document, remote_path, session: AsyncSession):
    """
    Сохраняет информацию о загруженном файле в базу данных.
    Если файл с таким же file_id или названием уже есть у пользователя, возвращает 'already_exists'.

    Returns:
        str: file_id сохранённого файла, 'already_exists' если файл уже есть, или None при ошибке.
    """
    try:
        file_id = document.file_id
        title = document.file_name

        # Проверяем, есть ли уже такой файл у пользователя (по file_id или названию)
        query = select(UserFile).where(
            (UserFile.user_id == user_id) &
            ((UserFile.file_id == file_id) | (UserFile.title == title))
        )
        result = await session.execute(query)
        existing_file = result.scalar_one_or_none()
        if existing_file:
            return 'already_exists'

        user_file = UserFile(
            file_id=file_id,
            user_id=user_id,
            title=title,
            yandex_path=remote_path,
        )
        session.add(user_file)
        await session.commit()
        await session.refresh(user_file)
        return user_file
    except Exception as ex:
        logger.error("Error during saving file to database: %s", str(ex))
        return None


async def get_users_files(user_id: int, session: AsyncSession):
    """
    Получает список всех файлов, загруженных пользователем.

    Выполняет запрос к базе данных и возвращает все объекты UserFile,
    принадлежащие пользователю с заданным user_id.

    Args:
        user_id (int): Идентификатор пользователя (Telegram user_id).
        session (AsyncSession): Асинхронная сессия для работы с базой данных.

    Returns:
        list[UserFile]: Список объектов UserFile, загруженных пользователем.
    """
    result = await session.execute(
        select(UserFile)
        .where(UserFile.user_id == user_id)
        .options(selectinload(UserFile.summary))
    )
    return result.scalars().all()


async def save_yandex_token(session: AsyncSession, user_id: int, token: str):
    """
    Асинхронно сохраняет OAuth-токен Яндекса для пользователя по его telegram_id.

    Если пользователь с указанным user_id существует в базе данных, его поле yandex_token будет обновлено.
    Если пользователь не найден, функция не производит никаких изменений.
    В случае ошибки логирует исключение.

    Args:
        session (AsyncSession): Асинхронная сессия SQLAlchemy для работы с базой данных.
        user_id (int): Telegram ID пользователя.
        token (str): OAuth-токен Яндекса, который необходимо сохранить.

    Returns:
        None
    """
    try:
        stmt = (
            update(User)
            .where(User.user_id == user_id)
            .values(yandex_token=token)
        )
        await session.execute(stmt)
        await session.commit()
    except Exception as ex:
        logger.error("Error during saving yandex token to database: %s", str(ex))
        return


async def get_yandex_token(session: AsyncSession, user_id: int) -> str | None:
    """
    Асинхронно получает OAuth-токен Яндекса пользователя по его telegram_id.

    Выполняет запрос к базе данных для поиска пользователя с заданным user_id и возвращает его токен.
    Если пользователь не найден или токен отсутствует, возвращает None.
    В случае ошибки логирует исключение.

    Args:
        session (AsyncSession): Асинхронная сессия SQLAlchemy для работы с базой данных.
        user_id (int): Telegram ID пользователя.

    Returns:
        Optional[str]: OAuth-токен Яндекса пользователя, либо None, если пользователь не найден или токен отсутствует.
    """
    try:
        stmt = select(User.yandex_token).where(User.user_id == user_id)
        result = await session.execute(stmt)
        token = result.scalar_one_or_none()
        return token
    except Exception as ex:
        logger.error("Error during getting yandex token: %s", str(ex))
        return


async def save_user_if_not_exists(session: AsyncSession, user_id: int):
    """
    Сохраняет пользователя в базу данных, если он ещё не сохранён.

    Args:
        session (AsyncSession): Асинхронная сессия SQLAlchemy.
        user_id (int): Telegram user_id пользователя.

    Returns:
        User: Объект пользователя (новый или существующий).
    """
    try:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(user_id=user_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user
    except Exception as ex:
        logger.error("Error during saving user: %s", str(ex))
        return


async def split_and_save_chunks(user_file: UserFile, full_text: str, session: AsyncSession):
    chunks = split_text_into_semantic_chunks(full_text)
    for idx, chunk_text in enumerate(chunks):
        chunk = FileChunk(file_id=user_file.file_id, chunk_index=idx, content=chunk_text)
        session.add(chunk)
    await session.commit()


async def save_chunk_ai_response(chunk_id: int, ai_response: str, session: AsyncSession):
    stmt = update(FileChunk).where(FileChunk.id == chunk_id).values(ai_response=ai_response, processed=True)
    await session.execute(stmt)
    await session.commit()


async def save_file_summary(file_id: str, summary: str, session: AsyncSession):
    summary_entry = FileSummary(file_id=file_id, summary=summary)
    session.add(summary_entry)
    await session.commit()


async def get_file_chunks(file_id: str, session: AsyncSession):
    result = await session.execute(
        select(FileChunk).where(FileChunk.file_id == file_id).order_by(FileChunk.chunk_index)
    )
    return result.scalars().all()
