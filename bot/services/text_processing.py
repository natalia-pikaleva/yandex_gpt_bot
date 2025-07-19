import os
import fitz
import docx
import logging
from nltk.tokenize import sent_tokenize
import pandas as pd
from striprtf.striprtf import rtf_to_text

logger = logging.getLogger(__name__)


def extract_text_from_file(filename):
    """
    Извлекает текстовое содержимое из файла различных форматов.

    Поддерживаемые форматы: .txt, .pdf, .docx, .rtf, .xlsx
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

        elif ext == '.xlsx':
            xls = pd.ExcelFile(filename)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                text += df.to_string() + "\n"

        elif ext == '.rtf':
            with open(filename, 'r', encoding='utf-8') as f:
                text = rtf_to_text(f.read())

        else:
            text = "Формат файла не поддерживается."

        return text

    except Exception as ex:
        logger.error("Error during extracting text from file: %s", str(ex))
        return "Формат файла не поддерживается"


def split_text_into_semantic_chunks(text: str, max_chunk_size: int = 1500) -> list[str]:
    """
    Разбивает текст на смысловые чанки, стараясь сохранять логические части: сначала по абзацам, потом по предложениям.

    Args:
        text (str): Исходный текст.
        max_chunk_size (int): Максимальная длина блока в символах.

    Returns:
        list[str]: Список текстовых блоков.
    """
    # 1. Сначала делим по двойному переносу строк (большие логические блоки)
    blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
    chunks = []
    for block in blocks:
        # Если блок меньше лимита — добавляем целиком
        if len(block) <= max_chunk_size:
            chunks.append(block)
        else:
            # Если больше лимита — делим по предложениям
            sentences = sent_tokenize(block)
            curr_chunk = ""
            for sent in sentences:
                if len(curr_chunk) + len(sent) + 1 <= max_chunk_size:
                    curr_chunk += (" " if curr_chunk else "") + sent
                else:
                    if curr_chunk:
                        chunks.append(curr_chunk.strip())
                    curr_chunk = sent
            if curr_chunk:
                chunks.append(curr_chunk.strip())
    return chunks
