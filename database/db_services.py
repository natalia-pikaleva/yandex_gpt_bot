from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from database.models import UserFile, KnowledgeEntry, DialogHistory, User
import numpy as np
from sqlalchemy import select, update
import logging

from external_services.ai_minilm import get_embedding
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
        return user_file.file_id
    except Exception as ex:
        logger.error("Error during saving file to database: %s", str(ex))
        return None


async def save_knowledge_entries(user_id: int, file_id: str,
                                 full_text: str, session: AsyncSession):
    """
    Сохраняет в базу данных фрагменты текста с эмбеддингами для последующего поиска.

    Текст разбивается на параграфы, из каждого формируется запись с эмбеддингом.

    Args:
        user_id (int): Идентификатор пользователя.
        file_id (str): Идентификатор файла, к которому относятся знания.
        full_text (str): Полный текст, извлечённый из файла.
        session (AsyncSession): Асинхронная сессия базы данных.
        """
    try:
        paragraphs = split_text_into_semantic_chunks(full_text)

        for para in paragraphs:
            title = para[:100]

            embedding = await get_embedding(para)
            embedding_list = embedding.tolist()

            entry = KnowledgeEntry(
                user_id=user_id,
                file_id=file_id,
                title=title,
                content=para,
                embedding=embedding_list
            )
            session.add(entry)

        await session.commit()
    except Exception as ex:
        logger.error("Error during saving knowledge entries to database: %s", str(ex))


async def find_relevant_knowledge(question: str, user_id: int, session, file_ids: list):
    """
    Выполняет семантический поиск релевантных фрагментов знаний по вопросу пользователя.

    1. Получает эмбеддинг вопроса.
    2. Загружает все записи знаний пользователя с эмбеддингами.
    3. Вычисляет косинусное сходство между вопросом и каждой записью.
    4. Возвращает топ-5 наиболее релевантных текстов.

    Args:
        question (str): Вопрос пользователя.
        user_id (int): Идентификатор пользователя.
        session (AsyncSession): Асинхронная сессия базы данных.

    Returns:
        list: Список текстовых фрагментов, наиболее релевантных вопросу.
    """
    try:
        # 1. Получаем эмбеддинг вопроса
        question_embedding = await get_embedding(question)

        # 2. Загружаем все записи пользователя с эмбеддингами
        result = await session.execute(
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.user_id == user_id,
                KnowledgeEntry.file_id.in_(file_ids),
                KnowledgeEntry.embedding != None
            )
        )
        entries = result.scalars().all()

        # 3. Вычисляем косинусное сходство
        def cosine_similarity(a, b):
            a = np.array(a)
            b = np.array(b)
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        scored_entries = []
        for entry in entries:
            sim = cosine_similarity(question_embedding, entry.embedding)
            scored_entries.append((sim, entry.content))

        # 4. Сортируем по убыванию сходства и выбираем топ-5
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        top_contents = [content for _, content in scored_entries[:5]]

        return top_contents
    except Exception as ex:
        logger.error("Error during finding relevant knowledge in database: %s", str(ex))


async def save_dialog_history(
        user_id: int,
        question: str,
        answer: str,
        session: AsyncSession,
        session_id: str = None
):
    """
    Сохраняет историю диалога (вопрос и ответ) пользователя в базу данных.

    Args:
        user_id (int): Идентификатор пользователя.
        question (str): Текст вопроса.
        answer (str): Текст ответа.
        session (AsyncSession): Асинхронная сессия базы данных.
        session_id (str, optional): Идентификатор сессии диалога. По умолчанию None.
    """
    try:
        # Сохраняем вопрос
        question_entry = DialogHistory(
            user_id=user_id,
            message_type='question',
            content=question,
            session_id=session_id
        )
        session.add(question_entry)

        # Сохраняем ответ
        answer_entry = DialogHistory(
            user_id=user_id,
            message_type='answer',
            content=answer,
            session_id=session_id
        )
        session.add(answer_entry)

        await session.commit()
    except Exception as ex:
        logger.error("Error during saving dialog history to database: %s", str(ex))


async def delete_dialog_history(user_id: int, session: AsyncSession):
    """
    Удаляет всю историю диалога пользователя из базы данных.

    Args:
        user_id (int): Идентификатор пользователя.
        session (AsyncSession): Асинхронная сессия базы данных.

    Returns:
        bool: False, если удаление прошло успешно, True — если возникла ошибка.
    """
    try:
        await session.execute(delete(DialogHistory).where(DialogHistory.user_id == user_id))
        await session.commit()
        return False
    except Exception as ex:
        logger.error("Error during delete dialog history to database: %s", str(ex))
        return True


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
    try:
        result = await session.execute(select(UserFile).where(UserFile.user_id == user_id))
        user_files = result.scalars().all()
        return user_files
    except Exception as ex:
        logger.error("Error during getting user files: %s", str(ex))
        return


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
