from sentence_transformers import SentenceTransformer

# Путь для локального кеша модели
local_dir = "./models/all-MiniLM-L6-v2"

model = SentenceTransformer(local_dir)


async def get_embedding(text: str):
    """
    Получает эмбеддинг (векторное представление) для заданного текста.

    Args:
        text (str): Входной текст для преобразования в эмбеддинг.

    Returns:
        list: Векторное представление текста.
    """
    embeddings = model.encode(text, batch_size=16, show_progress_bar=True)
    return embeddings
