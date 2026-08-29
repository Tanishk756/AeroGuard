"""Stage IM3-A S3-compatible enterprise cold storage adapter and bucket metadata health service."""

import hashlib
import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class S3ArchiveStoreError(RuntimeError):
    """Raised when an S3 cold storage operation fails."""


class S3ObjectNotFoundError(S3ArchiveStoreError):
    """Raised when the requested archive object key does not exist in S3."""


class S3ObjectArchiveStore:
    """Production S3-compatible cold storage adapter supporting AWS S3, MinIO, Ceph, and LocalStack.
    Implements the IncidentArchiveStore protocol.
    """

    def __init__(
        self,
        bucket_name: str | None = None,
        endpoint_url: str | None = None,
        region_name: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        sse_algorithm: str | None = None,
        sse_kms_key_id: str | None = None,
        s3_client: Any | None = None,
    ):
        settings = get_settings()
        self.bucket_name = bucket_name or settings.s3_bucket
        self.endpoint_url = endpoint_url or settings.s3_endpoint_url
        self.region_name = region_name or settings.s3_region
        self.access_key_id = access_key_id or settings.s3_access_key_id
        self.secret_access_key = secret_access_key or settings.s3_secret_access_key
        self.sse_algorithm = sse_algorithm or settings.s3_sse_algorithm
        self.sse_kms_key_id = sse_kms_key_id or settings.s3_sse_kms_key_id

        if s3_client is not None:
            self.s3_client = s3_client
        else:
            client_kwargs: dict[str, Any] = {
                "service_name": "s3",
                "region_name": self.region_name,
                "config": Config(signature_version="s3v4", retries={"max_attempts": 3}),
            }
            if self.endpoint_url:
                client_kwargs["endpoint_url"] = self.endpoint_url
            if self.access_key_id and self.secret_access_key:
                client_kwargs["aws_access_key_id"] = self.access_key_id
                client_kwargs["aws_secret_access_key"] = self.secret_access_key

            self.s3_client = boto3.client(**client_kwargs)

    def _get_object_key(self, archive_number: str, archive_format: str = "JSON") -> str:
        clean_num = archive_number.strip().replace("/", "_").replace("\\", "_")
        ext = "pdf" if archive_format.upper() == "PDF" else "json"
        return f"archives/{clean_num}.{ext}"

    def archive(self, archive_number: str, payload_bytes: bytes, archive_format: str) -> str:
        object_key = self._get_object_key(archive_number, archive_format)
        sha256_checksum = hashlib.sha256(payload_bytes).hexdigest()
        content_type = "application/pdf" if archive_format.upper() == "PDF" else "application/json"

        put_kwargs: dict[str, Any] = {
            "Bucket": self.bucket_name,
            "Key": object_key,
            "Body": payload_bytes,
            "ContentType": content_type,
            "Metadata": {
                "sha256-checksum": sha256_checksum,
                "archive-number": archive_number,
                "archive-format": archive_format.upper(),
            },
        }

        if self.sse_algorithm:
            put_kwargs["ServerSideEncryption"] = self.sse_algorithm
            if self.sse_algorithm == "aws:kms" and self.sse_kms_key_id:
                put_kwargs["SSEKMSKeyId"] = self.sse_kms_key_id

        try:
            self.s3_client.put_object(**put_kwargs)
            return f"s3://{self.bucket_name}/{object_key}"
        except (BotoCoreError, ClientError) as exc:
            logger.error(f"S3 archive upload failed for key {object_key}: {exc}")
            raise S3ArchiveStoreError(f"Failed to upload archive object to S3: {exc}") from exc

    def retrieve(self, archive_number: str) -> bytes:
        for ext in ["json", "pdf"]:
            object_key = f"archives/{archive_number.strip()}.{ext}"
            try:
                res = self.s3_client.get_object(Bucket=self.bucket_name, Key=object_key)
                return res["Body"].read()
            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code")
                if error_code in ("NoSuchKey", "404", "NotFound"):
                    continue
                raise S3ArchiveStoreError(f"Failed to retrieve S3 object {object_key}: {exc}") from exc
            except BotoCoreError as exc:
                raise S3ArchiveStoreError(f"S3 client error retrieving {object_key}: {exc}") from exc

        raise S3ObjectNotFoundError(f"Archive payload for {archive_number} not found in S3 bucket {self.bucket_name}")

    def verify(self, archive_number: str, expected_sha256: str) -> bool:
        try:
            payload_bytes = self.retrieve(archive_number)
            computed_sha = hashlib.sha256(payload_bytes).hexdigest()
            return computed_sha.lower() == expected_sha256.lower()
        except Exception as exc:
            logger.warning(f"S3 archive verification failed for {archive_number}: {exc}")
            return False

    def exists(self, archive_number: str) -> bool:
        for ext in ["json", "pdf"]:
            object_key = f"archives/{archive_number.strip()}.{ext}"
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
                return True
            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code")
                if error_code in ("NoSuchKey", "404", "NotFound"):
                    continue
                logger.warning(f"S3 head_object error checking {object_key}: {exc}")
                return False
            except BotoCoreError:
                return False
        return False

    def delete(self, archive_number: str) -> bool:
        deleted_any = False
        for ext in ["json", "pdf"]:
            object_key = f"archives/{archive_number.strip()}.{ext}"
            if self.exists(archive_number):
                try:
                    self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
                    deleted_any = True
                except (BotoCoreError, ClientError) as exc:
                    logger.error(f"S3 delete_object failed for {object_key}: {exc}")
                    raise S3ArchiveStoreError(f"Failed to delete S3 object {object_key}: {exc}") from exc
        return deleted_any

    def generate_presigned_url(self, archive_number: str, expires_in_seconds: int = 900) -> str:
        for ext in ["json", "pdf"]:
            object_key = f"archives/{archive_number.strip()}.{ext}"
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
                url = self.s3_client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": self.bucket_name, "Key": object_key},
                    ExpiresIn=expires_in_seconds,
                )
                return url
            except ClientError:
                continue
        raise S3ObjectNotFoundError(f"Cannot generate presigned URL. Archive {archive_number} not found in S3.")

    def check_health(self) -> dict[str, Any]:
        """Perform lightweight, non-mutating bucket health check."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return {
                "provider": "S3",
                "status": "HEALTHY",
                "bucket_name": self.bucket_name,
                "region": self.region_name,
                "endpoint_url": self.endpoint_url or "aws-default",
                "sse_algorithm": self.sse_algorithm,
                "reachable": True,
            }
        except Exception as exc:
            return {
                "provider": "S3",
                "status": "UNHEALTHY",
                "bucket_name": self.bucket_name,
                "region": self.region_name,
                "endpoint_url": self.endpoint_url or "aws-default",
                "sse_algorithm": self.sse_algorithm,
                "reachable": False,
                "error": str(exc),
            }
