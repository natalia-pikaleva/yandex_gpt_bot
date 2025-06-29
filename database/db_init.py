from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config import DATABASE_URL
from database.models import Base
import logging

logger = logging.getLogger(__name__)


# Создаем асинхронный движок
engine = create_async_engine(DATABASE_URL, future=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    """
    Инициализирует базу данных.

    Создает все таблицы, описанные в метаданных Base, если они еще не существуют.

    Использует асинхронное соединение с базой данных.

    Returns:
        None
    """
    async with engine.begin() as conn:
        # Создаем все таблицы, если их нет
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables successfully created")


async def get_session():
    """
    Асинхронный генератор сессии базы данных.

    Позволяет получать сессию для работы с БД в обработчиках и автоматически закрывает ее после использования.

    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy.
    """
    async with async_session() as session:
        yield session
