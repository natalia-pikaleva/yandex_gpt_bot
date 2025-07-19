import logging
import aiohttp
import yadisk
import os
import re
from urllib.parse import unquote, parse_qs, urlparse

from config import YANDEX_TOKEN

logger = logging.getLogger(__name__)

y = yadisk.AsyncClient(token=YANDEX_TOKEN)


async def check_auth():
    """
    Проверяет валидность токена доступа к Яндекс.Диску.

    Использует асинхронный клиент yadisk для проверки токена.

    Returns:
        bool: True, если токен валиден, иначе False.
    """
    try:
        async with yadisk.AsyncClient(token=YANDEX_TOKEN) as client:
            return await client.check_token()
    except Exception as ex:
        logger.error("Error during checking auth to Yandex.disk: %s", str(ex))


async def create_user_folder(user_id: int):
    """
    Создаёт папку на Яндекс.Диске для пользователя, если она ещё не существует.

    Args:
        user_id (int): Идентификатор пользователя.

    Returns:
        str: Путь к папке пользователя на Яндекс.Диске.
    """
    path = f"/{user_id}"
    exists = await y.exists(path)
    if not exists:
        await y.mkdir(path)
    return path


async def upload_user_file(user_id: int, local_file_path: str, file_id: str):
    """
    Загружает файл на Яндекс.Диск в папку пользователя.

    Имя файла формируется как file_{file_id} с сохранением расширения исходного файла.

    Args:
        user_id (int): Идентификатор пользователя.
        local_file_path (str): Путь к локальному файлу для загрузки.
        file_id (str): Идентификатор файла (используется для имени на диске).

    Returns:
        str: Путь к загруженному файлу на Яндекс.Диске.
    """
    try:
        user_folder = await create_user_folder(user_id)
        ext = os.path.splitext(local_file_path)[1]
        remote_path = f"{user_folder}/file_{file_id}{ext}"
        await y.upload(local_file_path, remote_path, overwrite=True)
        return remote_path
    except Exception as ex:
        logger.error("Error during upload user file to Yandex.disk: %s", str(ex))


async def download_public_link(public_url: str, downloads_dir: str) -> str | None:
    """
    Скачивает файл по публичной ссылке Яндекс.Диска.
    Возвращает локальный путь к файлу или None.
    """
    os.makedirs(downloads_dir, exist_ok=True)
    api_url = f"https://cloud-api.yandex.net/v1/disk/public/resources/download"
    params = {"public_key": public_url}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params, timeout=60) as resp:
                resp.raise_for_status()
                data = await resp.json()
                href = data.get("href")
                if not href:
                    logger.error(f"href for download not found in public link API response! data={data!r}")
                    return None
            # Получаем имя файла из href
            url = urlparse(href)
            qs = parse_qs(url.query)
            filename = unquote(qs["filename"][0]) if "filename" in qs else "downloaded_file"
            filename = os.path.basename(filename)
            local_path = os.path.join(downloads_dir, filename)
            # Скачиваем файл по прямой ссылке
            async with session.get(href, timeout=600) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    while True:
                        chunk = await r.content.read(1024 * 64)
                        if not chunk:
                            break
                        f.write(chunk)
        logger.info(f"Файл скачан и сохранён: '{local_path}', размер {os.path.getsize(local_path)} байт")
        return local_path
    except Exception as e:
        logger.error(f"Error while downloading file from public link: {e}")
        return None


def is_yadisk_public_link(s: str) -> bool:
    return bool(re.match(r'https?://disk\.yandex\.(ru|com)/[id]/[\w-]+', s.strip()))


async def download_file(remote_path_or_link, downloads_dir_or_path, user_token=None):
    """
    Скачивает файл с Яндекс.Диска по пути (private API, через OAuth) или по публичной ссылке.
    Для приватных — downloads_dir_or_path = точный путь (downloads/file.docx).
    Для публичных — это просто папка, там появится файл с оригинальным именем и расширением!
    """
    if is_yadisk_public_link(remote_path_or_link):
        return await download_public_link(remote_path_or_link, downloads_dir_or_path)
    else:
        # Здесь downloads_dir_or_path — это ИМЯ локального файла
        y = yadisk.AsyncClient(token=user_token)
        try:
            async with y:
                await y.download(remote_path_or_link, downloads_dir_or_path)
            return downloads_dir_or_path  # путь к файлу, для единообразия
        except Exception as ex:
            logger.error("Error during download file from Yandex.disk: %s", str(ex))
            return None


async def list_files(path="/"):
    """
    Получает список файлов и папок в указанной директории на Яндекс.Диске.

    Args:
        path (str, optional): Путь к директории на Яндекс.Диске. По умолчанию корень "/".

    Returns:
        list: Список словарей с информацией о файлах и папках:
              - name: имя объекта
              - type: "folder" или "file"
              - size: размер в байтах (если применимо)
              - path: полный путь объекта
    """
    files = []
    try:
        async for item in y.listdir(path):
            files.append({
                "name": item.name,
                "type": "folder" if item.is_dir else "file",
                "size": item.size,
                "path": item.path,
            })
    except Exception as ex:
        logger.error("Error during getting list files from Yandex.disk: %s", str(ex))
    return files


async def yandex_disk_delete(path: str):
    """
    Удаляет файл с Яндекс.Диска по указанному пути.

    Args:
        path (str): Путь к файлу на Яндекс.Диске, который необходимо удалить.

    Raises:
        Exception: Пробрасывает исключение, если удаление не удалось.

    Логи:
        При успешном удалении записывает информационное сообщение в лог.
        При ошибке удаление логирует ошибку и пробрасывает исключение дальше.
    """
    try:
        await y.remove(path, permanently=True)
        logger.info(f"Файл {path} удалён с Яндекс.Диска")
    except Exception as e:
        logger.error(f"Ошибка при удалении файла {path} с Яндекс.Диска: {e}")
        raise


async def download_prompt_from_yandex(local_prompt_path="prompt.txt", remote_prompt_path="/prompt.txt"):
    """
    Скачивает файл с Яндекс.Диска по корневому пути (например, /prompt.txt).
    Если файл уже есть локально, он перезаписывается.

    Args:
        local_prompt_path (str): Куда сохранить локально ('prompt.txt').
        remote_prompt_path (str): Где искать на Яндекс.Диске ('/prompt.txt').
    Returns:
        bool: True если скачано ОК, иначе False.
    """
    async with yadisk.AsyncClient(token=YANDEX_TOKEN) as y:
        try:
            await y.download(remote_prompt_path, local_prompt_path)
            return True
        except yadisk.exceptions.PathNotFoundError:
            logger.error(f"Файл {remote_prompt_path} не найден на Яндекс.Диске.")
            return False
        except Exception as ex:
            logger.error(f"Не удалось скачать промт с Яндекс.Диска: {ex}")
            return False
