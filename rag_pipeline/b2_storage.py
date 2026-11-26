"""
Backblaze B2 Cloud Storage integration (S3-compatible API via boto3).
Used in cloud/OpenShift deployments for:
1. Storing user-uploaded chat documents (PDF, DOCX, TXT).
2. Syncing the knowledge base (legal, pdd, court, news, cars, chroma) on startup.
"""

import argparse
import logging
import mimetypes
import re
from datetime import datetime, timezone
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

KB_SUBDIRS = ("legal", "pdd", "court", "news", "cars", "chroma")


def _normalize_kb_relative_path(raw_key: str) -> str:
    rel = raw_key.lstrip("/")
    if rel.startswith("kb/"):
        rel = rel[len("kb/"):]
    elif rel.startswith("data/"):
        rel = rel[len("data/"):]
    return rel.lstrip("/")


class B2StorageManager:
    """Client wrapper for Backblaze B2 bucket operations."""

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
            logger.error(f"Failed to initialize Backblaze B2 client: {e}")
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
                logger.info(f"Auto-selected Backblaze B2 bucket: {cls._resolved_bucket}")
                return cls._resolved_bucket
        except Exception as e:
            logger.warning(f"Failed to list Backblaze B2 buckets (set B2_BUCKET_NAME explicitly): {e}")
        return None

    @classmethod
    def upload_bytes(
        cls,
        object_key: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> Optional[str]:
        """Upload raw bytes to Backblaze B2. Returns object_key on success."""
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
            logger.info(f"Uploaded to B2: s3://{bucket}/{object_key} ({len(data)} bytes)")
            return object_key
        except Exception as e:
            logger.error(f"Failed to upload '{object_key}' to B2: {e}")
            return None

    @classmethod
    def download_bytes(cls, object_key: str) -> Optional[bytes]:
        """Download an object from Backblaze B2."""
        client = cls.get_client()
        bucket = cls.get_bucket_name()
        if not client or not bucket:
            return None
        try:
            resp = client.get_object(Bucket=bucket, Key=object_key)
            return resp["Body"].read()
        except Exception as e:
            logger.error(f"Failed to download '{object_key}' from B2: {e}")
            return None

    @classmethod
    def get_presigned_url(cls, object_key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate a temporary presigned download URL for a B2 object."""
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
            logger.warning(f"Failed to generate presigned URL for '{object_key}': {e}")
            return None

    @classmethod
    def upload_user_attachment(
        cls,
        user_email: str,
        chat_id: str,
        filename: str,
        file_bytes: bytes,
    ) -> Optional[str]:
        """Persist a user chat attachment in the Backblaze B2 bucket."""
        safe_email = re.sub(r"[^a-zA-Z0-9_.-]", "_", user_email.lower())
        safe_chat = re.sub(r"[^a-zA-Z0-9_-]", "_", chat_id)
        safe_name = re.sub(r"[^a-zA-Zа-яА-ЯёЁ0-9_.-]", "_", filename)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        key = f"attachments/{safe_email}/{safe_chat}/{ts}_{safe_name}"
        return cls.upload_bytes(key, file_bytes)

    @classmethod
    def _list_objects_by_prefix(cls, client: Any, bucket: str, prefix: str) -> List[Dict[str, Any]]:
        paginator = client.get_paginator("list_objects_v2")
        items: List[Dict[str, Any]] = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            items.extend(page.get("Contents", []))
        return items

    @classmethod
    def sync_kb_from_b2(cls, target_data_dir: Path = DATA_DIR) -> Dict[str, Any]:
        """
        Sync knowledge base files from Backblaze B2 into target_data_dir.
        Supports multiple bucket layouts: 'kb/', 'data/', or root subdirectories ('legal/', 'pdd/', etc.).
        """
        result = {"configured": cls.is_configured(), "prefix": None, "downloaded": 0, "skipped": 0, "errors": 0}
        if not cls.is_configured():
            return result

        client = cls.get_client()
        bucket = cls.get_bucket_name()
        if not client or not bucket:
            result["errors"] += 1
            return result

        try:
            objects = cls._list_objects_by_prefix(client, bucket, "kb/")
            prefix_used = "kb/"

            if not objects:
                data_objs = cls._list_objects_by_prefix(client, bucket, "data/")
                if data_objs:
                    objects = data_objs
                    prefix_used = "data/"

            if not objects:
                root_objs: List[Dict[str, Any]] = []
                for sub in KB_SUBDIRS:
                    root_objs.extend(cls._list_objects_by_prefix(client, bucket, f"{sub}/"))
                if root_objs:
                    objects = root_objs
                    prefix_used = "root"

            result["prefix"] = prefix_used

            for obj in objects:
                key = obj["Key"]
                if key.endswith("/"):
                    continue
                rel_path = _normalize_kb_relative_path(key)
                if not rel_path:
                    continue
                top_dir = rel_path.split("/")[0]
                if top_dir not in KB_SUBDIRS or "/cache/" in rel_path or rel_path.startswith("cache/"):
                    continue

                local_path = target_data_dir / rel_path
                if local_path.exists() and local_path.stat().st_size == obj.get("Size", -1):
                    result["skipped"] += 1
                    continue
                local_path.parent.mkdir(parents=True, exist_ok=True)
                client.download_file(bucket, key, str(local_path))
                result["downloaded"] += 1

            logger.info(f"B2 KB sync finished: {result}")
        except Exception as e:
            logger.warning(f"Failed to sync KB from Backblaze B2: {e}")
            result["errors"] += 1
        return result

    @classmethod
    def upload_kb_to_b2(cls, source_data_dir: Path = DATA_DIR) -> Dict[str, Any]:
        """Upload local knowledge base files (data/{legal,pdd,court,news,cars,chroma}) to B2 under kb/."""
        result = {"uploaded": 0, "errors": 0, "files": []}
        if not cls.is_configured():
            logger.error("Backblaze B2 is not configured (check B2_ENDPOINT, B2_KEY_ID, B2_APPLICATION_KEY).")
            return result

        client = cls.get_client()
        bucket = cls.get_bucket_name()
        if not client or not bucket:
            logger.error("Backblaze B2 bucket not found.")
            return result

        for sub in KB_SUBDIRS:
            sub_dir = source_data_dir / sub
            if not sub_dir.exists():
                continue
            for file_path in sub_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                rel = file_path.relative_to(source_data_dir).as_posix()
                if "/cache/" in rel or rel.startswith("cache/"):
                    continue
                b2_key = f"kb/{rel}"
                try:
                    client.upload_file(str(file_path), bucket, b2_key)
                    result["uploaded"] += 1
                    result["files"].append(b2_key)
                except Exception as e:
                    logger.error(f"Failed to upload {file_path} to {b2_key}: {e}")
                    result["errors"] += 1
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backblaze B2 Knowledge Base Sync")
    parser.add_argument("--upload-kb", action="store_true", help="Upload local data/ KB to B2 kb/ prefix")
    parser.add_argument("--sync-kb", action="store_true", help="Download B2 KB into local data/")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.upload_kb:
        print(B2StorageManager.upload_kb_to_b2())
    elif args.sync_kb:
        print(B2StorageManager.sync_kb_from_b2())
    else:
        print({"configured": B2StorageManager.is_configured(), "bucket": B2StorageManager.get_bucket_name()})
