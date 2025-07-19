import os
from fastapi import FastAPI, Request
import httpx
import requests
import logging

from config import YANDEX_CLIENT_ID, YANDEX_CLIENT_SECRET, BOT_TOKEN
from database.db_init import get_session
from database.models import User
from sqlalchemy import select

app = FastAPI()
logger = logging.getLogger(__name__)


def notify_user_via_http(user_id: int, text: str):
    """
    Отправляет уведомление пользователю в Telegram через Bot API.

    Args:
        user_id (int): Telegram user_id получателя сообщения.
        text (str): Текст уведомления, который будет отправлен пользователю.

    Returns:
        None
    """
    logger.info("Start notify_user_via_http")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": user_id, "text": text}
    requests.post(url, data=data)


@app.get("/yandex_oauth_callback")
async def yandex_oauth_callback(request: Request):
    """
    Обрабатывает OAuth-редирект от Яндекс.Диска и сохраняет токен пользователя.

    Получает авторизационный код из запроса, обменивает его на access_token Яндекс.Диска,
    сохраняет токен в базе данных по Telegram user_id (state) и отправляет пользователю
    уведомление о завершении авторизации через Telegram Bot API.

    Query Parameters:
        code (str): Авторизационный код, полученный от Яндекс OAuth (обязательный).
        state (str): Telegram user_id, переданный в процессе авторизации (обязательный).

    Returns:
        dict: Результат операции с access_token и state, либо описание ошибки.
    """
    code = request.query_params.get("code")
    state = request.query_params.get("state")  # сюда можно передавать user_id Telegram
    if not code:
        return {"error": "No code in request"}

    # Меняем code на access_token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth.yandex.ru/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": YANDEX_CLIENT_ID,
                "client_secret": YANDEX_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code != 200:
        return {"error": "Failed to get token", "details": resp.text}
    token_data = resp.json()
    access_token = token_data.get("access_token")

    # Проверяем, есть ли уже токен в базе
    async for session in get_session():
        result = await session.execute(
            select(User).where(User.user_id == int(state))
        )
        user = result.scalar_one_or_none()
        if not user:
            # Создать пользователя, если его нет
            user = User(user_id=int(state), yandex_token=access_token, notification_sent=True)
            session.add(user)
            await session.commit()
            notify_user_via_http(
                int(state),
                "Авторизация завершена! Теперь введите путь к файлу на вашем Яндекс.Диске:"
            )
        token = user.yandex_token
        if not token or not token.strip():
            user.yandex_token = access_token
            user.notification_sent = True
            await session.commit()
            notify_user_via_http(
                int(state),
                "Авторизация завершена! Теперь введите путь к файлу на вашем Яндекс.Диске:"
            )
        elif not user.notification_sent:
            user.notification_sent = True
            await session.commit()
            notify_user_via_http(
                int(state),
                "Авторизация завершена! Теперь введите путь к файлу на вашем Яндекс.Диске:"
            )
        else:
            logger.info(f"Notification already sent for user {state}, skipping.")

    return {"result": "OK", "access_token": access_token, "state": state}
