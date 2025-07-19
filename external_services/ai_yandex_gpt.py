import aiohttp
from config import YANDEX_GPT_API_KEY, FOLDER_ID

YANDEX_GPT_API_URL = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'

async def yandex_gpt_request(
    messages: list,
    model: str = "yandexgpt-lite",
    temperature: float = 0.6,
    max_tokens: int = 2000,
    stream: bool = False,
) -> dict:
    """
    Асинхронно отправляет запрос к YandexGPT и возвращает ответ
    :param api_key: API-KEY сервисного аккаунта
    :param folder_id: Идентификатор каталога (FOLDER_ID)
    :param messages: Список сообщений [{"role": "system"|"user"|"assistant", "text": ...}]
    :param model: Имя модели
    :param temperature: Температура сэмплирования (креативность)
    :param max_tokens: Макс. размер ответа
    :param stream: включить ли потоковый вывод (стрим)
    :return: dict — весь JSON-ответ Yandex GPT
    """
    url = YANDEX_GPT_API_URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}",
        "x-folder-id": FOLDER_ID,
    }
    payload = {
        "modelUri": f"gpt://{FOLDER_ID}/{model}",
        "completionOptions": {
            "stream": stream,
            "temperature": temperature,
            "maxTokens": str(max_tokens),
        },
        "messages": messages,
    }
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
        async with session.post(url, headers=headers, json=payload) as response:
            response.raise_for_status()
            return await response.json()
