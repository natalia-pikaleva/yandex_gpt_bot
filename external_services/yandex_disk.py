import logging
import yadisk
import os

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


async def download_file(remote_path, local_path, user_token):
    """
    Скачивает файл с Яндекс.Диска на локальный диск.

    Args:
        disk_path (str): Путь к файлу на Яндекс.Диске.
        local_file (str): Путь для сохранения файла локально.

    Returns:
        bool: True, если скачивание прошло успешно, иначе False.
    """
    y = yadisk.AsyncClient(token=user_token)
    try:
        async with y:
            await y.download(remote_path, local_path)
        return True
    except Exception as ex:
        logger.error("Error during download file from Yandex.disk: %s", str(ex))
        return False


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
