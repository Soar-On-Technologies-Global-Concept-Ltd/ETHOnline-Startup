"""Private evidence storage. Files reach the two parties only through short-lived signed URLs."""
import asyncio
import hashlib
import hmac
import time
from pathlib import Path

from app.core.config import get_settings


def _sign(key: str, exp: int) -> str:
    secret = get_settings().signing_secret.get_secret_value().encode()
    return hmac.new(secret, f"{key}:{exp}".encode(), hashlib.sha256).hexdigest()


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root)

    async def put(self, key: str, data: bytes, mime: str) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        return f"local://{key}"

    async def signed_url(self, uri: str) -> str:
        key = uri.removeprefix("local://")
        exp = int(time.time()) + get_settings().signed_url_ttl_seconds
        return f"{get_settings().public_base_url.rstrip('/')}/v1/files/{key}?exp={exp}&sig={_sign(key, exp)}"

    def read_verified(self, key: str, exp: int, sig: str) -> bytes | None:
        if exp < time.time() or not hmac.compare_digest(sig, _sign(key, exp)):
            return None
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents or not path.exists():
            return None
        return path.read_bytes()


class S3Storage:
    def __init__(self):
        import boto3
        s = get_settings()
        self.bucket = s.storage_bucket
        self.client = boto3.client("s3", endpoint_url=s.storage_endpoint or None, region_name=s.storage_region,
                                   aws_access_key_id=s.storage_access_key.get_secret_value() if s.storage_access_key else None,
                                   aws_secret_access_key=s.storage_secret_key.get_secret_value() if s.storage_secret_key else None)

    async def put(self, key: str, data: bytes, mime: str) -> str:
        await asyncio.to_thread(self.client.put_object, Bucket=self.bucket, Key=key, Body=data, ContentType=mime)
        return f"s3://{self.bucket}/{key}"

    async def signed_url(self, uri: str) -> str:
        key = uri.split("/", 3)[3]
        return await asyncio.to_thread(self.client.generate_presigned_url, "get_object",
                                       Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=get_settings().signed_url_ttl_seconds)


_storage = None


def storage():
    global _storage
    if _storage is None:
        s = get_settings()
        _storage = S3Storage() if s.storage_backend == "s3" else LocalStorage(s.local_storage_dir)
    return _storage
