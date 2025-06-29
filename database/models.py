from sqlalchemy import String, Integer, BigInteger, Column, DateTime, func, Text, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True) # Telegram user_id
    yandex_token = Column(String(255), nullable=True, default=None)
    notification_sent = Column(Boolean, default=False)

    # Связь с файлами пользователя
    files = relationship("UserFile", back_populates="user", cascade="all, delete-orphan")


class UserFile(Base):
    __tablename__ = "user_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(255), unique=True, nullable=False)  # Telegram file_id
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    title = Column(String(512), nullable=True)  # Оригинальное имя файла
    yandex_path = Column(String(1024), nullable=False)  # Путь на Яндекс.Диске
    upload_date = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="files")
    knowledge_entries = relationship("KnowledgeEntry", back_populates="user_file")


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    file_id = Column(String(255), ForeignKey("user_files.file_id"), nullable=False)
    title = Column(String(512), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    embedding = Column(JSON, nullable=True)

    user_file = relationship("UserFile", back_populates="knowledge_entries")


class DialogHistory(Base):
    __tablename__ = 'dialog_history'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    message_type = Column(String(10), nullable=False)  # 'question' или 'answer'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    session_id = Column(String(36), nullable=True)  # если нужно группировать сессии (UUID в виде строки)
