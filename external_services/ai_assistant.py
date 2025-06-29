from config import AUTHORIZATION_KEY, SERTIFICAT_PATH
import httpx
import requests
import uuid


async def get_access_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Authorization": f"Basic {AUTHORIZATION_KEY}",
        "RqUID": str(uuid.uuid4())
    }
    data = {
        "scope": "GIGACHAT_API_PERS"
    }
    async with httpx.AsyncClient(verify=SERTIFICAT_PATH) as client:
        response = await client.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()["access_token"]


async def generate_answer(access_token, question, context):
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": "Ты — помощник, который отвечает на вопросы."},
            {"role": "user", "content": f"Контекст: {context}\nВопрос: {question}"}
        ],
        "stream": False
    }
    async with httpx.AsyncClient(verify=SERTIFICAT_PATH) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
