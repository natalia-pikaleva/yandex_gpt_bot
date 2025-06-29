import os
import fitz
import docx
import pypandoc
import ebooklib
from bs4 import BeautifulSoup
from lxml import etree
import logging
from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)


def extract_text_from_fb2(filename):
    """
    Извлекает текстовое содержимое из файла формата FB2 (FictionBook 2.0).

    Парсит XML-структуру файла, извлекает все текстовые узлы внутри тегов <body>
    и объединяет их в один текстовый блок.

    Args:
        filename (str): Путь к файлу формата FB2.

    Returns:
        str: Извлечённый текст из файла. В случае ошибки возвращает пустую строку.
    """
    try:
        tree = etree.parse(filename)
        # Извлекаем все текстовые узлы внутри тега <body>
        bodies = tree.xpath('//body')
        texts = []
        for body in bodies:
            # Конвертируем содержимое в строку с текстом
            texts.append(' '.join(body.itertext()))
        return '\n\n'.join(texts)
    except Exception as e:
        logger.error(f"Ошибка при извлечении текста из fb2: {e}")
        return ""


def extract_text_from_epub(filename):
    """
    Извлекает текстовое содержимое из файла формата EPUB.

    Читает все документы внутри EPUB, парсит HTML-контент и объединяет текст.

    Args:
        filename (str): Путь к файлу формата EPUB.

    Returns:
        str: Извлечённый текст из файла. В случае ошибки возвращает пустую строку.
    """
    try:
        book = ebooklib.epub.read_epub(filename)
        texts = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            texts.append(soup.get_text())
        return '\n\n'.join(texts)
    except Exception as e:
        logger.error(f"Ошибка при извлечении текста из epub: {e}")
        return ""


def extract_text_from_file(filename):
    """
    Извлекает текстовое содержимое из файла различных форматов.

    Поддерживаемые форматы: .txt, .pdf, .docx, .rtf, .epub, .fb2.
    Если формат не поддерживается, возвращается соответствующее сообщение.

    Args:
        filename (str): Путь к файлу.

    Returns:
        str: Извлечённый текст из файла либо сообщение об ошибке.
    """
    try:
        ext = os.path.splitext(filename)[1].lower()
        text = ""

        if ext == '.txt':
            with open(filename, 'r', encoding='utf-8') as f:
                text = f.read()

        elif ext == '.pdf':
            doc = fitz.open(filename)
            for page in doc:
                text += page.get_text()

        elif ext == '.docx':
            doc = docx.Document(filename)
            for para in doc.paragraphs:
                text += para.text + "\n"

        elif ext == '.rtf':
            # Конвертируем rtf в plain text через pypandoc
            text = pypandoc.convert_file(filename, 'plain')

        elif ext == '.epub':
            text = extract_text_from_epub(filename)

        elif ext == '.fb2':
            text = extract_text_from_fb2(filename)

        else:
            text = "Формат файла не поддерживается."

        return text

    except Exception as ex:
        logger.error("Error during extracting text from file: %s", str(ex))
        return "Ошибка при извлечении текста из файла."


def split_text_into_semantic_chunks(text: str, max_chunk_size: int = 1500) -> list[str]:
    """
    Разбивает текст на смысловые части (абзацы/параграфы), не разрывая предложения.

    Алгоритм:
    1. Токенизирует текст на предложения.
    2. Объединяет предложения в блоки длиной не более max_chunk_size символов.

    Args:
        text (str): Исходный текст.
        max_chunk_size (int): Максимальная длина блока в символах.

    Returns:
        list[str]: Список текстовых блоков (смысловых частей).
    """
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
            current_chunk += (" " if current_chunk else "") + sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks
