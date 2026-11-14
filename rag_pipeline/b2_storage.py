"""
Интеграция с Backblaze B2 Cloud Storage (S3-совместимый API через boto3).
Используется на Render Free Tier (без постоянного диска) для:
1. Хранения документов, прикрепляемых пользователями в чате (PDF, DOCX, TXT).
2. Синхронизации базы знаний (data/legal, data/pdd, data/chroma и т.д.) при холодном старте.
"""

import argparse
import logging
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rag_pipeline.config import (
    B2_APPLICATION_KEY,
    B2_BUCKET_NAME,
    B2_ENDPOINT,
    B2_KEY_ID,
    B2_REGION,
    DATA_DIR,
)

logger = logging.getLogger("b2_storage")


class B2StorageManager:
    """Клиент для работы с бакетом Backblaze B2"""

    _client = None
    _resolved_bucket: Optional[str] = None

    @classmethod
    def is_configured(cls) -> bool:
        return bool(B2_ENDPOINT and B2_KEY_ID and B2_APPLICATION_KEY)

    @classmethod
    def get_client(cls):
        if not cls.is_configured():
            return None
        if cls._client is not None:
            return cls._client
        try:
            import boto3
            from botocore.config import Config

            cls._client = boto3.client(
                "s3",
                endpoint_url=B2_ENDPOINT,
                aws_access_key_id=B2_KEY_ID,
                aws_secret_access_key=B2_APPLICATION_KEY,
                region_name=B2_REGION or "eu-central-003",
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            )
            return cls._client
        except Exception as e:
            logger.error(f"Ошибка инициализации клиента Backblaze B2: {e}")
            return None

    @classmethod
    def get_bucket_name(cls) -> Optional[str]:
        if B2_BUCKET_NAME:
            return B2_BUCKET_NAME
        if cls._resolved_bucket:
            return cls._resolved_bucket
        client = cls.get_client()
        if not client:
            return None
        try:
            resp = client.list_buckets()
            buckets = resp.get("Buckets", [])
            if buckets:
                cls._resolved_bucket = buckets[0]["Name"]
                logger.info(f"Автоматически выбран бакет Backblaze B2: {cls._resolved_bucket}")
                return cls._resolved_bucket
        except Exception as e:
            logger.warning(f"Не удалось получить список бакетов B2 (задайте B2_BUCKET_NAME): {e}")
        return None

    @classmethod
    def upload_bytes(
        cls,
        object_key: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> Optional[str]:
        """Загрузка байтов в Backblaze B2. Возвращает object_key при успехе."""
        client = cls.get_client()
        bucket = cls.get_bucket_name()
        if not client or not bucket:
            return None

        if not content_type:
            guessed, _ = mimetypes.guess_type(object_key)
            content_type = guessed or "application/octet-stream"

        try:
            client.put_object(
                Bucket=bucket,
                Key=object_key,
                Body=data,
                ContentType=content_type,
            )
            logger.info(f"Файл загружен в B2: s3://{bucket}/{object_key} ({len(data)} байт)")
            return object_key
        except Exception as e:
            logger.error(f"Ошибка загрузки объекта '{object_key}' в B2: {e}")
            return None

    @classmethod
    def download_bytes(cls, object_key: str) -> Optional[bytes]:
        """Скачивание объекта из Backblaze B2."""
        client = cls.get_client()
        bucket = cls.get_bucket_name()
        if not client or not bucket:
            return None
        try:
            resp = client.get_object(Bucket=bucket, Key=object_key)
            return resp["Body"].read()
        except Exception as e:
            logger.error(f"Ошибка скачивания '{object_key}' из B2: {e}")
            return None

    @classmethod
    def get_presigned_url(cls, object_key: str, expires_in: int = 3600) -> Optional[str]:
        """Генерация временной ссылки на скачивание файла из B2."""
        client = cls.get_client()
        bucket = cls.get_bucket_name()
        if not client or not bucket:
            return None
        try:
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": object_key},
                ExpiresIn=expires_in,
            )
        except Exception as e:
            logger.warning(f"Ошибка генерации presigned URL для '{object_key}': {e}")
            return None

    @classmethod
    def upload_user_attachment(
        cls,
        user_email: str,
        chat_id: str,
        filename: str,
        file_bytes: bytes,
    ) -> Optional[str]:
        """Сохранение прикрепленного файла пользователя в бакет B2."""
        safe_email = re.sub(r"[^a-zA-Z0-9_.-]", "_", user_email.lower())
        safe_chat = re.sub(r"[^a-zA-Z0-9_-]", "_", chat_id)
        safe_name = re.sub(r"[^a-zA-Zа-яА-Я0-9_.-]", "_", filename)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        key = f"attachments/{safe_email}/{safe_chat}/{ts}_{safe_name}"
        return cls.upload_bytes(key, file_bytes)

    @classmethod
    def sync_kb_from_b2(cls, target_data_dir: Path = DATA_DIR) -> Dict[str, Any]:
        """
        Синхронизация файлов базы знаний (префикс kb/) из Backblaze B2 на локальный эфемерный диск
        при запуске на Render Free Tier (если локальные файлы отсутствуют).
        """
        result = {"configured": cls.is_configured(), "downloaded": 0, "skipped": 0, "errors": 0}
        if not cls.is_configured():
            return result

        client = cls.get_client()
        bucket = cls.get_bucket_name()
        if not client or not bucket:
            return result

        try:
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket, Prefix="kb/"):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    rel_path = key[len("kb/"):].lstrip("/")
                    if not rel_path or rel_path.endswith("/"):
                        continue
                    local_path = target_data_dir / rel_path
                    if local_path.exists() and local_path.stat().st_size == obj.get("Size", -1):
                        result["skipped"] += 1
                        continue
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    client.download_file(bucket, key, str(local_path))
                    result["downloaded"] += 1
            logger.info(f"Синхронизация БЗ из B2 завершена: {result}")
        except Exception as e:
            logger.warning(f"Ошибка синхронизации БЗ из Backblaze B2: {e}")
            result["errors"] += 1
        return result

    @classmethod
    def upload_kb_to_b2(cls, source_data_dir: Path = DATA_DIR) -> Dict[str, Any]:
        """Загрузка локальной базы знаний (data/{legal,pdd,court,news,cars,chroma}) в B2 под префикс kb/."""
        result = {"uploaded": 0, "errors": 0, "files": []}
        if not cls.is_configured():
            logger.error("Backblaze B2 не настроен (проверьте B2_ENDPOINT, B2_KEY_ID, B2_APPLICATION_KEY).")
            return result

        client = cls.get_client()
        bucket = cls.get_bucket_name()
        if not client or not bucket:
            logger.error("Не найден бакет Backblaze B2.")
            return result

        target_subdirs = ["legal", "pdd", "court", "news", "cars", "chroma"]
        for sub in target_subdirs:
            sub_dir = source_data_dir / sub
            if not sub_dir.exists():
                continue
            for file_path in sub_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                # Пропускаем тяжелые бинарники ChromaDB sqlite при желании или загружаем все
                rel = file_path.relative_to(source_data_dir).as_posix()
                b2_key = f"kb/{rel}"
                try:
                    client.upload_file(str(file_path), bucket, b2_key)
                    result["uploaded"] += 1
                    result["files"].append(b2_key)
                except Exception as e:
                    logger.error(f"Ошибка загрузки {file_path} в {b2_key}: {e}")
                    result["errors"] += 1
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backblaze B2 Knowledge Base Sync")
    parser.add_argument("--upload-kb", action="store_true", help="Upload local data/ KB to B2 kb/ prefix")
    parser.add_argument("--sync-kb", action="store_true", help="Download B2 kb/ prefix to local data/")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.upload_kb:
        print(B2StorageManager.upload_kb_to_b2())
    elif args.sync_kb:
        print(B2StorageManager.sync_kb_from_b2())
    else:
        print({"configured": B2StorageManager.is_configured(), "bucket": B2StorageManager.get_bucket_name()})
