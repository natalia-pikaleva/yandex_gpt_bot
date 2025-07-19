from sqlalchemy import (String, Integer, BigInteger, Column, DateTime, func,
                        Text, ForeignKey, JSON, Boolean, SmallInteger)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    yandex_token = Column(String(255), nullable=True, default=None)
    notification_sent = Column(Boolean, default=False)
    files = relationship("UserFile", back_populates="user", cascade="all, delete-orphan")

class UserFile(Base):
    __tablename__ = "user_files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(255), unique=True, nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    title = Column(String(512), nullable=True)
    yandex_path = Column(String(1024), nullable=False)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="files")
    chunks = relationship("FileChunk", back_populates="user_file", cascade="all, delete-orphan")
    summary = relationship("FileSummary", back_populates="user_file", uselist=False)

class FileChunk(Base):
    __tablename__ = "file_chunks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(255), ForeignKey("user_files.file_id"), nullable=False)
    chunk_index = Column(SmallInteger, nullable=False)  # Порядковый номер чанка
    content = Column(Text, nullable=False)  # Текст части документа
    ai_response = Column(Text, nullable=True)  # Ответ YandexGPT по этой части
    processed = Column(Boolean, default=False)  # Чанк обработан AI
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user_file = relationship("UserFile", back_populates="chunks")

class FileSummary(Base):
    __tablename__ = "file_summaries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(255), ForeignKey("user_files.file_id"), unique=True, nullable=False)
    summary = Column(Text, nullable=True)  # Итоговое резюме по всему документу
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_file = relationship("UserFile", back_populates="summary")
